import { useRef, useState, useCallback } from 'react';
import {
  Printer,
  Activity,
  AlertTriangle,
  Download,
  CheckCircle,
  FileText,
  Loader2,
  AlertCircle,
} from 'lucide-react';

import type {
  MultimodalPredictionResponse,
} from '../types';

import {
  generateClinicalReports,
  REPORT_UNAVAILABLE_AR,
  type GeneratedReports,
} from '../api/reportService';

import { DoctorReportRenderer } from './DoctorReportRenderer';

interface ReportViewProps {
  result: MultimodalPredictionResponse;
}

interface StoredPatientReport {
  patient_id: string;
  diagnosis: string;
  confidence_score: number;
  is_emergency: boolean;
  doctor_report: string;
  patient_report: string;
  generated_at: string;
}

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function getCurrentAnalysisPatientId(): string {
  try {
    const raw = localStorage.getItem('cg_latest_analysis');

    if (!raw) {
      return 'P001';
    }

    const parsed = JSON.parse(raw);

    return (
      parsed?.patient_id ??
      parsed?.patientId ??
      parsed?.metadata?.patient_id ??
      'P001'
    );
  } catch {
    return 'P001';
  }
}

export default function ReportView({
  result,
}: ReportViewProps) {
  const printRef = useRef<HTMLDivElement>(null);

  const [genReport, setGenReport] =
    useState<GeneratedReports | null>(null);

  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');

  const requestInFlight = useRef(false);

  const handleGenerateReport = useCallback(async () => {
    if (requestInFlight.current || genLoading) return;

    requestInFlight.current = true;
    setGenLoading(true);
    setGenError('');
    setGenReport(null);

    try {
      const reports = await generateClinicalReports({
        diagnosis: result.result.diagnosis,
        confidence_score: result.result.confidence_score,
        is_emergency: result.result.is_emergency,
      });

      setGenReport(reports);

      // ------------------------------------------------------
      // Save generated report for the correct patient portal
      // ------------------------------------------------------

      const patientId = getCurrentAnalysisPatientId();

      const storedReport: StoredPatientReport = {
        patient_id: patientId,
        diagnosis: result.result.diagnosis,
        confidence_score: result.result.confidence_score,
        is_emergency: result.result.is_emergency,
        doctor_report: reports.doctor_report || '',
        patient_report: reports.patient_report || '',
        generated_at: new Date().toISOString(),
      };

      localStorage.setItem(
        `cg_patient_report_${patientId}`,
        JSON.stringify(storedReport),
      );

      // Optional convenience pointer to latest generated report
      localStorage.setItem(
        'cg_latest_generated_report',
        JSON.stringify(storedReport),
      );

      console.info(
        `[CardioGuard] Clinical report saved for patient ${patientId}`,
      );
    } catch (err) {
      setGenError(
        err instanceof Error
          ? err.message
          : REPORT_UNAVAILABLE_AR,
      );
    } finally {
      setGenLoading(false);
      requestInFlight.current = false;
    }
  }, [result, genLoading]);

  function handlePrint() {
    window.print();
  }

  const prediction = result.result;

  const probabilities =
    prediction.raw_probabilities ??
    prediction.class_probabilities ??
    prediction.probabilities;

  const now = new Date().toLocaleDateString(
    'en-GB',
    {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    },
  );

  return (
    <>
      {/* Screen-only toolbar */}
      <div className="print-hidden flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white">
            Diagnosis Report
          </h2>

          <p className="text-sm text-cg-muted">
            Analysis Mode: {result.mode}
          </p>
        </div>

        <div className="flex gap-3">
          <button
            id="btn-print-report"
            onClick={handlePrint}
            className="btn-ghost"
          >
            <Printer className="w-4 h-4" />
            Print / Export PDF
          </button>

          <button
            id="btn-download-report"
            onClick={handlePrint}
            className="btn-primary"
          >
            <Download className="w-4 h-4" />
            Download PDF
          </button>
        </div>
      </div>

      {/* Printable report */}
      <div
        ref={printRef}
        id="printable-report"
        className="print-page bg-white text-gray-900 rounded-2xl overflow-hidden shadow-2xl print:shadow-none print:rounded-none"
      >
        {/* Letterhead */}
        <div className="flex items-center justify-between px-10 py-6 border-b-4 border-indigo-700">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-700 flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>

            <div>
              <h1 className="text-xl font-bold text-indigo-800 leading-tight">
                CardioGuard AI
              </h1>

              <p className="text-xs text-gray-500 leading-tight">
                Multimodal Clinical Decision Support System
              </p>
            </div>
          </div>

          <div className="text-right text-xs text-gray-500">
            <p className="font-semibold text-gray-700">
              AI Diagnostic Report
            </p>

            <p>Issued: {now}</p>
            <p>Mode: {result.mode}</p>
          </div>
        </div>

        <div className="px-10 py-8 space-y-8">
          {/* Emergency alert */}
          {prediction.is_emergency && (
            <div className="flex items-center gap-3 p-4 rounded-xl border-2 border-red-500 bg-red-50">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />

              <div>
                <p className="font-bold text-red-700 text-sm uppercase tracking-wide">
                  Emergency Clinical Alert
                </p>

                <p className="text-xs text-red-600 mt-0.5">
                  This result has been flagged for urgent
                  clinical review.
                </p>
              </div>
            </div>
          )}

          {/* Basic information */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
              1. Analysis Information
            </h2>

            <table className="w-full text-sm border-collapse">
              <tbody>
                {[
                  ['Report Date', now],
                  ['API Status', result.status],
                  ['Analysis Mode', result.mode],
                  [
                    'Model Pipeline',
                    result.mode === 'multimodal_fusion'
                      ? 'CardioGuard Multimodal Fusion'
                      : 'CardioGuard ECG Model',
                  ],
                ].map(([label, value]) => (
                  <tr
                    key={label}
                    className="border-b border-gray-100"
                  >
                    <td className="py-2 pr-4 font-semibold text-gray-600 w-44">
                      {label}
                    </td>

                    <td className="py-2 text-gray-800">
                      {value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Prediction */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
              2. AI Inference Results
            </h2>

            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="border border-gray-200 rounded-xl p-4 text-center">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">
                  Primary Diagnosis
                </p>

                <p className="font-bold text-indigo-800 text-base">
                  {prediction.diagnosis}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4 text-center">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">
                  Confidence Score
                </p>

                <p className="font-bold text-indigo-800 text-lg">
                  {pct(prediction.confidence_score)}
                </p>
              </div>

              <div className="border border-gray-200 rounded-xl p-4 text-center">
                <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">
                  Emergency Flag
                </p>

                <p
                  className={`font-bold text-lg ${prediction.is_emergency
                      ? 'text-red-700'
                      : 'text-emerald-700'
                    }`}
                >
                  {prediction.is_emergency ? 'YES' : 'NO'}
                </p>
              </div>
            </div>

            {probabilities && (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="text-left py-2 px-3 text-gray-500 font-semibold border border-gray-200">
                      Class
                    </th>

                    <th className="text-right py-2 px-3 text-gray-500 font-semibold border border-gray-200">
                      Probability
                    </th>

                    <th className="py-2 px-3 border border-gray-200 w-40" />
                  </tr>
                </thead>

                <tbody>
                  {Object.entries(probabilities)
                    .sort(([, a], [, b]) => b - a)
                    .map(([className, probability]) => (
                      <tr key={className}>
                        <td className="py-1.5 px-3 font-medium text-gray-700 border border-gray-200">
                          {className}
                        </td>

                        <td className="py-1.5 px-3 text-right font-mono text-gray-700 border border-gray-200">
                          {pct(probability)}
                        </td>

                        <td className="py-1.5 px-3 border border-gray-200">
                          <div className="w-full bg-gray-100 rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full bg-indigo-600"
                              style={{
                                width: `${probability * 100}%`,
                              }}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Fusion pipeline */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
              3. Model Pipeline
            </h2>

            <div className="space-y-2">
              {result.mode === 'multimodal_fusion' ? (
                <>
                  {[
                    '12-lead ECG signal processed',
                    'ECG feature extraction completed',
                    'ECG image feature extraction completed',
                    'Laboratory features included',
                    'Patient metadata included',
                    'Multimodal fusion inference completed',
                  ].map((item) => (
                    <div
                      key={item}
                      className="flex items-center gap-2 text-sm text-gray-700"
                    >
                      <CheckCircle className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                      {item}
                    </div>
                  ))}
                </>
              ) : (
                <div className="flex items-center gap-2 text-sm text-gray-700">
                  <CheckCircle className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                  Standalone ECG inference completed
                </div>
              )}
            </div>
          </section>

          {/* Disclaimer */}
          <section className="border-t border-gray-200 pt-6">
            <p className="text-[10px] text-gray-400 leading-relaxed">
              <span className="font-semibold">
                Disclaimer:
              </span>{' '}
              This report was generated automatically by
              CardioGuard AI. It is intended to assist,
              not replace, the clinical judgment of a
              qualified physician. Findings must be reviewed
              by an appropriate healthcare professional
              before clinical decisions are made.
            </p>
          </section>
        </div>

        <div className="flex items-center justify-between px-10 py-4 bg-gray-50 border-t border-gray-200 text-[10px] text-gray-400">
          <span>CardioGuard AI</span>
          <span>Confidential Medical Document</span>
          <span>{now}</span>
        </div>
      </div>

      {/* Manual GenAI Clinical Report */}
      <div className="print-hidden mt-8 glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              AI Clinical Report (RAG + Gemini)
            </h3>

            <p className="text-xs text-cg-muted mt-0.5">
              Generate a bilingual doctor &amp; patient report
              from medical guidelines. Uses one Gemini call.
            </p>
          </div>

          {!genReport && (
            <button
              id="btn-generate-clinical-report"
              type="button"
              onClick={handleGenerateReport}
              disabled={genLoading}
              className="btn-primary flex-shrink-0"
            >
              {genLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}

              {genLoading
                ? 'Generating…'
                : 'Generate Clinical Report'}
            </button>
          )}
        </div>

        {genError && (
          <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {genError}
          </div>
        )}

        {genReport && (
          <div className="space-y-4">
            {genReport.doctor_report && (
              <div className="print:block print:w-full">
                <DoctorReportRenderer 
                  reportText={genReport.doctor_report}
                  result={result}
                  patientId={getCurrentAnalysisPatientId()}
                />
              </div>
            )}

            {genReport.patient_report && (
              <div>
                <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wide mb-2">
                  تقرير المريض (عربي)
                </p>

                <div
                  dir="rtl"
                  lang="ar"
                  className="bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-cg-text leading-relaxed whitespace-pre-wrap"
                >
                  {genReport.patient_report}
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                id="btn-regenerate-clinical-report"
                type="button"
                onClick={() => {
                  setGenReport(null);
                  setGenError('');
                }}
                className="btn-ghost text-xs"
              >
                Regenerate
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}