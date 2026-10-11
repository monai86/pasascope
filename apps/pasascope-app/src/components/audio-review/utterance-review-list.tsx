"use client";

import React, { useRef, useEffect } from "react";
import { Play, Sparkles, CheckCircle2 } from "lucide-react";
import { formatTimecode } from "./audio-scrubber-bar";
import { speakerColour } from "@/design-system/dataviz";

export interface ReviewLine {
  lineId: string;
  speaker: string;
  text: string;
  startMs?: number;
  endMs?: number;
  clinicalTag?: string;
  verified?: boolean;
}

export interface UtteranceReviewListProps {
  lines: ReviewLine[];
  activeLineId?: string;
  onSelectLine?: (lineId: string) => void;
  onLineChange: (index: number, updatedLine: ReviewLine) => void;
  onPlayUtterance?: (startMs: number, endMs?: number) => void;
  className?: string;
}

export function UtteranceReviewList({
  lines,
  activeLineId,
  onSelectLine,
  onLineChange,
  onPlayUtterance,
  className = "",
}: UtteranceReviewListProps) {
  const activeRowRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll active row into view when activeLineId changes
  useEffect(() => {
    if (activeRowRef.current && typeof activeRowRef.current.scrollIntoView === "function") {
      activeRowRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [activeLineId]);

  const handleSpeakerChange = (index: number, newSpeaker: string) => {
    const targetLine = lines[index];
    if (!targetLine) return;
    onLineChange(index, {
      ...targetLine,
      speaker: newSpeaker,
    });
  };

  const handleTextChange = (index: number, newText: string) => {
    const targetLine = lines[index];
    if (!targetLine) return;
    onLineChange(index, {
      ...targetLine,
      text: newText,
    });
  };

  return (
    <div
      className={`flex flex-col gap-2 divide-y divide-line overflow-y-auto rounded-lg border border-line bg-white p-2 shadow-sm    ${className}`}
      data-testid="utterance-review-list"
    >
      {lines.length === 0 ? (
        <div className="py-8 text-center text-sm text-ink-muted">
          No utterances recorded for this session.
        </div>
      ) : (
        lines.map((line, index) => {
          const isActive = line.lineId === activeLineId;

          return (
            <div
              key={line.lineId || index}
              ref={isActive ? activeRowRef : null}
              onClick={() => onSelectLine?.(line.lineId)}
              className={`group flex flex-wrap items-center gap-2.5 rounded-md px-3 py-2 transition ${
                isActive
                  ? "bg-brand-soft ring-1 ring-[color:var(--color-focus-ring)]  "
                  : "hover:bg-surface-soft "
              }`}
            >
              {/* Play Utterance Button */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  if (typeof line.startMs === "number") {
                    onPlayUtterance?.(line.startMs, line.endMs);
                  }
                }}
                disabled={typeof line.startMs !== "number"}
                aria-label={`Play line ${index + 1}`}
                className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-surface-muted text-ink-muted transition hover:bg-brand hover:text-white disabled:opacity-30  "
              >
                <Play size={13} className="translate-x-0.5" />
              </button>

              {/* Timecode Badge */}
              <div className="w-24 flex-shrink-0 font-mono text-xs text-ink-subtle ">
                {typeof line.startMs === "number" && typeof line.endMs === "number" ? (
                  <span>
                    {formatTimecode(line.startMs).slice(3)} - {formatTimecode(line.endMs).slice(3)}
                  </span>
                ) : (
                  <span>--:--</span>
                )}
              </div>

              {/* Speaker Selector */}
              <div className="flex-shrink-0">
                <select
                  value={line.speaker.replace("*", "")}
                  onChange={(e) => handleSpeakerChange(index, e.target.value)}
                  // The left edge carries the speaker colour; the code stays in text ink.
                  className="h-9 rounded-control border border-line-strong border-l-4 bg-surface px-2 py-0.5 text-xs font-semibold text-ink transition"
                  style={{ borderLeftColor: speakerColour(line.speaker, "light") }}
                  aria-label="Speaker Role"
                >
                  <option value="CHI">CHI (Child)</option>
                  <option value="INV">INV (Clinician)</option>
                  <option value="MOT">MOT (Mother)</option>
                  <option value="FAT">FAT (Father)</option>
                  <option value="OTH">OTH (Other)</option>
                </select>
              </div>

              {/* Editable Thai Utterance Text Input */}
              <div className="min-w-[180px] flex-1">
                <input
                  type="text"
                  value={line.text}
                  onChange={(e) => handleTextChange(index, e.target.value)}
                  className="w-full rounded border border-transparent bg-transparent px-2 py-1 text-sm text-ink transition focus:border-line-strong focus:bg-white focus:outline-none focus:ring-1 focus:ring-[color:var(--color-focus-ring)]   "
                  placeholder="Enter Thai speech transcription..."
                />
              </div>

              {/* Clinical Cue Tag Badges */}
              {line.clinicalTag && (
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {line.clinicalTag.toLowerCase().includes("echolalia") && (
                    <span className="flex items-center gap-1 rounded-full bg-[color:var(--color-warning-bg)] px-2 py-0.5 text-xs font-medium text-[color:var(--color-warning-text)]  ">
                      <Sparkles size={11} />
                      Echolalia
                    </span>
                  )}
                  {line.clinicalTag.toLowerCase().includes("pronoun") && (
                    <span className="flex items-center gap-1 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand-strong  ">
                      Pronoun Reversal
                    </span>
                  )}
                </div>
              )}

              {/* Verified Status Indicator */}
              {line.verified && (
                <div
                  className="flex-shrink-0 text-[color:var(--color-success-text)] "
                  title="Verified by clinician"
                >
                  <CheckCircle2 size={16} />
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
