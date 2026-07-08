import {
  useState,
  useCallback,
  type DragEvent,
  type ChangeEvent,
} from 'react';
import {
  Upload,
  FileCode2,
  ImagePlus,
  User,
  CheckCircle2,
  Loader2,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';
import { analyzeECG } from '../api/patientService';
import type { UploadFormState, PatientMetadataForm, AnalysisResponse } from '../types';

interface NewAnalysisTabProps {
  onResult: (result: AnalysisResponse) => void;
}

const DEFAULT_META: PatientMetadataForm = {
  patient_id:    '',
  age:           '',
  systolic_bp:   '',
  diastolic_bp:  '',
  symptoms:      '',
  gender:        '',
};

// ── Drag-and-drop zone ────────────────────────────────────────────────────────
function DropZone({
  id,
  label,
  accept,
  icon: Icon,
  file,
  onFile,
}: {
  id:      string;
  label:   string;
  accept:  string;
  icon:    React.ElementType;
  file:    File | null;
  onFile:  (f: File) => void;
}) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onFile(f);
  }

  return (
    <div
      id={`dropzone-${id}`}
      onDragEnter={() => setDragging(true)}
      onDragLeave={() => setDragging(false)}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      className={`relative flex flex-col items-center justify-center gap-3 p-8 rounded-2xl border-2 border-dashed
                  cursor-pointer transition-all duration-200
                  ${dragging
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : file
                      ? 'border-emerald-500/50 bg-emerald-500/5'
                      : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'
                  }`}
      onClick={() => document.getElementById(`file-input-${id}`)?.click()}
    >
      <input
        id={`file-input-${id}`}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e: ChangeEvent<HTMLInputElement>) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
        }}
      />
      {file ? (
        <>
          <CheckCircle2 className="w-8 h-8 text-emerald-400" />
          <p className="text-xs text-emerald-400 font-medium text-center truncate max-w-full px-2">
            {file.name}
          </p>
          <p className="text-[10px] text-cg-muted">
            {(file.size / 1024).toFixed(1)} KB · Click to replace
          </p>
        </>
      ) : (
        <>
          <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center">
            <Icon className="w-6 h-6 text-cg-muted" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-white">{label}</p>
            <p className="text-xs text-cg-muted mt-0.5">Drag & drop or click to browse</p>
          </div>
          <Upload className="w-4 h-4 text-cg-muted" />
        </>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function NewAnalysisTab({ onResult }: NewAnalysisTabProps) {
  const [form, setForm] = useState<UploadFormState>({
    ecgFile:       null,
    labReportImage: null,
    ecgArray:      [],
    metadata:      DEFAULT_META,
  });

  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState('');
  const [parseWarn, setParseWarn] = useState('');

  const updateMeta = useCallback(
    (key: keyof PatientMetadataForm, value: string) =>
      setForm((prev) => ({ ...prev, metadata: { ...prev.metadata, [key]: value } })),
    [],
  );

  // Parse ECG JSON file → float array
  async function parseECGFile(file: File): Promise<number[]> {
    const text = await file.text();
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) return parsed.flat().map(Number);
      if (parsed.leads) return (parsed.leads as number[][]).flat().map(Number);
      throw new Error('Unrecognised JSON structure');
    } catch {
      throw new Error('ECG file must be a JSON array or { leads: [...] }');
    }
  }

  async function handleSubmit() {
    setError('');
    setParseWarn('');
    const { metadata, ecgFile } = form;

    if (!metadata.patient_id.trim()) { setError('Patient ID is required.'); return; }
    if (!ecgFile) { setError('Please upload an ECG data file.'); return; }

    setLoading(true);
    try {
      const leads = await parseECGFile(ecgFile);
      if (leads.length === 0) throw new Error('ECG array is empty after parsing.');
      if (leads.length < 100) setParseWarn(`Only ${leads.length} samples found — accuracy may be reduced.`);

      const result = await analyzeECG({ patient_id: metadata.patient_id, leads });
      onResult(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div>
        <h2 className="text-lg font-semibold text-white">New Multi-Modal Analysis</h2>
        <p className="text-sm text-cg-muted mt-0.5">
          Upload ECG data and patient metadata for TCN inference + RAG report generation.
        </p>
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
        </div>
      )}
      {parseWarn && (
        <div className="flex items-center gap-2 text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />{parseWarn}
        </div>
      )}

      {/* Upload zones */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Zone 1: ECG Array */}
        <div>
          <p className="text-xs font-semibold text-cg-muted uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <span className="w-5 h-5 rounded-full bg-indigo-600/30 inline-flex items-center justify-center text-indigo-400 text-[10px]">1</span>
            ECG Array Data (JSON)
          </p>
          <DropZone
            id="ecg-array"
            label="ECG Lead File (.json)"
            accept=".json,.txt"
            icon={FileCode2}
            file={form.ecgFile}
            onFile={(f) => setForm((p) => ({ ...p, ecgFile: f }))}
          />
        </div>

        {/* Zone 2: Lab Report Image */}
        <div>
          <p className="text-xs font-semibold text-cg-muted uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <span className="w-5 h-5 rounded-full bg-cyan-600/30 inline-flex items-center justify-center text-cyan-400 text-[10px]">2</span>
            Lab Report Image (OCR)
          </p>
          <DropZone
            id="lab-image"
            label="Lab Report (.jpg / .png / .pdf)"
            accept="image/*,.pdf"
            icon={ImagePlus}
            file={form.labReportImage}
            onFile={(f) => setForm((p) => ({ ...p, labReportImage: f }))}
          />
        </div>
      </div>

      {/* Zone 3: Patient Metadata form */}
      <div className="glass-card p-6">
        <p className="text-xs font-semibold text-cg-muted uppercase tracking-wide mb-4 flex items-center gap-1.5">
          <span className="w-5 h-5 rounded-full bg-emerald-600/30 inline-flex items-center justify-center text-emerald-400 text-[10px]">3</span>
          <User className="w-3.5 h-3.5" />
          Patient Metadata
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-cg-muted mb-1.5">Patient ID *</label>
            <input
              id="meta-patient-id"
              type="text"
              placeholder="PTB-XL-001"
              value={form.metadata.patient_id}
              onChange={(e) => updateMeta('patient_id', e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-xs text-cg-muted mb-1.5">Gender</label>
            <select
              id="meta-gender"
              value={form.metadata.gender}
              onChange={(e) => updateMeta('gender', e.target.value)}
              className="input-field"
            >
              <option value="">Select…</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-cg-muted mb-1.5">Age (years)</label>
            <input
              id="meta-age"
              type="number"
              min={0}
              max={130}
              placeholder="52"
              value={form.metadata.age}
              onChange={(e) => updateMeta('age', e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-xs text-cg-muted mb-1.5">Blood Pressure (mmHg)</label>
            <div className="flex gap-2">
              <input
                id="meta-systolic"
                type="number"
                placeholder="120"
                value={form.metadata.systolic_bp}
                onChange={(e) => updateMeta('systolic_bp', e.target.value)}
                className="input-field"
              />
              <span className="flex items-center text-cg-muted text-sm">/</span>
              <input
                id="meta-diastolic"
                type="number"
                placeholder="80"
                value={form.metadata.diastolic_bp}
                onChange={(e) => updateMeta('diastolic_bp', e.target.value)}
                className="input-field"
              />
            </div>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs text-cg-muted mb-1.5">Chief Symptoms</label>
            <textarea
              id="meta-symptoms"
              rows={3}
              placeholder="e.g., chest pain, shortness of breath, palpitations…"
              value={form.metadata.symptoms}
              onChange={(e) => updateMeta('symptoms', e.target.value)}
              className="input-field resize-none"
            />
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          id="btn-run-analysis"
          onClick={handleSubmit}
          disabled={loading}
          className="btn-primary"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          {loading ? 'Analysing…' : 'Run Analysis'}
        </button>
      </div>
    </div>
  );
}
