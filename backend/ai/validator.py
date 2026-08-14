import json
import logging
from typing import List
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

class LLMEmergencyReport(BaseModel):
    clinical_interpretation: str = Field(default="Clinical interpretation unavailable.")
    recommended_actions: List[str] = Field(default_factory=lambda: ["Urgent clinical assessment recommended."])
    retrieved_context_summary: str = Field(default="Context retrieval failed.")

def safe_parse_llm_json(raw_text: str) -> LLMEmergencyReport:
    """Safely parses JSON from the LLM, handling markdown fences and malformed output."""
    cleaned_text = raw_text.strip()
    
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:-3].strip()
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:-3].strip()
        
    try:
        data = json.loads(cleaned_text)
        return LLMEmergencyReport(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse or validate LLM output as JSON. Error: {e}")
        # Safe fallback
        return LLMEmergencyReport(
            clinical_interpretation="Failed to generate structured interpretation. Please review the raw ECG.",
            recommended_actions=["Manual review required.", "Clinical correlation required."],
            retrieved_context_summary="Could not parse retrieved context."
        )
