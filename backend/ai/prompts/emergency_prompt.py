def build_emergency_prompt(diagnosis: str, medical_context: str, confidence_score: float) -> str:
    """
    Constructs the string prompt to instruct an LLM to generate a structured 
    JSON report for life-threatening cardiac anomalies.
    """
    confidence_percentage = f"{confidence_score * 100:.1f}%"
    
    if confidence_score < 0.8:
        confidence_instruction = f"""
   - Confidence is {confidence_percentage} (LOW/MODERATE). You MUST use cautious language such as "AI analysis detected a possible pattern associated with...".
   - Do NOT use certainty language like "confirmed", "definitive", "diagnosed", or "life-threatening anomaly detected".
   - State clearly that clinical verification is required."""
    else:
        confidence_instruction = f"""
   - Confidence is {confidence_percentage} (HIGH). You may use stronger language such as "AI analysis indicates a pattern associated with...", but you must NOT present it as a final, confirmed diagnosis."""

    prompt = f"""You are an advanced medical AI providing clinical decision support for cardiologists.
Your task is to analyze an ECG anomaly and provide a structured JSON report.

CRITICAL INSTRUCTIONS:
1. TONE & STYLE: Use concise, professional clinical language. Do NOT use emojis, asterisks, ALL CAPS, dramatic AI phrasing, or claim a confirmed diagnosis.
2. CONFIDENCE AWARENESS:{confidence_instruction}
3. OUTPUT FORMAT: You must output strictly valid JSON conforming to the following schema. Do NOT wrap in markdown blocks like ```json.
{{
  "clinical_interpretation": "A short, professional paragraph interpreting the finding. Do not use asterisks or markdown. Mention the anomaly and confidence context.",
  "recommended_actions": [
    "First clinical recommendation based on the medical context.",
    "Second clinical recommendation...",
    "..."
  ],
  "retrieved_context_summary": "A brief summary of the evidence-grounded guidelines applied."
}}

=========================================
MEDICAL CONTEXT (Emergency Clinical Guidelines):
{medical_context}

=========================================
CRITICAL FINDING:
{diagnosis}
"""
    
    return prompt
