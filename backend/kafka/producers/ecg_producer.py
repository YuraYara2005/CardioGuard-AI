import json
import time
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Any

try:
    # pyrefly: ignore [missing-import]
    from confluent_kafka import Producer
except ImportError:
    Producer = None

# Configure module-level logger
logger = logging.getLogger(__name__)

class LiveECGProducer:
    """
    Simulates a real-time hospital ECG machine.
    
    Continuously streams 12-lead ECG data points (at roughly 100Hz) to an Apache Kafka topic.
    This module strictly handles data ingestion and does not perform inference.
    """

    def __init__(
        self, 
        broker_url: str = "localhost:9092", 
        topic_name: str = "live_ecg_stream",
        log_level: int = logging.INFO
    ):
        """
        Initializes the Kafka producer configuration.

        Args:
            broker_url: The Kafka bootstrap servers connection string.
            topic_name: The target Kafka topic for the ECG stream.
            log_level: The logging level to use. Defaults to logging.INFO.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)

        if Producer is None:
            logger.critical("confluent-kafka is not installed in the current environment.")
            raise ImportError("Cannot initialize producer because 'confluent-kafka' is not installed.")

        self.broker_url = broker_url
        self.topic_name = topic_name

        try:
            logger.info(f"Initializing Kafka Producer connecting to '{self.broker_url}'...")
            # We configure the producer with the bootstrap server
            self.producer = Producer({
                'bootstrap.servers': self.broker_url,
                # Optional optimizations for high-throughput streaming could go here
                'client.id': 'cardioguard_ecg_simulator'
            })
            logger.info("Kafka Producer successfully initialized.")
        except Exception as e:
            logger.critical(f"Failed to initialize Kafka Producer: {str(e)}")
            raise

    def _delivery_callback(self, err: Optional[Any], msg: Any) -> None:
        """
        Optional asynchronous callback triggered once a message is fully delivered 
        to the Kafka broker, or fails to deliver.
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        # In a high-throughput 100Hz system, we avoid logging success for every single message
        # to prevent disk I/O bottlenecks.

    def start_streaming(self, patient_id: str) -> None:
        """
        Begins an infinite loop generating simulated 12-lead ECG data and 
        pushing it to the configured Kafka topic at ~100Hz.

        Args:
            patient_id: The unique identifier for the patient being monitored.
        """
        logger.info(f"Starting 100Hz ECG stream for Patient ID: {patient_id} on topic '{self.topic_name}'...")
        logger.info("Press Ctrl+C to stop streaming gracefully.")

        try:
            while True:
                # 1. Generate simulated data matching the PTB-XL schema.
                # A real machine reads 12 distinct electrical vectors. 
                # We simulate normalized voltage readings roughly between -1.5 and 1.5 mV.
                leads = [round(random.uniform(-1.5, 1.5), 4) for _ in range(12)]
                
                # 2. Construct the exact JSON payload expected downstream.
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "patient_id": patient_id,
                    "leads": leads
                }
                
                # 3. Serialize to JSON bytes
                json_bytes = json.dumps(payload).encode('utf-8')

                # 4. Push to Kafka topic
                # We use the patient_id as the partition key to ensure strict ordering 
                # for a single patient's time-series data.
                self.producer.produce(
                    topic=self.topic_name,
                    key=patient_id.encode('utf-8'),
                    value=json_bytes,
                    callback=self._delivery_callback
                )

                # Serves delivery reports from previous produce() calls
                self.producer.poll(0)

                # 5. Simulate 100Hz ingestion (PTB-XL baseline)
                time.sleep(0.01)

        except KeyboardInterrupt:
            # Graceful shutdown handling
            logger.warning("KeyboardInterrupt detected. Initiating graceful shutdown...")
            
        except Exception as e:
            logger.error(f"Unexpected error during streaming: {str(e)}", exc_info=True)
            raise
            
        finally:
            logger.info("Flushing remaining messages to Kafka broker...")
            # Wait for any outstanding messages to be delivered and delivery reports received
            self.producer.flush()
            logger.info("Kafka Producer shut down cleanly.")
