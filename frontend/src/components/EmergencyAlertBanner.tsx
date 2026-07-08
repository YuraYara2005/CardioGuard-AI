import { AlertTriangle, X, Siren } from 'lucide-react';
import type { KafkaStreamPayload } from '../types';

interface EmergencyAlertBannerProps {
  payload:   KafkaStreamPayload;
  onDismiss: () => void;
}

export default function EmergencyAlertBanner({
  payload,
  onDismiss,
}: EmergencyAlertBannerProps) {
  return (
    <div
      id="emergency-banner"
      className="emergency-banner flex items-start gap-4 relative"
      role="alert"
      aria-live="assertive"
    >
      {/* Pulsing icon */}
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-500/20 border border-red-500/40
                      flex items-center justify-center animate-pulse">
        <Siren className="w-5 h-5 text-red-400" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span className="text-red-300 font-bold text-sm tracking-wide uppercase">
            Critical Emergency Detected
          </span>
          <span className="badge badge-danger ml-2 animate-pulse">
            {payload.anomaly_type ?? 'Unknown Anomaly'}
          </span>
        </div>

        <p className="text-sm text-red-200/80 leading-relaxed">
          Patient <span className="font-semibold text-white">{payload.patient_id}</span> has
          been flagged with{' '}
          <span className="font-semibold text-red-300">
            {payload.anomaly_type ?? 'a critical cardiac event'}
          </span>
          {payload.confidence !== undefined && (
            <> (confidence: {(payload.confidence * 100).toFixed(1)}%)</>
          )}
          . Immediate clinical review is required.
        </p>

        <div className="flex items-center gap-3 mt-2">
          <span className="text-[11px] text-red-400/70 font-mono">
            {new Date(payload.timestamp).toLocaleTimeString()}
          </span>
          {payload.lead && (
            <span className="text-[11px] text-red-400/70">
              Lead: {payload.lead}
            </span>
          )}
        </div>
      </div>

      {/* Dismiss */}
      <button
        id="btn-dismiss-emergency"
        onClick={onDismiss}
        className="flex-shrink-0 p-1 rounded-lg hover:bg-white/10 text-red-400/60
                   hover:text-white transition-colors"
        aria-label="Dismiss alert"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
