import os
import logging
from typing import Any, Optional

try:
    import tensorflow as tf
    # pyrefly: ignore [missing-import]
    import keras
    

    @tf.keras.saving.register_keras_serializable()
    class AttentionLayer(keras.layers.Layer):
        # [PASTE  __init__, build, call, and get_config METHODS HERE]
        pass

    # =====================================================================

except ImportError:
    tf = None

logger = logging.getLogger(__name__)

class TCNModelLoader:
    def __init__(self, model_path: str = "models/cardioguard_model.keras", log_level: int = logging.INFO):
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        self.model_path = model_path
        self._model: Optional[Any] = None
        
    def get_model(self) -> Any:
        if tf is None:
            raise ImportError("TensorFlow is not installed.")
        if self._model is not None:
            return self._model

        abs_model_path = os.path.abspath(self.model_path)
        if not os.path.exists(abs_model_path):
            raise FileNotFoundError(f"The model file '{self.model_path}' does not exist.")

        logger.info(f"Loading TCN model weights from '{abs_model_path}' into memory...")

        try:
            # Using compile=False just in case they have custom loss functions
            self._model = tf.keras.models.load_model(
                abs_model_path,
                custom_objects={"AttentionLayer": AttentionLayer},
                compile=False
            )
            logger.info("✅ TCN model successfully loaded (Inference Mode).")
            return self._model
            
        except Exception as e:
            raise RuntimeError(f"Model load failed: {str(e)}") from e