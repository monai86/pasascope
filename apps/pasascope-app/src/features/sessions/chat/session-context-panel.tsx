"use client";

import { useRef, useState } from "react";
import { Check, Pause, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { chatMessages } from "@/features/sessions/chat/chat.messages";
import { chatSteps, type ChatStep } from "@/features/sessions/chat/chat-thread-model";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";

export type SessionSummary = {
  caseLabel: string;
  caseCode?: string;
  ageMonths?: number;
  language?: string;
  sessionDate?: string;
  consentGranted: boolean;
};

export function clock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

/**
 * The side panel of a session conversation: who the session is for, where it
 * stands, its audio, and the notes written so far.
 */
export function SessionContextPanel({
  summary,
  step,
  completed,
  audioUrl,
  notes,
}: {
  summary: SessionSummary;
  step: ChatStep;
  completed: Record<ChatStep, boolean>;
  audioUrl?: string;
  notes: string[];
}) {
  const t = useMessages(chatMessages);
  const { locale } = useLocale();
  const facts = [
    summary.caseCode && summary.caseCode !== summary.caseLabel ? summary.caseCode : null,
    typeof summary.ageMonths === "number"
      ? t.panel.ageYearsMonths(Math.floor(summary.ageMonths / 12), summary.ageMonths % 12)
      : null,
  ].filter(Boolean);

  return (
    <section aria-labelledby="session-context-title" className="flex min-h-0 flex-1 flex-col gap-6">
      <div>
        <h2 id="session-context-title" className="font-display text-[22px] font-semibold leading-snug text-ink">
          {summary.caseLabel}
        </h2>
        {facts.length > 0 ? <p className="mt-0.5 text-ink-subtle">{facts.join(" · ")}</p> : null}
      </div>

      <ol aria-label={t.stepsLabel} className="flex flex-col gap-3.5">
        {chatSteps.map((candidate, index) => {
          const done = completed[candidate];
          const current = candidate === step && !done;
          return (
            <li
              key={candidate}
              aria-current={current ? "step" : undefined}
              className={cn("flex items-center gap-3", current ? "font-semibold text-ink" : done ? "text-ink" : "text-ink-subtle")}
            >
              <span
                aria-hidden="true"
                className={cn(
                  "grid h-7 w-7 shrink-0 place-items-center rounded-full text-[13px]",
                  done
                    ? "bg-navy text-white"
                    : current
                      ? "border-2 border-navy"
                      : "border border-chat-line-strong",
                )}
              >
                {done ? <Check size={15} strokeWidth={2.5} /> : index + 1}
              </span>
              <span>{t.steps[candidate]}</span>
              {done ? <span className="sr-only">({t.stepDone})</span> : null}
            </li>
          );
        })}
      </ol>

      {audioUrl ? <SessionAudioPlayer src={audioUrl} /> : null}

      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2.5 text-sm">
        {summary.sessionDate ? (
          <>
            <dt className="text-ink-subtle">{t.panel.date}</dt>
            <dd className="text-right">{formatDate(summary.sessionDate, locale)}</dd>
          </>
        ) : null}
        {summary.language ? (
          <>
            <dt className="text-ink-subtle">{t.panel.language}</dt>
            <dd className="text-right">{summary.language}</dd>
          </>
        ) : null}
        <dt className="text-ink-subtle">{t.panel.consent}</dt>
        <dd className="text-right">{summary.consentGranted ? t.panel.consentGranted : t.panel.consentNotGranted}</dd>
      </dl>

      <div>
        <h3 className="text-sm font-semibold text-ink">{t.panel.notes}</h3>
        {notes.length === 0 ? (
          <p className="mt-1.5 text-sm text-ink-subtle">{t.panel.noNotes}</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-2 text-sm leading-6 text-ink">
            {notes.map((note, index) => (
              <li key={`${index}-${note}`} className="rounded-control bg-chat-frame px-3 py-2">{note}</li>
            ))}
          </ul>
        )}
      </div>

      <Button href="/" variant="secondary" className="mt-auto w-full">
        {t.panel.newSession}
      </Button>
    </section>
  );
}

/** The one dark surface in the panel: play, pause and how far in. */
function SessionAudioPlayer({ src }: { src: string }) {
  const t = useMessages(chatMessages).panel;
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState<number | null>(null);

  function toggle() {
    const element = audio.current;
    if (!element) return;
    if (element.paused) void element.play().catch(() => setPlaying(false));
    else element.pause();
  }

  return (
    <div className="flex items-center gap-3 rounded-card bg-navy p-4 text-on-navy">
      <audio
        ref={audio}
        src={src}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={(event) => setPosition(event.currentTarget.currentTime)}
        onLoadedMetadata={(event) => {
          const length = event.currentTarget.duration;
          setDuration(Number.isFinite(length) ? length : null);
        }}
      />
      <button
        type="button"
        aria-label={playing ? t.pause : t.play}
        title={playing ? t.pause : t.play}
        onClick={toggle}
        className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-surface text-navy transition hover:bg-chat-frame focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
      >
        {playing ? <Pause size={18} aria-hidden="true" /> : <Play size={18} aria-hidden="true" />}
      </button>
      <span className="flex flex-col leading-snug">
        <span className="font-semibold tabular-nums">{clock(position)}</span>
        <span className="text-[13px] text-on-navy-muted">
          {duration === null ? t.audio : t.of(clock(duration))}
        </span>
      </span>
    </div>
  );
}
