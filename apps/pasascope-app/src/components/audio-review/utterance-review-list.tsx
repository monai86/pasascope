"use client";

import React, { memo, useCallback, useEffect, useLayoutEffect, useRef } from "react";
import { CheckCircle2, Pause, Play } from "lucide-react";

import { audioReviewMessages, SPEAKER_CHOICES } from "@/components/audio-review/audio-review.messages";
import { formatClock } from "@/components/audio-review/audio-scrubber-bar";
import { speakerColour } from "@/design-system/dataviz";
import { useMessages } from "@/i18n/locale-provider";

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
  /** Lines to show, when a filter hides some; their numbers stay those of `lines`. */
  visibleLineIds?: ReadonlySet<string>;
  activeLineId?: string;
  /** The line whose own playback is running, shown with a pause button. */
  playingLineId?: string | null;
  onSelectLine?: (lineId: string) => void;
  onLineChange: (index: number, updatedLine: ReviewLine) => void;
  onPlayUtterance?: (startMs: number, endMs?: number, lineId?: string) => void;
  className?: string;
}

type Copy = (typeof audioReviewMessages)["en"];

/**
 * Every transcribed line with its time, speaker and words, in reading order.
 * The list scrolls with the page rather than in a box of its own, so a phone
 * has one scroll to manage. On a phone each line is two rows (play, time and
 * speaker above, the words below); from `sm` it is one row with aligned
 * columns, and the words wrap onto as many lines as they need.
 */
export function UtteranceReviewList({
  lines,
  visibleLineIds,
  activeLineId,
  playingLineId = null,
  onSelectLine,
  onLineChange,
  onPlayUtterance,
  className = "",
}: UtteranceReviewListProps) {
  const copy = useMessages(audioReviewMessages);
  const activeRowRef = useRef<HTMLLIElement | null>(null);
  const linesRef = useRef(lines);
  const onLineChangeRef = useRef(onLineChange);
  linesRef.current = lines;
  onLineChangeRef.current = onLineChange;

  // Bring the line being heard into view, unless the therapist is typing in another one.
  useEffect(() => {
    const row = activeRowRef.current;
    if (!row || typeof row.scrollIntoView !== "function") return;
    const focused = document.activeElement;
    if (focused instanceof HTMLElement && focused.closest("[data-review-line]") && !row.contains(focused)) return;
    row.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeLineId]);

  const change = useCallback((index: number, patch: Partial<ReviewLine>) => {
    const line = linesRef.current[index];
    if (line) onLineChangeRef.current(index, { ...line, ...patch });
  }, []);

  if (lines.length === 0) {
    return <p className="rounded-panel border border-dashed border-line bg-surface-soft px-4 py-8 text-center text-sm text-ink-muted">{copy.lines.empty}</p>;
  }

  return (
    <ol className={`divide-y divide-line ${className}`} data-testid="utterance-review-list">
      {lines.map((line, index) =>
        visibleLineIds && !visibleLineIds.has(line.lineId) ? null : (
          <UtteranceRow
            key={line.lineId || index}
            line={line}
            index={index}
            active={line.lineId === activeLineId}
            playing={line.lineId === playingLineId}
            rowRef={line.lineId === activeLineId ? activeRowRef : undefined}
            copy={copy}
            onSelectLine={onSelectLine}
            onChange={change}
            onPlayUtterance={onPlayUtterance}
          />
        ),
      )}
    </ol>
  );
}

