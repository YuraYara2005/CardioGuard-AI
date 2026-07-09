import json
# pyrefly: ignore [missing-import]
import wfdb
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
from pathlib import Path

# Use a real PTB-XL record already on your computer
record_path = r"D:\CardioGuardAI\data\ptb-xl\records100\01000\01000_lr"

# Read the real 12-lead ECG
record = wfdb.rdrecord(record_path)
signal = record.p_signal  # shape should be (1000, 12)

print("ECG shape:", signal.shape)
print("Lead names:", record.sig_name)

# Create output folder
out = Path("demo_files")
out.mkdir(exist_ok=True)

# --------------------------------------------------
# 1. ECG JSON
# --------------------------------------------------
# Save as nested [1000][12] array
ecg_json = signal.tolist()

with open(out / "ptbxl_ecg.json", "w", encoding="utf-8") as f:
    json.dump(ecg_json, f)

# --------------------------------------------------
# 2. ECG IMAGE
# --------------------------------------------------
plt.figure(figsize=(14, 6))

# Plot Lead II if available, otherwise second lead
lead_index = 1
plt.plot(signal[:, lead_index])

plt.title("PTB-XL ECG - Lead II")
plt.xlabel("Sample")
plt.ylabel("Amplitude (mV)")
plt.grid(True)
plt.tight_layout()

plt.savefig(
    out / "ptbxl_ecg.png",
    dpi=200,
    bbox_inches="tight"
)

plt.close()

print("Created:")
print(out / "ptbxl_ecg.json")
print(out / "ptbxl_ecg.png")