import logging
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Request

import backend.services.episodes_db as episodes_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/episodes",
    tags=["Episodes"]
)

@router.get("/{patient_id}")
async def get_patient_episodes(patient_id: str):
    """List all frozen emergency episodes for a patient."""
    episodes = episodes_db.get_episodes_by_patient(patient_id)
    # Exclude heavy leads_data and attention_weights from list view
    from backend.api.routes.patients import _DEMO_PATIENTS
    for ep in episodes:
        ep.pop("leads_data", None)
        ep.pop("attention_weights", None)
        pt = next((p for p in _DEMO_PATIENTS if p.id == ep["patient_id"]), None)
        ep["patient_name"] = pt.name if pt else "Unknown Patient"
    return {"status": "success", "episodes": episodes}

@router.get("/detail/{episode_id}")
async def get_episode_detail(episode_id: int):
    """Get exact frozen episode including full ECG window and XAI."""
    episode = episodes_db.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    import json
    episode["leads_data"] = json.loads(episode["leads_data"])
    episode["attention_weights"] = json.loads(episode["attention_weights"])
    return {"status": "success", "episode": episode}

@router.post("/{episode_id}/generate-emergency-report")
async def generate_emergency_report(episode_id: int, request: Request):
    """Manually trigger the generation of an emergency RAG report for a frozen episode."""
    episode = episodes_db.get_episode_by_id(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    report_generator = getattr(request.app.state, "report_generator", None)
    if not report_generator:
        raise HTTPException(status_code=503, detail="Report generator not initialized")

    try:
        diagnosis_str = f"Patient {episode['patient_id']} experienced an emergency event of type: {episode['diagnosis']} at {episode['detected_at']}."
        
        # 1. Generate Raw JSON from LLM via Report Generator
        if hasattr(report_generator, "generate_structured_emergency_report"):
            raw_llm_json = report_generator.generate_structured_emergency_report(diagnosis_str, episode["confidence_score"])
        else:
            raise HTTPException(status_code=500, detail="Report generator lacks structured support.")
            
        # 2. Validate and Normalize LLM Output
        # pyrefly: ignore [missing-import]
        from backend.ai.validator import safe_parse_llm_json
        llm_report = safe_parse_llm_json(raw_llm_json)
        
        # 3. Get Patient Data
        from backend.api.routes.patients import _DEMO_PATIENTS
        pt = next((p for p in _DEMO_PATIENTS if p.id == episode["patient_id"]), None)
        patient_name = pt.name if pt else "Unknown Patient"
        blood_type = pt.bloodType if pt else "Unknown"
        
        # 4. Format Final Report Structure
        # pyrefly: ignore [missing-import]
        from backend.ai.formatter import format_structured_emergency_report
        report_text = format_structured_emergency_report(
            episode_id=episode_id,
            patient_id=episode["patient_id"],
            patient_name=patient_name,
            blood_type=blood_type,
            detected_at=episode["detected_at"],
            predicted_class=episode["diagnosis"],
            predicted_label=episode["anomaly_type"],
            confidence_score=episode["confidence_score"],
            llm_report=llm_report
        )
        
        episodes_db.update_episode_report(episode_id, report_text)
        
        return {"status": "success", "report": report_text}
    except Exception as e:
        logger.error(f"Failed to generate emergency report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
