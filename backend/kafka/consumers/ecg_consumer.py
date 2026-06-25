import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

try:
    # pyrefly: ignore [missing-import]
    from confluent_kafka import Consumer, KafkaError, KafkaException
except ImportError:
    Consumer, KafkaError, KafkaException = None, None, None

# Configure module-level logger
logger = logging.getLogger(__name__)

class ECGConsumer:
    """
    Consumes live streaming 12-lead ECG data from Apache Kafka, runs real-time 
    inference using the ECGPredictor, and triggers GenAI reporting if anomalies are detected.
    """

    def __init__(
        self,
        predictor: Any,
        report_generator: Any,
        broker_url: str = "localhost:9092",
        topic_name: str = "live_ecg_stream",
        group_id: str = "cardioguard_inference_group",
        log_level: int = logging.INFO
    ):
        """
        Initializes the Kafka consumer and injects the required AI services.

        Args:
            predictor: An instance of ECGPredictor for analyzing the ECG arrays.
            report_generator: An instance of MedicalReportGenerator for building reports.
            broker_url: The Kafka bootstrap servers connection string.
            topic_name: The Kafka topic to subscribe to.
            group_id: The Kafka consumer group ID for tracking offsets.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        if Consumer is None:
            logger.critical("confluent-kafka is not installed in the current environment.")
            raise ImportError("Cannot initialize consumer because 'confluent-kafka' is not installed.")

        self.predictor = predictor
        self.report_generator = report_generator
        self.broker_url = broker_url
        self.topic_name = topic_name
        
        # Buffer to accumulate incoming 100Hz timesteps per patient.
        # Maps patient_id -> list of 12-lead arrays.
        self.patient_buffers: Dict[str, List[List[float]]] = defaultdict(list)
        
        # The PTB-XL model expects 1000 timesteps (10 seconds of 100Hz data).
        # We trigger inference once we accumulate this much data for a patient.
        self.inference_window_size = 1000
        self.is_running = False

        try:
            logger.info(f"Initializing Kafka Consumer connecting to '{self.broker_url}'...")
            self.consumer = Consumer({
                'bootstrap.servers': self.broker_url,
                'group.id': group_id,
                # Start reading from the latest messages if no offset is committed
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True
            })
            logger.info("Kafka Consumer successfully initialized.")
        except Exception as e:
            logger.critical(f"Failed to initialize Kafka Consumer: {str(e)}")
            raise

    def stop_consuming(self) -> None:
        """Sets the flag to stop the consuming loop gracefully."""
        logger.info("Stop signal received for Kafka Consumer.")
        self.is_running = False

    def start_consuming(self) -> None:
        """
        Continuously polls the Kafka topic for new ECG data, accumulates it, 
        and triggers the inference pipeline when enough data is gathered.
        """
        logger.info(f"Subscribing to topic '{self.topic_name}'...")
        self.consumer.subscribe([self.topic_name])
        logger.info("Starting consumption loop. Waiting for live ECG streams...")
        logger.info("Press Ctrl+C to stop consuming gracefully.")
        self.is_running = True

        try:
            while self.is_running:
                # Poll blocks for a maximum of 1.0 seconds waiting for messages
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition reached, not an actual error
                        continue
                    else:
                        logger.error(f"Kafka error occurred: {msg.error()}")
                        continue

                try:
                    # 1. Deserialize the payload
                    payload = json.loads(msg.value().decode('utf-8'))
                    patient_id = payload.get("patient_id")
                    leads = payload.get("leads")
                    timestamp = payload.get("timestamp")

                    if not patient_id or not leads or len(leads) != 12:
                        logger.warning("Received malformed payload. Skipping...")
                        continue

                    # 2. Accumulate the timesteps
                    self.patient_buffers[patient_id].append(leads)

                    # 3. Check if we have enough data for inference (10 seconds)
                    if len(self.patient_buffers[patient_id]) >= self.inference_window_size:
                        logger.debug(f"Accumulated 10s of data for {patient_id}. Triggering inference...")
                        
                        leads_data = self.patient_buffers[patient_id]
                        
                        # Clear the buffer immediately to prevent infinite memory growth
                        # In a more advanced setup, this could be a rolling window (e.g., keep last 500 steps)
                        self.patient_buffers[patient_id] = []
                        
                        # 4. Pass the data to the ECGPredictor
                        result = self.predictor.analyze_ecg(leads_data)
                        
                        diagnosis = result.get("diagnosis", "Unknown")
                        confidence = result.get("confidence_score", 0.0)
                        is_emergency = result.get("is_emergency", False)
                        
                        # 5. Trigger Report Generator if an anomaly is found
                        # We don't want to generate heavy LLM reports for every 10 seconds of "Normal ECG"
                        if diagnosis != "Normal ECG" or is_emergency:
                            logger.warning(
                                f"🚨 ANOMALY DETECTED for {patient_id}: {diagnosis} "
                                f"(Confidence: {confidence:.2%}). Triggering GenAI Reports..."
                            )
                            
                            # Construct a human-readable diagnosis string for the LLM
                            clinical_finding = f"Patient {patient_id} shows signs of {diagnosis}."
                            
                            reports = self.report_generator.generate_reports(
                                diagnosis=clinical_finding,
                                confidence_score=confidence,
                                is_emergency=is_emergency
                            )
                            
                            logger.info(f"✅ GenAI Reports successfully generated for {patient_id}.")
                            # In a full system, you would push these reports to another Kafka topic,
                            # a database, or a WebSockets stream to alert doctors instantly.
                            
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON from message value.")
                except Exception as e:
                    logger.error(f"Error processing incoming message: {str(e)}", exc_info=True)

        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt detected. Initiating graceful shutdown of consumer...")
            
        except Exception as e:
            logger.error(f"Unexpected error in consumer loop: {str(e)}", exc_info=True)
            raise
            
        finally:
            logger.info("Closing Kafka consumer connection...")
            self.consumer.close()
            logger.info("Kafka Consumer shut down cleanly.")
