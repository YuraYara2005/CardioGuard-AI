import os
import logging
from typing import Optional

# Using the new Google Gen AI SDK
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Configure module-level logger
logger = logging.getLogger(__name__)

class GeminiLLMProvider:
    """
    A client wrapper for the Google Gemini API using the modern google-genai SDK.
    """

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model_name: str = "gemini-2.5-flash",
        log_level: int = logging.INFO
    ):
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        load_dotenv()

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.critical("No Gemini API key provided. Ensure GEMINI_API_KEY is set in your .env file.")
            raise ValueError("Missing Gemini API Key. Cannot initialize LLM Provider.")

        self.model_name = model_name

        try:
            logger.info(f"Configuring modern Google Gen AI client using model '{self.model_name}'...")
            # New SDK initialization
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client successfully configured.")
        except Exception as e:
            logger.critical(f"Failed to initialize the Gemini client: {str(e)}")
            raise RuntimeError(f"Generative AI Initialization Error: {str(e)}") from e

    def generate_response(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            logger.warning("An empty prompt was provided to the LLM. Returning empty response.")
            return ""

        logger.info(f"Sending prompt to {self.model_name} (Length: {len(prompt)} characters)...")

        try:
            # Modern SDK method for generation
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            if not response.text:
                logger.error("Response blocked or empty.")
                return "Error: The model returned an empty response. This could be due to safety filters or a network issue."
                
            generated_text = response.text
            logger.info(f"Successfully generated response (Length: {len(generated_text)} characters).")
            return generated_text

        except Exception as e:
            error_msg = f"Failed to generate response from modern Gemini API: {str(e)}"
            logger.error(error_msg)
            return f"Error: Unable to generate LLM response. {str(e)}"