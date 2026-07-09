"""
CardioGuard AI - Real PTB-XL Kafka ECG Producer

Replays locally downloaded PTB-XL 100 Hz, 12-lead ECG records
through Apache Kafka as a real-time telemetry stream.

Expected Kafka payload per timestep:

{
    "timestamp": "...",
    "patient_id": "P001",
    "leads": [12 floats]
}

Important architecture rule:
----------------------------
The producer streams ECG measurements only.

It does NOT send:
- diagnosis
- confidence
- is_emergency

Those fields must come from the backend inference pipeline so the
frontend does not confuse a dataset label with a model prediction.

Supported local layouts:
------------------------

data/ptb-xl/
    ptbxl_database.csv
    scp_statements.csv

    # Official-style:
    records100/
        01000/
            01000_lr.hea
            01000_lr.dat

    # Also supported:
    records/
        01000/
            01000_lr.hea
            01000_lr.dat

    # Also supported:
    01000_lr.hea
    01000_lr.dat

The producer recursively discovers all *_lr.hea files.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import random
import signal
import sys
import time

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    # pyrefly: ignore [missing-import]
    import wfdb
except ImportError as exc:
    raise ImportError(
        "wfdb is required. Install it with:\n"
        "python -m pip install wfdb"
    ) from exc

try:
    # pyrefly: ignore [missing-import]
    from confluent_kafka import Producer
except ImportError:
    Producer = None


# ============================================================
# Logging
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)

logger.setLevel(logging.INFO)
logger.propagate = False


# ============================================================
# Constants
# ============================================================

PTBXL_SUPERCLASSES = {
    "NORM",
    "MI",
    "STTC",
    "CD",
    "HYP",
}

ABNORMAL_CLASSES = {
    "MI",
    "STTC",
    "CD",
    "HYP",
}

CLASS_DISPLAY_NAMES = {
    "NORM": "Normal ECG",
    "MI": "Myocardial Infarction",
    "STTC": "ST/T Change",
    "CD": "Conduction Disturbance",
    "HYP": "Hypertrophy",
}

# This is only used for selecting a replay scenario.
# It is NOT sent as an AI prediction.
#
# MI is treated as the main emergency-demo candidate because your
# UI needs an emergency path. The actual consumer/model must still
# determine its own is_emergency output.
EMERGENCY_DEMO_CLASSES = {
    "MI",
}


# ============================================================
# Live ECG Producer
# ============================================================

class LiveECGProducer:
    """
    Replays real PTB-XL ECG records into Kafka at approximately 100 Hz.

    Main guarantees:
    - only locally existing waveform pairs are selected
    - .hea + .dat pairs are validated
    - real 12-lead PTB-XL signals are used
    - records are streamed continuously
    - Kafka payload stays compatible with the existing consumer
    - dataset labels are logged, not presented as model predictions
    """

    def __init__(
        self,
        broker_url: str = "localhost:9092",
        topic_name: str = "live_ecg_stream",
        dataset_dir: str | Path = "data/ptb-xl",
        sample_rate: int = 100,
        mode: str = "auto",
        normal_probability: float = 0.60,
        emergency_probability: float = 0.12,
        record_gap_seconds: float = 0.25,
        log_level: int = logging.INFO,
    ) -> None:

        logger.setLevel(log_level)

        if Producer is None:
            raise ImportError(
                "confluent-kafka is not installed.\n"
                "Install it with:\n"
                "python -m pip install confluent-kafka"
            )

        self.broker_url = broker_url
        self.topic_name = topic_name

        self.dataset_dir = Path(dataset_dir)

        if not self.dataset_dir.is_absolute():
            self.dataset_dir = (
                Path.cwd() / self.dataset_dir
            ).resolve()

        self.sample_rate = int(sample_rate)

        if self.sample_rate <= 0:
            raise ValueError(
                "sample_rate must be greater than zero."
            )

        self.sample_interval = 1.0 / self.sample_rate

        self.mode = mode.lower().strip()

        allowed_modes = {
            "auto",
            "normal",
            "abnormal",
            "emergency",
            "cycle",
        }

        if self.mode not in allowed_modes:
            raise ValueError(
                f"Unsupported mode '{mode}'. "
                f"Choose one of: {sorted(allowed_modes)}"
            )

        self.normal_probability = float(normal_probability)
        self.emergency_probability = float(emergency_probability)
        self.record_gap_seconds = max(
            0.0,
            float(record_gap_seconds)
        )

        if not 0.0 <= self.normal_probability <= 1.0:
            raise ValueError(
                "normal_probability must be between 0 and 1."
            )

        if not 0.0 <= self.emergency_probability <= 1.0:
            raise ValueError(
                "emergency_probability must be between 0 and 1."
            )

        self.is_running = False

        self.database: pd.DataFrame = pd.DataFrame()
        self.scp_statements: pd.DataFrame = pd.DataFrame()

        self.normal_records: pd.DataFrame = pd.DataFrame()
        self.abnormal_records: pd.DataFrame = pd.DataFrame()
        self.emergency_records: pd.DataFrame = pd.DataFrame()

        self.class_records: Dict[str, pd.DataFrame] = {}

        self._cycle_classes = [
            "NORM",
            "STTC",
            "CD",
            "HYP",
            "MI",
        ]
        self._cycle_index = 0

        self._delivery_error_count = 0
        self._delivered_count = 0

        # ----------------------------------------------------
        # Kafka Producer
        # ----------------------------------------------------

        logger.info(
            "Initializing Kafka Producer connecting to '%s'...",
            self.broker_url,
        )

        self.producer = Producer(
            {
                "bootstrap.servers": self.broker_url,
                "client.id": "cardioguard_ptbxl_replay",

                # Small batching helps throughput without creating
                # the huge UI delay seen previously.
                "linger.ms": 5,

                # Keep retries enabled for temporary broker issues.
                "retries": 5,

                # Avoid extremely long invisible queue buildup.
                "message.timeout.ms": 10000,

                # Compression is useful for free hosting / bandwidth.
                "compression.type": "snappy",
            }
        )

        logger.info(
            "Kafka Producer successfully initialized."
        )

        # ----------------------------------------------------
        # PTB-XL metadata
        # ----------------------------------------------------

        self._load_ptbxl_metadata()


    # ========================================================
    # Metadata helpers
    # ========================================================

    @staticmethod
    def _parse_scp_codes(value: Any) -> Dict[str, float]:
        """
        Safely parse the scp_codes field from ptbxl_database.csv.
        """

        if isinstance(value, dict):
            return value

        if pd.isna(value):
            return {}

        try:
            parsed = ast.literal_eval(str(value))

            if isinstance(parsed, dict):
                return parsed

        except (
            ValueError,
            SyntaxError,
            TypeError,
        ):
            pass

        return {}


    @staticmethod
    def _extract_ecg_id_from_stem(
        stem: str
    ) -> Optional[int]:
        """
        Convert:
            01000_lr -> 1000
            12312_lr -> 12312
        """

        cleaned = stem

        if cleaned.endswith("_lr"):
            cleaned = cleaned[:-3]

        try:
            return int(cleaned)
        except ValueError:
            return None


    def _discover_local_records(
        self
    ) -> Dict[int, Path]:
        """
        Recursively find complete PTB-XL waveform pairs.

        A record is accepted only when both:
            *_lr.hea
            *_lr.dat

        physically exist.
        """

        logger.info(
            "Scanning recursively for local PTB-XL waveforms..."
        )

        local_records: Dict[int, Path] = {}

        hea_files = list(
            self.dataset_dir.rglob("*_lr.hea")
        )

        logger.info(
            "Found %d candidate .hea files.",
            len(hea_files),
        )

        for hea_path in hea_files:

            record_path = hea_path.with_suffix("")
            dat_path = record_path.with_suffix(".dat")

            if not dat_path.exists():
                logger.warning(
                    "Skipping incomplete waveform pair: %s "
                    "(matching .dat missing)",
                    hea_path,
                )
                continue

            ecg_id = self._extract_ecg_id_from_stem(
                hea_path.stem
            )

            if ecg_id is None:
                logger.warning(
                    "Could not extract ECG ID from: %s",
                    hea_path.name,
                )
                continue

            local_records[ecg_id] = record_path.resolve()

        return local_records


    def _build_superclass_mapper(
        self
    ):
        """
        Build a function mapping SCP codes to PTB-XL
        diagnostic superclasses.
        """

        statements = self.scp_statements

        def get_superclasses(
            scp_codes: Dict[str, float]
        ) -> List[str]:

            classes = set()

            for code in scp_codes.keys():

                if code not in statements.index:
                    continue

                row = statements.loc[code]

                # Defensive handling in case duplicate index rows exist.
                if isinstance(row, pd.DataFrame):
                    rows = [
                        item
                        for _, item in row.iterrows()
                    ]
                else:
                    rows = [row]

                for statement_row in rows:

                    diagnostic = statement_row.get(
                        "diagnostic",
                        0,
                    )

                    try:
                        is_diagnostic = int(
                            float(diagnostic)
                        ) == 1
                    except (
                        ValueError,
                        TypeError,
                    ):
                        is_diagnostic = False

                    if not is_diagnostic:
                        continue

                    diagnostic_class = statement_row.get(
                        "diagnostic_class"
                    )

                    if pd.isna(diagnostic_class):
                        continue

                    diagnostic_class = str(
                        diagnostic_class
                    ).strip()

                    if diagnostic_class in PTBXL_SUPERCLASSES:
                        classes.add(
                            diagnostic_class
                        )

            return sorted(classes)

        return get_superclasses


    def _load_ptbxl_metadata(
        self
    ) -> None:
        """
        Load PTB-XL metadata and retain only records whose
        waveform files physically exist locally.
        """

        database_path = (
            self.dataset_dir / "ptbxl_database.csv"
        )

        statements_path = (
            self.dataset_dir / "scp_statements.csv"
        )

        if not database_path.exists():
            raise FileNotFoundError(
                "PTB-XL database file not found:\n"
                f"{database_path}"
            )

        if not statements_path.exists():
            raise FileNotFoundError(
                "PTB-XL SCP statements file not found:\n"
                f"{statements_path}"
            )

        logger.info(
            "Loading PTB-XL metadata from: %s",
            self.dataset_dir,
        )

        database = pd.read_csv(
            database_path,
            index_col="ecg_id",
        )

        statements = pd.read_csv(
            statements_path,
            index_col=0,
        )

        # Normalize statement index.
        statements.index = statements.index.map(
            str
        )

        database["scp_codes"] = database[
            "scp_codes"
        ].apply(
            self._parse_scp_codes
        )

        self.scp_statements = statements

        # ----------------------------------------------------
        # Discover only actual local files
        # ----------------------------------------------------

        local_records = self._discover_local_records()

        if not local_records:
            raise FileNotFoundError(
                "\nNo complete local PTB-XL waveform pairs found.\n\n"
                "Expected files such as:\n"
                "01000_lr.hea\n"
                "01000_lr.dat\n\n"
                f"somewhere under:\n{self.dataset_dir}\n"
            )

        logger.info(
            "Found %d complete local PTB-XL records.",
            len(local_records),
        )

        # ----------------------------------------------------
        # Match local waveform IDs to metadata IDs
        # ----------------------------------------------------

        available_ids = [
            ecg_id
            for ecg_id in local_records.keys()
            if ecg_id in database.index
        ]

        missing_metadata_ids = [
            ecg_id
            for ecg_id in local_records.keys()
            if ecg_id not in database.index
        ]

        if missing_metadata_ids:
            logger.warning(
                "%d local waveform IDs were not found "
                "in ptbxl_database.csv.",
                len(missing_metadata_ids),
            )

        if not available_ids:
            raise RuntimeError(
                "Waveform files were found, but none of their "
                "ECG IDs match ptbxl_database.csv."
            )

        database = database.loc[
            available_ids
        ].copy()

        # Store actual discovered local path.
        database["_local_record_path"] = [
            str(local_records[int(ecg_id)])
            for ecg_id in database.index
        ]

        # ----------------------------------------------------
        # Map SCP codes to diagnostic superclasses
        # ----------------------------------------------------

        superclass_mapper = (
            self._build_superclass_mapper()
        )

        database["_superclasses"] = database[
            "scp_codes"
        ].apply(
            superclass_mapper
        )

        # Keep a human-readable reference label.
        database["_reference_label"] = database[
            "_superclasses"
        ].apply(
            self._format_reference_label
        )

        self.database = database

        # ----------------------------------------------------
        # Build record pools
        # ----------------------------------------------------

        self.normal_records = database[
            database["_superclasses"].apply(
                lambda classes:
                    "NORM" in classes
            )
        ].copy()

        self.abnormal_records = database[
            database["_superclasses"].apply(
                lambda classes:
                    any(
                        cls in ABNORMAL_CLASSES
                        for cls in classes
                    )
            )
        ].copy()

        self.emergency_records = database[
            database["_superclasses"].apply(
                lambda classes:
                    any(
                        cls in EMERGENCY_DEMO_CLASSES
                        for cls in classes
                    )
            )
        ].copy()

        self.class_records = {}

        for class_name in self._cycle_classes:
            self.class_records[class_name] = database[
                database["_superclasses"].apply(
                    lambda classes,
                    target=class_name:
                        target in classes
                )
            ].copy()

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        logger.info(
            "PTB-XL local subset loaded successfully."
        )

        logger.info(
            "Local records available: %d",
            len(self.database),
        )

        logger.info(
            "Normal records available: %d",
            len(self.normal_records),
        )

        logger.info(
            "Abnormal records available: %d",
            len(self.abnormal_records),
        )

        logger.info(
            "Emergency MI candidates available: %d",
            len(self.emergency_records),
        )

        for class_name in self._cycle_classes:
            logger.info(
                "%s records available: %d",
                class_name,
                len(
                    self.class_records.get(
                        class_name,
                        pd.DataFrame(),
                    )
                ),
            )

        # Show first few records for debugging.
        preview_count = min(
            10,
            len(self.database),
        )

        logger.info(
            "First %d discovered local records:",
            preview_count,
        )

        for ecg_id, row in self.database.head(
            preview_count
        ).iterrows():

            logger.info(
                "  ECG %s | classes=%s | path=%s",
                ecg_id,
                row["_superclasses"],
                row["_local_record_path"],
            )


    @staticmethod
    def _format_reference_label(
        classes: Sequence[str]
    ) -> str:

        if not classes:
            return "Unknown"

        names = [
            CLASS_DISPLAY_NAMES.get(
                cls,
                cls,
            )
            for cls in classes
        ]

        return " + ".join(names)


    # ========================================================
    # Record selection
    # ========================================================

    @staticmethod
    def _random_row(
        frame: pd.DataFrame
    ) -> Tuple[int, pd.Series]:

        if frame.empty:
            raise ValueError(
                "Cannot select from an empty record pool."
            )

        random_position = random.randrange(
            len(frame)
        )

        ecg_id = int(
            frame.index[random_position]
        )

        row = frame.iloc[
            random_position
        ]

        return ecg_id, row


    def _select_auto_record(
        self
    ) -> Tuple[int, pd.Series, str]:
        """
        Auto mode behavior:

        - mostly normal records
        - some abnormal records
        - occasional MI emergency-demo candidate

        This controls replay variety only.
        The AI consumer still makes the real prediction.
        """

        roll = random.random()

        # Occasional emergency candidate.
        if (
            roll < self.emergency_probability
            and not self.emergency_records.empty
        ):
            ecg_id, row = self._random_row(
                self.emergency_records
            )
            return (
                ecg_id,
                row,
                "emergency_candidate",
            )

        # Mostly normal.
        if (
            roll
            < (
                self.emergency_probability
                + self.normal_probability
            )
            and not self.normal_records.empty
        ):
            ecg_id, row = self._random_row(
                self.normal_records
            )
            return (
                ecg_id,
                row,
                "normal",
            )

        # Otherwise abnormal.
        if not self.abnormal_records.empty:
            ecg_id, row = self._random_row(
                self.abnormal_records
            )
            return (
                ecg_id,
                row,
                "abnormal",
            )

        # Fallback.
        ecg_id, row = self._random_row(
            self.database
        )

        return (
            ecg_id,
            row,
            "fallback",
        )


    def _select_cycle_record(
        self
    ) -> Tuple[int, pd.Series, str]:
        """
        Cycle through available diagnostic classes.

        Empty classes are skipped automatically.
        """

        attempts = len(
            self._cycle_classes
        )

        for _ in range(attempts):

            class_name = self._cycle_classes[
                self._cycle_index
                % len(self._cycle_classes)
            ]

            self._cycle_index += 1

            frame = self.class_records.get(
                class_name,
                pd.DataFrame(),
            )

            if frame.empty:
                continue

            ecg_id, row = self._random_row(
                frame
            )

            return (
                ecg_id,
                row,
                f"cycle_{class_name}",
            )

        # No requested class available.
        ecg_id, row = self._random_row(
            self.database
        )

        return (
            ecg_id,
            row,
            "cycle_fallback",
        )


    def _select_record(
        self
    ) -> Tuple[int, pd.Series, str]:

        if self.mode == "auto":
            return self._select_auto_record()

        if self.mode == "cycle":
            return self._select_cycle_record()

        if self.mode == "normal":
            if not self.normal_records.empty:
                ecg_id, row = self._random_row(
                    self.normal_records
                )
                return ecg_id, row, "normal"

        if self.mode == "abnormal":
            if not self.abnormal_records.empty:
                ecg_id, row = self._random_row(
                    self.abnormal_records
                )
                return ecg_id, row, "abnormal"

        if self.mode == "emergency":
            if not self.emergency_records.empty:
                ecg_id, row = self._random_row(
                    self.emergency_records
                )
                return (
                    ecg_id,
                    row,
                    "emergency_candidate",
                )

            logger.warning(
                "Emergency mode requested, but no local MI "
                "candidate records are available. Falling back."
            )

        ecg_id, row = self._random_row(
            self.database
        )

        return (
            ecg_id,
            row,
            "fallback",
        )


    # ========================================================
    # WFDB loading
    # ========================================================

    def _load_record(
        self,
        row: pd.Series,
    ) -> np.ndarray:
        """
        Load one real PTB-XL record from the discovered local path.

        Returns:
            ndarray shaped approximately (1000, 12)
        """

        local_path = row.get(
            "_local_record_path"
        )

        if not local_path:
            raise ValueError(
                "Selected PTB-XL row has no local record path."
            )

        record_path = Path(
            str(local_path)
        )

        hea_path = record_path.with_suffix(
            ".hea"
        )

        dat_path = record_path.with_suffix(
            ".dat"
        )

        if not hea_path.exists():
            raise FileNotFoundError(
                f"Missing header file: {hea_path}"
            )

        if not dat_path.exists():
            raise FileNotFoundError(
                f"Missing signal file: {dat_path}"
            )

        logger.info(
            "Loading real PTB-XL waveform: %s",
            record_path,
        )

        record = wfdb.rdrecord(
            str(record_path)
        )

        signal_data = record.p_signal

        if signal_data is None:
            raise ValueError(
                "WFDB record contains no physical signal: "
                f"{record_path}"
            )

        ecg = np.asarray(
            signal_data,
            dtype=np.float32,
        )

        if ecg.ndim != 2:
            raise ValueError(
                f"Expected 2D ECG array, got shape {ecg.shape}"
            )

        # ----------------------------------------------------
        # Lead validation
        # ----------------------------------------------------

        if ecg.shape[1] == 12:
            pass

        elif ecg.shape[0] == 12:
            # Defensive transpose.
            ecg = ecg.T

        else:
            raise ValueError(
                "Expected 12-lead ECG. "
                f"Received shape: {ecg.shape}"
            )

        # ----------------------------------------------------
        # Handle NaN / infinity safely
        # ----------------------------------------------------

        ecg = np.nan_to_num(
            ecg,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        # ----------------------------------------------------
        # Sample-rate validation
        # ----------------------------------------------------

        record_fs = float(
            record.fs
        )

        if abs(
            record_fs - self.sample_rate
        ) > 0.01:

            logger.warning(
                "Record sample rate is %.2f Hz, producer configured "
                "for %d Hz.",
                record_fs,
                self.sample_rate,
            )

            ecg = self._resample_signal(
                ecg,
                source_rate=record_fs,
                target_rate=float(
                    self.sample_rate
                ),
            )

        logger.info(
            "Loaded ECG shape=%s | fs=%s Hz",
            ecg.shape,
            record_fs,
        )

        return ecg


    @staticmethod
    def _resample_signal(
        ecg: np.ndarray,
        source_rate: float,
        target_rate: float,
    ) -> np.ndarray:
        """
        Lightweight interpolation-based resampling.

        Usually unnecessary for records100 because those are 100 Hz.
        """

        if source_rate <= 0:
            raise ValueError(
                "source_rate must be positive."
            )

        if target_rate <= 0:
            raise ValueError(
                "target_rate must be positive."
            )

        old_length = ecg.shape[0]

        duration_seconds = (
            old_length / source_rate
        )

        new_length = max(
            1,
            int(
                round(
                    duration_seconds
                    * target_rate
                )
            ),
        )

        old_x = np.linspace(
            0.0,
            duration_seconds,
            num=old_length,
            endpoint=False,
        )

        new_x = np.linspace(
            0.0,
            duration_seconds,
            num=new_length,
            endpoint=False,
        )

        output = np.empty(
            (
                new_length,
                ecg.shape[1],
            ),
            dtype=np.float32,
        )

        for lead_index in range(
            ecg.shape[1]
        ):
            output[:, lead_index] = np.interp(
                new_x,
                old_x,
                ecg[:, lead_index],
            )

        return output


    # ========================================================
    # Kafka helpers
    # ========================================================

    def _delivery_callback(
        self,
        err: Optional[Any],
        msg: Any,
    ) -> None:

        if err is not None:
            self._delivery_error_count += 1

            # Avoid printing thousands of identical errors.
            if (
                self._delivery_error_count <= 5
                or self._delivery_error_count % 100 == 0
            ):
                logger.error(
                    "Kafka delivery failed "
                    "(error count=%d): %s",
                    self._delivery_error_count,
                    err,
                )

            return

        self._delivered_count += 1


    def _produce_payload(
        self,
        payload: Dict[str, Any],
        patient_id: str,
    ) -> None:
        """
        Produce one telemetry sample with queue-full handling.
        """

        encoded_value = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode(
            "utf-8"
        )

        encoded_key = patient_id.encode(
            "utf-8"
        )

        while self.is_running:
            try:
                self.producer.produce(
                    topic=self.topic_name,
                    key=encoded_key,
                    value=encoded_value,
                    callback=self._delivery_callback,
                )

                # Serve delivery callbacks.
                self.producer.poll(0)

                return

            except BufferError:
                logger.warning(
                    "Kafka producer queue full. "
                    "Waiting briefly..."
                )

                self.producer.poll(
                    0.1
                )


    # ========================================================
    # Real-time streaming
    # ========================================================

    def _stream_record(
        self,
        ecg: np.ndarray,
        patient_id: str,
    ) -> None:
        """
        Stream one ECG record sample-by-sample.

        Timing uses a monotonic deadline instead of repeatedly doing
        time.sleep(0.01), which reduces accumulated drift.
        """

        next_deadline = time.perf_counter()

        total_samples = ecg.shape[0]

        for sample_index in range(
            total_samples
        ):

            if not self.is_running:
                break

            leads = ecg[
                sample_index
            ].astype(
                float
            ).tolist()

            # Keep payload compatible with your current consumer.
            payload = {
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),

                "patient_id": patient_id,

                "leads": [
                    round(
                        float(value),
                        6,
                    )
                    for value in leads
                ],
            }

            self._produce_payload(
                payload=payload,
                patient_id=patient_id,
            )

            # ------------------------------------------------
            # Real-time pacing
            # ------------------------------------------------

            next_deadline += (
                self.sample_interval
            )

            remaining = (
                next_deadline
                - time.perf_counter()
            )

            if remaining > 0:
                time.sleep(
                    remaining
                )
            else:
                # If temporarily behind, reset deadline when
                # drift becomes significant rather than creating
                # a huge catch-up burst.
                if remaining < -0.5:
                    next_deadline = (
                        time.perf_counter()
                    )


    # ========================================================
    # Public API
    # ========================================================

    def stop_streaming(
        self
    ) -> None:

        logger.info(
            "Stop signal received."
        )

        self.is_running = False


    def start_streaming(
        self,
        patient_id: str = "P001",
    ) -> None:
        """
        Continuously select local real PTB-XL records and replay them.
        """

        if not patient_id:
            raise ValueError(
                "patient_id cannot be empty."
            )

        logger.info(
            "Starting real PTB-XL ECG replay."
        )

        logger.info(
            "Patient ID: %s",
            patient_id,
        )

        logger.info(
            "Kafka topic: %s",
            self.topic_name,
        )

        logger.info(
            "Mode: %s",
            self.mode,
        )

        logger.info(
            "Sample rate: %d Hz",
            self.sample_rate,
        )

        logger.info(
            "Press Ctrl+C to stop."
        )

        self.is_running = True

        try:
            while self.is_running:

                # --------------------------------------------
                # Select a local ECG
                # --------------------------------------------

                (
                    ecg_id,
                    row,
                    replay_scenario,
                ) = self._select_record()

                classes = row.get(
                    "_superclasses",
                    [],
                )

                reference_label = row.get(
                    "_reference_label",
                    "Unknown",
                )

                local_path = row.get(
                    "_local_record_path",
                    "Unknown",
                )

                logger.info(
                    "=" * 72
                )

                logger.info(
                    "Selected PTB-XL ECG ID: %s",
                    ecg_id,
                )

                logger.info(
                    "Replay scenario: %s",
                    replay_scenario,
                )

                logger.info(
                    "PTB-XL reference classes: %s",
                    classes,
                )

                logger.info(
                    "PTB-XL reference label: %s",
                    reference_label,
                )

                logger.info(
                    "Local path: %s",
                    local_path,
                )

                # Very important wording:
                # This is a dataset label, not the AI result.
                if replay_scenario == "emergency_candidate":
                    logger.warning(
                        "Emergency DEMO candidate selected. "
                        "The backend model must still independently "
                        "predict diagnosis and is_emergency."
                    )

                # --------------------------------------------
                # Load waveform
                # --------------------------------------------

                try:
                    ecg = self._load_record(
                        row
                    )

                except Exception as exc:
                    logger.error(
                        "Failed to load ECG %s: %s. "
                        "Skipping this record.",
                        ecg_id,
                        exc,
                        exc_info=True,
                    )

                    time.sleep(
                        0.25
                    )

                    continue

                # --------------------------------------------
                # Stream waveform
                # --------------------------------------------

                started_at = time.perf_counter()

                self._stream_record(
                    ecg=ecg,
                    patient_id=patient_id,
                )

                elapsed = (
                    time.perf_counter()
                    - started_at
                )

                logger.info(
                    "Completed ECG %s replay: "
                    "%d samples in %.2f seconds.",
                    ecg_id,
                    ecg.shape[0],
                    elapsed,
                )

                if (
                    self.is_running
                    and self.record_gap_seconds > 0
                ):
                    time.sleep(
                        self.record_gap_seconds
                    )

        except KeyboardInterrupt:
            logger.warning(
                "KeyboardInterrupt detected. "
                "Stopping PTB-XL replay..."
            )

            self.is_running = False

        except Exception as exc:
            logger.error(
                "Unexpected streaming error: %s",
                exc,
                exc_info=True,
            )

            raise

        finally:
            self.is_running = False

            logger.info(
                "Flushing Kafka messages..."
            )

            remaining = self.producer.flush(
                timeout=10
            )

            if remaining:
                logger.warning(
                    "%d Kafka messages remained undelivered.",
                    remaining,
                )

            logger.info(
                "Producer shut down cleanly."
            )


# ============================================================
# Environment helpers
# ============================================================

def _env_float(
    name: str,
    default: float,
) -> float:

    raw_value = os.getenv(
        name
    )

    if raw_value is None:
        return default

    try:
        return float(
            raw_value
        )
    except ValueError:
        logger.warning(
            "Invalid float for %s=%r. Using default %s.",
            name,
            raw_value,
            default,
        )
        return default


def _env_int(
    name: str,
    default: int,
) -> int:

    raw_value = os.getenv(
        name
    )

    if raw_value is None:
        return default

    try:
        return int(
            raw_value
        )
    except ValueError:
        logger.warning(
            "Invalid integer for %s=%r. Using default %s.",
            name,
            raw_value,
            default,
        )
        return default


# ============================================================
# Main
# ============================================================

def main() -> None:

    broker_url = os.getenv(
        "KAFKA_BROKER_URL",
        "localhost:9092",
    )

    topic_name = os.getenv(
        "KAFKA_ECG_TOPIC",
        "live_ecg_stream",
    )

    dataset_dir = os.getenv(
        "PTBXL_DATASET_DIR",
        "data/ptb-xl",
    )

    patient_id = os.getenv(
        "ECG_PATIENT_ID",
        "P001",
    )

    mode = os.getenv(
        "ECG_REPLAY_MODE",
        "auto",
    )

    sample_rate = _env_int(
        "ECG_SAMPLE_RATE",
        100,
    )

    normal_probability = _env_float(
        "ECG_NORMAL_PROBABILITY",
        0.60,
    )

    emergency_probability = _env_float(
        "ECG_EMERGENCY_PROBABILITY",
        0.12,
    )

    record_gap_seconds = _env_float(
        "ECG_RECORD_GAP_SECONDS",
        0.25,
    )

    producer = LiveECGProducer(
        broker_url=broker_url,
        topic_name=topic_name,
        dataset_dir=dataset_dir,
        sample_rate=sample_rate,
        mode=mode,
        normal_probability=normal_probability,
        emergency_probability=emergency_probability,
        record_gap_seconds=record_gap_seconds,
    )

    # --------------------------------------------------------
    # Graceful Ctrl+C / termination handling
    # --------------------------------------------------------

    def handle_shutdown(
        signum,
        frame,
    ):
        logger.warning(
            "Shutdown signal %s received.",
            signum,
        )

        producer.stop_streaming()

    try:
        signal.signal(
            signal.SIGINT,
            handle_shutdown,
        )

        if hasattr(
            signal,
            "SIGTERM",
        ):
            signal.signal(
                signal.SIGTERM,
                handle_shutdown,
            )

    except Exception:
        # Some environments restrict signal registration.
        pass

    producer.start_streaming(
        patient_id=patient_id
    )


if __name__ == "__main__":
    main()