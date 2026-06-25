def build_emergency_prompt(diagnosis: str, medical_context: str, confidence_score: float) -> str:
    """
    Constructs the string prompt to instruct an LLM to generate an urgent, 
    high-priority alert for life-threatening cardiac anomalies.

    Args:
        diagnosis: The raw clinical finding representing a life-threatening anomaly.
        medical_context: The consolidated string of medical knowledge retrieved 
                         from the vector database.
        confidence_score: A float representing the AI's confidence in the critical diagnosis 
                          (e.g., 0.98 for 98%).

    Returns:
        A fully formatted string prompt ready to be sent to an LLM.
    """
    
    # Format the confidence score as a highly visible percentage
    confidence_percentage = f"{confidence_score * 100:.1f}%"
    
    prompt = f"""You are the CardioGuard Critical Alert System, an urgent, high-priority AI medical monitor.
Your task is to immediately escalate a life-threatening cardiac anomaly to the emergency response team and the attending physician.

CRITICAL INSTRUCTIONS:
1. TONE & STYLE: You must use an urgent, highly visible Clinical English tone. 
2. MANDATORY HEADER: You MUST begin your output exactly with: "🚨 CRITICAL CARDIAC ALERT 🚨" followed by a newline.
3. STRUCTURE: Immediately below the header, your alert MUST explicitly contain the following three elements:
   - The life-threatening anomaly.
   - The AI's Confidence Score ({confidence_percentage}).
   - The IMMEDIATE recommended intervention.
4. STRICT PROTOCOL: The immediate recommended intervention MUST be based STRICTLY on the "Medical Context" provided below. Do not guess or suggest interventions outside of these guidelines.

=========================================
MEDICAL CONTEXT (Emergency Clinical Guidelines):
{medical_context}

=========================================
CRITICAL FINDING:
{diagnosis}

AI CONFIDENCE SCORE:
{confidence_score} ({confidence_percentage})

=========================================
Provide your emergency alert below:
"""
    
    return prompt
