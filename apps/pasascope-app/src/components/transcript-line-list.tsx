import { memo, useRef, type KeyboardEventHandler } from "react";
import { AlertTriangle, GitMerge, GitPullRequest, MoreHorizontal, Play, Trash2 } from "lucide-react";

import {
  LineMenuItem,
  TranscriptRowBoundary,
  formatTimestampRange,
  getLineConfidence,
  getRowStatus,
  parseTimestampRange,
} from "@/components/transcript-editor-support";
import type { speakerBulkMessages } from "@/components/transcript-speaker-bulk.messages";
import type { TranscriptLine, TranscriptQaStatus } from "@/lib/workflow";

type LineCopy = (typeof speakerBulkMessages)["en"];

type TranscriptLineListProps = {
  lines: TranscriptLine[];
  visibleLines: TranscriptLine[];
  lineIndexById: Map<string, number>;
  qaStatus: TranscriptQaStatus;
  activeLineId: string | null;
  selectedLineId: string | null;
  openMenuLineId: string | null;
  audioUrl?: string;
  busy: boolean;
  copy: LineCopy;
  onKeyDown: KeyboardEventHandler<HTMLDivElement>;
  assignSpeaker: (index: number, speaker: "CHI" | "THER") => void;
  updateLine: (index: number, patch: Partial<TranscriptLine>) => void;
  selectLine: (lineId: string) => void;
  playLine: (line: TranscriptLine) => void;
  registerLineRow: (lineId: string, node: HTMLElement | null) => void;
  registerMenuButton: (lineId: string, node: HTMLButtonElement | null) => void;
  toggleLineMenu: (lineId: string) => void;
  closeLineMenu: (lineId: string, restoreFocus?: boolean) => void;
  splitLine: (index: number, cursor?: number | null) => void;
  mergeLine: (index: number, direction: "previous" | "next") => void;
  deleteLine: (index: number) => void;
};

export function TranscriptLineList({
  lines,
  visibleLines,
  lineIndexById,
  qaStatus,
  activeLineId,
  selectedLineId,
  openMenuLineId,
  audioUrl,
  busy,
  copy,
  onKeyDown,
  assignSpeaker,
  updateLine,
  selectLine,
  playLine,
  registerLineRow,
  registerMenuButton,
  toggleLineMenu,
  closeLineMenu,
  splitLine,
  mergeLine,
  deleteLine,
}: TranscriptLineListProps) {
  return (
    <div className="mt-4 min-w-0 overflow-hidden rounded-panel border border-line bg-surface lg:col-start-1 lg:row-start-4">
      {/* One header for every line; each line names its fields only to assistive technology. */}
      <div aria-hidden="true" className="hidden gap-3 border-b border-line bg-surface-muted px-4 py-2.5 text-[13px] font-semibold text-ink-muted md:grid md:grid-cols-[10rem_7.5rem_minmax(0,1fr)]">
        <span>{copy.editor.columns.time}</span>
        <span>{copy.editor.columns.speaker}</span>
        <span>{copy.editor.columns.utterance}</span>
      </div>
      <div
        className="divide-y divide-line outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[color:var(--color-focus-ring)]"
        role="listbox"
        aria-label="Transcript lines"
        aria-activedescendant={selectedLineId && visibleLines.some((line) => line.lineId === selectedLineId) ? rowId(selectedLineId) : undefined}
        tabIndex={0}
        onKeyDown={onKeyDown}
      >
        {visibleLines.map((line) => {
          const index = lineIndexById.get(line.lineId) ?? -1;
          return (
            <TranscriptLineRow
              key={line.lineId}
              line={line}
              index={index}
              totalLines={lines.length}
              qaStatus={qaStatus}
              active={line.lineId === activeLineId}
              selected={line.lineId === selectedLineId}
              menuOpen={openMenuLineId === line.lineId}
              audioLinked={Boolean(audioUrl)}
              busy={busy}
              copy={copy}
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
          );
        })}
      </div>
    </div>
  );
}

