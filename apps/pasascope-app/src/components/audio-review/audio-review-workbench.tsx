"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Check, Save } from "lucide-react";

import { audioReviewMessages, SPEAKER_CHOICES } from "@/components/audio-review/audio-review.messages";
import { AudioScrubberBar } from "@/components/audio-review/audio-scrubber-bar";
import { DualViewWaveform } from "@/components/audio-review/dual-view-waveform";
import { useKeyboardReview } from "@/components/audio-review/use-keyboard-review";
import { UtteranceReviewList, type ReviewLine } from "@/components/audio-review/utterance-review-list";
import { useMessages } from "@/i18n/locale-provider";
import { apiBlob } from "@/lib/api";
import type { PersistenceStatus, TranscriptLine } from "@/lib/workflow";

export interface AudioReviewWorkbenchProps {
  lines: TranscriptLine[];
  onLinesChange: (lines: TranscriptLine[]) => void;
  audioUrl?: string;
  sessionId?: string;
  isAttested?: boolean;
  onAttest?: () => void;
  onSaveDraft?: () => void;
  saveStatus?: PersistenceStatus;
  isBusy?: boolean;
  findingsStale?: boolean;
  className?: string;
}

// Speaker codes the transcription pipeline uses for adults.
const ADULT_SPEAKERS = new Set(["INV", "MOT", "FAT", "THER"]);

const hasNoSpeaker = (line: TranscriptLine) =>
  !(SPEAKER_CHOICES as readonly string[]).includes(line.speaker.replace("*", "").trim().toUpperCase());

/**
 * Listening to the recording and assigning who said each line.
 *
 * Top to bottom: the player, which stays pinned to the top of the page while
 * the lines are worked through; the waveform; the lines; and a save bar
 * pinned to the bottom. The same order holds from a phone to a desktop, so
 * the page is learned once; only the density of each part changes.
 */
