import os
import threading
import logging
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
from fastapi import FastAPI

# pyrefly: ignore [missing-import]
from backend.ai.rag.embedding_service import MedicalEmbeddingService
# pyrefly: ignore [missing-import]
from backend.ai.rag.vector_store import MedicalVectorStore
# pyrefly: ignore [missing-import]
from backend.ai.rag.retriever import MedicalRetriever
# pyrefly: ignore [missing-import]
from backend.ai.llm.gemini_provider import GeminiLLMProvider
# pyrefly: ignore [missing-import]
from backend.ai.report_generator import MedicalReportGenerator

# pyrefly: ignore [missing-import]
from backend.inference.model_loader import TCNModelLoader
# pyrefly: ignore [missing-import]
from backend.inference.predictor import ECGPredictor
# pyrefly: ignore [missing-import]
from backend.kafka.consumers.ecg_consumer import ECGConsumer

# Import the report router
# pyrefly: ignore [missing-import]
from backend.api.routes.report import router as report_router

# Configure module-level logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the FastAPI application.
    Executes before the server starts receiving requests to pre-load heavy 
    AI models and database connections into memory.
    """
    logger.info("Starting CardioGuard AI API...")
    logger.info("Loading AI models and connecting to ChromaDB (this may take a moment)...")
    
    try:
        # Determine the absolute path to the project root relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../.."))
        chroma_dir = os.path.join(project_root, "chroma_db")
        model_path = os.path.join(project_root, "models", "cardioguard_model.keras")
        
        # 1. Instantiate RAG dependencies globally ONCE
        embedder = MedicalEmbeddingService()
        vector_store = MedicalVectorStore(persist_directory=chroma_dir)
        retriever = MedicalRetriever(embedding_service=embedder, vector_store=vector_store)
        llm = GeminiLLMProvider()
        
        # 2. Wrap everything in the MedicalReportGenerator orchestrator
        report_generator = MedicalReportGenerator(retriever=retriever, llm_provider=llm)
        
        # Attach the generator to the app state so HTTP routes can access it instantly
        app.state.report_generator = report_generator
        
        # 3. Instantiate Prediction & Kafka dependencies
        model_loader = TCNModelLoader(model_path=model_path)
        tcn_model = model_loader.get_model()  # Pulls weights into RAM
        predictor = ECGPredictor(model=tcn_model)
        
        consumer = ECGConsumer(
            predictor=predictor,
            report_generator=report_generator,
            broker_url="localhost:9092",
            topic_name="live_ecg_stream"
        )
        
        app.state.consumer = consumer
        
        # 4. Start the Kafka consumer in a background daemon thread
        # This allows it to run continuously without blocking the FastAPI HTTP event loop
        consumer_thread = threading.Thread(target=consumer.start_consuming, daemon=True)
        consumer_thread.start()
        app.state.consumer_thread = consumer_thread
        
        logger.info("✅ AI models and services loaded successfully. Background Kafka consumer started. API is ready for inference.")
        
        # Yield control back to FastAPI to start accepting requests
        yield
        
    except Exception as e:
        logger.critical(f"❌ Failed to initialize AI services during startup: {str(e)}")
        raise
    finally:
        # Cleanup logic executes when the application shuts down
        logger.info("Shutting down CardioGuard AI API. Cleaning up resources...")
        if hasattr(app.state, "consumer"):
            logger.info("Sending stop signal to background Kafka consumer...")
            app.state.consumer.stop_consuming()
        
        if hasattr(app.state, "consumer_thread"):
            # Give the thread a moment to cleanly flush offsets and close connections
            app.state.consumer_thread.join(timeout=3.0)
            logger.info("Background thread closed.")


# Initialize the main FastAPI application
app = FastAPI(
    title="CardioGuard AI API",
    description="Enterprise-grade AI healthcare platform API for generating RAG-backed bilingual clinical reports.",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routers
app.include_router(report_router)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Simple endpoint to verify the API is running and accessible.
    """
    return {"status": "CardioGuard AI API is active"}
