import { memo, useRef, useState, type KeyboardEventHandler } from "react";
import { AlertTriangle, GitMerge, GitPullRequest, MoreHorizontal, Play, Trash2 } from "lucide-react";

import { AutoGrowTextarea } from "@/components/auto-grow-textarea";
import { SpeakerSelect } from "@/components/speaker-select";
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

/**
 * The transcript as a list of lines. Each line reads as a sentence with its
 * speaker beside it, not as a row of form fields: on a phone the speaker and
 * the line's actions sit above the words, and from `sm` the speaker takes a
 * column to the left of them. The time and any mark needing attention sit
 * quietly under the words. Arrow keys move through the list.
 */
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
    <div
      className="divide-y divide-line border-t border-line outline-none focus-visible:ring-4 focus-visible:ring-inset focus-visible:ring-[color:var(--color-focus-ring)]"
      role="listbox"
      aria-label={copy.editor.list}
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
  // What is typed into the time field, kept until it parses, so a half-typed time is not thrown away.
  const [timeDraft, setTimeDraft] = useState<string | null>(null);
  const editor = copy.editor;
  const number = index + 1;
  const rowStatus = getRowStatus(line, qaStatus);
  const confidence = getLineConfidence(line);
  // Missing times are normal for a typed transcript, so only a low-confidence line is marked beyond the review states.
  const mark = rowStatus.label === "Unclear" || rowStatus.label === "Review"
    ? rowStatus
    : confidence.label === "Low" ? confidence : null;
  const hasTiming = line.startMs !== undefined && line.endMs !== undefined;
  const canPlay = hasTiming && audioLinked;

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
        aria-label={editor.line(number)}
        aria-selected={selected}
        className={`transcript-line-row grid scroll-mt-32 grid-cols-[2.75rem_minmax(0,1fr)_2.75rem] gap-x-2 gap-y-1 px-2 py-2.5 transition-colors motion-reduce:transition-none sm:grid-cols-[2.75rem_10rem_minmax(0,1fr)_2.75rem] sm:gap-x-3 sm:px-3 ${
          active || selected ? "bg-brand-soft" : "hover:bg-surface-soft"
        }`}
        onClick={() => selectLine(line.lineId)}
      >
        <div className="col-start-1 row-start-1 grid h-11 place-items-center">
          {canPlay ? (
            <button
              type="button"
              aria-label={copy.playLine(number)}
              onClick={(event) => {
                event.stopPropagation();
                playLine(line);
              }}
              className="grid h-11 w-11 place-items-center rounded-full bg-surface-muted text-ink-muted transition hover:bg-brand-strong hover:text-white motion-reduce:transition-none"
            >
              <Play size={15} aria-hidden="true" className="translate-x-px" />
            </button>
          ) : (
            <span aria-hidden="true" className="font-mono text-xs tabular-nums text-ink-subtle">{number}</span>
          )}
        </div>

        <SpeakerSelect
          className="col-start-2 row-start-1"
          value={line.speaker}
          label={editor.speaker(number)}
          onChange={(speaker) => updateLine(index, { speaker })}
          onFocus={() => selectLine(line.lineId)}
          onClick={(event) => event.stopPropagation()}
        />

        <div className="col-span-3 col-start-1 row-start-2 min-w-0 sm:col-span-1 sm:col-start-3 sm:row-start-1">
          <AutoGrowTextarea
            ref={textRef}
            value={line.text}
            placeholder={editor.placeholder}
            onChange={(event) => updateLine(index, { text: event.target.value })}
            onFocus={() => selectLine(line.lineId)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && line.text.trim()) {
                event.preventDefault();
                splitLine(index, event.currentTarget.selectionStart);
              }
            }}
            aria-label={editor.utterance(number)}
          />
          {hasTiming || selected || mark ? (
            <div className="flex flex-wrap items-center gap-2 px-1">
              {hasTiming || selected ? (
                <input
                  value={timeDraft ?? formatTimestampRange(line)}
                  onChange={(event) => {
                    setTimeDraft(event.target.value);
                    const timing = parseTimestampRange(event.target.value);
                    if (timing) updateLine(index, timing);
                  }}
                  onFocus={() => selectLine(line.lineId)}
                  onBlur={() => setTimeDraft(null)}
                  onClick={(event) => event.stopPropagation()}
                  aria-label={editor.timestamp(number)}
                  placeholder="00:00.000 – 00:01.000"
                  spellCheck={false}
                  className="h-10 w-[12.5rem] max-w-full rounded-control [@media(pointer:coarse)]:h-11 border border-transparent bg-transparent px-1.5 font-mono text-xs tabular-nums text-ink-muted outline-none transition hover:border-line focus:border-line-strong focus:bg-surface focus:text-ink focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
                />
              ) : null}
              {/* A line that needs a look says why, once; a line that is fine carries no mark. */}
              {mark ? (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${mark.className}`}>
                  {editor.marks[mark.label] ?? mark.label}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="relative col-start-3 row-start-1 sm:col-start-4">
          <button
            ref={(node) => registerMenuButton(line.lineId, node)}
            type="button"
            aria-label={editor.more(number)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            disabled={busy}
            onClick={(event) => {
              event.stopPropagation();
              toggleLineMenu(line.lineId);
            }}
            className={`grid h-11 w-11 place-items-center rounded-full text-ink-muted transition hover:bg-surface-muted hover:text-ink disabled:opacity-50 motion-reduce:transition-none ${menuOpen ? "bg-surface-muted text-ink" : ""}`}
          >
            <MoreHorizontal size={18} aria-hidden="true" />
          </button>
          {menuOpen ? (
            <div
              role="menu"
              aria-label={editor.menu(number)}
              className="motion-popover absolute right-0 z-30 mt-1 w-64 max-w-[calc(100vw-2rem)] rounded-card border border-line bg-surface p-1 shadow-lift"
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  event.preventDefault();
                  closeLineMenu(line.lineId);
                }
              }}
            >
              <LineMenuItem label={editor.split} onClick={() => { splitLine(index, textRef.current?.selectionStart); closeLineMenu(line.lineId); }} disabled={!line.text.trim()} autoFocus>
                <GitPullRequest size={15} aria-hidden="true" />
              </LineMenuItem>
              <LineMenuItem label={editor.mergePrevious} onClick={() => { mergeLine(index, "previous"); closeLineMenu(line.lineId); }} disabled={index === 0}>
                <GitMerge size={15} aria-hidden="true" />
              </LineMenuItem>
              <LineMenuItem label={editor.mergeNext} onClick={() => { mergeLine(index, "next"); closeLineMenu(line.lineId); }} disabled={index === totalLines - 1}>
                <GitMerge size={15} aria-hidden="true" />
              </LineMenuItem>
              <LineMenuItem label={line.unclear ? editor.markClear : editor.markUnclear} onClick={() => { updateLine(index, { unclear: !line.unclear }); closeLineMenu(line.lineId); }}>
                <AlertTriangle size={15} aria-hidden="true" />
              </LineMenuItem>
              <div aria-hidden="true" className="my-1 border-t border-line" />
              <LineMenuItem label={editor.deleteLine} onClick={() => { deleteLine(index); closeLineMenu(line.lineId, false); }} tone="danger">
                <Trash2 size={15} aria-hidden="true" />
              </LineMenuItem>
            </div>
          ) : null}
        </div>
      </article>
    </TranscriptRowBoundary>
  );
});

function rowId(lineId: string) {
  return `transcript-line-${lineId}`;
}
