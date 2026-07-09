import { Printer, AlertTriangle, Clock, User, Activity } from 'lucide-react';
import type { MultimodalPredictionResponse } from '../types';

interface DoctorReportRendererProps {
  reportText: string;
  result: MultimodalPredictionResponse;
  patientId: string;
}

function parseMarkdown(text: string) {
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let keyIdx = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      blocks.push(
        <ul
          key={`list-${keyIdx++}`}
          className="list-disc pl-5 mb-4 space-y-2 text-gray-700"
        >
          {[...listItems]}
        </ul>
      );
      listItems = [];
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      continue;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.substring(2).trim();

      listItems.push(
        <li key={`li-${keyIdx++}`}>
          {parseInline(content)}
        </li>
      );
    } else if (/^\d+\.\s/.test(trimmed)) {
      flushList();

      blocks.push(
        <div
          key={`p-${keyIdx++}`}
          className="mb-2 pl-4 text-gray-700"
        >
          {parseInline(trimmed)}
        </div>
      );
    } else if (trimmed.startsWith('#')) {
      flushList();

      const level = trimmed.match(/^#+/)?.[0].length || 1;
      const content = trimmed.replace(/^#+\s*/, '');
      const textSize = level === 1 ? 'text-lg' : 'text-base';

      blocks.push(
        <h3
          key={`h-${keyIdx++}`}
          className={`font-semibold text-indigo-900 mt-6 mb-3 pb-1 border-b border-gray-200 ${textSize}`}
        >
          {parseInline(content)}
        </h3>
      );
    } else if (
      trimmed.startsWith('**') &&
      trimmed.endsWith('**')
    ) {
      flushList();

      const content = trimmed.substring(
        2,
        trimmed.length - 2
      );

      blocks.push(
        <h4
          key={`h4-${keyIdx++}`}
          className="font-semibold text-indigo-800 mt-4 mb-2"
        >
          {parseInline(content)}
        </h4>
      );
    } else {
      flushList();

      blocks.push(
        <p
          key={`p-${keyIdx++}`}
          className="mb-3 text-gray-700 leading-relaxed"
        >
          {parseInline(trimmed)}
        </p>
      );
    }
  }

  flushList();

  return <div className="space-y-1">{blocks}</div>;
}

