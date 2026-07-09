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
        <ul key={`list-${keyIdx++}`} className="list-disc pl-5 mb-4 space-y-2 text-gray-700">
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
      listItems.push(<li key={`li-${keyIdx++}`}>{parseInline(content)}</li>);
    } else if (/^\d+\.\s/.test(trimmed)) {
      // Numbered lists are treated similarly but we can just render them as paragraphs with margins
      // or we can just render them as lists. Let's just flush bullets and render as text.
      flushList();
      blocks.push(
        <div key={`p-${keyIdx++}`} className="mb-2 pl-4 text-gray-700">
          {parseInline(trimmed)}
        </div>
      );
    } else if (trimmed.startsWith('#')) {
      flushList();
      const level = trimmed.match(/^#+/)?.[0].length || 1;
      const content = trimmed.replace(/^#+\s*/, '');
      const textSize = level === 1 ? 'text-lg' : 'text-base';
      blocks.push(
        <h3 key={`h-${keyIdx++}`} className={`font-semibold text-indigo-900 mt-6 mb-3 pb-1 border-b border-gray-200 ${textSize}`}>
          {parseInline(content)}
        </h3>
      );
    } else if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
      flushList();
      const content = trimmed.substring(2, trimmed.length - 2);
      blocks.push(
        <h4 key={`h4-${keyIdx++}`} className="font-semibold text-indigo-800 mt-4 mb-2">
          {parseInline(content)}
        </h4>
      );
    } else {
      flushList();
      blocks.push(
        <p key={`p-${keyIdx++}`} className="mb-3 text-gray-700 leading-relaxed">
          {parseInline(trimmed)}
        </p>
      );
    }
  }
  flushList();

  return <div className="space-y-1">{blocks}</div>;
}

function parseInline(text: string) {
  // Simple bold parser **text**
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold text-gray-900">{part.substring(2, part.length - 2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

export function DoctorReportRenderer({ reportText, result, patientId }: DoctorReportRendererProps) {
  const { diagnosis, confidence_score, is_emergency } = result.result;
  const now = new Date().toLocaleString();

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden mt-4">
      
      {/* Header Area */}
      <div className={`p-6 border-b ${is_emergency ? 'bg-red-50 border-red-100' : 'bg-indigo-50 border-indigo-100'}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${is_emergency ? 'bg-red-100 text-red-600' : 'bg-indigo-100 text-indigo-600'}`}>
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Clinical AI Assessment Report</h2>
              <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
                <Clock className="w-3 h-3" /> Generated: {now}
              </p>
            </div>
          </div>
          <button 
            onClick={() => window.print()} 
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors print:hidden"
          >
            <Printer className="w-3.5 h-3.5" /> Print / Save PDF
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-white/60 p-3 rounded-lg border border-white/50">
            <p className="text-[10px] text-gray-500 uppercase font-semibold mb-1 flex items-center gap-1">
              <User className="w-3 h-3" /> Patient ID
            </p>
            <p className="font-medium text-gray-900">{patientId || 'N/A'}</p>
          </div>
          
          <div className="bg-white/60 p-3 rounded-lg border border-white/50 sm:col-span-2">
            <p className="text-[10px] text-gray-500 uppercase font-semibold mb-1 flex items-center gap-1">
              <Activity className="w-3 h-3" /> AI Diagnosis
            </p>
            <p className="font-medium text-gray-900">{diagnosis}</p>
          </div>

          <div className="bg-white/60 p-3 rounded-lg border border-white/50">
            <p className="text-[10px] text-gray-500 uppercase font-semibold mb-1">
              Confidence
            </p>
            <p className="font-medium text-gray-900">{(confidence_score * 100).toFixed(1)}%</p>
          </div>
        </div>

        {is_emergency && (
          <div className="mt-4 flex items-center gap-2 text-red-700 bg-red-100/50 border border-red-200 rounded-lg px-4 py-2.5 text-sm font-semibold">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            CRITICAL EMERGENCY STATUS: Immediate Review Required
          </div>
        )}
      </div>

      {/* Body Area */}
      <div className="p-8 bg-white">
        <div className="prose prose-sm max-w-none text-gray-800">
          {parseMarkdown(reportText)}
        </div>
      </div>
      
      <div className="bg-gray-50 px-8 py-4 border-t border-gray-200 text-xs text-gray-400 flex justify-between print:block">
        <span>CardioGuard AI — Confidential Clinical Document</span>
        <span>Page 1 of 1</span>
      </div>
    </div>
  );
}
