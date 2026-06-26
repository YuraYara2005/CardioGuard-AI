# 🫀 CardioGuard AI: Real-Time Multi-Modal Cardiac Intelligence System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138.0-009688.svg)](https://fastapi.tiangolo.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.21.0-FF6F00.svg)](https://www.tensorflow.org/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-Latest-231F20.svg)](https://kafka.apache.org/)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4.svg)](https://ai.google.dev/)

CardioGuard AI is an enterprise-grade Clinical Decision Support System (CDSS) developed for the **DEPI (Digital Egypt Pioneers Initiative)** graduation project.

The platform utilizes a high-throughput Apache Kafka-driven streaming pipeline capable of ingesting live ECG signals at 500Hz. These signals are processed using a cutting-edge hybrid deep learning architecture (**1D-CNN + TCN + Custom Attention**) to detect dangerous heart rhythm abnormalities in real time. To enhance clinical trust and bridge the gap between AI predictions and patient understanding, the system integrates Explainable AI (XAI) and a **Bilingual Generative AI scribe** to automatically translate diagnostic outputs into structured physician reports and patient-friendly Egyptian Arabic summaries.

---

## 🌟 Core Architecture & Features

### Big Data Streaming (Apache Kafka)
- **High-Throughput Ingestion**: Sub-200ms latency ingestion of 12-lead ECG time-series data.
- **Decoupled Architecture**: Resilient producer/consumer daemon architecture using `confluent-kafka` for Python.

### Hybrid Inference Engine (TensorFlow/Keras)
- **Spatial & Temporal Analysis**: A **1D-CNN** backbone for spatial feature extraction combined with a **Temporal Convolutional Network (TCN)** and **Custom Attention** layers for deep temporal rhythm analysis.
- **Medical Datasets**: Trained rigorously on the **PTB-XL** and **MIT-BIH Arrhythmia** datasets.

### Explainable AI (XAI) & Fusion
- **Visual Heatmaps**: Integrates **Grad-CAM** and **SHAP** to generate visual heatmaps, highlighting the exact segments of the ECG signal that influenced the AI's prediction.
- **Multi-Modal Fusion**: Combines physiological ECG signals with patient metadata (Age, BMI, Activity) for individualized baseline modeling.

### Data Synthesis (TimeSeriesGAN)
- **Digital Twin Generation**: Addresses data imbalance in the MIT-BIH and PTB-XL datasets by generating high-fidelity synthetic ECG signals for rare arrhythmia classes using **TimeSeriesGAN**.

### Bilingual Medical Scribe (RAG + GenAI)
- **LLM Engine**: Powered by **Google Gemini 2.5 Flash** (via `google-genai`).
- **RAG Pipeline**: Utilizes **ChromaDB** as the vector store and **BAAI/bge-small-en-v1.5** for embeddings to cross-reference real-time predictions against official AHA and ESC cardiology guidelines.
- **Multi-Audience Reporting**: Generates highly technical English physician reports and culturally adapted Egyptian Arabic patient summaries simultaneously.

### Azure MLOps
- **Cloud Infrastructure**: CI/CD pipelines deployed to Microsoft Azure (Azure Machine Learning, Azure App Service).

---

## 🏗️ Mono-Repo Structure

```text
CardioGuardAI/
│
├── backend/                   # 🚀 (Member 1) FastAPI, Kafka, RAG Pipeline
│   ├── api/                   # HTTP endpoints and validation (Pydantic)
│   ├── ai/                    # Prompt builders, LLM wrappers, and RAG logic
│   ├── inference/             # Preprocessing and TCN TensorFlow model loader
│   └── kafka/                 # Background producers and consumers
│
├── model_training/            # 🧠 (Members 2 & 3) 1D-CNN-TCN-Attention Architectures
├── data_synthesis/            # 🧬 (Member 5) TimeSeriesGAN
├── xai_fusion/                # 🔍 (Member 6) Grad-CAM, SHAP, Metadata Fusion
├── .github/workflows/         # ⚙️ (Member 4) Azure CI/CD Pipelines
│
├── models/                    # 🚨 DROP ZONE: Place cardioguard_model.keras here
├── chroma_db/                 # Persistent local vector database for RAG
├── docker-compose.yml         # Apache Kafka broker configuration
├── requirements.txt           # Python backend dependencies
└── .env                       # Environment variables (API Keys, config)
```

---

## 🚀 Backend Quickstart Guide

### 1. Prerequisites
- **Python 3.10+**
- **Docker Desktop** (Required to spin up the local Kafka Broker)
- **Google Gemini API Key** (Set as `GEMINI_API_KEY` in the `.env` file)

### 2. Environment Setup

```bash
# Create and activate a virtual environment
python -m venv .venv

# Mac/Linux
source .venv/bin/activate  
# Windows
.venv\Scripts\activate     

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Apache Kafka

Spin up the local message broker using Docker Compose:

```bash
docker-compose up -d
```

### 4. Boot the Inference API

Ensure the ML team's trained `.keras` model is placed in the `models/` directory, then start the FastAPI server:

```bash
uvicorn backend.api.app:app --reload
```
The server will automatically load the AI weights into memory, connect to ChromaDB, and spin up the background Kafka consumer thread.

---

## 🤝 The Team

Developed for the **DEPI (Digital Egypt Pioneers Initiative)** Graduation Project.

- **Yara Mohamed** - Lead Systems & Knowledge Architect *(Kafka, FastAPI, Bilingual RAG Scribe)*
- **Jihad Ibrahim** - Sequential AI Specialist *(TCN and Custom Attention Layers)*
- **Mohamed Emara** - Signal Vision Expert *(1D-CNN spatial extraction and ECG denoising)*
- **Osama Mahmoud** - Azure MLOps Lead *(CI/CD pipelines, API deployment)*
- **Faten** - Data Synthesis & Digital Twin Lead *(TimeSeries GAN)*
- **Menna ObyadAllah** - XAI & Fusion Engineer *(Grad-CAM, SHAP, Patient Metadata)*