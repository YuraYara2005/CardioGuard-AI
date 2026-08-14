import { useState, useEffect, useRef } from 'react';

import { AlertTriangle, FileText, Activity } from 'lucide-react';
import type { EmergencyEpisode, Patient } from '../types';

export default function FrozenEpisodesTab({ patientId }: { patientId: string }) {
  const [episodes, setEpisodes] = useState<EmergencyEpisode[]>([]);
  const [selectedEpisode, setSelectedEpisode] = useState<EmergencyEpisode | null>(null);
  const [loading, setLoading] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [patientData, setPatientData] = useState<Patient | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    fetchEpisodes();
    fetchPatientData();
  }, [patientId]);

  const fetchPatientData = async () => {
    try {
      // apiClient ensures proper base URL and headers
      const { default: apiClient } = await import('../api/axiosInstance');
      const res = await apiClient.get(`/patients/${patientId}`);
      setPatientData(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchEpisodes();
  }, [patientId]);

  const fetchEpisodes = async () => {
    try {
      setLoading(true);
      const { default: apiClient } = await import('../api/axiosInstance');
      const res = await apiClient.get(`/episodes/${patientId}`);
      if (res.data.status === 'success') {
        setEpisodes(res.data.episodes);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadEpisodeDetail = async (id: number) => {
    try {
      setLoading(true);
      const { default: apiClient } = await import('../api/axiosInstance');
      const res = await apiClient.get(`/episodes/detail/${id}`);
      if (res.data.status === 'success') {
        setSelectedEpisode(res.data.episode);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async (id: number) => {
    try {
      setGeneratingReport(true);
      const { default: apiClient } = await import('../api/axiosInstance');
      const res = await apiClient.post(`/episodes/${id}/generate-emergency-report`);
      if (res.data.status === 'success') {
        setSelectedEpisode(prev => prev ? { ...prev, report_state: res.data.report } : null);
        fetchEpisodes();
      }
    } catch (e: any) {
      alert(e.response?.data?.detail || e.message || 'Error generating report');
      console.error(e);
    } finally {
      setGeneratingReport(false);
    }
  };

  useEffect(() => {
    if (selectedEpisode && selectedEpisode.leads_data && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const width = canvas.width;
      const height = canvas.height;

      // Clear canvas
      ctx.fillStyle = '#1e1e2e';
      ctx.fillRect(0, 0, width, height);

      const leads = selectedEpisode.leads_data; // Array of [12] leads over 1000 timesteps
      const weights = selectedEpisode.attention_weights || [];
      const numPoints = leads.length;

      // Draw Attention Heatmap Background
      if (weights.length > 0) {
        // Flatten weights to find max
        const flatWeights = weights.map(w => Array.isArray(w) ? w[0] : w);
        const maxWeight = Math.max(...flatWeights, 0.0001);

        flatWeights.forEach((w, i) => {
          const x = (i / numPoints) * width;
          const rectWidth = width / numPoints;
          const intensity = w / maxWeight; // 0 to 1

          if (intensity > 0.1) {
            ctx.fillStyle = `rgba(239, 68, 68, ${intensity * 0.5})`; // Red overlay
            ctx.fillRect(x, 0, rectWidth, height);
          }
        });
      }

      // Draw Lead II (Index 1)
      ctx.strokeStyle = '#4ade80'; // Emerald green
      ctx.lineWidth = 1.5;
      ctx.beginPath();

      const maxVal = Math.max(...leads.map(l => l[1]));
      const minVal = Math.min(...leads.map(l => l[1]));
      const range = maxVal - minVal || 1;

      leads.forEach((l, i) => {
        const x = (i / numPoints) * width;
        const val = l[1];
        // Scale and translate
        const normalized = (val - minVal) / range;
        const y = height - (normalized * height * 0.8 + height * 0.1);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Draw trigger line
      const triggerX = (selectedEpisode.trigger_index / numPoints) * width;
      ctx.strokeStyle = '#facc15';
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(triggerX, 0);
      ctx.lineTo(triggerX, height);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [selectedEpisode]);

  const renderReport = () => {
    if (!selectedEpisode || selectedEpisode.report_state === 'PENDING') return null;

    let parsedReport = null;
    try {
      parsedReport = JSON.parse(selectedEpisode.report_state);
    } catch (e) {
      // Legacy string
    }

    if (parsedReport && parsedReport.schema_version === 1) {
      const isLowConfidence = parsedReport.episode.confidence < 0.8;
      const confPercent = (parsedReport.episode.confidence * 100).toFixed(1);
      
      return (
        <div className="mt-6 flex flex-col gap-4">
          <div className="flex justify-between items-start border-b border-white/10 pb-4">
            <div>
              <h3 className="text-xl font-bold text-white">Emergency Clinical Report</h3>
              <p className="text-sm text-indigo-300">AI-Assisted Decision Support</p>
            </div>
            <div className="text-right">
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${parsedReport.severity === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                {parsedReport.severity.toUpperCase()}
              </span>
              <div className="text-xs text-cg-muted mt-2">
                Generated: {new Date(parsedReport.generated_at).toLocaleString()}
              </div>
            </div>
          </div>
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-white/5 p-4 rounded-lg">
            <div><div className="text-xs text-cg-muted">Patient Name</div><div className="font-semibold text-white">{parsedReport.patient.name}</div></div>
            <div><div className="text-xs text-cg-muted">Patient ID</div><div className="font-semibold text-white">{parsedReport.patient.id}</div></div>
            <div><div className="text-xs text-cg-muted">Blood Type</div><div className="font-semibold text-white">{parsedReport.patient.blood_type}</div></div>
            <div><div className="text-xs text-cg-muted">Episode Time</div><div className="font-semibold text-white">{new Date(parsedReport.episode.detected_at).toLocaleString()}</div></div>
          </div>
          {/* AI ECG Finding */}
          <div className="bg-white/5 p-4 rounded-lg border border-white/5">
            <h4 className="text-sm font-semibold text-white mb-2 uppercase tracking-wider text-cg-muted">AI ECG Finding</h4>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-lg font-bold text-red-400">{parsedReport.episode.predicted_label}</span>
              <span className="text-sm text-indigo-300">Confidence: {confPercent}%</span>
            </div>
            {isLowConfidence && (
              <div className="text-sm text-yellow-400 bg-yellow-400/10 px-3 py-2 rounded border border-yellow-400/20 mb-2 inline-block">
                {parsedReport.confidence_disclaimer || "Low-confidence prediction — clinical verification required"}
              </div>
            )}
            <p className="text-sm text-cg-muted">This is an AI prediction and not a confirmed diagnosis.</p>
          </div>
          {/* Clinical Interpretation */}
          <div className="bg-white/5 p-4 rounded-lg border border-white/5">
            <h4 className="text-sm font-semibold text-white mb-2 uppercase tracking-wider text-cg-muted">Clinical Interpretation</h4>
            <p className="text-sm text-white leading-relaxed whitespace-pre-wrap">{parsedReport.clinical_interpretation}</p>
          </div>
          {/* Recommended Actions */}
          <div className="bg-white/5 p-4 rounded-lg border border-white/5">
            <h4 className="text-sm font-semibold text-white mb-2 uppercase tracking-wider text-cg-muted">Recommended Actions</h4>
            <ol className="list-decimal list-inside space-y-2 text-sm text-white">
              {parsedReport.recommended_actions.map((act: string, idx: number) => (
                <li key={idx} className="leading-relaxed pl-1">{act}</li>
              ))}
            </ol>
          </div>
          {/* XAI & RAG */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white/5 p-4 rounded-lg border border-white/5">
               <h4 className="text-sm font-semibold text-white mb-2 uppercase tracking-wider text-cg-muted">Explainability Summary</h4>
               <p className="text-xs text-cg-muted leading-relaxed">{parsedReport.xai_summary}</p>
            </div>
            <div className="bg-white/5 p-4 rounded-lg border border-white/5">
               <h4 className="text-sm font-semibold text-white mb-2 uppercase tracking-wider text-cg-muted">Retrieved Clinical Context</h4>
               <p className="text-xs text-cg-muted leading-relaxed mb-1 italic">Evidence-grounded context retrieved from the CardioGuardAI medical knowledge base:</p>
               <p className="text-xs text-cg-muted leading-relaxed">{parsedReport.retrieved_context_summary}</p>
            </div>
          </div>
          {/* Footer */}
          <div className="mt-4 text-center border-t border-white/10 pt-4">
            <p className="text-xs text-cg-muted">{parsedReport.disclaimer}</p>
          </div>
        </div>
      );
    } else {
      // Legacy string rendering safely
      let safeStr = selectedEpisode.report_state
        .replace(/\*\*/g, '')
        .replace(/#/g, '')
        .replace(/🚨/g, '');
      return (
        <div className="mt-6 bg-white/5 p-4 rounded-xl border border-white/10 max-w-none">
          <h3 className="text-lg font-semibold text-white mb-4">Emergency Clinical Report (Legacy)</h3>
          <div className="text-sm text-white whitespace-pre-wrap leading-relaxed">{safeStr}</div>
        </div>
      );
    }
  };

  return (
    <div className="flex gap-6 h-full">
      {/* List Panel */}
      <div className="w-1/3 glass-card flex flex-col overflow-hidden">
        <div className="p-4 border-b border-white/5">
          <h2 className="font-semibold text-white">Frozen Emergency Episodes</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {loading && !selectedEpisode ? <div className="text-cg-muted p-4">Loading...</div> : null}
          {episodes.map(ep => (
            <div
              key={ep.id}
              onClick={() => loadEpisodeDetail(ep.id)}
              className={`p-3 m-2 rounded-lg cursor-pointer transition-colors ${selectedEpisode?.id === ep.id ? 'bg-indigo-500/20 border border-indigo-500/30' : 'bg-white/5 hover:bg-white/10 border border-transparent'
                }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-white">{ep.anomaly_type}</span>
              </div>
              <div className="text-xs text-cg-muted font-medium mb-1">
                {patientData?.name || ep.patient_name || patientId} ({patientId})
              </div>
              <div className="text-xs text-cg-muted">
                {new Date(ep.detected_at).toLocaleString()}
              </div>
              <div className="text-xs mt-2 flex justify-between">
                <span className="text-indigo-300">{(ep.confidence_score * 100).toFixed(1)}% Conf</span>
                <span className={ep.report_state === 'PENDING' ? 'text-yellow-400' : 'text-emerald-400'}>
                  {ep.report_state === 'PENDING' ? 'No Report' : 'Report Available'}
                </span>
              </div>
            </div>
          ))}
          {episodes.length === 0 && !loading && (
            <div className="text-center p-6 text-cg-muted text-sm">No frozen episodes found.</div>
          )}
        </div>
      </div>

      {/* Detail Panel */}
      <div className="w-2/3 glass-card flex flex-col p-6 overflow-y-auto">
        {selectedEpisode ? (
          <div className="space-y-6">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
                  <Activity className="text-red-400" />
                  {selectedEpisode.anomaly_type} Event
                </h2>
                <div className="text-md font-semibold text-indigo-300 mb-2">
                  Patient: {patientData?.name || selectedEpisode.patient_name || patientId} ({patientId})
                </div>
                <p className="text-sm text-cg-muted">
                  Detected at: {new Date(selectedEpisode.detected_at).toLocaleString()}
                </p>
                <p className="text-sm text-cg-muted">
                  Confidence: {(selectedEpisode.confidence_score * 100).toFixed(1)}%
                </p>
              </div>

              <button
                onClick={() => generateReport(selectedEpisode.id)}
                disabled={generatingReport}
                className="btn-primary flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                {generatingReport ? 'Generating...' : 'Generate RAG Report'}
              </button>
            </div>

            {selectedEpisode.leads_data && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-cg-muted">
                  <span>Pre-trigger window</span>
                  <span className="text-yellow-400">Trigger Point</span>
                  <span>Post-trigger window</span>
                </div>
                <div className="bg-[#1e1e2e] rounded-xl border border-white/10 p-4 relative overflow-hidden">
                  {/* Legend */}
                  <div className="absolute top-2 left-4 text-xs font-mono bg-black/50 px-2 py-1 rounded text-white flex gap-3">
                    <span className="text-[#4ade80]">Lead II</span>
                    <span className="text-red-400 flex items-center gap-1">
                      <div className="w-3 h-3 bg-red-500/50 rounded-sm"></div> XAI Attention Highlight
                    </span>
                  </div>
                  <canvas
                    ref={canvasRef}
                    width={800}
                    height={250}
                    className="w-full h-[250px] rounded"
                  />
                </div>
              </div>
            )}

            {renderReport()}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-cg-muted">
            Select an episode from the left panel to view details.
          </div>
        )}
      </div>
    </div>
  );
}
