import json
from datetime import datetime
# pyrefly: ignore [missing-import]
from backend.ai.validator import LLMEmergencyReport
# pyrefly: ignore [missing-import]
from backend.ai.confidence_handler import get_confidence_disclaimer, get_severity_from_confidence

def format_structured_emergency_report(
    episode_id: int,
    patient_id: str,
    patient_name: str,
    blood_type: str,
    detected_at: str,
    predicted_class: str,
    predicted_label: str,
    confidence_score: float,
    llm_report: LLMEmergencyReport
) -> str:
    """
    Constructs the final structured JSON report string, merging deterministic 
    application data with the validated LLM output.
    """
    severity = get_severity_from_confidence(confidence_score)
    disclaimer = get_confidence_disclaimer(confidence_score)
    
    base_disclaimer = "AI-generated clinical decision support. Not a final diagnosis. Clinical correlation and qualified medical review are required."
    
    report_dict = {
        "schema_version": 1,
        "report_type": "emergency_clinical_report",
        "report_id": f"REP-{episode_id}",
        "episode_id": episode_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "severity": severity,
        "patient": {
            "id": patient_id,
            "name": patient_name,
            "blood_type": blood_type
        },
        "episode": {
            "detected_at": detected_at,
            "predicted_class": predicted_class,
            "predicted_label": predicted_label,
            "confidence": confidence_score
        },
        "clinical_interpretation": llm_report.clinical_interpretation,
        "recommended_actions": llm_report.recommended_actions,
        "xai_summary": "Highlighted regions indicate timesteps receiving greater attention weight during model processing; they should not be interpreted as causal proof.",
        "retrieved_context_summary": llm_report.retrieved_context_summary,
        "confidence_disclaimer": disclaimer,
        "disclaimer": base_disclaimer
    }
    
    return json.dumps(report_dict)
