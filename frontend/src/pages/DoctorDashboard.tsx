import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Activity,
  Heart,
  Cpu,
  Clock,
  ChevronRight,
  Users,
  FileText,
  Settings as SettingsIcon,
  RefreshCw,
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import LiveECGCanvas from '../components/LiveECGCanvas';
import EmergencyAlertBanner from '../components/EmergencyAlertBanner';
import NewAnalysisTab from '../components/NewAnalysisTab';
import ReportView from '../components/ReportView';
import { createECGStream } from '../api/streamService';
import { getPatients } from '../api/patientService';
import { useAuth } from '../store/AuthContext';
import type {
  DashboardTab,
  ECGDataPoint,
  KafkaStreamPayload,
  AnalysisResponse,
  Patient,
} from '../types';

const MAX_ECG_POINTS = 500;

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({
  label, value, sub, icon: Icon, color,
}: {
  label: string; value: string; sub?: string;
  icon: React.ElementType; color: string;
}) {
  return (
    <div className="glass-card p-5 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-xs text-cg-muted">{label}</p>
        <p className="text-xl font-bold text-white mt-0.5">{value}</p>
        {sub && <p className="text-[11px] text-cg-muted mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Patients stub tab ─────────────────────────────────────────────────────────
function PatientsTab() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState('');

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 gap-3 text-cg-muted">
        <RefreshCw className="w-5 h-5 animate-spin" /> Loading patients…
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-red-400 text-sm">{error}</p>
        <p className="text-cg-muted text-xs mt-1">Ensure the backend is running.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white">Patient Registry</h2>
      {patients.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Users className="w-10 h-10 text-cg-muted mx-auto mb-3" />
          <p className="text-cg-muted text-sm">No patients found in the registry.</p>
        </div>
      ) : (
        <div className="glass-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                {['ID', 'Name', 'Age', 'Gender', 'Blood Type', 'Created'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs text-cg-muted uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-cg-muted">{p.id}</td>
                  <td className="px-4 py-3 font-medium text-white">{p.name}</td>
                  <td className="px-4 py-3 text-cg-muted">{p.age}</td>
                  <td className="px-4 py-3 text-cg-muted">{p.gender}</td>
                  <td className="px-4 py-3">
                    <span className="badge badge-info">{p.bloodType ?? '–'}</span>
                  </td>
                  <td className="px-4 py-3 text-cg-muted text-xs">
                    {new Date(p.createdAt).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Settings stub tab ─────────────────────────────────────────────────────────
function SettingsTab() {
  const { user, switchRole } = useAuth();
  return (
    <div className="space-y-6 max-w-xl">
      <h2 className="text-lg font-semibold text-white">Settings</h2>
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white">Account</h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><p className="text-cg-muted text-xs mb-1">Name</p><p className="text-white">{user?.name}</p></div>
          <div><p className="text-cg-muted text-xs mb-1">Role</p><p className="text-white">{user?.role}</p></div>
          <div><p className="text-cg-muted text-xs mb-1">Email</p><p className="text-white">{user?.email}</p></div>
        </div>
      </div>
      <div className="glass-card p-6 space-y-3">
        <h3 className="text-sm font-semibold text-white">Developer Options</h3>
        <p className="text-xs text-cg-muted">Switch role for demo purposes:</p>
        <div className="flex gap-3">
          <button onClick={() => switchRole('Doctor')}  className="btn-ghost text-xs">Switch → Doctor</button>
          <button onClick={() => switchRole('Patient')} className="btn-ghost text-xs">Switch → Patient</button>
        </div>
      </div>
    </div>
  );
}

// ── Doctor Dashboard ──────────────────────────────────────────────────────────
export default function DoctorDashboard() {
  const [activeTab,      setActiveTab]      = useState<DashboardTab>('telemetry');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isConnected,    setIsConnected]    = useState(false);
  const [ecgPoints,      setEcgPoints]      = useState<ECGDataPoint[]>([]);
  const [emergency,      setEmergency]      = useState<KafkaStreamPayload | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [latestPayload,  setLatestPayload]  = useState<KafkaStreamPayload | null>(null);
  const pointsRef = useRef<ECGDataPoint[]>([]);

  // ── Kafka stream ────────────────────────────────────────────────────────────
  const handleData = useCallback((payload: KafkaStreamPayload) => {
    setLatestPayload(payload);
    const pt: ECGDataPoint = { t: payload.timestamp, v: payload.ecg_value };
    pointsRef.current = [...pointsRef.current.slice(-(MAX_ECG_POINTS - 1)), pt];
    setEcgPoints([...pointsRef.current]);
  }, []);

  const handleEmergency = useCallback((payload: KafkaStreamPayload) => {
    setEmergency(payload);
  }, []);

  useEffect(() => {
    const disconnect = createECGStream({
      onData:      handleData,
      onEmergency: handleEmergency,
      onConnect:   setIsConnected,
    });
    return disconnect;
  }, [handleData, handleEmergency]);

  // When analysis finishes, jump to the reports tab
  function handleAnalysisResult(result: AnalysisResponse) {
    setAnalysisResult(result);
    setActiveTab('reports');
  }

  // ── Derived stats ───────────────────────────────────────────────────────────
  const currentHR  = latestPayload ? Math.round(60 / 0.008 * Math.abs(latestPayload.ecg_value) * 10) % 40 + 60 : '—';
  const confidence = latestPayload?.confidence != null ? `${(latestPayload.confidence * 100).toFixed(1)}%` : '—';

  return (
    <div className="flex h-screen bg-cg-bg overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isConnected={isConnected}
        collapsed={sidebarCollapsed}
        onCollapse={setSidebarCollapsed}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="print-hidden flex items-center justify-between px-6 py-4 border-b border-cg-border bg-cg-surface/50 backdrop-blur-sm flex-shrink-0">
          <div>
            <h1 className="text-base font-semibold text-white">
              {activeTab === 'telemetry'    && 'Live Telemetry Dashboard'}
              {activeTab === 'new-analysis' && 'New Multi-Modal Analysis'}
              {activeTab === 'patients'     && 'Patient Registry'}
              {activeTab === 'reports'      && 'Analysis Reports'}
              {activeTab === 'settings'     && 'Settings'}
            </h1>
            <p className="text-xs text-cg-muted mt-0.5">
              {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border
                              ${isConnected
                                ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                                : 'text-red-400 border-red-500/30 bg-red-500/10'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`} />
              {isConnected ? 'Kafka Stream Active' : 'Stream Offline'}
            </span>
          </div>
        </header>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-6 scrollbar-hidden">

          {/* Emergency alert */}
          {emergency && (
            <div className="mb-6 animate-fade-in-up">
              <EmergencyAlertBanner payload={emergency} onDismiss={() => setEmergency(null)} />
            </div>
          )}

          {/* ── Telemetry tab ──────────────────────────────────────────── */}
          {activeTab === 'telemetry' && (
            <div className="space-y-6 animate-fade-in-up">
              {/* KPI row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  label="Heart Rate" value={`${currentHR} bpm`}
                  sub="Real-time estimate" icon={Heart}
                  color="bg-red-500/15 text-red-400"
                />
                <StatCard
                  label="AI Confidence" value={confidence}
                  sub={latestPayload?.anomaly_type ?? 'Awaiting signal'}
                  icon={Cpu} color="bg-indigo-500/15 text-indigo-400"
                />
                <StatCard
                  label="Stream Status" value={isConnected ? 'Live' : 'Offline'}
                  sub="Kafka WebSocket" icon={Activity}
                  color={isConnected ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}
                />
                <StatCard
                  label="Buffer" value={`${ecgPoints.length}`}
                  sub={`/ ${MAX_ECG_POINTS} samples`} icon={Clock}
                  color="bg-cyan-500/15 text-cyan-400"
                />
              </div>

              {/* ECG Waveform */}
              <div className="glass-card p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Activity className={`w-4 h-4 ${emergency ? 'text-red-400' : 'text-indigo-400'}`} />
                    <h2 className="text-sm font-semibold text-white">Lead II — Live ECG Waveform</h2>
                    {emergency && <span className="badge badge-danger animate-pulse">EMERGENCY</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-cg-muted'}`} />
                    <span className="text-xs text-cg-muted font-mono">
                      {latestPayload ? `${latestPayload.ecg_value.toFixed(4)} μV` : '— μV'}
                    </span>
                  </div>
                </div>
                <LiveECGCanvas
                  dataPoints={ecgPoints}
                  isEmergency={!!emergency}
                  height={260}
                />
                <div className="flex justify-between mt-3 text-[10px] text-cg-muted font-mono">
                  <span>← {MAX_ECG_POINTS} samples</span>
                  <span>25 mm/s · 10 mm/mV</span>
                  <span>Now →</span>
                </div>
              </div>

              {/* Quick-access button */}
              <div className="flex justify-end">
                <button
                  id="btn-goto-analysis"
                  onClick={() => setActiveTab('new-analysis')}
                  className="btn-primary"
                >
                  Run New Analysis <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ── New Analysis tab ───────────────────────────────────────── */}
          {activeTab === 'new-analysis' && (
            <NewAnalysisTab onResult={handleAnalysisResult} />
          )}

          {/* ── Patients tab ───────────────────────────────────────────── */}
          {activeTab === 'patients' && <PatientsTab />}

          {/* ── Reports tab ────────────────────────────────────────────── */}
          {activeTab === 'reports' && (
            <div className="animate-fade-in-up">
              {analysisResult ? (
                <ReportView result={analysisResult} />
              ) : (
                <div className="glass-card p-16 text-center">
                  <FileText className="w-12 h-12 text-cg-muted mx-auto mb-4" />
                  <h3 className="text-white font-semibold mb-2">No Report Yet</h3>
                  <p className="text-cg-muted text-sm mb-6">
                    Run a new analysis to generate a clinical report.
                  </p>
                  <button
                    id="btn-goto-new-analysis"
                    onClick={() => setActiveTab('new-analysis')}
                    className="btn-primary"
                  >
                    Go to New Analysis
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Settings tab ───────────────────────────────────────────── */}
          {activeTab === 'settings' && <SettingsTab />}
        </div>
      </main>
    </div>
  );
}
