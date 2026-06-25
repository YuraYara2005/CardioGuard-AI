CardioGuard AI: Real-Time Multi-Modal Cardiac Intelligence System

CardioGuard AI is an enterprise-grade Clinical Decision Support System (CDSS) developed for the DEPI (Digital Egypt Pioneers Initiative) graduation project.

The platform utilizes an Apache Kafka-driven streaming pipeline capable of ingesting live ECG signals at 500Hz. These signals are processed using a hybrid deep learning architecture (1D-CNN + BiLSTM + Attention) to detect dangerous heart rhythm abnormalities in real time. To enhance clinical trust, the system integrates Explainable AI (XAI) and a Bilingual Generative AI scribe to automatically translate diagnostic outputs into physician reports and patient-friendly Egyptian Arabic summaries.

🌟 Core System Features

Big Data Streaming (Kafka):

High-throughput, sub-200ms latency ingestion of 12-lead ECG data.

Resilient producer/consumer daemon architecture ensuring decoupled messaging.

Hybrid Inference Engine (PyTorch/TensorFlow):

Spatial & Temporal Analysis: 1D-CNN backbone for spatial feature extraction combined with BiLSTM and Attention layers for deep temporal rhythm analysis.

Multi-Modal Fusion: Combines physiological ECG signals with patient metadata (Age, BMI, Activity) for individualized baseline modeling.

Explainable AI (XAI) & Trust:

Integrates Grad-CAM and SHAP to generate visual heatmaps, highlighting the exact segments of the ECG signal that influenced the AI's prediction.

Data Synthesis (TimeSeriesGAN):

Addresses data imbalance in the MIT-BIH and PTB-XL datasets by generating high-fidelity synthetic ECG signals for rare arrhythmia classes.

Bilingual Medical Scribe (RAG + GenAI):

Automated clinical report generation powered by LLMs.

Retrieval-Augmented Generation using ChromaDB cross-references real-time predictions against AHA and ESC cardiology guidelines.

Generates highly technical English physician reports and culturally adapted Egyptian Arabic patient summaries.

Azure MLOps & Digital Twin:

Monitored via Digital Twin drift analysis to track patient deterioration trends.

CI/CD pipelines deployed to Microsoft Azure (Azure Machine Learning, Azure App Service).

🏗️ Mono-Repo Architecture

CardioGuardAI/
│
├── backend/                   # 🚀 (Member 1) FastAPI, Kafka, RAG Pipeline
│   ├── api/                   
│   ├── ai/                    
│   ├── inference/             
│   └── kafka/                 
│
├── model_training/            # 🧠 (Members 2 & 3) CNN-BiLSTM-Attention Architectures
├── data_synthesis/            # 🧬 (Member 5) TimeSeriesGAN & Digital Twin Logic
├── xai_fusion/                # 🔍 (Member 6) Grad-CAM, SHAP, Metadata Fusion
├── .github/workflows/         # ⚙️ (Member 4) Azure CI/CD Pipelines
│
├── models/                    # 🚨 DROP ZONE: Place cardioguard_model.keras here
├── chroma_db/                 # Persistent local vector database for RAG
├── docker-compose.yml         # Apache Kafka broker configuration
└── requirements.txt           # Python backend dependencies


🚀 Backend Quickstart Guide

1. Prerequisites

Python 3.10+

Docker Desktop (Required for the local Kafka Broker)

GenAI API Key (Set as GEMINI_API_KEY in environment variables)

2. Environment Setup

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt


3. Start Apache Kafka

docker-compose up -d


4. Boot the Inference API

Ensure your ML team's trained model is placed in the models/ directory, then start the FastAPI server:

uvicorn backend.api.app:app --reload


🤝 The Team

Developed for the DEPI Graduation Project.

Yara Mohamed  - Lead Systems & Knowledge Architect: Apache Kafka streaming infrastructure and Bilingual RAG Scribe.

Jihad Ibrahim - Sequential AI Specialist: BiLSTM and Attention layers for deep temporal rhythm analysis.

Mohamed Emara - Signal Vision Expert: 1D-CNN backbone for spatial feature extraction and ECG denoising.

Osama Mahmoud - Azure MLOps Lead: Microsoft Azure environment setup, CI/CD pipelines, and scalable API deployment.

Faten - Data Synthesis & Digital Twin Lead: TimeSeries GAN data augmentation and Digital Twin drift monitoring.

Menna ObyadAllah - XAI & Fusion Engineer: Explainable AI techniques (Grad-CAM, SHAP) and patient metadata fusion.