function parseInline(text: string) {
  const parts = text.split(/(\*\*.*?\*\*)/g);

  return parts.map((part, i) => {
    if (
      part.startsWith('**') &&
      part.endsWith('**')
    ) {
      return (
        <strong
          key={i}
          className="font-semibold text-gray-900"
        >
          {part.substring(2, part.length - 2)}
        </strong>
      );
    }

    return <span key={i}>{part}</span>;
  });
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function markdownToPrintableHtml(text: string): string {
  const safeText = escapeHtml(text);

  return safeText
    .replace(
      /^### (.*)$/gm,
      '<h3>$1</h3>'
    )
    .replace(
      /^## (.*)$/gm,
      '<h2>$1</h2>'
    )
    .replace(
      /^# (.*)$/gm,
      '<h1>$1</h1>'
    )
    .replace(
      /\*\*(.*?)\*\*/g,
      '<strong>$1</strong>'
    )
    .replace(
      /^[-*] (.*)$/gm,
      '<div class="bullet">• $1</div>'
    )
    .replace(
      /^(\d+)\. (.*)$/gm,
      '<div class="numbered">$1. $2</div>'
    )
    .replace(/\n\n+/g, '</p><p>')
    .replace(/\n/g, '<br />');
}

export function DoctorReportRenderer({
  reportText,
  result,
  patientId,
}: DoctorReportRendererProps) {
  const {
    diagnosis,
    confidence_score,
    is_emergency,
  } = result.result;

  const now = new Date().toLocaleString();

  const handlePrintRAGReport = () => {
    const printWindow = window.open(
      '',
      '_blank',
      'width=1000,height=800'
    );

    if (!printWindow) {
      alert(
        'Unable to open print window. Please allow pop-ups and try again.'
      );
      return;
    }

    const safePatientId = escapeHtml(
      patientId || 'N/A'
    );

    const safeDiagnosis = escapeHtml(
      diagnosis || 'N/A'
    );

    const safeGeneratedAt = escapeHtml(now);

    const confidence = (
      confidence_score * 100
    ).toFixed(1);

    const reportHtml =
      markdownToPrintableHtml(reportText);

    printWindow.document.write(`
      <!DOCTYPE html>
      <html lang="en">
        <head>
          <meta charset="UTF-8" />

          <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
          />

          <title>
            CardioGuard AI Clinical Report - ${safePatientId}
          </title>

          <style>
            @page {
              size: A4;
              margin: 16mm;
            }

            * {
              box-sizing: border-box;
            }

            body {
              margin: 0;
              padding: 0;
              background: #ffffff;
              color: #1f2937;
              font-family:
                Arial,
                Helvetica,
                sans-serif;
              line-height: 1.6;
            }

            .report {
              max-width: 900px;
              margin: 0 auto;
            }

            .header {
              padding: 24px;
              border: 1px solid ${is_emergency
        ? '#fecaca'
        : '#c7d2fe'
      };
              border-radius: 12px;
              background: ${is_emergency
        ? '#fef2f2'
        : '#eef2ff'
      };
              margin-bottom: 24px;
            }

            .brand {
              font-size: 12px;
              font-weight: 700;
              color: #4f46e5;
              text-transform: uppercase;
              letter-spacing: 0.08em;
              margin-bottom: 8px;
            }

            h1 {
              margin: 0 0 8px;
              font-size: 24px;
              color: #111827;
            }

            .generated {
              color: #6b7280;
              font-size: 12px;
            }

            .meta-grid {
              display: grid;
              grid-template-columns:
                repeat(3, 1fr);
              gap: 12px;
              margin-top: 20px;
            }

            .meta-card {
              background: rgba(
                255,
                255,
                255,
                0.8
              );
              border: 1px solid #e5e7eb;
              border-radius: 8px;
              padding: 12px;
            }

            .meta-label {
              display: block;
              color: #6b7280;
              font-size: 10px;
              font-weight: 700;
              text-transform: uppercase;
              margin-bottom: 4px;
            }

            .meta-value {
              color: #111827;
              font-size: 14px;
              font-weight: 600;
            }

            .emergency {
              margin-top: 16px;
              padding: 12px 14px;
              border-radius: 8px;
              border: 1px solid #fca5a5;
              background: #fee2e2;
              color: #b91c1c;
              font-size: 13px;
              font-weight: 700;
            }

            .rag-section {
              padding: 24px;
              border: 1px solid #e5e7eb;
              border-radius: 12px;
            }

            .rag-label {
              font-size: 11px;
              color: #4f46e5;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 0.08em;
              margin-bottom: 16px;
            }

            .rag-content h1,
            .rag-content h2,
            .rag-content h3 {
              color: #312e81;
              margin-top: 22px;
              margin-bottom: 10px;
              page-break-after: avoid;
            }

            .rag-content h1 {
              font-size: 20px;
            }

            .rag-content h2 {
              font-size: 17px;
              border-bottom: 1px solid #e5e7eb;
              padding-bottom: 6px;
            }

            .rag-content h3 {
              font-size: 15px;
            }

            .rag-content p {
              margin: 0 0 12px;
            }

            .bullet,
            .numbered {
              margin: 6px 0;
              padding-left: 12px;
            }

            .footer {
              margin-top: 24px;
              padding-top: 12px;
              border-top: 1px solid #e5e7eb;
              color: #9ca3af;
              font-size: 10px;
              display: flex;
              justify-content: space-between;
            }

            @media print {
              body {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
              }
            }
          </style>
        </head>

        <body>
          <main class="report">
            <section class="header">
              <div class="brand">
                CardioGuard AI
              </div>

              <h1>
                Clinical AI Assessment Report
              </h1>

              <div class="generated">
                Generated: ${safeGeneratedAt}
              </div>

              <div class="meta-grid">
                <div class="meta-card">
                  <span class="meta-label">
                    Patient ID
                  </span>

                  <span class="meta-value">
                    ${safePatientId}
                  </span>
                </div>

                <div class="meta-card">
                  <span class="meta-label">
                    AI Diagnosis
                  </span>

                  <span class="meta-value">
                    ${safeDiagnosis}
                  </span>
                </div>

                <div class="meta-card">
                  <span class="meta-label">
                    Confidence
                  </span>

                  <span class="meta-value">
                    ${confidence}%
                  </span>
                </div>
              </div>

              ${is_emergency
        ? `
                    <div class="emergency">
                      CRITICAL EMERGENCY STATUS:
                      Immediate Review Required
                    </div>
                  `
        : ''
      }
            </section>

            <section class="rag-section">
              <div class="rag-label">
                RAG-Generated Clinical Report
              </div>

              <div class="rag-content">
                <p>${reportHtml}</p>
              </div>
            </section>

            <footer class="footer">
              <span>
                CardioGuard AI —
                Confidential Clinical Document
              </span>

              <span>
                AI-assisted clinical decision support
              </span>
            </footer>
          </main>
        </body>
      </html>
    `);

    printWindow.document.close();

    printWindow.focus();

    setTimeout(() => {
      printWindow.print();
    }, 300);
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden mt-4">

      {/* Header Area */}
      <div
        className={`p-6 border-b ${is_emergency
            ? 'bg-red-50 border-red-100'
            : 'bg-indigo-50 border-indigo-100'
          }`}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center ${is_emergency
                  ? 'bg-red-100 text-red-600'
                  : 'bg-indigo-100 text-indigo-600'
                }`}
            >
              <Activity className="w-5 h-5" />
            </div>

            <div>
              <h2 className="text-lg font-bold text-gray-900">
                Clinical AI Assessment Report
              </h2>

              <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                <Clock className="w-3 h-3" />
                Generated: {now}
              </p>
            </div>
          </div>

          <button
            onClick={handlePrintRAGReport}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors print:hidden"
          >
            <Printer className="w-3.5 h-3.5" />
            Print / Save RAG PDF
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-white/60 p-3 rounded-lg border border-white/50">
            <p className="text-[10px] text-gray-500 uppercase font-semibold mb-1 flex items-center gap-1">
              <User className="w-3 h-3" />
              Patient ID
            </p>

            <p className="font-medium text-gray-900">
              {patientId || 'N/A'}
            </p>
          </div>

          <div className="bg-white/60 p-3 rounded-lg border border-white/50 sm:col-span-2">
            <p className="text-[10px] text-gray-500 uppercase font-semibold mb-1 flex items-center gap-1">
              <Activity className="w-3 h-3" />
              AI Diagnosis
            </p>

            <p className="font-medium text-gray-900">
              {diagnosis}
            </p>
          </div>

          <div className="bg-white/60 p-3 rounded-lg border border-white/50">
            <p className="text-[10px] text-gray-500 uppercase font-semibold mb-1">
              Confidence
            </p>

            <p className="font-medium text-gray-900">
              {(confidence_score * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        {is_emergency && (
          <div className="mt-4 flex items-center gap-2 text-red-700 bg-red-100/50 border border-red-200 rounded-lg px-4 py-2.5 text-sm font-semibold">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />

            CRITICAL EMERGENCY STATUS:
            Immediate Review Required
          </div>
        )}
      </div>

      {/* RAG Body */}
      <div className="p-8 bg-white">
        <div className="prose prose-sm max-w-none text-gray-800">
          {parseMarkdown(reportText)}
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-8 py-4 border-t border-gray-200 text-xs text-gray-400 flex justify-between">
        <span>
          CardioGuard AI — Confidential Clinical Document
        </span>

        <span>
          RAG-Generated Clinical Report
        </span>
      </div>
    </div>
  );
}