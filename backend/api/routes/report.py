import logging
from typing import List, Union
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Request
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from backend.ai.llm.gemini_provider import ReportGenerationError


# Configure module-level logger
logger = logging.getLogger(__name__)

# Initialize the router
router = APIRouter(
    prefix="/report",
    tags=["Report Generation"]
)

class DiagnosisPayload(BaseModel):
    diagnosis: str = Field(..., description="The raw clinical findings or diagnosis text.")
    confidence_score: float = Field(..., description="The AI model's confidence in the diagnosis.")
    is_emergency: bool = Field(default=False)

class ECGAnalysisRequest(BaseModel):
    patient_id: str = Field(..., example="PTB-XL-001")
    leads: Union[List[float], List[List[float]]] = Field(
        ...,
        description="Raw 12-lead ECG data array. Must be (1000, 12) or flat list of 12000 floats.",
        example=[]
    )

@router.post("/generate")
async def generate_clinical_reports(payload: DiagnosisPayload, request: Request):
    """Generates GenAI reports from a hardcoded text diagnosis."""
    logger.info(f"Received request to /generate. Emergency: {payload.is_emergency}")
    try:
        # Instantly fetch the pre-loaded AI generator from RAM
        report_generator = request.app.state.report_generator
        
        reports = report_generator.generate_reports(
            diagnosis=payload.diagnosis,
            confidence_score=payload.confidence_score,
            is_emergency=payload.is_emergency
        )
        return reports

    except ReportGenerationError as rge:
        # Map typed error to the correct HTTP status code.
        # Log the full provider error (internal only).
        # Surface only the safe Arabic message to the client.
        logger.error(
            "Report generation failed (HTTP %d): %s",
            rge.status_code,
            str(rge)
        )
        raise HTTPException(
            status_code=rge.status_code,
            detail=rge.safe_message,
        )

    except Exception as e:
        logger.error(f"Unexpected failure during report generation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="تعذر إنشاء التقرير الذكي مؤقتًا. حاول مرة أخرى لاحقًا.")

@router.post("/analyze")
async def analyze_ecg_manually(payload: ECGAnalysisRequest, request: Request):
    """Takes raw ECG floats, runs TCN Inference, and generates RAG reports if anomalous."""
    logger.info(f"Received manual ECG analysis request for {payload.patient_id}")
    try:
        # Fetch pre-loaded AI dependencies
        predictor = request.app.state.consumer.predictor
        report_generator = request.app.state.report_generator

        # 1. Run AI Inference (The TCN Model)
        inference_result = predictor.analyze_ecg(payload.leads)
        diagnosis = inference_result["diagnosis"]
        confidence = inference_result["confidence_score"]
        is_emergency = inference_result["is_emergency"]

        # 2. Trigger GenAI if anomaly detected
        reports = None
        if diagnosis != "Normal ECG" or is_emergency:
            logger.info("Anomaly detected! Generating bilingual reports...")
            clinical_finding = f"Patient {payload.patient_id} shows signs of {diagnosis}."
            reports = report_generator.generate_reports(
                diagnosis=clinical_finding,
                confidence_score=confidence,
                is_emergency=is_emergency
            )

        return {
            "patient_id": payload.patient_id,
            "inference_results": inference_result,
            "ai_reports": reports
        }

    except ReportGenerationError as rge:
        logger.error(
            "Report generation failed for %s (HTTP %d): %s",
            payload.patient_id,
            rge.status_code,
            str(rge)
        )
        raise HTTPException(
            status_code=rge.status_code,
            detail=rge.safe_message,
        )

    except Exception as e:
        logger.error(f"Critical failure during ECG analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="تعذر إنشاء التقرير الذكي مؤقتًا. حاول مرة أخرى لاحقًا.")