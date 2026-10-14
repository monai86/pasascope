"use client";

import { speakerBulkMessages } from "@/components/transcript-speaker-bulk.messages";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";
import { useCallback, useMemo, useRef, useState, type KeyboardEvent } from "react";
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
import { TranscriptQaDetails, TranscriptReviewControls } from "@/components/transcript-review-controls";
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
  const editor = bulk.editor;
  const { openGates } = useAppMode();
  const [activeLineId, setActiveLineId] = useState<string | null>(null);
  const [selectedLineId, setSelectedLineId] = useState<string | null>(lines[0]?.lineId ?? null);
  const [selectedFilter, setSelectedFilter] = useState<TranscriptFilter>("all");
  const [openMenuLineId, setOpenMenuLineId] = useState<string | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [inspectorView, setInspectorView] = useState<"audio" | "qa">("audio");
  const [qaDetailsOpen, setQaDetailsOpen] = useState(false);
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

  return (
    <section
      aria-labelledby="transcript-editor-title"
      className={`min-w-0 max-md:pb-44 lg:grid lg:gap-x-4 ${inspectorOpen ? "lg:grid-cols-[minmax(0,13fr)_minmax(17rem,7fr)]" : "lg:grid-cols-1"}`}
      data-testid="transcript-workbench"
    >
      {/* Title, line count and the two ways to read the transcript, on one row. */}
      <div className={`flex flex-wrap items-center justify-between gap-3 ${inspectorOpen ? "lg:col-span-2" : ""}`}>
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 id="transcript-editor-title" className="text-xl font-semibold text-ink">{editor.title}</h2>
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
        <div className="flex flex-wrap items-center gap-2">
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
          <button
            type="button"
            onClick={addLine}
            disabled={busy}
            aria-label={editor.addLine}
            className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-full border border-action-quiet-border bg-surface px-3 text-sm font-semibold text-action-quiet-text transition hover:bg-action-quiet-hover disabled:opacity-50 motion-reduce:transition-none sm:px-4"
          >
            <Plus size={16} aria-hidden="true" />
            <span className="hidden sm:inline">{editor.addLine}</span>
          </button>
        </div>
      </div>

      {editorMode === "talkbank" ? (
        <div className="mt-4 lg:col-span-2">
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
      ) : null}

      <div className={`mt-4 hidden items-center justify-between gap-3 md:flex ${inspectorOpen ? "lg:col-span-2" : ""} ${editorMode === "talkbank" ? "hidden" : ""}`}>
        {inspectorOpen ? (
          <div className="inline-flex rounded-full border border-line bg-surface p-1" aria-label={editor.inspector.label}>
            {(["audio", "qa"] as const).map((view) => (
              <button
                key={view}
                type="button"
                aria-pressed={inspectorView === view}
                onClick={() => {
                  setInspectorView(view);
                  setQaDetailsOpen(view === "qa");
                }}
                className={`min-h-10 rounded-full px-4 text-sm font-semibold ${inspectorView === view ? "bg-brand-soft text-brand-strong" : "text-ink-muted"}`}
              >
                {view === "audio" ? editor.inspector.audio : editor.inspector.qa}
              </button>
            ))}
          </div>
        ) : <span />}
        <button
          type="button"
          aria-expanded={inspectorOpen}
          onClick={() => setInspectorOpen((current) => !current)}
          className="min-h-11 rounded-full border border-line bg-surface px-4 text-sm font-semibold text-ink-muted transition hover:text-ink motion-reduce:transition-none"
        >
          {inspectorOpen ? editor.inspector.hide : editor.inspector.show}
        </button>
      </div>

      <div className={`mt-4 overflow-hidden rounded-panel border border-line bg-ink p-3 text-white max-md:sticky max-md:top-0 max-md:z-20 lg:col-start-2 lg:row-start-3 lg:self-start lg:bg-surface-soft lg:p-4 lg:text-ink ${!inspectorOpen ? "hidden" : inspectorView === "qa" ? "md:hidden" : ""}`} data-testid="transcript-audio-inspector">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold">{editor.inspector.audioTitle}</h3>
          </div>
          {audioUrl ? (
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              onTimeUpdate={handleTimeUpdate}
              onSeeking={() => {
                if (lineSeekRef.current) lineSeekRef.current = false;
                else stopAtMsRef.current = null;
              }}
              className="w-full min-w-0 max-w-md outline-none focus:ring-2 focus:ring-[color:var(--color-focus-ring)]"
              aria-label="Workspace audio playback"
            />
          ) : (
            <span className="rounded-full border border-white/25 px-3 py-1 text-xs font-semibold text-white lg:border-line lg:bg-surface lg:text-ink-muted">
              {editor.inspector.noAudio}
            </span>
          )}
        </div>
      </div>

      <div className="min-w-0 lg:col-start-1 lg:row-start-3">
        <div className="mt-4 flex min-w-0 items-center gap-2 self-start">
          <ListFilter size={17} aria-hidden="true" className="shrink-0 text-ink-muted" />
          <label className="sr-only" htmlFor="transcript-line-filter">{editor.filterLabel}</label>
          <select
            id="transcript-line-filter"
            value={selectedFilter}
            onChange={(event) => setSelectedFilter(event.target.value as TranscriptFilter)}
            className="min-h-11 min-w-0 max-w-full rounded-card border border-line bg-surface px-3 text-sm font-semibold text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
          >
            {transcriptFilters.map((filter) => {
              const count = lines.filter((line) => lineMatchesFilter(line, filter.id, qaStatus)).length;
              return <option key={filter.id} value={filter.id}>{editor.filters[filter.id] ?? filter.label} ({count})</option>;
            })}
          </select>
          <span className="text-xs text-ink-subtle" aria-live="polite">{editor.shown(visibleLines.length)}</span>
        </div>

        {unassignedSpeakerCount > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">
            <span className="font-semibold">{bulk.unassigned(unassignedSpeakerCount)}</span>
            <span>{bulk.setAllTo}</span>
            <button type="button" disabled={busy} onClick={() => assignUnknownSpeakers("CHI")} className="min-h-11 rounded-control border border-line bg-surface px-3 text-sm font-semibold text-ink disabled:opacity-60">
              {bulk.child}
            </button>
            <button type="button" disabled={busy} onClick={() => assignUnknownSpeakers("THER")} className="min-h-11 rounded-control border border-line bg-surface px-3 text-sm font-semibold text-ink disabled:opacity-60">
              {bulk.therapist}
            </button>
            <span className="basis-full text-xs">{bulk.hint}</span>
          </div>
        ) : null}
        {lines.length > 0 ? (
          <div className="mt-3 grid gap-1 text-xs text-ink-muted">
            <p>{bulk.splitHint}</p>
            <p className="hidden md:block">{bulk.shortcuts}</p>
          </div>
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
          assignSpeaker={assignSpeaker}
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
          <div className="mt-4 rounded-panel border border-dashed border-line bg-surface-soft p-5 text-center text-sm text-ink-muted">
            Add a transcript line to begin review.
          </div>
        ) : null}
        {lines.length > 0 && visibleLines.length === 0 ? (
          <div className="mt-4 rounded-panel border border-dashed border-line bg-surface-soft p-5 text-center text-sm text-ink-muted">
            No lines match the current review filter.
          </div>
        ) : null}
      </div>

      <TranscriptQaDetails
        qaStatus={qaStatus}
        qaIssues={qaIssues}
        qaBlockedReason={qaBlockedReason}
        inspectorOpen={inspectorOpen}
        inspectorView={inspectorView}
        open={qaDetailsOpen}
        onToggle={setQaDetailsOpen}
      />

      <TranscriptReviewControls
        busy={busy}
        linesCount={lines.length}
        selectedLineIndex={selectedLineIndex}
        saveStatus={saveStatus}
        qaBlockedReason={qaBlockedReason}
        qaStatus={qaStatus}
        canAttest={canAttest}
        attested={attested}
        inspectorOpen={inspectorOpen}
        onSpeakerTools={() => setSelectedFilter("missing_speaker")}
        onAddNote={addNoteLine}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
        onAttest={onAttest}
        onExport={onExport}
      />
    </section>
  );
}
