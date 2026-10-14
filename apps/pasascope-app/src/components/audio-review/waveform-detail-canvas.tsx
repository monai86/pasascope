"use client";

import React, { useCallback, useEffect, useRef } from "react";

import { prepareCanvas, useElementSize } from "@/components/audio-review/use-element-size";
import { speakerColour, withAlpha, WORKBENCH_CANVAS } from "@/design-system/dataviz";

export interface WaveformSegment {
  id: string;
  speaker: string;
  startMs: number;
  endMs: number;
  text?: string;
}

export interface WaveformDetailCanvasProps {
  currentTimeMs: number;
  viewportStartMs: number;
  viewportEndMs: number;
  segments: WaveformSegment[];
  peaks?: Int8Array | null;
  /** Length of the whole recording, to place the peaks of the visible window. */
  durationMs?: number;
  onSeek?: (timeMs: number) => void;
  onSegmentBoundaryChange?: (segmentId: string, startMs: number, endMs: number) => void;
  label?: string;
  className?: string;
}

interface DragState {
  segmentId: string;
  edge: "start" | "end";
}

interface PressState {
  pointerId: number;
  x: number;
  y: number;
}

// Movement below this is a tap, which seeks; above it the gesture belongs to whoever claimed it.
const TAP_SLOP_PX = 8;
const MIN_DURATION_MS = 150;

/**
 * A close-up of the recording around the playhead: the waveform, each line as
 * a band in its speaker's colour, and the playhead. A tap seeks, and dragging
 * a band's edge moves that line's start or end. The canvas follows its box at
 * the screen's pixel density, and a vertical swipe across it still scrolls the
 * page, so it behaves on a phone as it does with a mouse.
 */
