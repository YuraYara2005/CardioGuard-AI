import logging
from typing import Dict, List
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predict",
    tags=["Prediction"]
)


# ============================================================
# Request Schemas
# ============================================================

class StandaloneECGRequest(BaseModel):
    """
    Raw 12-lead ECG data.

    Accepted shapes:
    - (1000, 12)
    - (12, 1000)
    - flat list divisible by 12

    The predictor handles padding/truncation to 1000 timesteps.
    """
    leads_data: List


class LabValues(BaseModel):
    troponin: float
    ck_mb: float = Field(alias="ck-mb")
    bnp: float
    creatinine: float
    hba1c: float

    model_config = {
        "populate_by_name": True
    }


class MultimodalPredictionRequest(BaseModel):
    """
    Complete multimodal fusion request.
    """

    # ECG signal
    leads_data: List

    # ECG image already resized to 224x224x3
    image_data: List

    # Exactly five lab values
    labs: LabValues

    # Patient identity (optional for backward compatibility)
    patient_id: str = Field(default=None)

    # Metadata
    age: float
    blood_pressure: float
    heart_rate: float
    sex: str

    symptoms: List[str] = Field(
        default_factory=list
    )


# ============================================================
# Standalone ECG Endpoint
# ============================================================

@router.post("/ecg")
async def predict_ecg(
    payload: StandaloneECGRequest,
    request: Request
):
    """
    Run standalone ECG inference.

    Pipeline:
    raw ECG
        -> preprocessing
        -> ECG model
        -> 5-class prediction
    """

    predictor = getattr(
        request.app.state,
        "predictor",
        None
    )

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="ECG predictor is not initialized."
        )

    try:
        result = predictor.analyze_ecg(
            leads_data=payload.leads_data
        )

        return {
            "status": "success",
            "mode": "standalone_ecg",
            "result": result
        }

    except ValueError as exc:
        logger.warning(
            "Invalid ECG prediction request: %s",
            exc
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        logger.exception(
            "Standalone ECG inference failed."
        )

        raise HTTPException(
            status_code=500,
            detail=f"ECG inference failed: {exc}"
        ) from exc


# ============================================================
# Multimodal Fusion Endpoint
# ============================================================

@router.post("/multimodal")
async def predict_multimodal(
    payload: MultimodalPredictionRequest,
    request: Request
):
    """
    Run complete multimodal fusion inference.

    Pipeline:

    ECG
      -> ECG feature extractor
      -> 128 features

    ECG image
      -> image feature extractor
      -> 1280 features
      -> projection model
      -> 128 features

    Labs
      -> 5 features

    Metadata
      -> scaler
      -> sex encoder
      -> symptom encoder
      -> 9 features

    All four branches
      -> fusion model
      -> 5-class prediction
    """

    predictor = getattr(
        request.app.state,
        "predictor",
        None
    )

    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="ECG predictor is not initialized."
        )

    if not predictor.is_fusion_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Multimodal fusion artifacts "
                "are not fully available."
            )
        )

    try:
        # Convert Pydantic object into the exact dictionary
        # expected by predictor._preprocess_labs()
        labs_dict: Dict[str, float] = {
            "troponin": payload.labs.troponin,
            "ck-mb": payload.labs.ck_mb,
            "bnp": payload.labs.bnp,
            "creatinine": payload.labs.creatinine,
            "hba1c": payload.labs.hba1c,
        }

        result = predictor.analyze_multimodal(
            leads_data=payload.leads_data,
            image_data=payload.image_data,
            labs=labs_dict,
            age=payload.age,
            blood_pressure=payload.blood_pressure,
            heart_rate=payload.heart_rate,
            sex=payload.sex,
            symptoms=payload.symptoms,
        )

        return {
            "status": "success",
            "mode": "multimodal_fusion",
            "patient_id": payload.patient_id,
            "result": result
        }

    except ValueError as exc:
        logger.warning(
            "Invalid multimodal prediction request: %s",
            exc
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        logger.exception(
            "Multimodal fusion inference failed."
        )

        raise HTTPException(
            status_code=500,
            detail=f"Multimodal inference failed: {exc}"
        ) from exc