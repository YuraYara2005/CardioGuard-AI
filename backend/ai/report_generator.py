import logging
from typing import Any, Dict, Optional

# pyrefly: ignore [missing-import]
from backend.ai.prompts.doctor_prompt import build_doctor_prompt
# pyrefly: ignore [missing-import]
from backend.ai.prompts.patient_prompt import build_patient_prompt
# pyrefly: ignore [missing-import]
from backend.ai.prompts.emergency_prompt import build_emergency_prompt
# pyrefly: ignore [missing-import]
from backend.ai.llm.gemini_provider import ReportGenerationError

# Configure module-level logger
logger = logging.getLogger(__name__)

class MedicalReportGenerator:
    """
    The orchestration layer for the CardioGuard GenAI reporting system.
    
    This class coordinates between the RAG Retriever (for fetching clinical context)
    and the LLM Provider (for generating reports). It uses specialized prompt builders
    to generate distinct, audience-specific reports simultaneously.

    Raises:
        ReportGenerationError: If any LLM call fails. The caller is responsible
            for deciding whether to surface this as an HTTP error or log-and-continue.
    """

    def __init__(self, retriever: Any, llm_provider: Any, log_level: int = logging.INFO):
        """
        Initializes the MedicalReportGenerator with required dependencies.

        Args:
            retriever: An instance of MedicalRetriever (or compatible) for fetching context.
            llm_provider: An instance of an LLM client (e.g., GeminiLLMProvider) for inference.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        self.retriever = retriever
        self.llm_provider = llm_provider
        
        logger.info("MedicalReportGenerator initialized with injected Retriever and LLM Provider.")

    def generate_reports(self, diagnosis: str, confidence_score: float, is_emergency: bool = False) -> Dict[str, Optional[str]]:
        """
        Coordinates the generation of multi-audience clinical reports.

        Args:
            diagnosis: The AI-generated clinical findings.
            confidence_score: The AI's confidence in the diagnosis (e.g., 0.95).
            is_emergency: Flag indicating if the diagnosis is a critical anomaly.

        Returns:
            A dictionary containing the generated reports:
            {
                "doctor_report": str,
                "patient_report": str,
                "emergency_alert": str or None
            }

        Raises:
            ReportGenerationError: If the LLM provider fails (quota exceeded,
                service unavailable, etc.). The caller must handle this and
                decide whether to return an HTTP error or log-and-continue.
        """
        logger.info(f"Starting report generation workflow for diagnosis. Emergency: {is_emergency}")

        results: Dict[str, Optional[str]] = {
            "doctor_report": None,
            "patient_report": None,
            "emergency_alert": None
        }

        # 1. Fetch Medical Context
        logger.info("Fetching clinical context via Retriever...")
        try:
            # We use the diagnosis as the query to fetch highly relevant guidelines
            medical_context = self.retriever.retrieve_context(query=diagnosis, n_results=5)
        except Exception as e:
            logger.error(f"Failed to fetch medical context. Falling back to empty context. Error: {str(e)}")
            medical_context = "No medical context available due to retrieval error."

        # 2. Generate Doctor's Clinical Report
        # ReportGenerationError from the LLM is intentionally NOT caught here —
        # it propagates to the caller so HTTP routes can return a proper error code.
        logger.info("Generating Doctor's Clinical Report...")
        doctor_prompt = build_doctor_prompt(diagnosis, medical_context)
        results["doctor_report"] = self.llm_provider.generate_response(doctor_prompt)

        # 3. Generate Patient's Egyptian Arabic Report
        logger.info("Generating Patient's Bilingual Report (Egyptian Arabic)...")
        patient_prompt = build_patient_prompt(diagnosis, medical_context)
        results["patient_report"] = self.llm_provider.generate_response(patient_prompt)

        # 4. Generate Emergency Alert (if flagged)
        if is_emergency:
            logger.warning("Emergency flag detected. Generating Critical Alert...")
            emergency_prompt = build_emergency_prompt(diagnosis, medical_context, confidence_score)
            results["emergency_alert"] = self.llm_provider.generate_response(emergency_prompt)
        else:
            logger.debug("Non-emergency diagnosis. Skipping Emergency Alert generation.")

        logger.info("Report generation workflow completed.")
        return results
