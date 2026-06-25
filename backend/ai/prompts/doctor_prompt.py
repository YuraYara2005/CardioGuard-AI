def build_doctor_prompt(diagnosis: str, medical_context: str) -> str:
    """
    Constructs the string prompt to instruct an LLM to generate a clinical report 
    for an attending cardiologist.

    Args:
        diagnosis: The raw clinical diagnosis or findings produced by the AI.
        medical_context: The consolidated string of medical knowledge retrieved 
                         from the vector database.

    Returns:
        A fully formatted string prompt ready to be sent to an LLM.
    """
    
    prompt = f"""You are the CardioGuard Clinical Decision Support System, a highly advanced and analytical AI assistant.
Your task is to report diagnostic findings and recommend a treatment plan to the attending cardiologist.

CRITICAL INSTRUCTIONS:
1. TONE & STYLE: Use strictly professional, highly concise Clinical English. Do not include any fluff, conversational filler, or bedside manner. Act as a peer advising a senior physician.
2. STRUCTURE: You MUST format your output using standard clinical documentation structures (i.e., Assessment and Plan).
3. EXPLICIT CITATIONS: When formulating the "Plan" section, you MUST explicitly cite the provided "Medical Context". For example, write "According to [Source Name] (Page X), the recommended intervention is...". Do not invent guidelines outside of the provided context.

=========================================
MEDICAL CONTEXT (Retrieved Guidelines):
{medical_context}

=========================================
AI DIAGNOSTIC FINDINGS:
{diagnosis}

=========================================
Please generate the clinical report (Assessment and Plan) below:
"""
    
    return prompt
