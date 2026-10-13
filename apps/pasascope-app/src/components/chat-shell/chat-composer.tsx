"use client";

import { useRef, type FormEvent } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowUp, Paperclip } from "lucide-react";

import { cn } from "@/lib/cn";

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

export type ComposerChip = {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
};

export type ComposerAttach = {
  label: string;
  /** File types offered by the picker, e.g. "audio/*,.cha". */
  accept: string;
  onFile: (file: File) => void;
};

/**
 * The text field at the foot of a conversation. With `chips` it is the roomy
 * home composer from tablet width up; otherwise, and always on a phone, it is
 * one pill. What typing does is the page's business: this only reports it.
 */
export function ChatComposer({
  label,
  placeholder,
  value,
  onChange,
  onSubmit,
  submitLabel,
  attach,
  chips = [],
  disabled = false,
  testId,
}: {
  /** Names the text field for assistive technology. */
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  submitLabel: string;
  attach?: ComposerAttach;
  chips?: ComposerChip[];
  disabled?: boolean;
  testId?: string;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const roomy = chips.length > 0;
  const canSubmit = !disabled && value.trim().length > 0;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) onSubmit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid={testId}
      className={cn(
        "chat-composer mx-auto flex w-full max-w-[660px] items-center gap-1 rounded-full bg-surface py-1.5 pl-5 pr-1.5 shadow-chat-composer",
        roomy && "md:flex-wrap md:gap-2 md:rounded-[28px] md:border md:border-chat-line md:bg-white/70 md:p-3 md:pl-5 md:shadow-none",
      )}
    >
      <input
        type="text"
        aria-label={label}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        autoComplete="off"
        // 16px keeps iOS from zooming the page when the field takes focus.
        className={cn(
          "min-h-11 min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-ink-subtle focus-visible:outline-none",
          roomy && "md:mb-1 md:basis-full",
        )}
      />

      {attach ? (
        <>
          <input
            ref={fileInput}
            type="file"
            accept={attach.accept}
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(event) => {
              const file = event.target.files?.[0];
              // Cleared so choosing the same file again still reports it.
              event.target.value = "";
              if (file) attach.onFile(file);
            }}
          />
          {/* An icon in the pill; a labelled chip in the roomy layout. */}
          <button
            type="button"
            aria-label={attach.label}
            title={attach.label}
            disabled={disabled}
            onClick={() => fileInput.current?.click()}
            className={cn(
              "grid h-11 w-11 shrink-0 place-items-center rounded-full text-ink-subtle transition hover:bg-chat-frame hover:text-ink motion-reduce:transition-none",
              FOCUS_RING,
              roomy && "md:inline-flex md:w-auto md:items-center md:gap-2 md:bg-surface md:px-[18px] md:font-medium md:text-ink md:shadow-chat-card",
            )}
          >
            <Paperclip size={roomy ? 18 : 20} aria-hidden="true" />
            {roomy ? <span aria-hidden="true" className="hidden md:inline">{attach.label}</span> : null}
          </button>
        </>
      ) : null}

      {chips.map((chip) => {
        const Icon = chip.icon;
        return (
          <button
            key={chip.label}
            type="button"
            onClick={chip.onClick}
            disabled={disabled}
            className={cn(
              "hidden min-h-11 items-center gap-2 rounded-full bg-surface px-[18px] font-medium text-ink shadow-chat-card transition hover:shadow-soft motion-reduce:transition-none md:inline-flex",
              FOCUS_RING,
            )}
          >
            <Icon size={18} aria-hidden="true" className="text-ink-subtle" />
            {chip.label}
          </button>
        );
      })}

      <button
        type="submit"
        aria-label={submitLabel}
        title={submitLabel}
        disabled={!canSubmit}
        className={cn(
          "grid h-11 w-11 shrink-0 place-items-center rounded-full transition duration-200 motion-reduce:transition-none",
          FOCUS_RING,
          roomy && "md:ml-auto",
          canSubmit ? "bg-action text-white shadow-chat-action hover:bg-action-hover" : "bg-chat-line text-ink-subtle",
        )}
      >
        <ArrowUp size={20} aria-hidden="true" />
      </button>
    </form>
  );
}
