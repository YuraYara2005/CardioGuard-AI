import apiClient from './axiosInstance';
import type { ClinicalReport } from '../types';

export interface ReportGeneratePayload {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
}

export interface GeneratedReports {
  english_report: ClinicalReport;
  arabic_report: ClinicalReport;
}

/**
 * POST /report/generate
 * Sends a diagnosis payload and returns bilingual RAG reports.
 */
export async function generateClinicalReports(
  payload: ReportGeneratePayload,
): Promise<GeneratedReports> {
  const { data } = await apiClient.post<GeneratedReports>(
    '/report/generate',
    payload,
  );
  return data;
}
