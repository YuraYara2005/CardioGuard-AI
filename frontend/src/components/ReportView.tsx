import { useRef } from 'react';
import { Printer, Activity, CheckCircle, AlertTriangle, Download } from 'lucide-react';
import type { AnalysisResponse } from '../types';

interface ReportViewProps {
  result: AnalysisResponse;
}

function urgencyColor(level?: string) {
  switch (level) {
    case 'CRITICAL': return 'text-red-600 border-red-600';
    case 'HIGH':     return 'text-orange-600 border-orange-600';
    case 'MEDIUM':   return 'text-amber-600 border-amber-600';
    default:         return 'text-emerald-700 border-emerald-700';
  }
}

function pct(v: number) { return `${(v * 100).toFixed(1)}%`; }

export default function ReportView({ result }: ReportViewProps) {
  const printRef = useRef<HTMLDivElement>(null);

  function handlePrint() { window.print(); }

  const { inference_results: ir, ai_reports } = result;
  const eng = ai_reports?.english_report;
  const hrv = ir.hrv_metrics;
  const now = new Date().toLocaleDateString('en-GB', {
    day: '2-digit', month: 'long', year: 'numeric',
  });

  return (
    <>
      {/* ── Screen-only toolbar ─────────────────────────────────────────── */}
      <div className="print-hidden flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-white">Diagnosis Report</h2>
          <p className="text-sm text-cg-muted">Patient ID: {result.patient_id}</p>
        </div>
        <div className="flex gap-3">
          <button id="btn-print-report" onClick={handlePrint} className="btn-ghost">
            <Printer className="w-4 h-4" /> Print / Export PDF
          </button>
          <button id="btn-download-report" onClick={handlePrint} className="btn-primary">
            <Download className="w-4 h-4" /> Download PDF
          </button>
        </div>
      </div>

      {/* ── Printable report ────────────────────────────────────────────── */}
      <div
        ref={printRef}
        id="printable-report"
        className="print-page bg-white text-gray-900 rounded-2xl overflow-hidden
                   shadow-2xl print:shadow-none print:rounded-none"
      >
        {/* Letterhead */}
        <div className="flex items-center justify-between px-10 py-6 border-b-4 border-indigo-700">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-700 flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-indigo-800 leading-tight">CardioGuard AI</h1>
              <p className="text-xs text-gray-500 leading-tight">Clinical Decision Support System</p>
            </div>
          </div>
          <div className="text-right text-xs text-gray-500">
            <p className="font-semibold text-gray-700">ECG Diagnostic Report</p>
            <p>Issued: {now}</p>
            <p>Report ID: RPT-{result.patient_id}-{Date.now()}</p>
          </div>
        </div>

        {/* Body */}
        <div className="px-10 py-8 space-y-8">

          {/* ── Emergency badge ──────────────────────────────────────────── */}
          {ir.is_emergency && (
            <div className="flex items-center gap-3 p-4 rounded-xl border-2 border-red-500 bg-red-50">
              <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
              <div>
                <p className="font-bold text-red-700 text-sm uppercase tracking-wide">
                  ⚠ Emergency Clinical Alert
                </p>
                <p className="text-xs text-red-600 mt-0.5">
                  This patient has been flagged for immediate clinical intervention. Please escalate to the attending physician.
                </p>
              </div>
            </div>
          )}

          {/* ── Section 1: Basic Information ─────────────────────────────── */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
              1. Basic Information
            </h2>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {[
                  ['Patient ID',     result.patient_id],
                  ['Report Date',    now],
                  ['System Version', 'CardioGuard AI v1.0 · TCN-Attention Model'],
                  ['Urgency Level',  eng?.urgency_level ?? 'N/A'],
                ].map(([label, value]) => (
                  <tr key={label} className="border-b border-gray-100">
                    <td className="py-2 pr-4 font-semibold text-gray-600 w-44">{label}</td>
                    <td className="py-2 text-gray-800">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* ── Section 2: TCN Inference Results ────────────────────────── */}
          <section>
            <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
              2. TCN-Attention Inference Results
            </h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              {[
                { label: 'Primary Diagnosis', value: ir.diagnosis, large: true },
                { label: 'Confidence Score',  value: pct(ir.confidence_score) },
                { label: 'Emergency Flag',    value: ir.is_emergency ? 'YES' : 'NO' },
              ].map(({ label, value, large }) => (
                <div key={label} className="border border-gray-200 rounded-xl p-4 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-gray-400 mb-1">{label}</p>
                  <p className={`font-bold text-indigo-800 ${large ? 'text-base' : 'text-lg'}`}>
                    {value}
                  </p>
                </div>
              ))}
            </div>

            {/* Probability table */}
            {ir.raw_probabilities && (
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="text-left py-2 px-3 text-gray-500 font-semibold border border-gray-200">Class</th>
                    <th className="text-right py-2 px-3 text-gray-500 font-semibold border border-gray-200">Probability</th>
                    <th className="py-2 px-3 border border-gray-200 w-40"></th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(ir.raw_probabilities)
                    .sort(([, a], [, b]) => b - a)
                    .map(([cls, prob]) => (
                      <tr key={cls} className="border-b border-gray-100">
                        <td className="py-1.5 px-3 font-medium text-gray-700 border border-gray-200">{cls}</td>
                        <td className="py-1.5 px-3 text-right font-mono text-gray-700 border border-gray-200">{pct(prob)}</td>
                        <td className="py-1.5 px-3 border border-gray-200">
                          <div className="w-full bg-gray-100 rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full bg-indigo-600"
                              style={{ width: `${prob * 100}%` }}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </section>

          {/* ── Section 3: HRV Metrics ───────────────────────────────────── */}
          {hrv && (
            <section>
              <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
                3. Heart Rate Variability (HRV) Metrics
              </h2>
              <div className="grid grid-cols-5 gap-3">
                {[
                  { label: 'RMSSD',     value: `${hrv.rmssd.toFixed(1)} ms`,     help: 'Short-term HRV' },
                  { label: 'SDNN',      value: `${hrv.sdnn.toFixed(1)} ms`,      help: 'Overall HRV' },
                  { label: 'pNN50',     value: `${hrv.pnn50.toFixed(1)}%`,       help: '% of NN50' },
                  { label: 'LF/HF',     value: hrv.lf_hf_ratio.toFixed(2),       help: 'Sympathovagal' },
                  { label: 'Mean HR',   value: `${hrv.mean_hr.toFixed(0)} bpm`,  help: 'Heart rate' },
                ].map(({ label, value, help }) => (
                  <div key={label} className="border border-gray-200 rounded-xl p-3 text-center">
                    <p className="text-[10px] uppercase tracking-wider text-gray-400">{label}</p>
                    <p className="text-base font-bold text-gray-800 mt-1">{value}</p>
                    <p className="text-[9px] text-gray-400 mt-0.5">{help}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── Section 4: RAG-Generated AHA/ESC Guidelines ──────────────── */}
          {eng && (
            <section>
              <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-700 mb-3 border-b border-gray-200 pb-2">
                4. AHA/ESC Guideline Recommendations (RAG Pipeline)
              </h2>

              {/* Clinical Summary */}
              <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 mb-4">
                <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-1">Clinical Summary</p>
                <p className="text-sm text-gray-700 leading-relaxed">{eng.summary}</p>
              </div>

              {/* Guidelines list */}
              {eng.guidelines.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-semibold text-gray-600 mb-2">Referenced Guidelines</p>
                  <ul className="space-y-1">
                    {eng.guidelines.map((g, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        <CheckCircle className="w-4 h-4 text-indigo-500 flex-shrink-0 mt-0.5" />
                        {g}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {eng.recommendations.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-600 mb-2">Clinical Recommendations</p>
                  <ul className="space-y-1">
                    {eng.recommendations.map((r, i) => (
                      <li key={i} className={`flex items-start gap-2 text-sm`}>
                        <span className="text-indigo-500 font-bold">{i + 1}.</span>
                        <span className="text-gray-700">{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Urgency */}
              <div className={`mt-4 inline-flex items-center gap-2 border-2 rounded-lg px-4 py-2 text-sm font-bold ${urgencyColor(eng.urgency_level)}`}>
                Urgency: {eng.urgency_level}
              </div>
            </section>
          )}

          {/* ── Section 5: Disclaimer ─────────────────────────────────────── */}
          <section className="border-t border-gray-200 pt-6">
            <p className="text-[10px] text-gray-400 leading-relaxed">
              <span className="font-semibold">Disclaimer:</span> This report was generated automatically by CardioGuard AI using a TCN-Attention deep learning model and a RAG pipeline referencing AHA/ESC guidelines. It is intended to assist—not replace—the clinical judgment of a qualified physician. All findings must be reviewed and confirmed by a licensed cardiologist before any clinical decision is made.
            </p>
          </section>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-10 py-4 bg-gray-50 border-t border-gray-200 text-[10px] text-gray-400">
          <span>CardioGuard AI · www.cardioguard.ai</span>
          <span>Confidential Medical Document · Do Not Distribute</span>
          <span>{now}</span>
        </div>
      </div>
    </>
  );
}
