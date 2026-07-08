import type { KafkaStreamPayload } from '../types';

const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000';

// ── Callback types ────────────────────────────────────────────────────────────
export type ECGDataCallback    = (payload: KafkaStreamPayload) => void;
export type EmergencyCallback  = (payload: KafkaStreamPayload) => void;
export type ConnectionCallback = (connected: boolean) => void;
export type ErrorCallback      = (err: Event) => void;

// ── Options ───────────────────────────────────────────────────────────────────
export interface StreamServiceOptions {
  patientId?: string;
  onData:      ECGDataCallback;
  onEmergency: EmergencyCallback;
  onConnect?:  ConnectionCallback;
  onError?:    ErrorCallback;
}

/**
 * ECGStreamService
 *
 * Manages a persistent WebSocket connection to the CardioGuard Kafka
 * bridge endpoint (ws://…/ws/ecg-stream).
 *
 * Every incoming frame is a JSON-serialised `KafkaStreamPayload`.
 * If `is_emergency` is true the dedicated `onEmergency` callback fires
 * IN ADDITION TO the regular `onData` callback so the UI can render both
 * the waveform AND the alert banner without extra logic.
 *
 * Reconnection: exponential back-off capped at 30 s.
 */
export class ECGStreamService {
  private ws: WebSocket | null = null;
  private opts: StreamServiceOptions;
  private retryDelay = 1_000;   // ms – doubles on each failure, max 30 s
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private manualClose = false;

  constructor(opts: StreamServiceOptions) {
    this.opts = opts;
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  connect(): void {
    this.manualClose = false;
    this._open();
  }

  disconnect(): void {
    this.manualClose = true;
    this._clearRetry();
    this.ws?.close(1000, 'Client disconnect');
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // ── Private helpers ─────────────────────────────────────────────────────────

  private _open(): void {
    const { patientId } = this.opts;
    const url = patientId
      ? `${WS_BASE}/ws/ecg-stream?patient_id=${patientId}`
      : `${WS_BASE}/ws/ecg-stream`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.info('[ECGStreamService] Connected to Kafka bridge.');
      this.retryDelay = 1_000;      // reset back-off on successful connect
      this.opts.onConnect?.(true);
    };

    this.ws.onmessage = (event: MessageEvent<string>) => {
      try {
        const payload: KafkaStreamPayload = JSON.parse(event.data);
        this.opts.onData(payload);
        if (payload.is_emergency) {
          this.opts.onEmergency(payload);
        }
      } catch (err) {
        console.warn('[ECGStreamService] Failed to parse frame:', event.data, err);
      }
    };

    this.ws.onerror = (err) => {
      console.error('[ECGStreamService] WebSocket error:', err);
      this.opts.onError?.(err);
    };

    this.ws.onclose = (ev) => {
      this.opts.onConnect?.(false);
      if (!this.manualClose) {
        console.warn(
          `[ECGStreamService] Connection closed (${ev.code}). Retrying in ${this.retryDelay / 1000}s…`,
        );
        this._scheduleRetry();
      }
    };
  }

  private _scheduleRetry(): void {
    this._clearRetry();
    this.retryTimer = setTimeout(() => {
      this.retryDelay = Math.min(this.retryDelay * 2, 30_000);
      this._open();
    }, this.retryDelay);
  }

  private _clearRetry(): void {
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }
}

// ── Convenience factory ───────────────────────────────────────────────────────

/** Creates and immediately connects an ECGStreamService. Returns a disconnect fn. */
export function createECGStream(opts: StreamServiceOptions): () => void {
  const svc = new ECGStreamService(opts);
  svc.connect();
  return () => svc.disconnect();
}
