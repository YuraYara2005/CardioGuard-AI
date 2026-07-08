# pyrefly: ignore [missing-import]
import joblib
from pathlib import Path

MODELS_DIR = Path("models")

artifact_files = [
    "deployment_config.pkl",
    "metadata_scaler.pkl",
    "sex_encoder.pkl",
    "symptom_encoder.pkl",
]

for filename in artifact_files:
    path = MODELS_DIR / filename

    print("\n" + "=" * 80)
    print(f"ARTIFACT: {filename}")
    print("=" * 80)

    obj = joblib.load(path)

    print("TYPE:")
    print(type(obj))

    print("\nOBJECT:")
    print(obj)

    # --------------------------------------------------------
    # Dictionary inspection
    # --------------------------------------------------------
    if isinstance(obj, dict):
        print("\nDICTIONARY CONTENTS:")

        for key, value in obj.items():
            print(f"\n  KEY: {key!r}")
            print(f"  VALUE TYPE: {type(value)}")
            print(f"  VALUE: {value!r}")

    # --------------------------------------------------------
    # Common sklearn attributes
    # --------------------------------------------------------
    attributes = [
        "classes_",
        "feature_names_in_",
        "n_features_in_",
        "data_min_",
        "data_max_",
        "data_range_",
        "scale_",
        "min_",
        "mean_",
        "var_",
    ]

    print("\nKNOWN ATTRIBUTES:")

    found_any = False

    for attr in attributes:
        if hasattr(obj, attr):
            found_any = True
            value = getattr(obj, attr)
            print(f"  {attr}: {value!r}")

    if not found_any:
        print("  No common inspected sklearn attributes found.")

    # --------------------------------------------------------
    # General object state
    # --------------------------------------------------------
    if hasattr(obj, "__dict__"):
        print("\nOBJECT __dict__:")

        for key, value in obj.__dict__.items():
            print(f"  {key}: {value!r}")