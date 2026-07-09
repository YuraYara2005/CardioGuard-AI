import axios from 'axios';
import apiClient from './axiosInstance';

export interface ReportGeneratePayload {
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
}

export interface GeneratedReports {
  doctor_report: string | null;
  patient_report: string | null;
  emergency_alert?: string | null;
}

/**
 * Arabic fallback shown to patients when the AI report service
 * is unavailable (quota exceeded, service down, network error).
 * Never exposes provider-specific error details.
 */
export const REPORT_UNAVAILABLE_AR =
  'تعذر إنشاء التقرير الذكي مؤقتًا. حاول مرة أخرى لاحقًا.';

/**
 * Returns true when the report string is a backend error message
 * rather than real clinical content.
 *
 * This is a safety net for older backend versions that may still
 * return error strings as report bodies instead of HTTP errors.
 */
function isErrorString(value: string | null | undefined): boolean {
  if (!value) return false;
  const lower = value.toLowerCase();
  return (
    lower.startsWith('error:') ||
    lower.startsWith('تعذر') ||
    lower.includes('unable to generate') ||
    lower.includes('429') ||
    lower.includes('quota')
  );
}

/**
 * Calls POST /report/generate.
 *
 * Throws an Error with an Arabic safe message when:
 * - The server returns a non-2xx status (429, 503, 500, …)
 * - The server returns a 200 with an error string in the body
 *   (legacy backend behaviour)
 *
 * The caught error's `message` is safe to display to patients.
 */
export async function generateClinicalReports(
  payload: ReportGeneratePayload,
): Promise<GeneratedReports> {
  try {
    const { data } = await apiClient.post<GeneratedReports>(
      '/report/generate',
      payload,
    );

    // Safety net: treat error strings from older backend as failures
    if (
      isErrorString(data.doctor_report) ||
      isErrorString(data.patient_report)
    ) {
      console.warn(
        '[reportService] Server returned an error string in report body. ' +
        'Backend should be upgraded to return HTTP 4xx/5xx instead.',
      );
      throw new Error(REPORT_UNAVAILABLE_AR);
    }

    return data;

  } catch (err) {
    if (axios.isAxiosError(err)) {
      // Non-2xx response: use the detail from the backend if it
      // looks like our safe Arabic message, otherwise use the default.
      const detail: unknown = err.response?.data?.detail;
      const safeDetail =
        typeof detail === 'string' && !detail.startsWith('Error:')
          ? detail
          : REPORT_UNAVAILABLE_AR;

      throw new Error(safeDetail);
    }

    // Re-throw any error we deliberately threw above (e.g. error string body)
    throw err;
  }
}