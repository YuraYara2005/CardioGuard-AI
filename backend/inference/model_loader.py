import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict

import tensorflow as tf

# pyrefly: ignore [missing-import]
import keras

# pyrefly: ignore [missing-import]
from keras import layers

try:
    # pyrefly: ignore [missing-import]
    import joblib
except ImportError:
    joblib = None


logger = logging.getLogger(__name__)


# ============================================================
# Exact custom attention layer from the training notebook
# ============================================================

@keras.saving.register_keras_serializable(
    name="MultiHeadAttentionLayer"
)
class MultiHeadAttentionLayer(layers.Layer):
    def __init__(
        self,
        num_heads=1,
        return_attention_weights=False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.num_heads = num_heads
        self.return_attention_weights = return_attention_weights

    def build(self, input_shape):
        d_model = input_shape[-1]

        self.mha = layers.MultiHeadAttention(
            num_heads=self.num_heads,
            key_dim=d_model // self.num_heads
        )

        self.pooling = layers.GlobalAveragePooling1D()

        super().build(input_shape)

    def call(self, x):
        context, weights = self.mha(
            x,
            x,
            x,
            return_attention_scores=True
        )

        pooled = self.pooling(context)

        if self.return_attention_weights:
            avg_weights = tf.reduce_mean(
                weights,
                axis=1
            )

            avg_weights = tf.reduce_mean(
                avg_weights,
                axis=-1,
                keepdims=True
            )

            return pooled, avg_weights

        return pooled

    def get_config(self):
        config = super().get_config()

        config.update({
            "num_heads": self.num_heads,
            "return_attention_weights":
                self.return_attention_weights
        })

        return config


# ============================================================
# Multi-model artifact loader
# ============================================================

class TCNModelLoader:
    """
    Thread-safe lazy loader for all CardioGuard multimodal
    inference models and preprocessing artifacts.

    Does not modify:
    - model architecture
    - model weights
    - serialized .keras files
    - teammate training outputs
    """

    _load_lock = Lock()

    MODEL_FILES = {
        "ecg_model":
            "ecg_model.keras",

        "ecg_feature_extractor":
            "ecg_feature_extractor.keras",

        "image_feature_extractor":
            "image_feature_extractor.keras",

        "image_projection_model":
            "image_projection_model.keras",

        "fusion_model":
            "fusion_model.keras",
    }

    ARTIFACT_FILES = {
        "deployment_config":
            "deployment_config.pkl",

        "metadata_scaler":
            "metadata_scaler.pkl",

        "sex_encoder":
            "sex_encoder.pkl",

        "symptom_encoder":
            "symptom_encoder.pkl",
    }

    OPTIONAL_FILES = {
        "fusion_weights":
            "fusion_model.weights.h5",
    }

    def __init__(
        self,
        models_dir: str = "models"
    ):
        self.models_dir = Path(
            models_dir
        ).resolve()

        self._artifacts: Dict[str, Any] = {}
        self._is_loaded = False

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def get_artifacts(self) -> Dict[str, Any]:
        if self._is_loaded:
            return self._artifacts

        with self._load_lock:
            if self._is_loaded:
                return self._artifacts

            self._validate_models_directory()

            logger.info(
                "Loading CardioGuard multimodal artifacts "
                "from '%s'...",
                self.models_dir
            )

            self._load_preprocessing_artifacts()
            self._load_keras_models()
            self._register_optional_files()

            self._is_loaded = True

            logger.info(
                "All required CardioGuard multimodal "
                "artifacts loaded successfully."
            )

            return self._artifacts

    def get_model(self):
        """
        Backward-compatible method for old backend code.

        Returns the standalone ECG classifier.
        """
        artifacts = self.get_artifacts()
        return artifacts["ecg_model"]

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def _validate_models_directory(self):
        if not self.models_dir.exists():
            raise FileNotFoundError(
                f"Models directory not found: "
                f"{self.models_dir}"
            )

        if not self.models_dir.is_dir():
            raise NotADirectoryError(
                f"Models path is not a directory: "
                f"{self.models_dir}"
            )

        missing_models = []

        for filename in self.MODEL_FILES.values():
            model_path = self.models_dir / filename

            if not model_path.exists():
                missing_models.append(filename)

        if missing_models:
            raise FileNotFoundError(
                "Missing required model files: "
                + ", ".join(missing_models)
            )

    # --------------------------------------------------------
    # PKL artifacts
    # --------------------------------------------------------

    def _load_preprocessing_artifacts(self):
        if joblib is None:
            raise ImportError(
                "joblib is required to load CardioGuard "
                "preprocessing artifacts. Install it with: "
                "pip install joblib scikit-learn"
            )

        for key, filename in self.ARTIFACT_FILES.items():
            artifact_path = (
                self.models_dir / filename
            )

            if not artifact_path.exists():
                raise FileNotFoundError(
                    f"Required preprocessing artifact "
                    f"not found: {artifact_path}"
                )

            try:
                artifact = joblib.load(
                    artifact_path
                )

                self._artifacts[key] = artifact

                logger.info(
                    "Loaded preprocessing artifact: %s",
                    filename
                )

            except Exception as exc:
                logger.exception(
                    "Failed to load preprocessing "
                    "artifact '%s'.",
                    filename
                )

                raise RuntimeError(
                    f"Failed to load artifact "
                    f"'{filename}': {exc}"
                ) from exc

    # --------------------------------------------------------
    # Keras models
    # --------------------------------------------------------

    def _load_keras_models(self):
        original_dense_from_config = (
            layers.Dense.from_config
        )

        def compatible_dense_from_config(config):
            """
            Compatibility-only deserialization shim.

            Removes quantization_config only when its
            serialized value is None.

            This does not alter architecture or weights.
            """
            config = dict(config)

            if config.get(
                "quantization_config"
            ) is None:
                config.pop(
                    "quantization_config",
                    None
                )

            return original_dense_from_config(
                config
            )

        layers.Dense.from_config = staticmethod(
            compatible_dense_from_config
        )

        try:
            for key, filename in (
                self.MODEL_FILES.items()
            ):
                model_path = (
                    self.models_dir / filename
                )

                logger.info(
                    "Loading model '%s' from '%s'...",
                    key,
                    model_path
                )

                model = keras.models.load_model(
                    str(model_path),
                    custom_objects={
                        "MultiHeadAttentionLayer":
                            MultiHeadAttentionLayer
                    },
                    compile=False
                )

                self._artifacts[key] = model

                logger.info(
                    "Loaded model '%s' successfully.",
                    key
                )

        except Exception as exc:
            logger.exception(
                "Failed while loading CardioGuard "
                "Keras models."
            )

            self._artifacts.clear()

            raise RuntimeError(
                f"Model loading failed: {exc}"
            ) from exc

        finally:
            layers.Dense.from_config = (
                original_dense_from_config
            )

    # --------------------------------------------------------
    # Optional files
    # --------------------------------------------------------

    def _register_optional_files(self):
        for key, filename in (
            self.OPTIONAL_FILES.items()
        ):
            file_path = (
                self.models_dir / filename
            )

            if file_path.exists():
                self._artifacts[key] = file_path

                logger.info(
                    "Registered optional artifact: %s",
                    filename
                )
            else:
                logger.warning(
                    "Optional artifact not found: %s",
                    filename
                )