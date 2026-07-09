import apiClient from './axiosInstance';
import type { Patient } from '../types';


// ============================================================
// Health Response
// ============================================================

export interface HealthResponse {
  status: string;
  predictor_ready: boolean;
  multimodal_fusion_available: boolean;
  loaded_ml_artifacts: string[];
}


// ============================================================
// Prediction Result
// ============================================================

export interface PredictionResult {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;

  predicted_class?: string;
  predicted_classes?: string[];

  probabilities?: Record<string, number>;
  class_probabilities?: Record<string, number>;

  attention_weights?: unknown;
}


// ============================================================
// Standalone ECG Types
// ============================================================

export interface StandaloneECGRequest {
  leads_data: number[] | number[][];
}

export interface StandaloneECGResponse {
  status: string;
  mode: 'standalone_ecg';
  result: PredictionResult;
}


// ============================================================
// Multimodal Types
// ============================================================

export interface LabValues {
  troponin: number;
  'ck-mb': number;
  bnp: number;
  creatinine: number;
  hba1c: number;
}

export interface MultimodalPredictionRequest {
  patient_id?: string;
  leads_data: number[] | number[][];
  image_data: number[][][];

  labs: LabValues;

  age: number;
  blood_pressure: number;
  heart_rate: number;
  sex: string;
  symptoms: string[];
}

export interface MultimodalPredictionResponse {
  status: string;
  mode: 'multimodal_fusion';
  patient_id?: string;
  result: PredictionResult;
}


// ============================================================
// Patient API
// ============================================================

export async function getPatients(): Promise<Patient[]> {
  const { data } =
    await apiClient.get<Patient[]>('/patients');

  return data;
}

export async function getPatientById(
  patientId: string,
): Promise<Patient> {
  const { data } =
    await apiClient.get<Patient>(
      `/patients/${patientId}`,
    );

  return data;
}


// ============================================================
// Standalone ECG Prediction
// ============================================================

export async function predictECG(
  payload: StandaloneECGRequest,
): Promise<StandaloneECGResponse> {
  const { data } =
    await apiClient.post<StandaloneECGResponse>(
      '/predict/ecg',
      payload,
    );

  return data;
}


// ============================================================
// Multimodal Fusion Prediction
// ============================================================

export async function predictMultimodal(
  payload: MultimodalPredictionRequest,
): Promise<MultimodalPredictionResponse> {
  const { data } =
    await apiClient.post<MultimodalPredictionResponse>(
      '/predict/multimodal',
      payload,
    );

  return data;
}


// ============================================================
// Health Check
// ============================================================

export async function getHealthStatus(): Promise<HealthResponse> {
  const { data } =
    await apiClient.get<HealthResponse>(
      '/health',
    );

  return data;
}