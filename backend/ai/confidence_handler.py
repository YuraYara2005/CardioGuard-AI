def get_confidence_tier(score: float) -> str:
    """Returns a textual tier based on confidence score."""
    if score >= 0.8:
        return "high"
    elif score >= 0.5:
        return "moderate"
    else:
        return "low"

def get_confidence_disclaimer(score: float) -> str:
    """Returns a clinical warning disclaimer based on confidence score."""
    tier = get_confidence_tier(score)
    if tier == "low":
        return "Low-confidence prediction — clinical verification required"
    return ""

def get_severity_from_confidence(score: float) -> str:
    """Determine the severity level based on AI confidence."""
    if score >= 0.8:
        return "critical"
    elif score >= 0.5:
        return "urgent"
    else:
        return "review"
