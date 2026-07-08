import logging
from typing import Optional
# pyrefly: ignore [missing-import]
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)
# pyrefly: ignore [missing-import]
from backend.api.websocket_manager import (
    ecg_websocket_manager,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    tags=["Live ECG Stream"]
)


@router.websocket("/ws/ecg-stream")
async def ecg_stream_websocket(
    websocket: WebSocket,
    patient_id: Optional[str] = None
):
    """
    Browser-facing WebSocket endpoint.

    Frontend connects to:

        ws://localhost:8000/ws/ecg-stream

    Or optionally:

        ws://localhost:8000/ws/ecg-stream
        ?patient_id=patient-123
    """

    await ecg_websocket_manager.connect(
        websocket=websocket,
        patient_id=patient_id
    )

    try:
        # Keep the WebSocket alive.
        #
        # The server primarily pushes Kafka telemetry
        # to the browser. Incoming client messages are
        # only used as keep-alive traffic if sent.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info(
            "Frontend ECG WebSocket disconnected."
        )

    except Exception as exc:
        logger.warning(
            "ECG WebSocket connection ended: %s",
            exc
        )

    finally:
        ecg_websocket_manager.disconnect(
            websocket=websocket,
            patient_id=patient_id
        )