export function AudioReviewWorkbench({
  lines,
  onLinesChange,
  audioUrl,
  sessionId,
  onSaveDraft,
  saveStatus = "idle",
  isBusy = false,
  findingsStale = false,
  className = "",
}: AudioReviewWorkbenchProps) {
  const copy = useMessages(audioReviewMessages);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(60000);
  const [speed, setSpeed] = useState(1);
  const [isLooping, setIsLooping] = useState(false);
  const [activeLineId, setActiveLineId] = useState<string>(lines[0]?.lineId || "");
  // The line whose own play button started playback; playback stops at its end.
  const [playingLineId, setPlayingLineId] = useState<string | null>(null);
  // Undefined while loading, null when the recording has none.
  const [peaks, setPeaks] = useState<Int8Array | null | undefined>(undefined);
  // The lines that had no speaker when the filter was turned on. Kept fixed,
  // so a line does not vanish the moment its speaker is chosen.
  const [unassignedFilter, setUnassignedFilter] = useState<ReadonlySet<string> | null>(null);

  const linesRef = useRef(lines);
  linesRef.current = lines;

  useEffect(() => {
    if (!sessionId) return;
    let live = true;
    apiBlob(`/sessions/${sessionId}/audio/waveform-peaks`)
      .then((blob) => blob.arrayBuffer())
      .then((buffer) => {
        if (live) setPeaks(new Int8Array(buffer));
      })
      .catch(() => {
        if (live) setPeaks(null);
      });
    return () => {
      live = false;
    };
  }, [sessionId]);

  // Until the audio reports its length, the last line's end stands in for it.
  useEffect(() => {
    const maxEnd = Math.max(0, ...lines.map((line) => line.endMs || 0));
    if (maxEnd > 0 && !(audioRef.current && Number.isFinite(audioRef.current.duration))) setDurationMs(maxEnd);
  }, [lines]);

  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio) return;
    const ms = audio.currentTime * 1000;
    setCurrentTimeMs(ms);
    const current = linesRef.current;

    const anchorId = playingLineId ?? (isLooping ? activeLineId : null);
    const anchor = anchorId ? current.find((line) => line.lineId === anchorId) : undefined;
    if (anchor && typeof anchor.endMs === "number" && ms >= anchor.endMs) {
      if (isLooping) {
        audio.currentTime = (anchor.startMs || 0) / 1000;
        return;
      }
      audio.pause();
      setIsPlaying(false);
      setPlayingLineId(null);
      return;
    }

    const heard = current.find(
      (line) => typeof line.startMs === "number" && typeof line.endMs === "number" && ms >= line.startMs && ms <= line.endMs,
    );
    if (heard && heard.lineId !== activeLineId) setActiveLineId(heard.lineId);
  };

  const play = useCallback(() => {
    audioRef.current?.play().then(() => setIsPlaying(true)).catch(() => {});
  }, []);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) {
      setIsPlaying((previous) => !previous);
      return;
    }
    if (audio.paused) play();
    else {
      audio.pause();
      setIsPlaying(false);
    }
  }, [play]);

  const handleSeek = useCallback((timeMs: number) => {
    setCurrentTimeMs(timeMs);
    // Moving the playhead by hand ends a single line's playback.
    setPlayingLineId(null);
    if (audioRef.current) audioRef.current.currentTime = timeMs / 1000;
  }, []);

  const handleSpeedChange = useCallback((value: number) => {
    setSpeed(value);
    if (audioRef.current) audioRef.current.playbackRate = value;
  }, []);

  const handleToggleLoop = useCallback(() => setIsLooping((previous) => !previous), []);

  const playLine = useCallback(
    (startMs: number, _endMs?: number, lineId?: string) => {
      if (lineId && lineId === playingLineId && isPlaying) {
        audioRef.current?.pause();
        setIsPlaying(false);
        setPlayingLineId(null);
        return;
      }
      setCurrentTimeMs(startMs);
      if (audioRef.current) audioRef.current.currentTime = startMs / 1000;
      if (lineId) {
        setActiveLineId(lineId);
        setPlayingLineId(lineId);
      }
      play();
    },
    [isPlaying, playingLineId, play],
  );

  const handleReplayActive = useCallback(() => {
    const active = linesRef.current.find((line) => line.lineId === activeLineId);
    if (active && typeof active.startMs === "number") playLine(active.startMs, active.endMs, active.lineId);
  }, [activeLineId, playLine]);

  const handleAssignSpeaker = useCallback(
    (speaker: "CHI" | "INV" | "MOT" | "FAT") => {
      onLinesChange(linesRef.current.map((line) => (line.lineId === activeLineId ? { ...line, speaker } : line)));
    },
    [activeLineId, onLinesChange],
  );

  const handleAdvanceLine = useCallback(() => {
    const current = linesRef.current;
    const index = current.findIndex((line) => line.lineId === activeLineId);
    const next = index >= 0 ? current[index + 1] : undefined;
    if (!next) return;
    setActiveLineId(next.lineId);
    if (typeof next.startMs === "number") handleSeek(next.startMs);
  }, [activeLineId, handleSeek]);

  useKeyboardReview({
    onPlayPause: handlePlayPause,
    onReplayActive: handleReplayActive,
    onToggleLoop: handleToggleLoop,
    onAssignSpeaker: handleAssignSpeaker,
    onAdvanceLine: handleAdvanceLine,
    isEnabled: true,
  });

  const selectLine = useCallback(
    (lineId: string) => {
      setActiveLineId(lineId);
      const line = linesRef.current.find((candidate) => candidate.lineId === lineId);
      if (line && typeof line.startMs === "number" && audioRef.current?.paused !== false) handleSeek(line.startMs);
    },
    [handleSeek],
  );

  const handleLineChange = useCallback(
    (index: number, updated: ReviewLine) => {
      onLinesChange(linesRef.current.map((line, lineIndex) => (lineIndex === index ? { ...line, ...updated } : line)));
    },
    [onLinesChange],
  );

  const handleSegmentBoundaryChange = useCallback(
    (segmentId: string, startMs: number, endMs: number) => {
      onLinesChange(linesRef.current.map((line) => (line.lineId === segmentId ? { ...line, startMs, endMs } : line)));
    },
    [onLinesChange],
  );

  // Conversation measures from the lines as they stand.
  const { childTalkRatio, avgLatencyMs, turnsCount } = useMemo(() => {
    let childMs = 0;
    let adultMs = 0;
    let turns = 0;
    const latencies: number[] = [];
    lines.forEach((line, index) => {
      const speaker = line.speaker.toUpperCase().replace("*", "");
      const length = Math.max(0, (line.endMs || 0) - (line.startMs || 0));
      if (speaker === "CHI") childMs += length;
      else if (ADULT_SPEAKERS.has(speaker)) adultMs += length;
      if (index === 0) return;
      const previous = lines[index - 1];
      const previousSpeaker = previous.speaker.toUpperCase().replace("*", "");
      if (speaker !== previousSpeaker) turns += 1;
      if (ADULT_SPEAKERS.has(previousSpeaker) && speaker === "CHI" && typeof line.startMs === "number" && typeof previous.endMs === "number") {
        const gap = line.startMs - previous.endMs;
        if (gap >= 0 && gap <= 5000) latencies.push(gap);
      }
    });
    const total = childMs + adultMs;
    // No timed speech, or no adult-to-child turn, is "not measured", not zero.
    return {
      childTalkRatio: total > 0 ? (childMs / total) * 100 : null,
      avgLatencyMs: latencies.length > 0 ? latencies.reduce((sum, gap) => sum + gap, 0) / latencies.length : null,
      turnsCount: turns,
    };
  }, [lines]);

  const segments = useMemo(
    () =>
      lines.map((line) => ({
        id: line.lineId,
        speaker: line.speaker,
        startMs: line.startMs || 0,
        endMs: line.endMs || (line.startMs || 0) + 1500,
        text: line.text,
      })),
    [lines],
  );

  const unassignedCount = lines.filter(hasNoSpeaker).length;
  const toggleUnassigned = () =>
    setUnassignedFilter((current) => (current ? null : new Set(lines.filter(hasNoSpeaker).map((line) => line.lineId))));

  const saved = saveStatus === "saved";
  const saving = saveStatus === "saving" || (isBusy && saveStatus === "unsaved");

  return (
    <div className={`space-y-4 ${className}`} data-testid="audio-review-workbench">
      {audioUrl ? (
        <audio
          ref={audioRef}
          src={audioUrl}
          aria-label={copy.waveform.recording}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => {
            if (audioRef.current && Number.isFinite(audioRef.current.duration)) setDurationMs(audioRef.current.duration * 1000);
          }}
          onPause={() => setIsPlaying(false)}
          onPlay={() => setIsPlaying(true)}
          onEnded={() => {
            setIsPlaying(false);
            setPlayingLineId(null);
          }}
        />
      ) : null}

      {findingsStale ? (
        <p role="status" className="flex items-start gap-2.5 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-4 py-3 text-sm font-medium text-[color:var(--color-warning-text)]">
          <AlertCircle size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
          {copy.stale}
        </p>
      ) : null}

      {/* Pinned while the lines below are worked through. */}
      <AudioScrubberBar
        className="sticky top-0 z-20"
        isPlaying={isPlaying}
        currentTimeMs={currentTimeMs}
        durationMs={durationMs}
        speed={speed}
        isLooping={isLooping}
        onPlayPause={handlePlayPause}
        onSpeedChange={handleSpeedChange}
        onToggleLoop={handleToggleLoop}
        onSeek={handleSeek}
      />

      <DualViewWaveform
        currentTimeMs={currentTimeMs}
        durationMs={durationMs}
        segments={segments}
        peaks={peaks}
        onSeek={handleSeek}
        onSegmentBoundaryChange={handleSegmentBoundaryChange}
      />

      <section aria-labelledby="audio-review-lines-title" className="rounded-panel border border-line bg-surface px-2 pb-2 pt-4 sm:px-3">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-2 pb-3">
          <div className="flex items-baseline gap-2.5">
            <h2 id="audio-review-lines-title" className="text-lg font-semibold text-ink">{copy.lines.title}</h2>
            <span className="text-sm text-ink-muted">{copy.lines.count(lines.length)}</span>
          </div>
          {unassignedCount > 0 || unassignedFilter ? (
            <button
              type="button"
              aria-pressed={Boolean(unassignedFilter)}
              onClick={toggleUnassigned}
              className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-semibold transition motion-reduce:transition-none ${
                unassignedFilter
                  ? "border-brand-strong bg-brand-strong text-white"
                  : "border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]"
              }`}
            >
              {unassignedFilter ? <Check size={15} aria-hidden="true" /> : null}
              {unassignedCount > 0 ? copy.lines.onlyUnassigned(unassignedCount) : copy.lines.noneUnassigned}
            </button>
          ) : null}
        </div>

        <dl aria-label={copy.stats.label} className="flex flex-wrap gap-x-5 gap-y-1 border-t border-line px-2 py-2.5 text-[13px] text-ink-muted">
          <Measure term={copy.stats.childTalk} value={childTalkRatio === null ? "–" : `${Math.round(childTalkRatio)}%`} />
          <Measure term={copy.stats.turns} value={String(turnsCount)} />
          <Measure term={copy.stats.latency} value={avgLatencyMs === null ? "–" : `${(avgLatencyMs / 1000).toFixed(1)} s`} />
        </dl>

        {/* Keyboard shortcuts mean nothing on a touch screen, so they show only where there is a mouse. */}
        <p className="hidden border-t border-line px-2 py-2.5 text-xs text-ink-muted [@media(hover:hover)_and_(pointer:fine)]:block">
          <span className="font-semibold text-ink">{copy.shortcuts.label}</span>{" "}
          <Key>Space</Key> {copy.shortcuts.play} · <Key>Alt</Key>+<Key>1</Key> {copy.shortcuts.child} · <Key>Alt</Key>+<Key>2</Key> {copy.shortcuts.clinician} ·{" "}
          <Key>Alt</Key>+<Key>L</Key> {copy.shortcuts.loop} · <Key>Alt</Key>+<Key>R</Key> {copy.shortcuts.replay}
        </p>

        <UtteranceReviewList
          className="border-t border-line pt-1"
          lines={lines}
          visibleLineIds={unassignedFilter ?? undefined}
          activeLineId={activeLineId}
          playingLineId={isPlaying ? playingLineId : null}
          onSelectLine={selectLine}
          onLineChange={handleLineChange}
          onPlayUtterance={playLine}
        />
      </section>

      {onSaveDraft ? (
        <div
          data-testid="audio-review-save-bar"
          className="sticky bottom-2 z-20 flex items-center justify-between gap-3 rounded-panel border border-line bg-surface/95 py-2 pl-4 pr-2 shadow-lift backdrop-blur-sm"
        >
          <p role="status" aria-live="polite" className="flex min-w-0 items-center gap-2 text-sm font-medium text-ink-muted">
            <span
              aria-hidden="true"
              className={`h-2 w-2 shrink-0 rounded-full ${saved ? "bg-brand" : saveStatus === "failed" ? "bg-[color:var(--color-danger-text)]" : "bg-[color:var(--color-warning-text)]"}`}
            />
            <span className="truncate">{copy.save.status[saving ? "saving" : saveStatus]}</span>
          </p>
          <button
            type="button"
            onClick={onSaveDraft}
            disabled={saved || saving || isBusy}
            className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full bg-action px-5 text-sm font-semibold text-white transition hover:bg-action-hover disabled:bg-surface-muted disabled:text-ink-muted motion-reduce:transition-none"
          >
            {saved ? <Check size={16} aria-hidden="true" /> : <Save size={16} aria-hidden="true" />}
            {saved ? copy.save.saved : saving ? copy.save.saving : copy.save.save}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function Measure({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt>{term}</dt>
      <dd className="font-semibold tabular-nums text-ink">{value}</dd>
    </div>
  );
}

function Key({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border border-line bg-surface-soft px-1 py-px font-mono text-[11px] text-ink">{children}</kbd>;
}
