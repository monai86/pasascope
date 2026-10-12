"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ShieldCheck } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { PageHeader } from "@/components/page-header";
import { SafetyNotice } from "@/components/safety-notice";
import { casesMessages } from "@/features/cases/cases.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
import { createBackendSessionForCase, type BackendCase } from "@/lib/workflow";

function caseLabel(caseItem: BackendCase) {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function codeLabel(caseItem: BackendCase) {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function canStartSession(caseItem: BackendCase) {
  return caseItem.consent_status?.toLowerCase() === "granted";
}

export function StartSessionSelector({ cases, preselectedCaseId }: { cases: BackendCase[]; preselectedCaseId?: string }) {
  const router = useRouter();
  const { shared, start: t } = useMessages(casesMessages);
  const safety = useSafetyCopy();
  const preselected = preselectedCaseId
    ? cases.find((caseItem) => caseItem.case_id === preselectedCaseId && canStartSession(caseItem))
    : undefined;
  const [selectedCaseId, setSelectedCaseId] = useState(() => (
    preselected ? preselected.case_id : ""
  ));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedCase = cases.find((caseItem) => caseItem.case_id === selectedCaseId && canStartSession(caseItem));
  const hasConsentedCase = cases.some(canStartSession);

  useEffect(() => {
    if (preselected) setSelectedCaseId(preselected.case_id);
  }, [preselected]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCase || busy) return;

    setBusy(true);
    setMessage(t.creating);
    try {
      const session = await createBackendSessionForCase(selectedCase.case_id);
      router.push(`/sessions/${encodeURIComponent(session.session_id)}?view=intake`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t.failed);
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t.title}
        description={t.description}
        meta={[t.meta]}
        actions={<ActionButton href="/cases" tone="ghost"><ArrowLeft size={16} aria-hidden="true" />{t.backToCases}</ActionButton>}
      />

      <form className="workspace-panel p-4 sm:p-5" onSubmit={handleSubmit}>
        <fieldset disabled={busy}>
          <legend className="text-lg font-semibold text-ink">{t.available}</legend>
          <p className="mt-1 text-sm leading-6 text-ink-muted">
            {t.availableNote}
          </p>
          {preselected ? (
            <p className="mt-3 rounded-card border border-line bg-surface-muted px-3 py-2 text-sm text-ink-muted">
              {t.preselected(codeLabel(preselected))}
            </p>
          ) : null}
          {!hasConsentedCase ? (
            <div className="mt-4 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-4 text-[color:var(--color-warning-text)]">
              <h2 className="font-semibold">{t.noneTitle}</h2>
              <p className="mt-1 text-sm leading-6">
                {t.noneBody}
              </p>
            </div>
          ) : null}
          <ul className="mt-4 grid gap-3" aria-label={t.listLabel}>
            {cases.map((caseItem) => {
              const allowed = canStartSession(caseItem);
              const selected = selectedCaseId === caseItem.case_id;
              return (
                <li key={caseItem.case_id}>
                  <label className={`flex min-h-16 cursor-pointer items-start gap-3 rounded-card border p-4 transition focus-within:ring-4 focus-within:ring-[color:var(--color-focus-ring)] ${
                    selected
                      ? "border-brand-strong bg-brand-soft"
                      : "border-line bg-surface"
                  } ${allowed ? "" : "cursor-not-allowed opacity-65"}`}>
                    <input
                      type="radio"
                      name="case-id"
                      value={caseItem.case_id}
                      checked={selected}
                      onChange={() => setSelectedCaseId(caseItem.case_id)}
                      disabled={!allowed}
                      className="mt-1 h-5 w-5 shrink-0 accent-brand-strong"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold text-ink">{caseLabel(caseItem)}</span>
                      <span className="mt-1 block text-sm text-ink-muted">
                        {codeLabel(caseItem)} · {caseItem.language ?? shared.languageNotRecorded}
                      </span>
                    </span>
                    <span className="inline-flex min-h-8 shrink-0 items-center gap-2 rounded-card border border-line px-3 text-xs font-semibold text-ink-muted">
                      <ShieldCheck size={14} aria-hidden="true" />
                      {allowed ? t.consentActive : t.consentRequired}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <ActionButton type="submit" disabled={!selectedCase || busy}>
            {busy ? t.creatingButton : selectedCase ? t.startFor(codeLabel(selectedCase)) : t.start}
          </ActionButton>
          <p className="text-sm text-ink-muted" role="status" aria-live="polite">
            {message}
          </p>
        </div>
      </form>

      <SafetyNotice>
        {t.safetyNote} {safety.THERAPIST_REVIEW_AND_CONSENT_REQUIRED}
      </SafetyNotice>
    </div>
  );
}
