"use client";

import type { FormEvent } from "react";

import { ActionButton } from "@/components/action-button";
import { consentMessages } from "@/components/consent.messages";
import { useLocale, useMessages } from "@/i18n/locale-provider";

/**
 * Shared caregiver-consent verification form used by both the Case detail page
 * and the Session Intake consent gate, so the two surfaces never drift apart in
 * fields or wording.
 *
 * Bilingual labeling policy: field labels follow the interface language. The
 * caregiver-consent confirmation statement is the one clinically sensitive
 * phrase a therapist must verify unambiguously, so it always renders in both
 * languages, with the interface language first.
 */

const CONFIRMATION_EN = "I verify that written or verbal caregiver consent has been obtained.";
const CONFIRMATION_TH = "ข้าพเจ้ายืนยันว่าได้รับการลงนามยินยอมจากผู้ปกครองเพื่อเก็บข้อมูลตัวอย่างเสียงแล้ว";

export type CaregiverConsentFormProps = {
  busy: boolean;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  signer: string;
  onSignerChange: (value: string) => void;
  consentDate: string;
  onConsentDateChange: (value: string) => void;
  notes: string;
  onNotesChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  submitLabel: string;
  /** Optional reason shown when the submit action is blocked (e.g. box unchecked). */
  submitBlockedReason?: string;
  /** id of the blocked-reason element; submit button points at it via aria-describedby. */
  reasonId?: string;
  /** Prefix for field ids so multiple instances never collide. */
  idPrefix: string;
};

export function CaregiverConsentForm({
  busy,
  checked,
  onCheckedChange,
  signer,
  onSignerChange,
  consentDate,
  onConsentDateChange,
  notes,
  onNotesChange,
  onSubmit,
  submitLabel,
  submitBlockedReason,
  reasonId,
  idPrefix,
}: CaregiverConsentFormProps) {
  const signerId = `${idPrefix}-consent-signer`;
  const dateId = `${idPrefix}-consent-date`;
  const notesId = `${idPrefix}-consent-notes`;
  const t = useMessages(consentMessages);
  const thaiFirst = useLocale().locale === "th";
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <label className="flex cursor-pointer items-start gap-3 text-sm font-medium text-ink">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4 rounded border-line accent-brand-strong"
          checked={checked}
          onChange={(event) => onCheckedChange(event.target.checked)}
          disabled={busy}
          required
        />
        <span className="grid gap-1">
          <span>{thaiFirst ? CONFIRMATION_TH : CONFIRMATION_EN}</span>
          <span className="text-xs leading-5 text-ink-muted">{thaiFirst ? CONFIRMATION_EN : CONFIRMATION_TH}</span>
        </span>
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label htmlFor={signerId} className="grid gap-1 text-sm font-medium text-ink">
          {t.signer}
          <input
            id={signerId}
            type="text"
            className="min-h-11 w-full rounded-card border border-line bg-surface px-4 text-sm text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
            value={signer}
            onChange={(event) => onSignerChange(event.target.value)}
            disabled={busy}
            placeholder={t.signerPlaceholder}
            required
          />
        </label>

        <label htmlFor={dateId} className="grid gap-1 text-sm font-medium text-ink">
          {t.date}
          <input
            id={dateId}
            type="date"
            className="min-h-11 w-full rounded-card border border-line bg-surface px-4 text-sm text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
            value={consentDate}
            onChange={(event) => onConsentDateChange(event.target.value)}
            disabled={busy}
            required
          />
        </label>
      </div>

      <label htmlFor={notesId} className="grid gap-1 text-sm font-medium text-ink">
        {t.notes}
        <textarea
          id={notesId}
          className="min-h-24 w-full resize-y rounded-card border border-line bg-surface p-4 text-sm text-ink outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
          value={notes}
          onChange={(event) => onNotesChange(event.target.value)}
          disabled={busy}
          placeholder={t.notesPlaceholder}
        />
      </label>

      <div className="flex flex-wrap gap-3">
        <ActionButton
          type="submit"
          disabled={busy || !checked}
          aria-describedby={submitBlockedReason && reasonId ? reasonId : undefined}
        >
          {busy ? t.verifying : submitLabel}
        </ActionButton>
      </div>

      {submitBlockedReason && reasonId ? (
        <p id={reasonId} role="status" className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]">
          {submitBlockedReason}
        </p>
      ) : null}
    </form>
  );
}