type TranscriptLineRowProps = {
  line: TranscriptLine;
  index: number;
  totalLines: number;
  qaStatus: TranscriptQaStatus;
  active: boolean;
  selected: boolean;
  menuOpen: boolean;
  audioLinked: boolean;
  busy: boolean;
  copy: LineCopy;
  assignSpeaker: (index: number, speaker: "CHI" | "THER") => void;
  updateLine: (index: number, patch: Partial<TranscriptLine>) => void;
  selectLine: (lineId: string) => void;
  playLine: (line: TranscriptLine) => void;
  registerLineRow: (lineId: string, node: HTMLElement | null) => void;
  registerMenuButton: (lineId: string, node: HTMLButtonElement | null) => void;
  toggleLineMenu: (lineId: string) => void;
  closeLineMenu: (lineId: string, restoreFocus?: boolean) => void;
  splitLine: (index: number, cursor?: number | null) => void;
  mergeLine: (index: number, direction: "previous" | "next") => void;
  deleteLine: (index: number) => void;
};

const TranscriptLineRow = memo(function TranscriptLineRow({
  line,
  index,
  totalLines,
  qaStatus,
  active,
  selected,
  menuOpen,
  audioLinked,
  busy,
  copy,
  assignSpeaker,
  updateLine,
  selectLine,
  playLine,
  registerLineRow,
  registerMenuButton,
  toggleLineMenu,
  closeLineMenu,
  splitLine,
  mergeLine,
  deleteLine,
}: TranscriptLineRowProps) {
  const textRef = useRef<HTMLTextAreaElement>(null);
  const rowStatus = getRowStatus(line, qaStatus);
  const confidence = getLineConfidence(line);
  // Missing times are normal for a typed transcript, so only a low-confidence line is marked beyond the review states.
  const mark = rowStatus.label === "Unclear" || rowStatus.label === "Review"
    ? rowStatus
    : confidence.label === "Low" ? confidence : null;
  const hasTiming = line.startMs !== undefined && line.endMs !== undefined;

  return (
    <TranscriptRowBoundary
      line={line}
      index={index}
      totalLines={totalLines}
      qaStatus={qaStatus}
      active={active}
      selected={selected}
      menuOpen={menuOpen}
      audioLinked={audioLinked}
      copy={copy}
    >
      <article
        id={rowId(line.lineId)}
        ref={(node) => registerLineRow(line.lineId, node)}
        role="option"
        aria-label={`Transcript line ${index + 1}`}
        aria-selected={selected}
        className={`transcript-line-row px-3 py-3 transition motion-reduce:transition-none sm:px-4 ${active || selected ? "bg-brand-soft" : "bg-transparent"}`}
        onClick={() => selectLine(line.lineId)}
      >
        <div className="grid min-w-0 grid-cols-2 gap-x-3 gap-y-2 md:grid-cols-[10rem_7.5rem_minmax(0,1fr)] md:items-start">
          <label className="col-span-2 grid gap-1 text-xs font-semibold text-ink-muted md:col-span-1">
            <span className="md:sr-only">{copy.editor.columns.time}</span>
            <input
              value={formatTimestampRange(line)}
              onChange={(event) => {
                const timing = parseTimestampRange(event.target.value);
                if (timing) updateLine(index, timing);
              }}
              onFocus={() => selectLine(line.lineId)}
              aria-label={`Timestamp for line ${index + 1}`}
              placeholder="00:00.000 – 00:01.000"
              className="min-h-11 w-full min-w-0 rounded-control border border-line bg-surface px-2.5 text-[13px] font-normal tabular-nums text-ink"
            />
          </label>
          <label className="grid gap-1 text-xs font-semibold text-ink-muted">
            <span className="md:sr-only">{copy.editor.columns.speaker}</span>
            <select
              value={line.speaker}
              onChange={(event) => updateLine(index, { speaker: event.target.value })}
              onFocus={() => selectLine(line.lineId)}
              aria-label={`Speaker for line ${index + 1}`}
              className="min-h-11 w-full rounded-control border border-line bg-surface px-3 text-sm font-semibold text-ink"
            >
              {[...new Set([...speakers, line.speaker])].map((speaker) => (
                <option key={speaker} value={speaker}>{speaker}</option>
              ))}
            </select>
          </label>
          <label className="col-span-2 grid gap-1 text-xs font-semibold text-ink-muted md:col-span-1">
            <span className="md:sr-only">{copy.editor.columns.utterance}</span>
            <textarea
              ref={textRef}
              value={line.text}
              onChange={(event) => updateLine(index, { text: event.target.value })}
              onFocus={() => selectLine(line.lineId)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && line.text.trim()) {
                  event.preventDefault();
                  splitLine(index, event.currentTarget.selectionStart);
                }
              }}
              aria-label={`Utterance text ${index + 1}`}
              className="min-h-11 w-full min-w-0 resize-y rounded-control border border-line bg-surface px-3 py-2 text-[15px] font-normal leading-6 text-ink outline-none focus:ring-2 focus:ring-brand"
            />
          </label>
          {/* A line that needs a look says why, once; a line that is fine carries no mark. */}
          <div className="col-span-2 flex items-center md:col-span-2 md:col-start-1">
            {mark ? (
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${mark.className}`}>
                {copy.editor.marks[mark.label] ?? mark.label}
              </span>
            ) : null}
          </div>
          <div className="col-span-2 flex flex-wrap gap-2 md:col-span-1 md:col-start-3">
            {hasTiming && audioLinked ? (
              <button
                type="button"
                aria-label={copy.playLine(index + 1)}
                onClick={(event) => {
                  event.stopPropagation();
                  playLine(line);
                }}
                className={rowButtonClass}
              >
                <Play size={15} fill="currentColor" aria-hidden="true" />
              </button>
            ) : null}
            {quickSpeakers.map((speaker) => {
              const label = speaker === "CHI" ? copy.childShort : copy.therapistShort;
              const chosen = line.speaker === speaker;
              return (
                <button
                  key={speaker}
                  type="button"
                  aria-label={copy.setSpeaker(index + 1, label)}
                  aria-pressed={chosen}
                  disabled={busy}
                  onClick={(event) => {
                    event.stopPropagation();
                    assignSpeaker(index, speaker);
                  }}
                  className={`${rowButtonShape} border px-3 text-sm font-semibold disabled:opacity-60 ${chosen ? "border-brand bg-brand-soft text-brand-strong" : "border-line bg-surface text-ink"}`}
                >
                  {label}
                </button>
              );
            })}
            <div className="relative">
              <button
                ref={(node) => registerMenuButton(line.lineId, node)}
                type="button"
                aria-label={`More actions for line ${index + 1}`}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={(event) => {
                  event.stopPropagation();
                  toggleLineMenu(line.lineId);
                }}
                className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-line bg-surface text-ink"
              >
                <MoreHorizontal size={18} aria-hidden="true" />
              </button>
              {menuOpen ? (
                <div
                  role="menu"
                  aria-label={`Actions for transcript line ${index + 1}`}
                  className="motion-popover absolute right-0 z-20 mt-1 w-52 rounded-card border border-line bg-surface p-1 shadow-lg"
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") {
                      event.preventDefault();
                      closeLineMenu(line.lineId);
                    }
                  }}
                >
                  {hasTiming && audioLinked ? (
                    <LineMenuItem label="Play line" onClick={() => { playLine(line); closeLineMenu(line.lineId); }} autoFocus>
                      <Play size={15} fill="currentColor" aria-hidden="true" />
                    </LineMenuItem>
                  ) : null}
                  <LineMenuItem label="Split line" onClick={() => { splitLine(index, textRef.current?.selectionStart); closeLineMenu(line.lineId); }} disabled={!line.text.trim()} autoFocus={!hasTiming || !audioLinked}>
                    <GitPullRequest size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label="Merge with previous" onClick={() => { mergeLine(index, "previous"); closeLineMenu(line.lineId); }} disabled={index === 0}>
                    <GitMerge size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label="Merge with next" onClick={() => { mergeLine(index, "next"); closeLineMenu(line.lineId); }} disabled={index === totalLines - 1}>
                    <GitMerge size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label={line.unclear ? "Mark clear" : "Mark unclear"} onClick={() => { updateLine(index, { unclear: !line.unclear }); closeLineMenu(line.lineId); }}>
                    <AlertTriangle size={15} aria-hidden="true" />
                  </LineMenuItem>
                  <LineMenuItem label="Delete line" onClick={() => { deleteLine(index); closeLineMenu(line.lineId, false); }} tone="danger">
                    <Trash2 size={15} aria-hidden="true" />
                  </LineMenuItem>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </article>
    </TranscriptRowBoundary>
  );
});

const speakers = ["CHI", "THER", "PAR", "INV", "MOT", "FAT", "UNK"];
const quickSpeakers = ["CHI", "THER"] as const;
const rowButtonShape = "inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg";
const rowButtonClass = `${rowButtonShape} border border-line bg-surface text-ink`;

function rowId(lineId: string) {
  return `transcript-line-${lineId}`;
}
