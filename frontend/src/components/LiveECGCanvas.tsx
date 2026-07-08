import { useRef, useEffect, useCallback } from 'react';
import type { ECGDataPoint } from '../types';

interface LiveECGCanvasProps {
  dataPoints:  ECGDataPoint[];
  isEmergency: boolean;
  width?:      number;
  height?:     number;
}

const BUFFER_SIZE  = 500;   // max visible samples
const LINE_COLOR   = '#6366f1';
const EMERG_COLOR  = '#ef4444';
const GRID_COLOR   = 'rgba(255,255,255,0.04)';
const BASELINE     = 0;

export default function LiveECGCanvas({
  dataPoints,
  isEmergency,
  height = 220,
}: LiveECGCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    // ── Background ──────────────────────────────────────────────────────────
    ctx.fillStyle = '#0d0d1a';
    ctx.fillRect(0, 0, W, H);

    // ── Grid ────────────────────────────────────────────────────────────────
    ctx.strokeStyle = GRID_COLOR;
    ctx.lineWidth   = 1;
    const gridCols = 20;
    const gridRows = 8;
    for (let i = 0; i <= gridCols; i++) {
      const x = (W / gridCols) * i;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let j = 0; j <= gridRows; j++) {
      const y = (H / gridRows) * j;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }

    // Baseline
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2);
    ctx.stroke();
    ctx.setLineDash([]);

    if (dataPoints.length < 2) return;

    const visiblePoints = dataPoints.slice(-BUFFER_SIZE);
    const values = visiblePoints.map((p) => p.v);
    const minV   = Math.min(...values, BASELINE) - 0.05;
    const maxV   = Math.max(...values, BASELINE) + 0.05;
    const rangeV = maxV - minV || 1;

    const toX = (_: number, i: number) => (i / (BUFFER_SIZE - 1)) * W;
    const toY = (v: number) => H - ((v - minV) / rangeV) * H;

    // ── ECG line ────────────────────────────────────────────────────────────
    const strokeColor = isEmergency ? EMERG_COLOR : LINE_COLOR;

    // Glow effect
    ctx.save();
    ctx.shadowBlur  = 12;
    ctx.shadowColor = strokeColor;
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.lineCap     = 'round';
    ctx.beginPath();
    visiblePoints.forEach((pt, i) => {
      const x = toX(pt.t, i);
      const y = toY(pt.v);
      if (i === 0) ctx.moveTo(x, y);
      else         ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();

    // ── Scanning cursor ─────────────────────────────────────────────────────
    const cursorX = toX(0, visiblePoints.length - 1);
    const gradient = ctx.createLinearGradient(cursorX - 30, 0, cursorX, 0);
    gradient.addColorStop(0, 'rgba(0,0,0,0)');
    gradient.addColorStop(1, isEmergency ? 'rgba(239,68,68,0.15)' : 'rgba(99,102,241,0.15)');
    ctx.fillStyle = gradient;
    ctx.fillRect(cursorX - 30, 0, 30, H);
  }, [dataPoints, isEmergency]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Resize observer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const obs = new ResizeObserver(() => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      draw();
    });
    obs.observe(canvas);
    return () => obs.disconnect();
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: '100%', height }}
      className="rounded-xl block"
    />
  );
}
