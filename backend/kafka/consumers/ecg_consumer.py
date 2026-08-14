import json
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

try:
    # pyrefly: ignore [missing-import]
    from confluent_kafka import Consumer, KafkaError
except ImportError:
    Consumer = None
    KafkaError = None

from backend.api.websocket_manager import ecg_websocket_manager
import backend.services.episodes_db as episodes_db
from datetime import datetime

logger = logging.getLogger(__name__)

ENABLE_STREAMING_GENAI: bool = False
REPORT_COOLDOWN_SECONDS: int = 1800  # 30 minutes

class ECGConsumer:
    def __init__(
        self,
        predictor: Any,
        report_generator: Any,
        broker_url: str = "localhost:9092",
        topic_name: str = "live_ecg_stream",
        group_id: str = "cardioguard_inference_group",
        log_level: int = logging.INFO
    ):
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        if Consumer is None:
            logger.critical("confluent-kafka is not installed.")
            raise ImportError("Cannot initialize consumer because 'confluent-kafka' is not installed.")

        self.predictor = predictor
        self.report_generator = report_generator
        self.broker_url = broker_url
        self.topic_name = topic_name
        self.is_running = False

        self.patient_states: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "buffer": [],
            "state": "NORMAL", # NORMAL, CAPTURING, COOLDOWN
            "post_trigger_count": 0,
            "trigger_index": -1,
            "trigger_timestamp": 0,
            "diagnosis": "",
            "confidence": 0.0,
            "anomaly_type": "",
            "cooldown_until": 0.0,
            "frame_count": 0
        })

        try:
            logger.info("Initializing Kafka Consumer connecting to '%s'...", self.broker_url)
            self.consumer = Consumer({
                "bootstrap.servers": self.broker_url,
                "group.id": group_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            })
            logger.info("Kafka Consumer successfully initialized.")
        except Exception as exc:
            logger.critical("Failed to initialize Kafka Consumer: %s", exc)
            raise

    def stop_consuming(self) -> None:
        logger.info("Stop signal received for Kafka Consumer.")
        self.is_running = False

    @staticmethod
    def _normalize_timestamp(timestamp: Any) -> int:
        if timestamp is None:
            return int(time.time() * 1000)
        try:
            value = float(timestamp)
            if value < 10_000_000_000:
                value *= 1000
            return int(value)
        except (TypeError, ValueError):
            return int(time.time() * 1000)

    def _broadcast_raw_sample(self, patient_id: str, leads: List[float], timestamp: Any) -> None:
        ecg_value = float(leads[1] if len(leads) > 1 else leads[0])
        stream_payload = {
            "type": "raw_sample",
            "timestamp": self._normalize_timestamp(timestamp),
            "ecg_value": ecg_value,
            "patient_id": str(patient_id),
            "is_emergency": False,
            "lead": "Lead II",
        }
        ecg_websocket_manager.publish_from_thread(stream_payload)

    def _broadcast_inference_result(self, patient_id: str, leads: List[float], timestamp: Any, result: Dict[str, Any]) -> None:
        diagnosis = result.get("diagnosis", "Unknown")
        confidence = float(result.get("confidence_score", 0.0))
        is_emergency = bool(result.get("is_emergency", False))
        ecg_value = float(leads[1] if len(leads) > 1 else leads[0])

        stream_payload = {
            "type": "inference_result",
            "timestamp": self._normalize_timestamp(timestamp),
            "ecg_value": ecg_value,
            "patient_id": str(patient_id),
            "is_emergency": is_emergency,
            "anomaly_type": diagnosis,
            "confidence": confidence,
            "lead": "Lead II",
        }
        ecg_websocket_manager.publish_from_thread(stream_payload)

    def start_consuming(self) -> None:
        logger.info("Subscribing to topic '%s'...", self.topic_name)
        self.consumer.subscribe([self.topic_name])
        logger.info("Starting consumption loop. Waiting for live ECG streams...")
        self.is_running = True

        try:
            while self.is_running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None: continue
                if msg.error():
                    if KafkaError is not None and msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error("Kafka error occurred: %s", msg.error())
                    continue

                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    patient_id = str(payload.get("patient_id", ""))
                    leads = payload.get("leads", [])
                    timestamp = payload.get("timestamp")

                    if not patient_id or not isinstance(leads, list) or len(leads) != 12:
                        continue
                    try:
                        leads = [float(value) for value in leads]
                    except (TypeError, ValueError):
                        continue

                    # 3. Broadcast RAW Sample Immediately
                    self._broadcast_raw_sample(patient_id, leads, timestamp)

                    # 4. State Machine Buffer Update
                    state_info = self.patient_states[patient_id]
                    state_info["buffer"].append(leads)
                    state_info["frame_count"] += 1

                    if len(state_info["buffer"]) > 1500:
                        # Optimization: pop multiple to amortize cost if it were a list, 
                        # but keeping it simple. For high frequency, a deque is better. 
                        # Since we are using a list currently, pop(0) is slow. 
                        # We'll just slice the list periodically instead of pop(0) every frame.
                        state_info["buffer"] = state_info["buffer"][-1000:]
                    
                    if state_info["state"] == "COOLDOWN":
                        if time.time() > state_info["cooldown_until"]:
                            state_info["state"] = "NORMAL"

                    if state_info["state"] == "CAPTURING":
                        state_info["post_trigger_count"] += 1
                        if state_info["post_trigger_count"] >= 250:
                            episode_data = state_info["buffer"][-1000:]
                            # Run XAI once per finalized emergency event
                            result = self.predictor.analyze_ecg(episode_data)
                            attention_weights = result.get("attention_weights", [])
                            
                            episodes_db.save_episode(
                                patient_id=patient_id,
                                detected_at=datetime.fromtimestamp(state_info["trigger_timestamp"]/1000.0).isoformat(),
                                finalized_at=datetime.utcnow().isoformat(),
                                diagnosis=state_info["diagnosis"],
                                confidence_score=state_info["confidence"],
                                anomaly_type=state_info["anomaly_type"],
                                trigger_index=750,
                                trigger_timestamp=state_info["trigger_timestamp"],
                                leads_data=episode_data,
                                attention_weights=attention_weights
                            )
                            ecg_websocket_manager.publish_from_thread({
                                "type": "emergency_episode_frozen",
                                "patient_id": patient_id
                            })
                            
                            state_info["state"] = "COOLDOWN"
                            state_info["cooldown_until"] = time.time() + REPORT_COOLDOWN_SECONDS
                        continue

                    # If NORMAL or COOLDOWN, run inference periodically (every 250 frames)
                    if len(state_info["buffer"]) < 1000:
                        continue
                        
                    if state_info["frame_count"] % 250 != 0:
                        continue

                    leads_data = state_info["buffer"][-1000:]
                    result = self.predictor.analyze_ecg(leads_data)

                    diagnosis = result.get("diagnosis", "Unknown")
                    confidence = float(result.get("confidence_score", 0.0))
                    is_emergency = bool(result.get("is_emergency", False))

                    self._broadcast_inference_result(patient_id, leads, timestamp, result)

                    if is_emergency and state_info["state"] == "NORMAL":
                        logger.warning("Emergency detected for %s. Transitioning to CAPTURING.", patient_id)
                        state_info["state"] = "CAPTURING"
                        state_info["trigger_timestamp"] = self._normalize_timestamp(timestamp)
                        state_info["post_trigger_count"] = 0
                        state_info["diagnosis"] = diagnosis
                        state_info["confidence"] = confidence
                        state_info["anomaly_type"] = diagnosis

                except json.JSONDecodeError:
                    pass
                except Exception as exc:
                    logger.error("Error processing incoming Kafka message: %s", exc, exc_info=True)

        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt detected. Initiating graceful shutdown...")
        except Exception as exc:
            logger.error("Unexpected error in consumer loop: %s", exc, exc_info=True)
            raise
        finally:
            logger.info("Closing Kafka consumer connection...")
            self.consumer.close()
            logger.info("Kafka Consumer shut down cleanly.")