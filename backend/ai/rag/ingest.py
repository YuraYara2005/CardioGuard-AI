import logging
import os

# Import your newly created classes
from document_loader import MedicalDocumentLoader
from chunker import MedicalTextChunker
from embedding_service import MedicalEmbeddingService
from vector_store import MedicalVectorStore

# Configure logging to see what is happening in the terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_ingestion_pipeline():
    # 1. Define Paths
    # Assuming this script is run from inside backend/ai/rag/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    knowledge_dir = os.path.join(project_root, "medical_knowledge")
    chroma_dir = os.path.join(project_root, "chroma_db")

    logger.info("=== Starting CardioGuard Knowledge Ingestion ===")

    # 2. Initialize the Services
    loader = MedicalDocumentLoader()
    chunker = MedicalTextChunker(chunk_size=1000, chunk_overlap=200)
    embedder = MedicalEmbeddingService(model_name="BAAI/bge-small-en-v1.5")
    vector_store = MedicalVectorStore(persist_directory=chroma_dir)

    # 3. Execute the Pipeline
    logger.info("\n--- STEP 1: Loading Documents ---")
    pages = loader.load_directory(knowledge_dir, recursive=True)
    
    if not pages:
        logger.error("No pages loaded. Please check if your PDFs are in the medical_knowledge folder.")
        return

    logger.info("\n--- STEP 2: Chunking Text ---")
    chunks = chunker.chunk_documents(pages)

    logger.info("\n--- STEP 3: Generating Embeddings ---")
    embedded_chunks = embedder.embed_chunks(chunks)

    logger.info("\n--- STEP 4: Storing in ChromaDB ---")
    vector_store.store_chunks(embedded_chunks)

    # 4. The Ultimate Test
    logger.info("\n=== INGESTION COMPLETE. RUNNING TEST QUERY ===")
    test_query = "What is the recommended treatment for a patient with acute myocardial infarction?"
    
    logger.info(f"Test Query: '{test_query}'")
    query_vector = embedder.embed_query(test_query)
    
    results = vector_store.search_by_vector(query_vector, n_results=2)
    
    print("\n" + "="*50)
    print("🧠 CARDIOGUARD RETRIEVAL RESULTS 🧠")
    print("="*50)
    for i, res in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"Source: {res['metadata'].get('filename', 'Unknown')} (Page {res['metadata'].get('page_number', 'Unknown')})")
        print(f"Content Snippet: {res['content'][:300]}...")
        print("-" * 50)

if __name__ == "__main__":
    run_ingestion_pipeline()