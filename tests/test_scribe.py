import sys
import os
import logging

# 1. Path Fix: Tell Python to look at the main project folder for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

# Now these imports will work perfectly
from backend.ai.rag.embedding_service import MedicalEmbeddingService
from backend.ai.rag.vector_store import MedicalVectorStore
from backend.ai.rag.retriever import MedicalRetriever
from backend.ai.prompts.patient_prompt import build_patient_prompt
from backend.ai.llm.gemini_provider import GeminiLLMProvider

# Keep the terminal clean
logging.getLogger("httpx").setLevel(logging.WARNING)

def run_scribe_test():
    # 2. Setup ChromaDB path correctly from the tests folder
    chroma_dir = os.path.join(project_root, "chroma_db")

    print("🔌 Initializing CardioGuard AI Layer...")
    embedder = MedicalEmbeddingService()
    vector_store = MedicalVectorStore(persist_directory=chroma_dir)
    retriever = MedicalRetriever(embedding_service=embedder, vector_store=vector_store)
    llm = GeminiLLMProvider()

    # 3. Simulate the AI model's diagnosis (Pretending the TCN model flagged this)
    mock_diagnosis = "Patient exhibits signs of Atrial Fibrillation (AFib) with a rapid ventricular response."
    print(f"\n⚠️ Simulated TCN Diagnosis: {mock_diagnosis}")

    # 4. Retrieve Medical Context
    print("📚 Retrieving AHA/ESC context from ChromaDB...")
    context = retriever.retrieve_context("What is the guideline treatment for Atrial Fibrillation?")

    # 5. Build the Prompt
    print("📝 Constructing the Egyptian Arabic patient prompt...")
    final_prompt = build_patient_prompt(diagnosis=mock_diagnosis, medical_context=context)

    # 6. Generate the Bilingual Report
    print("✨ Generating patient report via Gemini (this takes a few seconds)...\n")
    report = llm.generate_response(final_prompt)

    print("="*60)
    print("🩺 CARDIOGUARD PATIENT SCRIBE OUTPUT (العامية المصرية) 🩺")
    print("="*60)
    print(report)
    print("="*60)

if __name__ == "__main__":
    run_scribe_test()