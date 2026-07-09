import os, sys, traceback
from dotenv import load_dotenv

from backend.ai.llm.gemini_provider import GeminiLLMProvider
from backend.ai.report_generator import MedicalReportGenerator

class DummyRetriever:
    def retrieve_context(self, query, n_results):
        return "Mock guidelines: treat MI with aspirin."

def main():
    load_dotenv()
    llm = GeminiLLMProvider()
    retriever = DummyRetriever()
    gen = MedicalReportGenerator(retriever, llm)
    
    print("Testing generate_reports...")
    try:
        res = gen.generate_reports("Patient P001 shows signs of Myocardial Infarction.", 0.94, True)
        print("SUCCESS:", res.keys())
    except Exception as e:
        print("FAILED with Exception:", type(e))
        print("Exception msg:", str(e))
        traceback.print_exc()

if __name__ == "__main__":
    main()
