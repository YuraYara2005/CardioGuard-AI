import json
import logging
import time

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


try:
    # pyrefly: ignore [missing-import]
    from confluent_kafka import (
        Consumer,
        KafkaError,
    )

except ImportError:
    Consumer = None
    KafkaError = None


# pyrefly: ignore [missing-import]
from backend.api.websocket_manager import (
    ecg_websocket_manager,
)


logger = logging.getLogger(__name__)


# ============================================================
# Streaming GenAI Feature Flag
# ============================================================
#
# Set to True ONLY if you want the Kafka consumer to
# automatically trigger Gemini report generation for each
# detected anomaly window.
#
# WARNING: With Gemini free-tier, each anomaly window that
# reaches inference fires TWO Gemini requests (doctor report +
# patient report). At 100 Hz / 1000-sample windows, one patient
# producing continuous anomalies generates 2 requests every
# ~10 seconds, exhausting the free-tier quota within minutes.
#
# The deduplication cooldown below provides a secondary safety
# net, but the primary protection is this flag being False.
#
ENABLE_STREAMING_GENAI: bool = False


# ============================================================
# Streaming GenAI Deduplication Cooldown
# ============================================================
#
# Even when ENABLE_STREAMING_GENAI is True, a report will only
# be generated for a given (patient_id, diagnosis) pair at most
# once per REPORT_COOLDOWN_SECONDS.
#
# Emergency state transitions (non-emergency → emergency) are
# allowed to bypass the cooldown ONCE per transition.
# Repeated emergency frames while is_emergency stays True do
# NOT bypass the cooldown.
#
REPORT_COOLDOWN_SECONDS: int = 1800  # 30 minutes


