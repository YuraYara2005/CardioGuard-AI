import sys
import os
import logging

# Path Fix to access backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from backend.kafka.producers.ecg_producer import LiveECGProducer

logging.basicConfig(level=logging.INFO, format='%(message)s')

if __name__ == "__main__":
    producer = LiveECGProducer(broker_url="localhost:9092", topic_name="live_ecg_stream")
    # Simulate a patient ID
    producer.start_streaming(patient_id="PTB-XL-Patient-001")