import asyncio
import logging
from typing import Any, Dict, Optional, Set
# pyrefly: ignore [missing-import]
from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ECGWebSocketManager:
    """
    Manages all active frontend WebSocket connections.

    Supports:
    - Global telemetry subscribers
    - Optional patient-specific subscribers
    - Broadcasting from the Kafka consumer background thread
    """

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

        self.patient_connections: Dict[
            str,
            Set[WebSocket]
        ] = {}

        self._loop: Optional[
            asyncio.AbstractEventLoop
        ] = None


    # ========================================================
    # Event Loop Binding
    # ========================================================

    def bind_event_loop(
        self,
        loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Store FastAPI's running asyncio event loop.

        This allows the Kafka consumer thread to safely
        schedule WebSocket broadcasts.
        """

        self._loop = loop

        logger.info(
            "ECG WebSocket manager bound to FastAPI event loop."
        )


    # ========================================================
    # Connect
    # ========================================================

    async def connect(
        self,
        websocket: WebSocket,
        patient_id: Optional[str] = None
    ) -> None:

        await websocket.accept()

        if patient_id:
            if patient_id not in self.patient_connections:
                self.patient_connections[patient_id] = set()

            self.patient_connections[
                patient_id
            ].add(websocket)

            logger.info(
                "Patient-specific WebSocket connected: %s",
                patient_id
            )

        else:
            self.active_connections.add(websocket)

            logger.info(
                "Global ECG WebSocket connected."
            )

        logger.info(
            "Total WebSocket clients: %d",
            self.connection_count
        )


    # ========================================================
    # Disconnect
    # ========================================================

    def disconnect(
        self,
        websocket: WebSocket,
        patient_id: Optional[str] = None
    ) -> None:

        if patient_id:
            connections = self.patient_connections.get(
                patient_id
            )

            if connections:
                connections.discard(websocket)

                if not connections:
                    self.patient_connections.pop(
                        patient_id,
                        None
                    )

        else:
            self.active_connections.discard(
                websocket
            )

        logger.info(
            "ECG WebSocket disconnected. "
            "Remaining clients: %d",
            self.connection_count
        )


    # ========================================================
    # Broadcast
    # ========================================================

    async def broadcast(
        self,
        payload: Dict[str, Any]
    ) -> None:

        patient_id = payload.get(
            "patient_id"
        )

        targets: Set[WebSocket] = set(
            self.active_connections
        )

        if patient_id:
            targets.update(
                self.patient_connections.get(
                    str(patient_id),
                    set()
                )
            )

        if not targets:
            return

        disconnected: Set[WebSocket] = set()

        for websocket in targets:
            try:
                await websocket.send_json(
                    payload
                )

            except Exception:
                disconnected.add(
                    websocket
                )

        for websocket in disconnected:
            self.active_connections.discard(
                websocket
            )

            for connections in (
                self.patient_connections.values()
            ):
                connections.discard(
                    websocket
                )


    # ========================================================
    # Thread-Safe Publish
    # ========================================================

    def publish_from_thread(
        self,
        payload: Dict[str, Any]
    ) -> None:
        """
        Called from the Kafka consumer background thread.

        Safely schedules the async WebSocket broadcast
        on FastAPI's event loop.
        """

        if self._loop is None:
            logger.debug(
                "WebSocket event loop not available yet."
            )
            return

        if self._loop.is_closed():
            logger.warning(
                "Cannot publish telemetry because "
                "FastAPI event loop is closed."
            )
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                self.broadcast(payload),
                self._loop
            )

            def handle_result(done_future):
                try:
                    done_future.result()
                except Exception as exc:
                    logger.error(
                        "WebSocket broadcast failed: %s",
                        exc,
                        exc_info=True
                    )

            future.add_done_callback(
                handle_result
            )

        except Exception as exc:
            logger.error(
                "Failed to schedule WebSocket broadcast: %s",
                exc,
                exc_info=True
            )


    # ========================================================
    # Connection Count
    # ========================================================

    @property
    def connection_count(self) -> int:

        patient_count = sum(
            len(connections)
            for connections
            in self.patient_connections.values()
        )

        return (
            len(self.active_connections)
            + patient_count
        )


# Shared singleton used by:
# - FastAPI WebSocket route
# - Kafka consumer background thread

ecg_websocket_manager = ECGWebSocketManager()