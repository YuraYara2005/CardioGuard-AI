from pathlib import Path

# pyrefly: ignore [missing-import]
import keras
# pyrefly: ignore [missing-import]
from keras import layers

from backend.inference.model_loader import MultiHeadAttentionLayer


MODELS_DIR = Path("models").resolve()

MODEL_FILES = [
    "ecg_model.keras",
    "ecg_feature_extractor.keras",
    "image_feature_extractor.keras",
    "image_projection_model.keras",
    "fusion_model.keras",
]


# Save original Dense deserializer
original_dense_from_config = layers.Dense.from_config


def compatible_dense_from_config(config):
    """
    Compatibility-only patch.

    Removes quantization_config ONLY when its value is None.
    Does not modify model architecture, weights, or model files.
    """
    config = dict(config)

    if config.get("quantization_config") is None:
        config.pop("quantization_config", None)

    return original_dense_from_config(config)


# Apply the same compatibility idea that already succeeded
layers.Dense.from_config = staticmethod(
    compatible_dense_from_config
)


try:
    for filename in MODEL_FILES:
        model_path = MODELS_DIR / filename

        print("\n" + "=" * 70)
        print(f"MODEL: {filename}")
        print("=" * 70)

        if not model_path.exists():
            print(f"NOT FOUND: {model_path}")
            continue

        try:
            model = keras.models.load_model(
                str(model_path),
                custom_objects={
                    "MultiHeadAttentionLayer":
                        MultiHeadAttentionLayer,
                },
                compile=False,
            )

            print("LOADED SUCCESSFULLY")

            print("\nINPUTS:")
            for i, tensor in enumerate(model.inputs):
                print(
                    f"  [{i}] "
                    f"name={tensor.name}, "
                    f"shape={tensor.shape}, "
                    f"dtype={tensor.dtype}"
                )

            print("\nOUTPUTS:")
            for i, tensor in enumerate(model.outputs):
                print(
                    f"  [{i}] "
                    f"name={tensor.name}, "
                    f"shape={tensor.shape}, "
                    f"dtype={tensor.dtype}"
                )

            print("\nMODEL NAME:")
            print(f"  {model.name}")

        except Exception as e:
            print("FAILED TO LOAD")
            print(f"ERROR TYPE: {type(e).__name__}")
            print(f"ERROR: {e}")


finally:
    # Always restore Keras behavior
    layers.Dense.from_config = original_dense_from_config