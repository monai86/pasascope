"use client";

import type { FocusEventHandler, MouseEventHandler } from "react";

import { speakerColour } from "@/design-system/dataviz";
import { defineMessages } from "@/i18n/messages";
import { useMessages } from "@/i18n/locale-provider";

/** The speakers offered for a line, in the order they are listed. THER is the app's code for the therapist. */
export const SPEAKER_CHOICES = ["CHI", "THER", "MOT", "FAT", "PAR", "OTH"] as const;

type SpeakerCode = (typeof SPEAKER_CHOICES)[number] | "INV";

export const speakerSelectMessages = defineMessages<{ speakers: Record<SpeakerCode, string>; notSet: string }>({
  en: {
    speakers: { CHI: "Child", THER: "Therapist", MOT: "Mother", FAT: "Father", PAR: "Parent", OTH: "Other", INV: "Investigator" },
    notSet: "Not set",
  },
  th: {
    speakers: { CHI: "เด็ก", THER: "นักบำบัด", MOT: "แม่", FAT: "พ่อ", PAR: "ผู้ปกครอง", OTH: "อื่นๆ", INV: "ผู้ประเมิน" },
    notSet: "ยังไม่ระบุ",
  },
});

export function speakerCode(speaker: string): string {
  return speaker.replace("*", "").trim().toUpperCase();
}

/** True when the line has no speaker the therapist has chosen. */
export function speakerIsUnset(speaker: string): boolean {
  const code = speakerCode(speaker);
  return code === "" || code === "UNK";
}

/**
 * Who said a line, as a native select so every platform gives its own picker.
 * The dot carries the speaker's colour and the name stays in text ink; a line
 * the transcription could not attribute reads "Not set" in the warning tone
 * instead of showing the first speaker as if it had been chosen.
 */
export function SpeakerSelect({
  value,
  label,
  onChange,
  onFocus,
  onClick,
  disabled,
  className = "",
}: {
  value: string;
  label: string;
  onChange: (speaker: string) => void;
  onFocus?: FocusEventHandler<HTMLSelectElement>;
  onClick?: MouseEventHandler<HTMLSelectElement>;
  disabled?: boolean;
  className?: string;
}) {
  const copy = useMessages(speakerSelectMessages);
  const code = speakerCode(value);
  const unset = speakerIsUnset(value);
  const listed = (SPEAKER_CHOICES as readonly string[]).includes(code);
  const nameOf = (speaker: string) => copy.speakers[speaker as SpeakerCode] ?? speaker;

  return (
    <div className={`relative self-start ${className}`}>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute left-3 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full"
        style={unset ? { boxShadow: "inset 0 0 0 1.5px var(--color-border-strong)" } : { backgroundColor: speakerColour(code, "light") }}
      />
      <select
        value={code}
        onChange={(event) => onChange(event.target.value)}
        onFocus={onFocus}
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        className={`h-11 w-full rounded-control border bg-surface pl-8 pr-7 text-sm font-semibold outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:opacity-60 motion-reduce:transition-none ${
          unset ? "border-[color:var(--color-attention-border)] text-[color:var(--color-warning-text)]" : "border-line text-ink"
        }`}
      >
        {listed ? null : <option value={code}>{unset ? copy.notSet : nameOf(code)}</option>}
        {SPEAKER_CHOICES.map((choice) => (
          <option key={choice} value={choice}>
            {nameOf(choice)}
          </option>
        ))}
      </select>
    </div>
  );
}