class ECGConsumer:
    """
    Consumes live streaming 12-lead ECG data from Kafka.

    Responsibilities:

    1. Receive raw 12-lead ECG timesteps
    2. Broadcast live telemetry to frontend WebSocket clients
    3. Accumulate 1000 timesteps per patient
    4. Run ECG inference
    5. Broadcast inference results
    6. Optionally generate reports for detected anomalies
       (controlled by ENABLE_STREAMING_GENAI flag and cooldown)
    """

    def __init__(
        self,
        predictor: Any,
        report_generator: Any,
        broker_url: str = "localhost:9092",
        topic_name: str = "live_ecg_stream",
        group_id: str = "cardioguard_inference_group",
        log_level: int = logging.INFO
    ):

        if not logger.handlers:
            handler = logging.StreamHandler()

            formatter = logging.Formatter(
                "%(asctime)s - "
                "%(name)s - "
                "%(levelname)s - "
                "%(message)s"
            )

            handler.setFormatter(
                formatter
            )

            logger.addHandler(
                handler
            )

        logger.setLevel(
            log_level
        )


        if Consumer is None:
            logger.critical(
                "confluent-kafka is not installed."
            )

            raise ImportError(
                "Cannot initialize consumer because "
                "'confluent-kafka' is not installed."
            )


        self.predictor = predictor

        self.report_generator = (
            report_generator
        )

        self.broker_url = broker_url

        self.topic_name = topic_name


        # ====================================================
        # Patient Buffers
        # ====================================================

        self.patient_buffers: Dict[
            str,
            List[List[float]]
        ] = defaultdict(list)


        # PTB-XL model:
        # 1000 timesteps = 10 seconds @ 100 Hz

        self.inference_window_size = 1000

        self.is_running = False


        # ====================================================
        # GenAI Deduplication State
        # ====================================================
        #
        # Tracks (last_report_time, last_diagnosis,
        #         last_was_emergency) per patient.
        # Used only when ENABLE_STREAMING_GENAI is True.
        #

        # patient_id -> (report_timestamp_s, diagnosis_str, was_emergency)
        self._last_report_state: Dict[
            str,
            Tuple[float, str, bool]
        ] = {}


        # ====================================================
        # Kafka Consumer
        # ====================================================

        try:
            logger.info(
                "Initializing Kafka Consumer "
                "connecting to '%s'...",
                self.broker_url
            )

            self.consumer = Consumer({
                "bootstrap.servers":
                    self.broker_url,

                "group.id":
                    group_id,

                "auto.offset.reset":
                    "latest",

                "enable.auto.commit":
                    True,
            })

            logger.info(
                "Kafka Consumer successfully initialized."
            )

        except Exception as exc:
            logger.critical(
                "Failed to initialize Kafka Consumer: %s",
                exc
            )

            raise


    # ========================================================
    # Stop Consumer
    # ========================================================

    def stop_consuming(self) -> None:

        logger.info(
            "Stop signal received for Kafka Consumer."
        )

        self.is_running = False


    # ========================================================
    # Timestamp Normalization
    # ========================================================

    @staticmethod
    def _normalize_timestamp(
        timestamp: Any
    ) -> int:
        """
        Frontend expects Unix milliseconds.

        Handles:
        - missing timestamps
        - seconds
        - milliseconds
        """

        if timestamp is None:
            return int(
                time.time() * 1000
            )

        try:
            value = float(timestamp)

            # Likely Unix seconds
            if value < 10_000_000_000:
                value *= 1000

            return int(value)

        except (
            TypeError,
            ValueError
        ):
            return int(
                time.time() * 1000
            )


    # ========================================================
    # Raw Telemetry Broadcast
    # ========================================================

    def _broadcast_raw_sample(
        self,
        patient_id: str,
        leads: List[float],
        timestamp: Any
    ) -> None:
        """
        Broadcast one ECG timestep to the browser.

        The dashboard currently renders one waveform.
        Lead II is conventionally index 1 in the
        incoming 12-lead array.
        """

        ecg_value = float(
            leads[1]
            if len(leads) > 1
            else leads[0]
        )

        stream_payload = {
            "timestamp":
                self._normalize_timestamp(
                    timestamp
                ),

            "ecg_value":
                ecg_value,

            "patient_id":
                str(patient_id),

            "is_emergency":
                False,

            "lead":
                "Lead II",
        }

        ecg_websocket_manager.publish_from_thread(
            stream_payload
        )


    # ========================================================
    # Inference Broadcast
    # ========================================================

    def _broadcast_inference_result(
        self,
        patient_id: str,
        leads: List[float],
        timestamp: Any,
        result: Dict[str, Any]
    ) -> None:

        diagnosis = result.get(
            "diagnosis",
            "Unknown"
        )

        confidence = float(
            result.get(
                "confidence_score",
                0.0
            )
        )

        is_emergency = bool(
            result.get(
                "is_emergency",
                False
            )
        )

        ecg_value = float(
            leads[1]
            if len(leads) > 1
            else leads[0]
        )

        stream_payload = {
            "timestamp":
                self._normalize_timestamp(
                    timestamp
                ),

            "ecg_value":
                ecg_value,

            "patient_id":
                str(patient_id),

            "is_emergency":
                is_emergency,

            "anomaly_type":
                diagnosis,

            "confidence":
                confidence,

            "lead":
                "Lead II",
        }

        ecg_websocket_manager.publish_from_thread(
            stream_payload
        )


    # ========================================================
    # GenAI Deduplication Check
    # ========================================================

    def _should_generate_report(
        self,
        patient_id: str,
        diagnosis: str,
        is_emergency: bool,
    ) -> bool:
        """
        Returns True only when a new GenAI report is warranted.

        Rules:
        1. If we have never generated a report for this patient,
           allow it.
        2. If the diagnosis has changed, allow it (but still
           subject to cooldown unless it is also a new emergency).
        3. If the patient transitioned from non-emergency to
           emergency, bypass the cooldown once.
        4. Otherwise, enforce the 30-minute cooldown window.
        """

        now = time.monotonic()
        state = self._last_report_state.get(patient_id)

        if state is None:
            # First report for this patient
            return True

        last_time, last_diagnosis, last_was_emergency = state

        # New emergency transition: non-emergency → emergency
        new_emergency_transition = (
            is_emergency and not last_was_emergency
        )

        if new_emergency_transition:
            logger.info(
                "New emergency transition detected for "
                "patient %s. Bypassing cooldown.",
                patient_id
            )
            return True

        # Check cooldown
        elapsed = now - last_time
        if elapsed < REPORT_COOLDOWN_SECONDS:
            logger.debug(
                "Skipping GenAI report for patient %s "
                "(same diagnosis within cooldown: "
                "%.0f / %d seconds elapsed).",
                patient_id,
                elapsed,
                REPORT_COOLDOWN_SECONDS
            )
            return False

        return True


    def _record_report_generated(
        self,
        patient_id: str,
        diagnosis: str,
        is_emergency: bool,
    ) -> None:
        """Record that a report was generated for deduplication."""
        self._last_report_state[patient_id] = (
            time.monotonic(),
            diagnosis,
            is_emergency,
        )


    # ========================================================
    # Optional Streaming GenAI Report
    # ========================================================

    def _maybe_generate_streaming_report(
        self,
        patient_id: str,
        diagnosis: str,
        confidence: float,
        is_emergency: bool,
    ) -> None:
        """
        Conditionally triggers GenAI report generation.

        This method is only called when ENABLE_STREAMING_GENAI
        is True. Any failure is caught locally and logged —
        it will NEVER propagate to the consumer loop.
        """

        if not self._should_generate_report(
            patient_id, diagnosis, is_emergency
        ):
            return

        try:
            clinical_finding = (
                f"Patient {patient_id} "
                f"shows signs of "
                f"{diagnosis}."
            )

            self.report_generator.generate_reports(
                diagnosis=clinical_finding,
                confidence_score=confidence,
                is_emergency=is_emergency
            )

            self._record_report_generated(
                patient_id, diagnosis, is_emergency
            )

            logger.info(
                "Streaming GenAI reports generated "
                "for patient %s.",
                patient_id
            )

        except Exception as exc:
            # Report generation failure must NEVER crash the loop.
            logger.error(
                "Streaming GenAI report generation failed "
                "for patient %s (will retry after cooldown): %s",
                patient_id,
                exc
            )


    # ========================================================
    # Start Consumer
    # ========================================================

    def start_consuming(self) -> None:

        logger.info(
            "Subscribing to topic '%s'...",
            self.topic_name
        )

        self.consumer.subscribe([
            self.topic_name
        ])

        logger.info(
            "Starting consumption loop. "
            "Waiting for live ECG streams..."
        )

        if ENABLE_STREAMING_GENAI:
            logger.warning(
                "ENABLE_STREAMING_GENAI is True. "
                "Gemini will be called for anomalies "
                "(30-minute cooldown per patient active)."
            )
        else:
            logger.info(
                "ENABLE_STREAMING_GENAI is False. "
                "Kafka streaming runs independently of Gemini. "
                "No automatic GenAI calls will occur."
            )

        self.is_running = True


        try:
            while self.is_running:

                msg = self.consumer.poll(
                    timeout=1.0
                )


                if msg is None:
                    continue


                if msg.error():

                    if (
                        KafkaError is not None
                        and
                        msg.error().code()
                        == KafkaError._PARTITION_EOF
                    ):
                        continue

                    logger.error(
                        "Kafka error occurred: %s",
                        msg.error()
                    )

                    continue


                try:
                    # ========================================
                    # 1. Decode Kafka Payload
                    # ========================================

                    payload = json.loads(
                        msg.value().decode(
                            "utf-8"
                        )
                    )


                    patient_id = payload.get(
                        "patient_id"
                    )

                    leads = payload.get(
                        "leads"
                    )

                    timestamp = payload.get(
                        "timestamp"
                    )


                    # ========================================
                    # 2. Validate Payload
                    # ========================================

                    if not patient_id:

                        logger.warning(
                            "Kafka payload missing "
                            "patient_id. Skipping."
                        )

                        continue


                    if not isinstance(
                        leads,
                        list
                    ):

                        logger.warning(
                            "Kafka payload has invalid "
                            "leads field. Skipping."
                        )

                        continue


                    if len(leads) != 12:

                        logger.warning(
                            "Expected 12 ECG leads, "
                            "received %d. Skipping.",
                            len(leads)
                        )

                        continue


                    try:
                        leads = [
                            float(value)
                            for value in leads
                        ]

                    except (
                        TypeError,
                        ValueError
                    ):

                        logger.warning(
                            "ECG leads contain "
                            "non-numeric values. Skipping."
                        )

                        continue


                    # ========================================
                    # 3. Broadcast RAW Sample Immediately
                    # ========================================

                    self._broadcast_raw_sample(
                        patient_id=str(
                            patient_id
                        ),

                        leads=leads,

                        timestamp=timestamp
                    )


                    # ========================================
                    # 4. Add to Inference Buffer
                    # ========================================

                    self.patient_buffers[
                        str(patient_id)
                    ].append(
                        leads
                    )


                    # ========================================
                    # 5. Wait for 1000 Timesteps
                    # ========================================

                    if (
                        len(
                            self.patient_buffers[
                                str(patient_id)
                            ]
                        )
                        < self.inference_window_size
                    ):
                        continue


                    logger.info(
                        "Accumulated 1000 ECG timesteps "
                        "for patient %s. "
                        "Triggering inference...",
                        patient_id
                    )


                    leads_data = (
                        self.patient_buffers[
                            str(patient_id)
                        ][
                            -self.inference_window_size:
                        ]
                    )


                    # Clear completed window
                    self.patient_buffers[
                        str(patient_id)
                    ] = []


                    # ========================================
                    # 6. Run ECG Model
                    # ========================================

                    result = (
                        self.predictor.analyze_ecg(
                            leads_data
                        )
                    )


                    diagnosis = result.get(
                        "diagnosis",
                        "Unknown"
                    )

                    confidence = float(
                        result.get(
                            "confidence_score",
                            0.0
                        )
                    )

                    is_emergency = bool(
                        result.get(
                            "is_emergency",
                            False
                        )
                    )


                    logger.info(
                        "Inference completed for %s: "
                        "%s (%.2f%%)",
                        patient_id,
                        diagnosis,
                        confidence * 100
                    )


                    # ========================================
                    # 7. Broadcast AI Result
                    # ========================================

                    self._broadcast_inference_result(
                        patient_id=str(
                            patient_id
                        ),

                        leads=leads,

                        timestamp=timestamp,

                        result=result
                    )


                    # ========================================
                    # 8. Optional: Streaming GenAI Report
                    #
                    # Controlled by ENABLE_STREAMING_GENAI.
                    # Defaults to False to protect free-tier
                    # Gemini quota.
                    # ========================================

                    if (
                        ENABLE_STREAMING_GENAI
                        and (
                            diagnosis != "Normal ECG"
                            or is_emergency
                        )
                    ):
                        logger.warning(
                            "ANOMALY DETECTED for %s: "
                            "%s "
                            "(Confidence: %.2f%%). "
                            "Evaluating GenAI report eligibility...",
                            patient_id,
                            diagnosis,
                            confidence * 100
                        )

                        self._maybe_generate_streaming_report(
                            patient_id=str(patient_id),
                            diagnosis=diagnosis,
                            confidence=confidence,
                            is_emergency=is_emergency,
                        )

                    elif diagnosis != "Normal ECG" or is_emergency:
                        # Still log the anomaly even when GenAI is off
                        logger.warning(
                            "ANOMALY DETECTED for %s: "
                            "%s "
                            "(Confidence: %.2f%%). "
                            "Streaming GenAI is disabled — "
                            "no report generated.",
                            patient_id,
                            diagnosis,
                            confidence * 100
                        )


                except json.JSONDecodeError:

                    logger.error(
                        "Failed to decode JSON "
                        "from Kafka message."
                    )


                except Exception as exc:

                    logger.error(
                        "Error processing incoming "
                        "Kafka message: %s",
                        exc,
                        exc_info=True
                    )


        except KeyboardInterrupt:

            logger.warning(
                "KeyboardInterrupt detected. "
                "Initiating graceful shutdown..."
            )


        except Exception as exc:

            logger.error(
                "Unexpected error in consumer loop: %s",
                exc,
                exc_info=True
            )

            raise


        finally:

            logger.info(
                "Closing Kafka consumer connection..."
            )

            self.consumer.close()

            logger.info(
                "Kafka Consumer shut down cleanly."
            )