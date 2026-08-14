import os
import pandas as pd
import numpy as np
import ast
# pyrefly: ignore [missing-import]
import wfdb
from backend.inference.model_loader import TCNModelLoader
from backend.inference.predictor import ECGPredictor

loader = TCNModelLoader(models_dir="models")
artifacts = loader.get_artifacts()
predictor = ECGPredictor(artifacts=artifacts)

df = pd.read_csv("data/ptb-xl/ptbxl_database.csv")
df.scp_codes = df.scp_codes.apply(lambda x: ast.literal_eval(x))

scp_df = pd.read_csv("data/ptb-xl/scp_statements.csv", index_col=0)
diag_df = scp_df[scp_df.diagnostic == 1]

def aggregate_diagnostic(y_dict):
    tmp = []
    for key in y_dict.keys():
        if key in diag_df.index:
            tmp.append(diag_df.loc[key].diagnostic_class)
    return list(set(tmp))

df['diagnostic_superclass'] = df.scp_codes.apply(aggregate_diagnostic)

# filter for existing records
def record_exists(row):
    return os.path.exists(os.path.join("data/ptb-xl", row.filename_lr) + ".hea")

existing_df = df[df.apply(record_exists, axis=1)]

# find 1 MI, 1 NORM, 1 STTC
mi_record = existing_df[existing_df.diagnostic_superclass.apply(lambda x: 'MI' in x)].iloc[0]
norm_record = existing_df[existing_df.diagnostic_superclass.apply(lambda x: 'NORM' in x)].iloc[0]
sttc_record = existing_df[existing_df.diagnostic_superclass.apply(lambda x: 'STTC' in x)].iloc[0]

for name, row in [("MI", mi_record), ("NORM", norm_record), ("STTC", sttc_record)]:
    record_path = os.path.join("data/ptb-xl", row.filename_lr)
    record = wfdb.rdrecord(record_path)
    ecg_data = record.p_signal
    res = predictor.analyze_ecg(ecg_data[:1000].tolist())
    print("="*40)
    print("Expected:", name, "| Record:", row.filename_lr)
    print("Input Shape:", np.array(ecg_data[:1000]).shape)
    print("Raw output:", res['class_probabilities'])
    print("Diagnosis:", res['diagnosis'])
    print("Mapped Code:", res['class_code'])
    print("Confidence:", res['confidence_score'])
