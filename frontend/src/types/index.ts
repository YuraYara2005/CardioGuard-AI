// ─────────────────────────────────────────────
// Auth & User
// ─────────────────────────────────────────────
export type UserRole = 'Doctor' | 'Patient';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatarUrl?: string;
  patientId?: string;
}

// ─────────────────────────────────────────────
// Patient
// ─────────────────────────────────────────────
export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Male' | 'Female' | 'Other';
  bloodType?: string;
  dateOfBirth: string;
  contactNumber?: string;
  email?: string;
  medicalHistory?: string[];
  createdAt: string;
}

// ─────────────────────────────────────────────
// Legacy ECG Analysis
// Keep temporarily for older frontend code.
// ─────────────────────────────────────────────
export interface ECGAnalysisRequest {
  patient_id: string;
  leads: number[] | number[][];
}

export interface HRVMetrics {
  rmssd: number;
  sdnn: number;
  pnn50: number;
  lf_hf_ratio: number;
  mean_hr: number;
}

export interface InferenceResult {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
  predicted_class_index?: number;
  hrv_metrics?: HRVMetrics;
  raw_probabilities?: Record<string, number>;
}

export interface AnalysisResponse {
  patient_id: string;
  inference_results: InferenceResult;
  ai_reports: {
    english_report: ClinicalReport;
    arabic_report: ClinicalReport;
  } | null;
}

// ─────────────────────────────────────────────
// Current CardioGuard Prediction API
// ─────────────────────────────────────────────
export interface PredictionResult {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;

  predicted_class_index?: number;
  predicted_class?: string;

  hrv_metrics?: HRVMetrics;
  raw_probabilities?: Record<string, number>;

  class_probabilities?: Record<string, number>;
  probabilities?: Record<string, number>;
}

export interface MultimodalPredictionResponse {
  status: string;
  mode: 'multimodal_fusion' | string;
  result: PredictionResult;
}

export interface StandaloneECGPredictionResponse {
  status: string;
  mode: 'standalone_ecg' | string;
  result: PredictionResult;
}

// ─────────────────────────────────────────────
// RAG / Report Generation
// ─────────────────────────────────────────────
export interface DiagnosisPayload {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
}

// Keep this because some UI components may still
// use structured reports in the future.
export interface ClinicalReport {
  language: 'en' | 'ar';
  title: string;
  summary: string;
  guidelines: string[];
  recommendations: string[];
  urgency_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  generated_at: string;
}

// This matches the CURRENT backend /report/generate
// response used by reportService.ts.
export interface GeneratedReports {
  doctor_report: string;
  patient_report: string;
}

// ─────────────────────────────────────────────
// Kafka / WebSocket Stream
// ─────────────────────────────────────────────
export interface KafkaStreamPayload {
  timestamp: number;
  ecg_value: number;
  patient_id: string;
  is_emergency: boolean;
  anomaly_type?: string;
  confidence?: number;
  lead?: string;
}

export interface ECGDataPoint {
  t: number;
  v: number;
}

// ─────────────────────────────────────────────
// New-Analysis Upload Form
// ─────────────────────────────────────────────
export interface PatientMetadataForm {
  patient_id: string;
  age: number | '';
  systolic_bp: number | '';
  diastolic_bp: number | '';
  symptoms: string;
  gender: 'Male' | 'Female' | 'Other' | '';
}

export interface UploadFormState {
  ecgFile: File | null;
  labReportImage: File | null;
  ecgArray: number[];
  metadata: PatientMetadataForm;
}

// ─────────────────────────────────────────────
// Sidebar Navigation
// ─────────────────────────────────────────────
export type DashboardTab =
  | 'telemetry'
  | 'new-analysis'
  | 'patients'
  | 'reports'
  | 'settings';