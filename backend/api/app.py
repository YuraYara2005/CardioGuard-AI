import os
import asyncio
import threading
import logging
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI

# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

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

# Existing report router
# pyrefly: ignore [missing-import]
from backend.api.routes.report import router as report_router

# Existing prediction router
# pyrefly: ignore [missing-import]
from backend.api.routes.predict import router as predict_router

# NEW: WebSocket stream router
# pyrefly: ignore [missing-import]
from backend.api.routes.stream import router as stream_router

# Patients registry router
# pyrefly: ignore [missing-import]
from backend.api.routes.patients import router as patients_router

# NEW: Shared WebSocket manager
# pyrefly: ignore [missing-import]
from backend.api.websocket_manager import ecg_websocket_manager


# ============================================================
# Logging Configuration
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# FastAPI Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the FastAPI application.

    Startup:
    - Resolves project paths
    - Loads embedding model
    - Connects to ChromaDB
    - Initializes RAG retriever
    - Initializes Gemini
    - Loads all multimodal ML artifacts
    - Initializes ECG/fusion predictor
    - Binds WebSocket manager to FastAPI event loop
    - Initializes Kafka consumer
    - Starts Kafka consumer background thread

    Shutdown:
    - Stops Kafka consumer
    - Waits briefly for background thread to close
    """

    logger.info("Starting CardioGuard AI API...")

    logger.info(
        "Loading AI models, multimodal artifacts, "
        "connecting to ChromaDB, and initializing "
        "the live telemetry bridge..."
    )

    try:
        # ====================================================
        # Resolve Project Paths
        # ====================================================

        current_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        project_root = os.path.abspath(
            os.path.join(current_dir, "../..")
        )

        chroma_dir = os.path.join(
            project_root,
            "chroma_db"
        )

        models_dir = os.path.join(
            project_root,
            "models"
        )

        logger.info(
            "Project root resolved to: %s",
            project_root
        )

        logger.info(
            "Models directory resolved to: %s",
            models_dir
        )

        logger.info(
            "ChromaDB directory resolved to: %s",
            chroma_dir
        )

        # ====================================================
        # 1. Initialize RAG Dependencies
        # ====================================================

        embedder = MedicalEmbeddingService()

        vector_store = MedicalVectorStore(
            persist_directory=chroma_dir
        )

        retriever = MedicalRetriever(
            embedding_service=embedder,
            vector_store=vector_store
        )

        llm = GeminiLLMProvider()

        # ====================================================
        # 2. Initialize Medical Report Generator
        # ====================================================

        report_generator = MedicalReportGenerator(
            retriever=retriever,
            llm_provider=llm
        )

        # Store shared services on FastAPI state
        app.state.embedder = embedder
        app.state.vector_store = vector_store
        app.state.retriever = retriever
        app.state.llm = llm
        app.state.report_generator = report_generator

        logger.info(
            "RAG and report-generation services "
            "initialized successfully."
        )

        # ====================================================
        # 3. Load ALL Multimodal ML Artifacts
        # ====================================================

        model_loader = TCNModelLoader(
            models_dir=models_dir
        )

        artifacts = model_loader.get_artifacts()

        logger.info(
            "Loaded ML artifacts: %s",
            list(artifacts.keys())
        )

        # Keep references available to routes/services
        app.state.model_loader = model_loader
        app.state.ml_artifacts = artifacts

        # ====================================================
        # 4. Initialize Multimodal Predictor
        # ====================================================

        predictor = ECGPredictor(
            artifacts=artifacts
        )

        # Prediction routes access the shared predictor here
        app.state.predictor = predictor

        logger.info(
            "ECG Predictor initialized. "
            "Multimodal fusion available: %s",
            predictor.is_fusion_available()
        )

        # ====================================================
        # 5. Initialize WebSocket Telemetry Bridge
        # ====================================================

        # Get FastAPI/Uvicorn's currently running asyncio loop.
        # The Kafka consumer runs in a separate background thread,
        # so it needs this loop to safely schedule async WebSocket
        # broadcasts back to connected React clients.
        running_loop = asyncio.get_running_loop()

        ecg_websocket_manager.bind_event_loop(
            running_loop
        )

        app.state.websocket_manager = (
            ecg_websocket_manager
        )

        logger.info(
            "WebSocket telemetry bridge initialized successfully."
        )

        # ====================================================
        # 6. Initialize Kafka Consumer
        # ====================================================

        consumer = ECGConsumer(
            predictor=predictor,
            report_generator=report_generator,
            broker_url="localhost:9092",
            topic_name="live_ecg_stream"
        )

        app.state.consumer = consumer

        # ====================================================
        # 7. Start Kafka Consumer Background Thread
        # ====================================================

        consumer_thread = threading.Thread(
            target=consumer.start_consuming,
            daemon=True,
            name="cardioguard-kafka-consumer"
        )

        consumer_thread.start()

        app.state.consumer_thread = consumer_thread

        # ====================================================
        # Startup Complete
        # ====================================================

        logger.info(
            "✅ CardioGuard AI startup complete."
        )

        logger.info(
            "✅ RAG pipeline ready."
        )

        logger.info(
            "✅ Gemini provider ready."
        )

        logger.info(
            "✅ ChromaDB ready."
        )

        logger.info(
            "✅ Multimodal ML artifacts loaded."
        )

        logger.info(
            "✅ Fusion available: %s",
            predictor.is_fusion_available()
        )

        logger.info(
            "✅ Prediction endpoints ready."
        )

        logger.info(
            "✅ WebSocket endpoint ready at /ws/ecg-stream."
        )

        logger.info(
            "✅ Kafka-to-WebSocket telemetry bridge ready."
        )

        logger.info(
            "✅ Background Kafka consumer started."
        )

        logger.info(
            "✅ API is ready for inference and live telemetry."
        )

        # Give control back to FastAPI
        yield

    except Exception as e:
        logger.critical(
            "❌ Failed to initialize CardioGuard AI "
            "services during startup: %s",
            str(e),
            exc_info=True
        )

        raise

    finally:
        # ====================================================
        # Shutdown Cleanup
        # ====================================================

        logger.info(
            "Shutting down CardioGuard AI API. "
            "Cleaning up resources..."
        )

        if hasattr(app.state, "consumer"):
            logger.info(
                "Sending stop signal to "
                "background Kafka consumer..."
            )

            try:
                app.state.consumer.stop_consuming()

            except Exception as e:
                logger.error(
                    "Error while stopping Kafka consumer: %s",
                    str(e),
                    exc_info=True
                )

        if hasattr(app.state, "consumer_thread"):
            try:
                app.state.consumer_thread.join(
                    timeout=3.0
                )

                if app.state.consumer_thread.is_alive():
                    logger.warning(
                        "Background Kafka thread did not "
                        "fully stop within the timeout."
                    )
                else:
                    logger.info(
                        "Background Kafka thread closed."
                    )

            except Exception as e:
                logger.error(
                    "Error while joining Kafka thread: %s",
                    str(e),
                    exc_info=True
                )


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="CardioGuard AI API",
    description=(
        "Enterprise-grade multimodal AI healthcare "
        "platform API for ECG analysis, multimodal "
        "fusion inference, Kafka streaming, WebSocket "
        "live telemetry, and RAG-backed bilingual "
        "clinical reports."
    ),
    version="2.1.0",
    lifespan=lifespan
)


# ============================================================
# CORS Middleware
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API Routers
# ============================================================

# Report-generation endpoints:
# POST /report/generate
# POST /report/analyze
app.include_router(
    report_router
)

# Prediction endpoints:
# POST /predict/ecg
# POST /predict/multimodal
app.include_router(
    predict_router
)

# Live telemetry WebSocket:
# WS /ws/ecg-stream
app.include_router(
    stream_router
)

# Patient registry:
# GET /patients
# GET /patients/{patient_id}
app.include_router(
    patients_router
)


# ============================================================
# Health Check
# ============================================================

@app.get(
    "/health",
    tags=["Health Check"]
)
async def health_check():
    """
    Verifies that the CardioGuard API is running and
    reports readiness of prediction, fusion, loaded
    artifacts, and the WebSocket telemetry bridge.
    """

    predictor_ready = hasattr(
        app.state,
        "predictor"
    )

    fusion_available = False

    loaded_artifacts = []

    websocket_bridge_ready = hasattr(
        app.state,
        "websocket_manager"
    )

    websocket_clients = 0

    kafka_consumer_ready = hasattr(
        app.state,
        "consumer"
    )

    kafka_thread_alive = False

    if hasattr(
        app.state,
        "ml_artifacts"
    ):
        try:
            loaded_artifacts = list(
                app.state.ml_artifacts.keys()
            )

        except Exception:
            loaded_artifacts = []

    if predictor_ready:
        try:
            fusion_available = (
                app.state.predictor.is_fusion_available()
            )

        except Exception:
            fusion_available = False

    if websocket_bridge_ready:
        try:
            websocket_clients = (
                app.state
                .websocket_manager
                .connection_count
            )

        except Exception:
            websocket_clients = 0

    if hasattr(
        app.state,
        "consumer_thread"
    ):
        try:
            kafka_thread_alive = (
                app.state
                .consumer_thread
                .is_alive()
            )

        except Exception:
            kafka_thread_alive = False

    return {
        "status": "CardioGuard AI API is active",
        "predictor_ready": predictor_ready,
        "multimodal_fusion_available": fusion_available,
        "loaded_ml_artifacts": loaded_artifacts,
        "websocket_bridge_ready": websocket_bridge_ready,
        "connected_websocket_clients": websocket_clients,
        "kafka_consumer_ready": kafka_consumer_ready,
        "kafka_consumer_thread_alive": kafka_thread_alive
    }