export function WaveformDetailCanvas({
  currentTimeMs,
  viewportStartMs,
  viewportEndMs,
  segments,
  peaks,
  durationMs,
  onSeek,
  onSegmentBoundaryChange,
  label = "Waveform close-up",
  className = "",
}: WaveformDetailCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const pressRef = useRef<PressState | null>(null);
  const { width, height } = useElementSize(containerRef);

  const windowMs = Math.max(1000, viewportEndMs - viewportStartMs);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || width === 0 || height === 0) return;
    const ctx = prepareCanvas(canvas, width, height);
    if (!ctx) return;
    const xAt = (ms: number) => ((ms - viewportStartMs) / windowMs) * width;
    const laneTop = 20;
    const laneHeight = height - laneTop - 4;
    const midY = laneTop + laneHeight / 2;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = WORKBENCH_CANVAS.background;
    ctx.fillRect(0, 0, width, height);

    // Second marks, thinned out so the labels never collide on a narrow screen.
    const pxPerSecond = (width / windowMs) * 1000;
    const stepMs = pxPerSecond >= 44 ? 1000 : pxPerSecond >= 22 ? 2000 : 5000;
    ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 1;
    for (let t = Math.ceil(viewportStartMs / stepMs) * stepMs; t <= viewportEndMs; t += stepMs) {
      const x = Math.round(xAt(t)) + 0.5;
      ctx.strokeStyle = WORKBENCH_CANVAS.grid;
      ctx.beginPath();
      ctx.moveTo(x, laneTop - 4);
      ctx.lineTo(x, height);
      ctx.stroke();
      ctx.fillStyle = WORKBENCH_CANVAS.axisLabel;
      ctx.fillText(formatAxis(t), x + 3, 9);
    }

    // Line bands behind the waveform, so the waveform reads on top of them.
    for (const seg of segments) {
      if (seg.endMs < viewportStartMs || seg.startMs > viewportEndMs) continue;
      const startX = xAt(seg.startMs);
      const endX = xAt(seg.endMs);
      const colour = speakerColour(seg.speaker, "navy");
      ctx.fillStyle = withAlpha(colour, 0.18);
      ctx.fillRect(startX, laneTop, Math.max(2, endX - startX), laneHeight);
      ctx.fillStyle = colour;
      ctx.fillRect(startX, laneTop, Math.max(2, endX - startX), 3);
      // Edge grips, the parts that can be dragged.
      ctx.fillRect(startX - 1.5, midY - 12, 3, 24);
      ctx.fillRect(endX - 1.5, midY - 12, 3, 24);

      const labelWidth = endX - startX - 12;
      if (labelWidth > 24) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(startX + 6, laneTop + 4, labelWidth, 18);
        ctx.clip();
        ctx.font = "600 11px system-ui, sans-serif";
        ctx.fillStyle = WORKBENCH_CANVAS.segmentLabel;
        ctx.fillText(`${seg.speaker.replace("*", "")}  ${seg.text ?? ""}`, startX + 6, laneTop + 13);
        ctx.restore();
      }
    }

    // The waveform of the visible window, one bar per two pixels.
    if (peaks && peaks.length > 0 && durationMs && durationMs > 0) {
      ctx.fillStyle = withAlpha(WORKBENCH_CANVAS.peaks, 0.85);
      const half = laneHeight / 2 - 6;
      for (let x = 0; x < width; x += 2) {
        const ms = viewportStartMs + (x / width) * windowMs;
        const index = Math.floor((ms / durationMs) * peaks.length);
        if (index < 0 || index >= peaks.length) continue;
        const bar = Math.max(1, (Math.abs(peaks[index]) / 128) * half);
        ctx.fillRect(x, midY - bar, 1.25, bar * 2);
      }
    } else {
      ctx.strokeStyle = WORKBENCH_CANVAS.grid;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();
    }

    if (currentTimeMs >= viewportStartMs && currentTimeMs <= viewportEndMs) {
      const x = xAt(currentTimeMs);
      ctx.strokeStyle = WORKBENCH_CANVAS.playhead;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, laneTop - 4);
      ctx.lineTo(x, height);
      ctx.stroke();
      ctx.fillStyle = WORKBENCH_CANVAS.playhead;
      ctx.beginPath();
      ctx.moveTo(x - 5, laneTop - 8);
      ctx.lineTo(x + 5, laneTop - 8);
      ctx.lineTo(x, laneTop - 1);
      ctx.fill();
    }
  }, [currentTimeMs, viewportStartMs, viewportEndMs, windowMs, segments, peaks, durationMs, width, height]);

  useEffect(() => {
    draw();
  }, [draw]);

  const msAt = (clientX: number) => {
    const rect = containerRef.current!.getBoundingClientRect();
    return viewportStartMs + ((clientX - rect.left) / Math.max(1, rect.width)) * windowMs;
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    pressRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
    const rect = containerRef.current.getBoundingClientRect();
    const pointerMs = msAt(event.clientX);
    // A fingertip is less exact than a cursor, so its grab zone is wider.
    const grabPx = event.pointerType === "mouse" ? 8 : 16;
    const grabMs = (grabPx / Math.max(1, rect.width)) * windowMs;
    let nearest: { drag: DragState; distance: number } | null = null;
    for (const seg of segments) {
      for (const edge of ["start", "end"] as const) {
        const distance = Math.abs((edge === "start" ? seg.startMs : seg.endMs) - pointerMs);
        if (distance <= grabMs && (!nearest || distance < nearest.distance)) {
          nearest = { drag: { segmentId: seg.id, edge }, distance };
        }
      }
    }
    if (nearest && onSegmentBoundaryChange) {
      dragRef.current = nearest.drag;
      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch {
        // Capture is a nicety; dragging still works inside the box.
      }
    }
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || !onSegmentBoundaryChange) return;
    const seg = segments.find((s) => s.id === drag.segmentId);
    if (!seg) return;
    // Boundaries land on 50 ms steps.
    const ms = Math.round(msAt(event.clientX) / 50) * 50;
    if (drag.edge === "start") {
      onSegmentBoundaryChange(seg.id, Math.max(0, Math.min(ms, seg.endMs - MIN_DURATION_MS)), seg.endMs);
    } else {
      onSegmentBoundaryChange(seg.id, seg.startMs, Math.max(ms, seg.startMs + MIN_DURATION_MS));
    }
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    const press = pressRef.current;
    const dragged = dragRef.current;
    pressRef.current = null;
    dragRef.current = null;
    if (!press || press.pointerId !== event.pointerId) return;
    const moved = Math.hypot(event.clientX - press.x, event.clientY - press.y);
    if (!dragged && moved < TAP_SLOP_PX) onSeek?.(Math.max(0, msAt(event.clientX)));
  };

  const handlePointerCancel = () => {
    pressRef.current = null;
    dragRef.current = null;
  };

  return (
    <div
      ref={containerRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      className={`relative h-32 w-full cursor-crosshair touch-pan-y select-none overflow-hidden rounded-control bg-navy sm:h-40 ${className}`}
      data-testid="waveform-detail-canvas"
      role="img"
      aria-label={label}
    >
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}

function formatAxis(ms: number): string {
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
