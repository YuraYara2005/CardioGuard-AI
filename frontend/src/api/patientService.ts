import apiClient from './axiosInstance';
import type {
  Patient,
  ECGAnalysisRequest,
  AnalysisResponse,
  DiagnosisPayload,
  ClinicalReport,
} from '../types';

// ── Patient CRUD ─────────────────────────────────────────────────────────────

/** Fetch all patients from the registry. */
export async function getPatients(): Promise<Patient[]> {
  const { data } = await apiClient.get<Patient[]>('/patients');
  return data;
}

/** Fetch a single patient record by ID. */
export async function getPatientById(patientId: string): Promise<Patient> {
  const { data } = await apiClient.get<Patient>(`/patients/${patientId}`);
  return data;
}

// ── ECG Analysis ─────────────────────────────────────────────────────────────

/**
 * POST /report/analyze
 * Runs TCN inference on raw ECG lead data and returns AI inference +
 * RAG-generated bilingual reports if an anomaly is detected.
 */
export async function analyzeECG(
  payload: ECGAnalysisRequest,
): Promise<AnalysisResponse> {
  const { data } = await apiClient.post<AnalysisResponse>(
    '/report/analyze',
    payload,
  );
  return data;
}

// ── Report Generation ─────────────────────────────────────────────────────────

/**
 * POST /report/generate
 * Directly generate RAG-backed clinical reports from a diagnosis string.
 * Useful when a diagnosis already exists and you only need the narrative.
 */
export async function generateReport(
  payload: DiagnosisPayload,
): Promise<{ english_report: ClinicalReport; arabic_report: ClinicalReport }> {
  const { data } = await apiClient.post('/report/generate', payload);
  return data;
}

// ── Health Check ─────────────────────────────────────────────────────────────

export async function getHealthStatus(): Promise<{ status: string }> {
  const { data } = await apiClient.get<{ status: string }>('/health');
  return data;
}
