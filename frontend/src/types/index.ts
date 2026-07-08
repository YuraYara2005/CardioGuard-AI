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
  dateOfBirth: string;          // ISO 8601
  contactNumber?: string;
  email?: string;
  medicalHistory?: string[];
  createdAt: string;
}

// ─────────────────────────────────────────────
// ECG Analysis
// ─────────────────────────────────────────────
export interface ECGAnalysisRequest {
  patient_id: string;
  leads: number[] | number[][];
}

export interface InferenceResult {
  diagnosis: string;
  confidence_score: number;       // 0.0 – 1.0
  is_emergency: boolean;
  predicted_class_index: number;
  hrv_metrics?: HRVMetrics;
  raw_probabilities?: Record<string, number>;
}

export interface HRVMetrics {
  rmssd: number;    // ms
  sdnn: number;     // ms
  pnn50: number;    // %
  lf_hf_ratio: number;
  mean_hr: number;  // bpm
}

// ─────────────────────────────────────────────
// RAG / Report Generation
// ─────────────────────────────────────────────
export interface DiagnosisPayload {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
}

export interface ClinicalReport {
  language: 'en' | 'ar';
  title: string;
  summary: string;
  guidelines: string[];
  recommendations: string[];
  urgency_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  generated_at: string;
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
// Kafka / WebSocket Stream
// ─────────────────────────────────────────────
export interface KafkaStreamPayload {
  timestamp: number;              // Unix ms
  ecg_value: number;              // Amplitude μV
  patient_id: string;
  is_emergency: boolean;
  anomaly_type?: string;          // e.g. "AFib", "Heart Attack"
  confidence?: number;
  lead?: string;                  // e.g. "Lead II"
}

export interface ECGDataPoint {
  t: number;      // x-axis: time ms
  v: number;      // y-axis: voltage μV
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
