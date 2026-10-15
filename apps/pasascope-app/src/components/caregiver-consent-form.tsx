"use client";

import type { FormEvent } from "react";

import { ActionButton } from "@/components/action-button";
import { consentMessages } from "@/components/consent.messages";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";

/**
 * Shared caregiver-consent verification form used by the Case detail page and
 * the conversation that starts a session, so the two never drift apart in
 * wording. It asks for the confirmation only; the signer and date sent with it
 * are the caller's defaults.
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
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  submitLabel: string;
  /** Optional reason shown when the submit action is blocked (e.g. box unchecked). */
  submitBlockedReason?: string;
  /** id of the blocked-reason element; submit button points at it via aria-describedby. */
  reasonId?: string;
};

export function CaregiverConsentForm({
  busy,
  checked,
  onCheckedChange,
  onSubmit,
  submitLabel,
  submitBlockedReason,
  reasonId,
}: CaregiverConsentFormProps) {
  const t = useMessages(consentMessages);
  const thaiFirst = useLocale().locale === "th";
  const { externalTranscription } = useAppMode();
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
      {externalTranscription ? (
        <p className="rounded-xl border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">
          {t.externalTranscription}
        </p>
      ) : null}

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
