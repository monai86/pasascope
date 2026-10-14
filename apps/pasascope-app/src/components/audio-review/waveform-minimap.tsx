"use client";

import React, { useCallback, useEffect, useRef } from "react";

import { prepareCanvas, useElementSize } from "@/components/audio-review/use-element-size";
import { withAlpha, WORKBENCH_CANVAS } from "@/design-system/dataviz";

export interface WaveformMinimapProps {
  durationMs: number;
  currentTimeMs: number;
  viewportStartMs: number;
  viewportEndMs: number;
  peaks?: Int8Array | null;
  onViewportChange?: (startMs: number, endMs: number) => void;
  onSeek?: (timeMs: number) => void;
  label?: string;
  className?: string;
}

const TAP_SLOP_PX = 8;

/**
 * The whole recording at a glance, with the close-up's window outlined. A tap
 * jumps there; a sideways drag scrubs. A vertical swipe is left to the page.
 */
export function WaveformMinimap({
  durationMs,
  currentTimeMs,
  viewportStartMs,
  viewportEndMs,
  peaks,
  onViewportChange,
  onSeek,
  label = "Whole recording",
  className = "",
}: WaveformMinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const pressRef = useRef<{ pointerId: number; x: number; y: number; scrubbing: boolean } | null>(null);
  const { width, height } = useElementSize(containerRef);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || width === 0 || height === 0) return;
    const ctx = prepareCanvas(canvas, width, height);
    if (!ctx) return;
    const midY = height / 2;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = WORKBENCH_CANVAS.background;
    ctx.fillRect(0, 0, width, height);

    if (peaks && peaks.length > 0) {
      ctx.fillStyle = WORKBENCH_CANVAS.peaks;
      for (let x = 0; x < width; x += 2) {
        const value = Math.abs(peaks[Math.floor((x / width) * peaks.length)] || 0) / 128;
        const bar = Math.max(0.75, value * (height / 2 - 3));
        ctx.fillRect(x, midY - bar, 1.25, bar * 2);
      }
    } else {
      ctx.strokeStyle = WORKBENCH_CANVAS.grid;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(width, midY);
      ctx.stroke();
    }

    if (durationMs > 0) {
      const startX = (viewportStartMs / durationMs) * width;
      const endX = (viewportEndMs / durationMs) * width;
      ctx.fillStyle = withAlpha(WORKBENCH_CANVAS.background, 0.6);
      ctx.fillRect(0, 0, startX, height);
      ctx.fillRect(endX, 0, width - endX, height);
      ctx.strokeStyle = withAlpha(WORKBENCH_CANVAS.viewport, 0.85);
      ctx.lineWidth = 1.5;
      ctx.strokeRect(startX + 0.75, 0.75, Math.max(6, endX - startX) - 1.5, height - 1.5);

      const playheadX = (currentTimeMs / durationMs) * width;
      ctx.strokeStyle = WORKBENCH_CANVAS.playhead;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();
    }
  }, [durationMs, currentTimeMs, viewportStartMs, viewportEndMs, peaks, width, height]);

  useEffect(() => {
    draw();
  }, [draw]);

  const msAt = (clientX: number) => {
    const rect = containerRef.current!.getBoundingClientRect();
    return Math.max(0, Math.min(1, (clientX - rect.left) / Math.max(1, rect.width))) * durationMs;
  };

  const jumpTo = (targetMs: number) => {
    onSeek?.(targetMs);
    if (!onViewportChange) return;
    const windowMs = Math.max(1000, viewportEndMs - viewportStartMs);
    let start = Math.max(0, targetMs - windowMs / 2);
    let end = start + windowMs;
    if (end > durationMs) {
      end = durationMs;
      start = Math.max(0, durationMs - windowMs);
    }
    onViewportChange(start, end);
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current || durationMs <= 0) return;
    pressRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, scrubbing: event.pointerType === "mouse" };
    // A mouse press seeks at once; a touch waits to see whether it is a tap, a scrub or a scroll.
    if (event.pointerType === "mouse") {
      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch {
        // Not needed for a click.
      }
      jumpTo(msAt(event.clientX));
    }
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const press = pressRef.current;
    if (!press || press.pointerId !== event.pointerId) return;
    if (!press.scrubbing && Math.abs(event.clientX - press.x) > TAP_SLOP_PX) press.scrubbing = true;
    if (press.scrubbing) onSeek?.(msAt(event.clientX));
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    const press = pressRef.current;
    pressRef.current = null;
    if (!press || press.pointerId !== event.pointerId || event.pointerType === "mouse") return;
    if (press.scrubbing || Math.hypot(event.clientX - press.x, event.clientY - press.y) < TAP_SLOP_PX) jumpTo(msAt(event.clientX));
  };

  return (
    <div
      ref={containerRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={() => {
        pressRef.current = null;
      }}
      className={`relative h-11 w-full cursor-pointer touch-pan-y select-none overflow-hidden rounded-control bg-navy ${className}`}
      data-testid="waveform-minimap"
      role="img"
      aria-label={label}
    >
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}
