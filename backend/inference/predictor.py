import logging
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np


logger = logging.getLogger(__name__)


class ECGPredictor:
    """
    CardioGuard inference engine.

    Supports:

    1. Standalone ECG inference
       Raw ECG -> ecg_model

    2. Multimodal fusion inference
       Raw ECG -> ECG feature extractor -> 128
       ECG image -> image feature extractor -> 1280
       1280 -> image projection model -> 128
       Labs -> 5
       Metadata -> 9
       All features -> fusion model -> 5 classes

    The class does not modify teammate models, weights,
    preprocessing artifacts, or serialized files.
    """

    CLASS_LABELS = [
        "NORM",
        "MI",
        "STTC",
        "CD",
        "HYP",
    ]

    CLASS_NAMES = {
        "NORM": "Normal ECG",
        "MI": "Myocardial Infarction",
        "STTC": "ST/T Change",
        "CD": "Conduction Disturbance",
        "HYP": "Hypertrophy",
    }

    EMERGENCY_CLASSES = {
        "MI",
    }

    def __init__(
        self,
        model: Any = None,
        artifacts: Optional[Dict[str, Any]] = None,
        log_level: int = logging.INFO,
    ):
        if not logger.handlers:
            handler = logging.StreamHandler()

            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - "
                "%(levelname)s - %(message)s"
            )

            handler.setFormatter(formatter)
            logger.addHandler(handler)

        logger.setLevel(log_level)

        self.artifacts = artifacts or {}

        # Backward compatibility:
        # old app.py injects model=tcn_model
        self.ecg_model = (
            self.artifacts.get("ecg_model")
            if self.artifacts
            else model
        )

        if self.ecg_model is None:
            self.ecg_model = model

        # Multimodal models
        self.ecg_feature_extractor = (
            self.artifacts.get(
                "ecg_feature_extractor"
            )
        )

        self.image_feature_extractor = (
            self.artifacts.get(
                "image_feature_extractor"
            )
        )

        self.image_projection_model = (
            self.artifacts.get(
                "image_projection_model"
            )
        )

        self.fusion_model = (
            self.artifacts.get(
                "fusion_model"
            )
        )

        # Preprocessing artifacts
        self.deployment_config = (
            self.artifacts.get(
                "deployment_config",
                {}
            )
        )

        self.metadata_scaler = (
            self.artifacts.get(
                "metadata_scaler"
            )
        )

        self.sex_encoder = (
            self.artifacts.get(
                "sex_encoder"
            )
        )

        self.symptom_encoder = (
            self.artifacts.get(
                "symptom_encoder"
            )
        )

        # Prefer exact teammate-saved class order
        self.class_labels = list(
            self.deployment_config.get(
                "superclasses",
                self.CLASS_LABELS
            )
        )

        self.class_thresholds = dict(
            self.deployment_config.get(
                "class_thresholds",
                {}
            )
        )

        self.lab_feature_names = list(
            self.deployment_config.get(
                "lab_features",
                [
                    "troponin",
                    "ck-mb",
                    "bnp",
                    "creatinine",
                    "hba1c",
                ]
            )
        )

        self.image_size = tuple(
            self.deployment_config.get(
                "image_size",
                (224, 224)
            )
        )

        if self.ecg_model is None:
            raise ValueError(
                "ECG model is required."
            )

        logger.info(
            "ECGPredictor initialized. "
            "Multimodal fusion available: %s",
            self.is_fusion_available()
        )

    # ========================================================
    # Capability checks
    # ========================================================

    def is_fusion_available(self) -> bool:
        required = [
            self.ecg_feature_extractor,
            self.image_feature_extractor,
            self.image_projection_model,
            self.fusion_model,
            self.metadata_scaler,
            self.sex_encoder,
            self.symptom_encoder,
        ]

        return all(
            item is not None
            for item in required
        )

    # ========================================================
    # ECG preprocessing
    # ========================================================

    def _preprocess_ecg(
        self,
        leads_data: Union[
            List[float],
            List[List[float]],
            np.ndarray,
        ],
    ) -> np.ndarray:
        raw_array = np.asarray(
            leads_data,
            dtype=np.float32
        )

        if raw_array.size == 0:
            raise ValueError(
                "Input leads_data cannot be empty."
            )

        if raw_array.ndim == 1:
            if raw_array.size % 12 != 0:
                raise ValueError(
                    "Flat ECG input length must be "
                    "divisible by 12."
                )

            raw_array = raw_array.reshape(
                -1,
                12
            )

        if raw_array.ndim != 2:
            raise ValueError(
                "ECG input must be a 1D flat array "
                "or a 2D array."
            )

        # Accept either:
        # (timesteps, 12)
        # or
        # (12, timesteps)
        if raw_array.shape[1] == 12:
            pass

        elif raw_array.shape[0] == 12:
            raw_array = raw_array.T

        else:
            raise ValueError(
                "Expected ECG data with exactly "
                "12 leads."
            )

        target_steps = 1000
        time_steps = raw_array.shape[0]

        if time_steps > target_steps:
            processed = raw_array[
                -target_steps:,
                :
            ]

        elif time_steps < target_steps:
            padding_needed = (
                target_steps - time_steps
            )

            processed = np.pad(
                raw_array,
                (
                    (padding_needed, 0),
                    (0, 0)
                ),
                mode="constant"
            )

        else:
            processed = raw_array

        processed = processed.astype(
            np.float32,
            copy=False
        )

        return np.expand_dims(
            processed,
            axis=0
        )

    # ========================================================
    # Image preprocessing
    # ========================================================

    def _preprocess_image(
        self,
        image_data: Union[
            List,
            np.ndarray,
        ],
    ) -> np.ndarray:
        image = np.asarray(
            image_data,
            dtype=np.float32
        )

        if image.size == 0:
            raise ValueError(
                "ECG image cannot be empty."
            )

        # Remove batch dimension if caller passed one image
        if (
            image.ndim == 4
            and image.shape[0] == 1
        ):
            image = image[0]

        if image.ndim == 2:
            image = np.stack(
                [image, image, image],
                axis=-1
            )

        if image.ndim != 3:
            raise ValueError(
                "ECG image must have shape "
                "(height, width, channels)."
            )

        if image.shape[-1] == 1:
            image = np.repeat(
                image,
                3,
                axis=-1
            )

        if image.shape[-1] != 3:
            raise ValueError(
                "ECG image must contain "
                "exactly 3 channels."
            )

        expected_height = int(
            self.image_size[0]
        )

        expected_width = int(
            self.image_size[1]
        )

        if image.shape[:2] != (
            expected_height,
            expected_width
        ):
            raise ValueError(
                "ECG image must already be resized "
                f"to {self.image_size}. "
                f"Received {image.shape[:2]}."
            )

        # Conservative normalization:
        # convert 0..255 images to 0..1.
        if np.max(image) > 1.0:
            image = image / 255.0

        return np.expand_dims(
            image.astype(
                np.float32,
                copy=False
            ),
            axis=0
        )

    # ========================================================
    # Lab preprocessing
    # ========================================================

    def _preprocess_labs(
        self,
        labs: Union[
            Dict[str, float],
            Sequence[float],
            np.ndarray,
        ],
    ) -> np.ndarray:
        if isinstance(labs, dict):
            missing = [
                feature
                for feature in self.lab_feature_names
                if feature not in labs
            ]

            if missing:
                raise ValueError(
                    "Missing lab features: "
                    + ", ".join(missing)
                )

            values = [
                labs[feature]
                for feature
                in self.lab_feature_names
            ]

        else:
            values = labs

        lab_array = np.asarray(
            values,
            dtype=np.float32
        ).reshape(1, -1)

        if lab_array.shape[1] != 5:
            raise ValueError(
                "Fusion model requires exactly "
                "5 lab features in this order: "
                + ", ".join(
                    self.lab_feature_names
                )
            )

        return lab_array

    # ========================================================
    # Metadata preprocessing
    # ========================================================

    def _preprocess_metadata(
        self,
        age: float,
        blood_pressure: float,
        heart_rate: float,
        sex: str,
        symptoms: Sequence[str],
    ) -> np.ndarray:
        if self.metadata_scaler is None:
            raise RuntimeError(
                "metadata_scaler is not loaded."
            )

        if self.sex_encoder is None:
            raise RuntimeError(
                "sex_encoder is not loaded."
            )

        if self.symptom_encoder is None:
            raise RuntimeError(
                "symptom_encoder is not loaded."
            )

        numeric_metadata = np.asarray(
            [[
                age,
                blood_pressure,
                heart_rate,
            ]],
            dtype=np.float32
        )

        scaled_numeric = (
            self.metadata_scaler.transform(
                numeric_metadata
            )
        )

        sex_value = self.sex_encoder.transform(
            [sex]
        ).astype(
            np.float32
        ).reshape(1, 1)

        symptom_values = (
            self.symptom_encoder.transform(
                [list(symptoms)]
            )
        ).astype(
            np.float32
        )

        metadata_vector = np.concatenate(
            [
                scaled_numeric.astype(
                    np.float32
                ),
                sex_value,
                symptom_values,
            ],
            axis=1
        )

        if metadata_vector.shape != (1, 9):
            raise RuntimeError(
                "Metadata preprocessing produced "
                f"{metadata_vector.shape}; "
                "expected (1, 9)."
            )

        return metadata_vector

    # ========================================================
    # Prediction postprocessing
    # ========================================================

    def _build_result(
        self,
        probabilities: np.ndarray,
        source: str,
    ) -> Dict[str, Any]:
        probs = np.asarray(
            probabilities,
            dtype=np.float32
        ).reshape(-1)

        if probs.size != len(
            self.class_labels
        ):
            raise ValueError(
                "Model returned "
                f"{probs.size} class values; "
                f"expected {len(self.class_labels)}."
            )

        predicted_index = int(
            np.argmax(probs)
        )

        class_code = self.class_labels[
            predicted_index
        ]

        confidence = float(
            probs[predicted_index]
        )

        threshold = self.class_thresholds.get(
            class_code
        )

        threshold_passed = (
            confidence >= float(threshold)
            if threshold is not None
            else None
        )

        diagnosis_name = self.CLASS_NAMES.get(
            class_code,
            class_code
        )

        class_probabilities = {
            label: round(
                float(probability),
                6
            )
            for label, probability
            in zip(
                self.class_labels,
                probs
            )
        }

        return {
            "diagnosis": diagnosis_name,
            "class_code": class_code,
            "confidence_score": round(
                confidence,
                6
            ),
            "is_emergency":
                class_code
                in self.EMERGENCY_CLASSES,
            "threshold": (
                float(threshold)
                if threshold is not None
                else None
            ),
            "threshold_passed":
                threshold_passed,
            "class_probabilities":
                class_probabilities,
            "prediction_source": source,
        }

    # ========================================================
    # Standalone ECG inference
    # ========================================================

    def analyze_ecg(
        self,
        leads_data: Union[
            List[float],
            List[List[float]],
            np.ndarray,
        ],
    ) -> Dict[str, Any]:
        model_input = self._preprocess_ecg(
            leads_data
        )

        raw_predictions = (
            self.ecg_model.predict(
                model_input,
                verbose=0
            )
        )

        attention_weights = None

        if isinstance(
            raw_predictions,
            (list, tuple)
        ):
            class_probs = raw_predictions[0]

            if len(raw_predictions) > 1:
                attention_weights = (
                    raw_predictions[1]
                )

        else:
            class_probs = raw_predictions

        result = self._build_result(
            class_probs[0],
            source="standalone_ecg"
        )

        if attention_weights is not None:
            result["attention_shape"] = list(
                np.asarray(
                    attention_weights
                ).shape
            )

        logger.info(
            "Standalone ECG prediction: %s "
            "(%.2f%%)",
            result["class_code"],
            result["confidence_score"] * 100
        )

        return result

    # ========================================================
    # Multimodal fusion inference
    # ========================================================

    def analyze_multimodal(
        self,
        leads_data: Union[
            List[float],
            List[List[float]],
            np.ndarray,
        ],
        image_data: Union[
            List,
            np.ndarray,
        ],
        labs: Union[
            Dict[str, float],
            Sequence[float],
            np.ndarray,
        ],
        age: float,
        blood_pressure: float,
        heart_rate: float,
        sex: str,
        symptoms: Sequence[str],
    ) -> Dict[str, Any]:
        if not self.is_fusion_available():
            raise RuntimeError(
                "Multimodal fusion artifacts "
                "are not fully loaded."
            )

        ecg_input = self._preprocess_ecg(
            leads_data
        )

        image_input = self._preprocess_image(
            image_data
        )

        lab_vector = self._preprocess_labs(
            labs
        )

        metadata_vector = (
            self._preprocess_metadata(
                age=age,
                blood_pressure=blood_pressure,
                heart_rate=heart_rate,
                sex=sex,
                symptoms=symptoms,
            )
        )

        # Raw ECG -> 128
        ecg_features = (
            self.ecg_feature_extractor.predict(
                ecg_input,
                verbose=0
            )
        )

        # ECG image -> 1280
        raw_image_features = (
            self.image_feature_extractor.predict(
                image_input,
                verbose=0
            )
        )

        # 1280 -> 128
        image_features = (
            self.image_projection_model.predict(
                raw_image_features,
                verbose=0
            )
        )

        if ecg_features.shape != (1, 128):
            raise RuntimeError(
                "ECG feature extractor produced "
                f"{ecg_features.shape}; "
                "expected (1, 128)."
            )

        if image_features.shape != (1, 128):
            raise RuntimeError(
                "Image projection model produced "
                f"{image_features.shape}; "
                "expected (1, 128)."
            )

        # Fusion model input order comes directly from
        # the inspected model signature:
        #
        # 0 -> ECG features      (128)
        # 1 -> image features    (128)
        # 2 -> lab features      (5)
        # 3 -> metadata features (9)

        fusion_predictions = (
            self.fusion_model.predict(
                [
                    ecg_features,
                    image_features,
                    lab_vector,
                    metadata_vector,
                ],
                verbose=0
            )
        )

        result = self._build_result(
            fusion_predictions[0],
            source="multimodal_fusion"
        )

        result["feature_shapes"] = {
            "ecg_features":
                list(ecg_features.shape),

            "raw_image_features":
                list(
                    raw_image_features.shape
                ),

            "image_features":
                list(image_features.shape),

            "lab_features":
                list(lab_vector.shape),

            "metadata_features":
                list(metadata_vector.shape),
        }

        logger.info(
            "Multimodal fusion prediction: %s "
            "(%.2f%%)",
            result["class_code"],
            result["confidence_score"] * 100
        )

        return result