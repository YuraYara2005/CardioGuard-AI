import json
#prelify
# pyrefly: ignore [missing-import]
import wfdb
from pathlib import Path

records_dir = Path("data/ptb-xl/records100/01000")

hea_files = list(records_dir.glob("*.hea"))

if not hea_files:
    raise FileNotFoundError(
        f"No .hea files found inside {records_dir}"
    )

record_path = hea_files[0].with_suffix("")

print(f"Loading PTB-XL record: {record_path}")

record = wfdb.rdrecord(str(record_path))

signal = record.p_signal

if signal is None:
    raise ValueError("Record contains no physical ECG signal.")

print("Original shape:", signal.shape)

# Exactly 1000 timesteps
signal = signal[:1000]

# Ensure 12 leads
if signal.shape[1] != 12:
    raise ValueError(
        f"Expected 12 leads, got {signal.shape[1]}"
    )

output = signal.tolist()

output_path = Path("demo_ecg.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f)

print(f"Created: {output_path}")
print(f"Final shape: {len(output)} x {len(output[0])}")