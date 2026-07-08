import apiClient from './axiosInstance';

export interface ReportGeneratePayload {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
}

export interface GeneratedReports {
  doctor_report: string;
  patient_report: string;
}

export async function generateClinicalReports(
  payload: ReportGeneratePayload,
): Promise<GeneratedReports> {
  const { data } =
    await apiClient.post<GeneratedReports>(
      '/report/generate',
      payload,
    );

  return data;
}