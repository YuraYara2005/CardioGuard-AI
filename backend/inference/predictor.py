import logging
from typing import Any, Dict, List, Union

try:
    # pyrefly: ignore [missing-import]
    import numpy as np
except ImportError:
    np = None

# Configure module-level logger
logger = logging.getLogger(__name__)

class ECGPredictor:
    """
    The core inference engine for CardioGuard.
    
    Responsible strictly for taking raw 12-lead ECG data, preprocessing it to match 
    the PTB-XL Temporal Convolutional Network (TCN) input shape, executing the 
    prediction, and returning a structured, human-readable diagnosis.
    """

    # Mock mapping for demonstration. In production, this matches the exact 
    # categorical outputs of your trained TCN model.
    # Format: class_index: ("Diagnosis String", is_emergency_boolean)
    DIAGNOSIS_MAP = {
        0: ("Normal ECG", False),
        1: ("Signs of Atrial Fibrillation (AFib)", False),
        2: ("Acute Myocardial Infarction (Heart Attack)", True),
        3: ("ST/T Change (Ischemia)", True)
    }

    def __init__(self, model: Any, log_level: int = logging.INFO):
        """
        Initializes the ECGPredictor.

        Args:
            model: The compiled TensorFlow/Keras model injected from TCNModelLoader.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        if np is None:
            logger.critical("numpy is not installed in the current environment.")
            raise ImportError("Cannot initialize predictor because 'numpy' is not installed.")

        if model is None:
            logger.critical("A valid TensorFlow model instance must be injected.")
            raise ValueError("Injected model cannot be None.")

        self.model = model
        logger.info("ECGPredictor initialized with injected TensorFlow model.")

    def _preprocess(self, leads_data: Union[List[float], List[List[float]]]) -> Any: # np.ndarray
        """
        Preprocesses raw 12-lead data into the expected TCN input shape (1, 1000, 12).
        
        Args:
            leads_data: A flat list or 2D array representing the ECG leads.

        Returns:
            A numpy array of shape (1, 1000, 12).
        """
        # Convert input to a float32 numpy array
        raw_array = np.array(leads_data, dtype=np.float32)

        # If it's a flat list (e.g., just a single 12-lead reading of length 12)
        if raw_array.ndim == 1:
            # Reshape to (1, 12) -> meaning 1 timestep, 12 channels
            raw_array = raw_array.reshape(-1, 12)
        
        time_steps, channels = raw_array.shape

        if channels != 12:
            raise ValueError(f"Expected 12 channels (leads), but got {channels}.")

        # The PTB-XL model expects exactly 1000 timesteps (10 seconds @ 100Hz)
        target_steps = 1000
        
        if time_steps > target_steps:
            # Truncate to the most recent 1000 steps
            processed_array = raw_array[-target_steps:, :]
        elif time_steps < target_steps:
            # Pad with zeros at the beginning (pre-padding)
            padding_needed = target_steps - time_steps
            processed_array = np.pad(raw_array, ((padding_needed, 0), (0, 0)), mode='constant')
        else:
            processed_array = raw_array

        # Expand dimensions to add the batch_size of 1 -> shape becomes (1, 1000, 12)
        final_input = np.expand_dims(processed_array, axis=0)
        
        return final_input

    def analyze_ecg(self, leads_data: Union[List[float], List[List[float]]]) -> Dict[str, Any]:
        """
        Executes the full inference pipeline on raw ECG data.

        Args:
            leads_data: The raw 12-lead ECG data points.

        Returns:
            A dictionary containing the structured diagnosis:
            {
                "diagnosis": str,
                "confidence_score": float,
                "is_emergency": bool
            }
        """
        if not leads_data:
            logger.warning("Empty leads_data provided for analysis.")
            raise ValueError("Input leads_data cannot be empty.")

        try:
            # 1. Preprocess
            model_input = self._preprocess(leads_data)
            
            # 2. Predict
            # verbose=0 suppresses the TF progress bar in standard output
            predictions = self.model.predict(model_input, verbose=0)
            
            # 3. Postprocess
            # Assuming the model outputs a softmax array for a single sample: e.g., [[0.1, 0.8, 0.05, 0.05]]
            probabilities = predictions[0]
            predicted_class_index = int(np.argmax(probabilities))
            confidence_score = float(probabilities[predicted_class_index])

            # Map to human-readable strings
            diagnosis_str, is_emergency = self.DIAGNOSIS_MAP.get(
                predicted_class_index, 
                ("Unknown Anomaly Detected", True) # Fallback safety
            )

            result = {
                "diagnosis": diagnosis_str,
                "confidence_score": round(confidence_score, 4),
                "is_emergency": is_emergency
            }

            logger.info(f"ECG Analyzed. Diagnosis: '{diagnosis_str}' (Confidence: {result['confidence_score']:.2%})")
            return result

        except Exception as e:
            logger.error(f"Error during ECG analysis: {str(e)}", exc_info=True)
            raise RuntimeError(f"Inference pipeline failed: {str(e)}") from e