const UtteranceRow = memo(function UtteranceRow({
  line,
  index,
  active,
  playing,
  rowRef,
  copy,
  onSelectLine,
  onChange,
  onPlayUtterance,
}: {
  line: ReviewLine;
  index: number;
  active: boolean;
  playing: boolean;
  rowRef?: React.Ref<HTMLLIElement>;
  copy: Copy;
  onSelectLine?: (lineId: string) => void;
  onChange: (index: number, patch: Partial<ReviewLine>) => void;
  onPlayUtterance?: (startMs: number, endMs?: number, lineId?: string) => void;
}) {
  const number = index + 1;
  const code = line.speaker.replace("*", "").trim().toUpperCase();
  const known = (SPEAKER_CHOICES as readonly string[]).includes(code);
  const timed = typeof line.startMs === "number";
  const echolalia = line.clinicalTag?.toLowerCase().includes("echolalia");
  const pronoun = line.clinicalTag?.toLowerCase().includes("pronoun");

  return (
    <li
      ref={rowRef}
      data-review-line={line.lineId}
      aria-current={active ? "true" : undefined}
      onClick={() => onSelectLine?.(line.lineId)}
      className={`grid scroll-mt-40 grid-cols-[2.75rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-2 py-2.5 transition-colors motion-reduce:transition-none sm:grid-cols-[2.75rem_6.75rem_10.5rem_minmax(0,1fr)] sm:items-start sm:px-3 ${
        active ? "bg-brand-soft" : "hover:bg-surface-soft"
      }`}
    >
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          if (timed) onPlayUtterance?.(line.startMs!, line.endMs, line.lineId);
        }}
        disabled={!timed}
        aria-label={playing ? copy.lines.pauseLine(number) : copy.lines.playLine(number)}
        className={`grid h-11 w-11 place-items-center rounded-full transition motion-reduce:transition-none disabled:opacity-30 ${
          playing ? "bg-brand-strong text-white" : "bg-surface-muted text-ink-muted hover:bg-brand-strong hover:text-white"
        }`}
      >
        {playing ? <Pause size={15} aria-hidden="true" /> : <Play size={15} aria-hidden="true" className="translate-x-px" />}
      </button>

      <p className="whitespace-nowrap font-mono text-xs tabular-nums text-ink-muted sm:pt-3.5">
        {timed && typeof line.endMs === "number" ? `${formatClock(line.startMs!)}–${formatClock(line.endMs)}` : "–"}
      </p>

      {/* The dot carries the speaker's colour; the name stays in text ink. */}
      <div className="relative justify-self-end sm:justify-self-stretch sm:pt-0.5">
        <span
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full sm:top-[calc(50%+1px)]"
          style={{ backgroundColor: known ? speakerColour(code, "light") : "transparent", boxShadow: known ? undefined : "inset 0 0 0 1.5px var(--color-border-strong)" }}
        />
        <select
          value={code}
          onChange={(event) => onChange(index, { speaker: event.target.value })}
          onClick={(event) => event.stopPropagation()}
          onFocus={() => onSelectLine?.(line.lineId)}
          aria-label={copy.lines.speaker(number)}
          className={`h-11 w-full min-w-[8rem] rounded-control border bg-surface pl-8 pr-8 text-sm font-semibold outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none ${
            known ? "border-line text-ink" : "border-[color:var(--color-attention-border)] text-[color:var(--color-warning-text)]"
          }`}
        >
          {/* A line the pipeline could not attribute says so, rather than showing the first speaker as if chosen. */}
          {known ? null : <option value={code}>{code === "UNK" || code === "" ? copy.notSet : copy.speakers[code as keyof Copy["speakers"]] ?? code}</option>}
          {SPEAKER_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {copy.speakers[choice]}
            </option>
          ))}
        </select>
      </div>

      <div className="col-span-3 col-start-1 min-w-0 sm:col-span-1 sm:col-start-4">
        <AutoGrowText
          value={line.text}
          label={copy.lines.text(number)}
          placeholder={copy.lines.placeholder}
          onFocus={() => onSelectLine?.(line.lineId)}
          onChange={(text) => onChange(index, { text })}
        />
        {echolalia || pronoun || line.verified ? (
          <div className="mt-1 flex flex-wrap items-center gap-1.5 px-2.5">
            {echolalia ? <span className="rounded-full bg-[color:var(--color-warning-bg)] px-2 py-0.5 text-xs font-medium text-[color:var(--color-warning-text)]">{copy.lines.echolalia}</span> : null}
            {pronoun ? <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand-strong">{copy.lines.pronounReversal}</span> : null}
            {line.verified ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-[color:var(--color-success-text)]">
                <CheckCircle2 size={14} aria-hidden="true" />
                {copy.lines.verified}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
});

/** A text box as tall as its words, so a long line is read whole instead of scrolled sideways. */
function AutoGrowText({
  value,
  label,
  placeholder,
  onFocus,
  onChange,
}: {
  value: string;
  label: string;
  placeholder: string;
  onFocus: () => void;
  onChange: (value: string) => void;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const fit = () => {
    const element = ref.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight}px`;
  };
  useLayoutEffect(fit, [value]);
  useEffect(() => {
    if (typeof ResizeObserver === "undefined" || !ref.current) return;
    // A narrower box wraps the words onto more lines.
    let lastWidth = 0;
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width !== lastWidth) {
        lastWidth = entry.contentRect.width;
        fit();
      }
    });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      aria-label={label}
      placeholder={placeholder}
      onFocus={onFocus}
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => onChange(event.target.value)}
      className="block min-h-11 w-full resize-none overflow-hidden rounded-control border border-transparent bg-transparent px-2.5 py-2.5 text-[15px] leading-6 text-ink outline-none transition placeholder:text-ink-subtle hover:border-line focus:border-line-strong focus:bg-surface focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
    />
  );
}
