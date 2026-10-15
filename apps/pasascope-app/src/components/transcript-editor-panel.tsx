"use client";

import { audioReviewMessages } from "@/components/audio-review/audio-review.messages";
import { AudioScrubberBar } from "@/components/audio-review/audio-scrubber-bar";
import { speakerBulkMessages } from "@/components/transcript-speaker-bulk.messages";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";
import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { FileCode, ListFilter, Plus, Table } from "lucide-react";

import { REVIEW_REQUIRED_LABEL, TRANSCRIPT_REVIEW_REQUIRED_LABEL } from "@/lib/clinical-safety-copy";

import {
  createLineId,
  getQaBlockedReason,
  hasNoSpeaker,
  lineMatchesFilter,
  listKeyAction,
  splitLineAt,
  transcriptFilters,
  type TranscriptFilter,
} from "@/components/transcript-editor-support";
import { TranscriptLineList } from "@/components/transcript-line-list";
import { TranscriptDoneActions, TranscriptQaDetails, TranscriptSaveBar } from "@/components/transcript-review-controls";
import { TalkbankChatViewer } from "@/features/sessions/transcript/talkbank-chat-viewer";
import type { PersistenceStatus, TranscriptLine, TranscriptQaStatus } from "@/lib/workflow";


type TranscriptEditorPanelProps = {
  lines: TranscriptLine[];
  qaStatus: TranscriptQaStatus;
  qaIssues: string[];
  attested: boolean;
  busy: boolean;
  saveStatus?: PersistenceStatus;
  onChange: (lines: TranscriptLine[]) => void;
  onSaveDraft: () => void;
  onRunQa: () => void;
  onAttest: () => void;
  onExport: () => void;
  backendUnavailable?: boolean;
  audioUrl?: string;
  /** Set by a page that shows its own view switch; the editor then hides its own. */
  view?: "table" | "talkbank";
};

