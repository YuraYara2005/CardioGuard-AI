import logging
from pathlib import Path
from threading import Lock

import tensorflow as tf
# pyrefly: ignore [missing-import]
import keras
# pyrefly: ignore [missing-import]
from keras import layers

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
# Compatibility shim for newer-Keras serialized Dense configs
#
# IMPORTANT:
# - Does NOT change model architecture
# - Does NOT remove any layer
# - Does NOT modify weights
# - Does NOT modify the .keras file
# - Only ignores quantization_config when its value is None
# ============================================================

class CompatibleDense(layers.Dense):
    @classmethod
    def from_config(cls, config):
        config = dict(config)

        if config.get("quantization_config") is None:
            config.pop(
                "quantization_config",
                None
            )

        return cls(**config)


# ============================================================
# Model Loader
# ============================================================

class TCNModelLoader:
    """
    Thread-safe lazy loader for the trained CardioGuard TCN model.
    """

    _load_lock = Lock()

    def __init__(self, model_path):
        self.model_path = Path(model_path).resolve()
        self._model = None

    def get_model(self):
        if self._model is not None:
            return self._model

        with self._load_lock:
            if self._model is not None:
                return self._model

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found: {self.model_path}"
                )

            logger.info(
                "Loading final TCN model from '%s' into memory...",
                self.model_path
            )

            # ------------------------------------------------
            # Temporarily patch Keras 3 Dense.from_config only
            # during deserialization.
            #
            # The saved archive explicitly serializes Dense as:
            #
            # module='keras.layers'
            # class_name='Dense'
            #
            # Therefore the patch must target standalone Keras 3,
            # not tf_keras / legacy Keras.
            #
            # This does NOT remove quantization from the model.
            # It only ignores quantization_config when its value
            # is explicitly None.
            # ------------------------------------------------

            original_dense_from_config = (
                layers.Dense.from_config
            )

            def compatible_dense_from_config(config):
                config = dict(config)

                if config.get("quantization_config") is None:
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
                self._model = keras.models.load_model(
                    str(self.model_path),
                    custom_objects={
                        "MultiHeadAttentionLayer":
                            MultiHeadAttentionLayer,
                    },
                    compile=False
                )

                logger.info(
                    "TCN model loaded successfully."
                )

                return self._model

            except Exception as e:
                logger.exception(
                    "Failed to load TCN model."
                )

                raise RuntimeError(
                    f"Model load failed: {e}"
                ) from e

            finally:
                layers.Dense.from_config = (
                    original_dense_from_config
                )