export function TranscriptEditorPanel({
  lines,
  qaStatus,
  qaIssues,
  attested,
  busy,
  saveStatus = "idle",
  onChange,
  onSaveDraft,
  onRunQa,
  onAttest,
  onExport,
  backendUnavailable,
  audioUrl,
  view,
}: TranscriptEditorPanelProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const bulk = useMessages(speakerBulkMessages);
  const audioCopy = useMessages(audioReviewMessages);
  const editor = bulk.editor;
  const { openGates } = useAppMode();
  const [activeLineId, setActiveLineId] = useState<string | null>(null);
  const [selectedLineId, setSelectedLineId] = useState<string | null>(lines[0]?.lineId ?? null);
  const [selectedFilter, setSelectedFilter] = useState<TranscriptFilter>("all");
  const [openMenuLineId, setOpenMenuLineId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);
  const [speed, setSpeed] = useState(1);
  // QA results open themselves when the last run found something.
  const [qaDetailsOpen, setQaDetailsOpen] = useState(qaIssues.length > 0);
  useEffect(() => {
    if (qaIssues.length > 0) setQaDetailsOpen(true);
  }, [qaIssues]);
  const [ownEditorMode, setEditorMode] = useState<"table" | "talkbank">("table");
  const editorMode = view ?? ownEditorMode;
  const menuButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const lineRowRefs = useRef(new Map<string, HTMLElement>());
  const linesRef = useRef(lines);
  const onChangeRef = useRef(onChange);
  // Where playback of a single line ends; cleared when the therapist takes over the player.
  const stopAtMsRef = useRef<number | null>(null);
  const lineSeekRef = useRef(false);
  linesRef.current = lines;
  onChangeRef.current = onChange;

  function handleTimeUpdate() {
    if (!audioRef.current) return;
    const timeMs = Math.round(audioRef.current.currentTime * 1000);
    setCurrentTimeMs(timeMs);
    if (stopAtMsRef.current !== null && timeMs >= stopAtMsRef.current) {
      stopAtMsRef.current = null;
      audioRef.current.pause();
    }
    const active = lines.find(
      (line) =>
        line.startMs !== undefined &&
        line.endMs !== undefined &&
        timeMs >= line.startMs &&
        timeMs <= line.endMs
    );
    if (active) {
      if (active.lineId !== activeLineId) {
        setActiveLineId(active.lineId);
      }
    } else {
      if (activeLineId !== null) {
        setActiveLineId(null);
      }
    }
  }
  const updateLine = useCallback((index: number, patch: Partial<TranscriptLine>) => {
    onChangeRef.current(linesRef.current.map((line, lineIndex) => lineIndex === index ? { ...line, ...patch } : line));
  }, []);
  const unassignedSpeakerCount = lines.filter(hasNoSpeaker).length;
  // A draft without speaker separation labels every line unknown; this sets
  // them all to the therapist's choice so only the exceptions need editing.
  function assignUnknownSpeakers(speaker: "CHI" | "THER") {
    onChangeRef.current(linesRef.current.map((line) => (hasNoSpeaker(line) ? { ...line, speaker } : line)));
  }

  function addLine() {
    onChange([
      ...lines,
      {
        lineId: createLineId(),
        speaker: "UNK",
        text: "",
        unclear: false
      }
    ]);
  }

  function addNoteLine() {
    const line = {
      lineId: createLineId(),
      speaker: "THER",
      text: "[note] ",
      unclear: false
    } satisfies TranscriptLine;
    onChange([...lines, line]);
    setSelectedFilter("notes");
    setSelectedLineId(line.lineId);
  }

  const deleteLine = useCallback((index: number) => {
    onChangeRef.current(linesRef.current.filter((_, lineIndex) => lineIndex !== index));
  }, []);

  const splitLine = useCallback((index: number, cursor?: number | null) => {
    const currentLines = linesRef.current;
    const [first, second] = splitLineAt(currentLines[index], cursor);
    onChangeRef.current([...currentLines.slice(0, index), first, second, ...currentLines.slice(index + 1)]);
    if (cursor != null) setSelectedLineId(second.lineId);
  }, []);

  // Sets the speaker and moves on to the next line that still has none.
  const assignSpeaker = useCallback((index: number, speaker: "CHI" | "THER") => {
    const currentLines = linesRef.current;
    onChangeRef.current(currentLines.map((line, lineIndex) => lineIndex === index ? { ...line, speaker } : line));
    const next = currentLines.find((line, lineIndex) => lineIndex > index && hasNoSpeaker(line));
    if (next) {
      setSelectedLineId(next.lineId);
      queueMicrotask(() => lineRowRefs.current.get(next.lineId)?.scrollIntoView?.({ block: "nearest", inline: "nearest" }));
    }
  }, []);

  const mergeLine = useCallback((index: number, direction: "previous" | "next") => {
    const currentLines = linesRef.current;
    const adjacentIndex = direction === "previous" ? index - 1 : index + 1;
    if (adjacentIndex < 0 || adjacentIndex >= currentLines.length) return;

    const firstIndex = Math.min(index, adjacentIndex);
    const secondIndex = Math.max(index, adjacentIndex);
    const first = currentLines[firstIndex];
    const second = currentLines[secondIndex];
    const merged: TranscriptLine = {
      ...first,
      text: `${first.text.trim()} ${second.text.trim()}`.trim(),
      unclear: Boolean(first.unclear || second.unclear),
      startMs: first.startMs ?? second.startMs,
      endMs: second.endMs ?? first.endMs
    };

    onChangeRef.current([
      ...currentLines.slice(0, firstIndex),
      merged,
      ...currentLines.slice(secondIndex + 1)
    ]);
  }, []);

  const canAttest = lines.length > 0 && qaStatus !== "not_run" && qaStatus !== "fail";
  const visibleLines = useMemo(
    () => lines.filter((line) => lineMatchesFilter(line, selectedFilter, qaStatus)),
    [lines, qaStatus, selectedFilter]
  );
  const lineIndexById = useMemo(
    () => new Map(lines.map((line, index) => [line.lineId, index])),
    [lines]
  );
  const qaBlockedReason = getQaBlockedReason(lines, saveStatus);
  const activeSelectedLineId = activeLineId ?? selectedLineId;
  const selectedLineIndex = activeSelectedLineId ? (lineIndexById.get(activeSelectedLineId) ?? -1) : -1;

  const closeLineMenu = useCallback((lineId: string, restoreFocus = true) => {
    setOpenMenuLineId(null);
    if (restoreFocus) {
      queueMicrotask(() => menuButtonRefs.current.get(lineId)?.focus());
    }
  }, []);

  const selectLine = useCallback((lineId: string) => {
    setSelectedLineId(lineId);
    queueMicrotask(() => {
      const row = lineRowRefs.current.get(lineId);
      row?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    });
  }, []);
  const toggleLineMenu = useCallback((lineId: string) => {
    setSelectedLineId(lineId);
    setOpenMenuLineId((current) => current === lineId ? null : lineId);
  }, []);
  const registerMenuButton = useCallback((lineId: string, node: HTMLButtonElement | null) => {
    if (node) menuButtonRefs.current.set(lineId, node);
    else menuButtonRefs.current.delete(lineId);
  }, []);
  const registerLineRow = useCallback((lineId: string, node: HTMLElement | null) => {
    if (node) lineRowRefs.current.set(lineId, node);
    else lineRowRefs.current.delete(lineId);
  }, []);
  const playLine = useCallback((line: TranscriptLine) => {
    setSelectedLineId(line.lineId);
    if (!audioRef.current || line.startMs === undefined) return;
    lineSeekRef.current = true;
    audioRef.current.currentTime = line.startMs / 1000;
    stopAtMsRef.current = line.endMs ?? null;
    void audioRef.current.play();
  }, []);

  function handleListKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const action = listKeyAction(event, visibleLines, selectedLineId);
    if (!action) return;
    event.preventDefault();
    if (action.kind === "select") selectLine(action.line.lineId);
    else if (action.kind === "play") playLine(action.line);
    else if (action.kind === "speaker" && !busy) assignSpeaker(lineIndexById.get(action.line.lineId) ?? -1, action.speaker);
  }

  const qaReason = qaBlockedReason ? (editor.qaBlocked[qaBlockedReason] ?? qaBlockedReason) : undefined;

  return (
    <section aria-labelledby="transcript-editor-title" className="min-w-0 space-y-4" data-testid="transcript-workbench">
      {audioUrl ? (
        <>
          <audio
            ref={audioRef}
            src={audioUrl}
            preload="metadata"
            aria-label={audioCopy.waveform.recording}
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={() => {
              if (audioRef.current && Number.isFinite(audioRef.current.duration)) setDurationMs(audioRef.current.duration * 1000);
            }}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onSeeking={() => {
              if (lineSeekRef.current) lineSeekRef.current = false;
              else stopAtMsRef.current = null;
            }}
          />
          {/* The same player as the listening view, pinned while the lines are edited. */}
          <AudioScrubberBar
            className="sticky top-0 z-20"
            isPlaying={isPlaying}
            currentTimeMs={currentTimeMs}
            durationMs={durationMs || Math.max(0, ...lines.map((line) => line.endMs ?? 0))}
            speed={speed}
            onPlayPause={() => {
              const audio = audioRef.current;
              if (!audio) return;
              stopAtMsRef.current = null;
              if (audio.paused) void audio.play()?.catch?.(() => {});
              else audio.pause();
            }}
            onSpeedChange={(value) => {
              setSpeed(value);
              if (audioRef.current) audioRef.current.playbackRate = value;
            }}
            onSeek={(ms) => {
              stopAtMsRef.current = null;
              setCurrentTimeMs(ms);
              if (audioRef.current) audioRef.current.currentTime = ms / 1000;
            }}
          />
        </>
      ) : null}

      <div className="rounded-panel border border-line bg-surface">
        {/* Title and count, then how the lines are shown and a new line, on one row where it fits. */}
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 px-4 py-3 sm:px-5">
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 id="transcript-editor-title" className="text-lg font-semibold text-ink">{editor.title}</h2>
            <p className="text-sm text-ink-muted">{editor.lineCount(lines.length)}</p>
            {openGates ? null : (
              <span
                className={`inline-flex min-h-7 items-center rounded-full border px-2.5 text-xs font-semibold ${attested ? "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]" : "border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]"}`}
                data-testid="transcript-attestation-badge"
                aria-label={attested ? editor.attested : TRANSCRIPT_REVIEW_REQUIRED_LABEL}
              >
                {attested ? editor.attested : REVIEW_REQUIRED_LABEL}
              </span>
            )}
          </div>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            {view ? null : (
              <SegmentedControl<"table" | "talkbank">
                label={editor.views.label}
                size="sm"
                value={editorMode}
                onChange={setEditorMode}
                options={[
                  { value: "table", label: editor.views.table, icon: Table },
                  { value: "talkbank", label: editor.views.chat, icon: FileCode },
                ]}
              />
            )}
            {editorMode === "talkbank" ? null : (
              <div className="relative min-w-0 flex-1 sm:flex-none">
                <ListFilter size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
                <label className="sr-only" htmlFor="transcript-line-filter">{editor.filterLabel}</label>
                <select
                  id="transcript-line-filter"
                  value={selectedFilter}
                  onChange={(event) => setSelectedFilter(event.target.value as TranscriptFilter)}
                  className="h-11 w-full rounded-full border border-line bg-surface pl-9 pr-8 text-sm font-semibold text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] sm:w-auto"
                >
                  {transcriptFilters.map((filter) => {
                    const count = lines.filter((line) => lineMatchesFilter(line, filter.id, qaStatus)).length;
                    return <option key={filter.id} value={filter.id}>{editor.filters[filter.id] ?? filter.label} ({count})</option>;
                  })}
                </select>
              </div>
            )}
            <button
              type="button"
              onClick={addLine}
              disabled={busy}
              aria-label={editor.addLine}
              className="inline-flex h-11 min-w-11 shrink-0 items-center justify-center gap-2 rounded-full border border-action-quiet-border bg-surface px-3 text-sm font-semibold text-action-quiet-text transition hover:bg-action-quiet-hover disabled:opacity-50 motion-reduce:transition-none sm:px-4"
            >
              <Plus size={16} aria-hidden="true" />
              <span className="hidden sm:inline">{editor.addLine}</span>
            </button>
          </div>
        </div>

        {editorMode === "talkbank" ? (
          <div className="border-t border-line p-4">
            <TalkbankChatViewer
              utterances={lines.map((l) => ({
                id: l.lineId,
                speaker: l.speaker,
                text: l.text,
                startMs: l.startMs,
                endMs: l.endMs,
                unclear: l.unclear,
              }))}
            />
          </div>
        ) : (
          <>
            {unassignedSpeakerCount > 0 ? (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-4 py-3 text-sm text-[color:var(--color-warning-text)] sm:px-5">
                <p className="basis-full font-semibold sm:basis-auto">{bulk.unassigned(unassignedSpeakerCount)}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <span>{bulk.setAllTo}</span>
                  <button type="button" disabled={busy} onClick={() => assignUnknownSpeakers("CHI")} className="min-h-11 rounded-full border border-line bg-surface px-4 text-sm font-semibold text-ink disabled:opacity-60">
                    {bulk.child}
                  </button>
                  <button type="button" disabled={busy} onClick={() => assignUnknownSpeakers("THER")} className="min-h-11 rounded-full border border-line bg-surface px-4 text-sm font-semibold text-ink disabled:opacity-60">
                    {bulk.therapist}
                  </button>
                </div>
                <p className="basis-full text-xs">{bulk.hint}</p>
              </div>
            ) : null}
            {/* Keyboard shortcuts mean nothing on a touch screen, so they show only where there is a mouse. */}
            {lines.length > 0 ? (
              <p className="hidden border-t border-line px-4 py-2.5 text-xs text-ink-muted sm:px-5 [@media(hover:hover)_and_(pointer:fine)]:block">
                {bulk.shortcuts}
              </p>
            ) : null}
            <TranscriptLineList
              lines={lines}
              visibleLines={visibleLines}
              lineIndexById={lineIndexById}
              qaStatus={qaStatus}
              activeLineId={activeLineId}
              selectedLineId={selectedLineId}
              openMenuLineId={openMenuLineId}
              audioUrl={audioUrl}
              busy={busy}
              copy={bulk}
              onKeyDown={handleListKeyDown}
              updateLine={updateLine}
              selectLine={selectLine}
              playLine={playLine}
              registerLineRow={registerLineRow}
              registerMenuButton={registerMenuButton}
              toggleLineMenu={toggleLineMenu}
              closeLineMenu={closeLineMenu}
              splitLine={splitLine}
              mergeLine={mergeLine}
              deleteLine={deleteLine}
            />
            {lines.length === 0 ? (
              <p className="border-t border-line px-4 py-8 text-center text-sm text-ink-muted">{editor.empty}</p>
            ) : null}
            {lines.length > 0 && visibleLines.length === 0 ? (
              <p className="border-t border-line px-4 py-8 text-center text-sm text-ink-muted">{editor.noMatch}</p>
            ) : null}
          </>
        )}
      </div>

      <TranscriptQaDetails
        qaStatus={qaStatus}
        qaIssues={qaIssues}
        qaBlockedReason={qaReason}
        open={qaDetailsOpen}
        onToggle={setQaDetailsOpen}
      />

      <TranscriptDoneActions
        busy={busy}
        linesCount={lines.length}
        qaStatus={qaStatus}
        attested={attested}
        onAddNote={addNoteLine}
        onAttest={onAttest}
        onExport={onExport}
      />

      <TranscriptSaveBar
        busy={busy}
        saveStatus={saveStatus}
        qaBlockedReason={qaReason}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
      />
    </section>
  );
}
