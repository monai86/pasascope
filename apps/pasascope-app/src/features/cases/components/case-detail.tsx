"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { CaregiverConsentForm } from "@/components/caregiver-consent-form";
import { DataTable } from "@/components/data-table";
import { LanguageProgressChart } from "@/features/dashboard/components/language-progress-chart";
import { SafetyNotice } from "@/components/safety-notice";
import { StatusBadge } from "@/components/status-badge";
import type { CaseDetailViewModel } from "@/features/cases/hooks/use-cases-workspace";
import { casesMessages } from "@/features/cases/cases.messages";
import { formatDateTime } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
import { useGateReason } from "@/lib/gate-reason";
import { grantConsentBlockedReason } from "@/lib/workflow-gates";
import { deleteBackendCase, type BackendCase, type BackendTimelineEvent } from "@/lib/workflow";

type Copy = typeof casesMessages.en;
type Shared = Copy["shared"];

function ageLabel(caseItem: BackendCase, shared: Shared) {
  if (caseItem.age_months == null) return shared.ageNotRecorded;
  return shared.age(Math.floor(caseItem.age_months / 12), caseItem.age_months % 12);
}

function caseLabel(caseItem: BackendCase) {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function codeLabel(caseItem: BackendCase) {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

function consentLabel(value: string | undefined, shared: Shared) {
  if (!value) return shared.consentUnknown;
  return shared.consentStates[value.toLowerCase()] ?? value;
}

export function CaseDetail({ model }: { model: CaseDetailViewModel }) {
  const { caseItem, timeline, goals, consent } = model;
  const {
    localConsent,
    consentSigner,
    setConsentSigner,
    consentChecked,
    setConsentChecked,
    consentDate,
    setConsentDate,
    consentNotes,
    setConsentNotes,
    consentBusy,
    consentMsg,
  } = consent;
  const { shared, detail: t } = useMessages(casesMessages);
  const safety = useSafetyCopy();
  const gate = useGateReason();
  const isConsentGranted = localConsent.toLowerCase() === "granted";

  function handleGrantConsent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void consent.grantConsent();
  }

  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);

  function handleWithdrawConsent() {
    setWithdrawDialogOpen(true);
  }

  function confirmWithdrawConsent() {
    setWithdrawDialogOpen(false);
    void consent.withdrawConsent();
  }

  // A case with nothing recorded for it can be deleted; the API checks again.
  const router = useRouter();
  const canDelete =
    timeline.length === 0 && goals.length === 0 && !caseItem.latest_session_date && localConsent.toLowerCase() !== "withdrawn";
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteFailed, setDeleteFailed] = useState(false);

  async function confirmDelete() {
    setDeleting(true);
    setDeleteFailed(false);
    try {
      await deleteBackendCase(caseItem.case_id);
      router.push("/cases");
    } catch {
      setDeleteFailed(true);
      setDeleting(false);
      setDeleteDialogOpen(false);
    }
  }

  const consentState = localConsent.toLowerCase();
  const startHref = `/cases?intent=start-session&case_id=${encodeURIComponent(caseItem.case_id)}`;
  const facts = [codeLabel(caseItem), ageLabel(caseItem, shared), caseItem.language ?? shared.languageNotRecorded];

  return (
    <div className="mx-auto grid w-full max-w-[1040px] gap-6">
      <ConfirmDialog
        open={withdrawDialogOpen}
        title={t.withdrawTitle}
        description={t.withdrawBody}
        confirmLabel={t.withdrawConfirm}
        cancelLabel={t.withdrawCancel}
        destructive
        onConfirm={confirmWithdrawConsent}
        onCancel={() => setWithdrawDialogOpen(false)}
      />
      <ConfirmDialog
        open={deleteDialogOpen}
        title={t.remove.title}
        description={t.remove.body}
        confirmLabel={t.remove.confirm}
        cancelLabel={t.remove.cancel}
        destructive
        busy={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleteDialogOpen(false)}
      />

      {/* Who the case is, where consent stands, and the one thing to do next. */}
      <header className="flex flex-col gap-5 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="break-words font-display text-[2rem] font-semibold leading-tight text-ink md:text-[2.5rem]">{caseLabel(caseItem)}</h1>
          <p className="mt-2 text-[15px] text-ink-muted">{facts.join(" · ")}</p>
          <p className="mt-3">
            <ConsentChip state={consentState} label={consentLabel(localConsent, shared)} />
          </p>
        </div>
        {/* Without consent the form below is the next step, so it needs no button here. */}
        {isConsentGranted ? (
          <Button href={startHref} className="shrink-0 self-start sm:self-auto">{t.createSession}</Button>
        ) : null}
      </header>

      {!isConsentGranted ? (
        <Panel id="case-consent" title={t.consentFormTitle} description={t.consentFormBody}>
          <CaregiverConsentForm
            busy={consentBusy}
            checked={consentChecked}
            onCheckedChange={setConsentChecked}
            signer={consentSigner}
            onSignerChange={setConsentSigner}
            consentDate={consentDate}
            onConsentDateChange={setConsentDate}
            notes={consentNotes}
            onNotesChange={setConsentNotes}
            onSubmit={handleGrantConsent}
            submitLabel={shared.verifyConsent}
            submitBlockedReason={gate(grantConsentBlockedReason({ checked: consentChecked, busy: consentBusy }))}
            reasonId="case-grant-consent-reason"
            idPrefix="case"
          />
        </Panel>
      ) : null}

      {consentMsg ? (
        <p
          role="status"
          className={`rounded-control border px-4 py-3 text-sm font-medium ${
            consentMsg.includes("Failed") || consentMsg.includes("Could not")
              ? "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]"
              : "border-brand-border bg-brand-soft text-brand"
          }`}
        >
          {consentMsg}
        </p>
      ) : null}

      <Panel title={t.sessions}>
        {timeline.length ? (
          <SessionHistory timeline={timeline} />
        ) : (
          // The header already offers the way to start one.
          <p className="text-sm leading-6 text-ink-muted">
            {t.sessionsEmpty} {isConsentGranted ? null : t.consentNeeded}
          </p>
        )}
      </Panel>

      {timeline.length ? (
        <Panel title={t.progress}>
          <LanguageProgressChart trends={model.featureTrend} />
        </Panel>
      ) : null}

      <Panel title={t.goals}>
        {goals.length ? (
          <ul className="divide-y divide-line">
            {goals.map((goal) => (
              <li key={goal.goal_id} className="py-3 first:pt-0 last:pb-0">
                <p className="font-semibold text-ink">{goal.title}</p>
                <p className="mt-1 text-sm text-ink-muted">{goal.target?.trim() || t.goalTargetEmpty}</p>
                {goal.notes?.trim() ? <p className="mt-1 text-sm leading-6 text-ink-muted">{goal.notes}</p> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm leading-6 text-ink-muted">{t.goalsEmpty}</p>
        )}
      </Panel>

      <Panel title={t.overview}>
        <dl className="border-t border-line">
          <Fact label={t.childLabel}>{caseLabel(caseItem)}</Fact>
          <Fact label={t.age}>{ageLabel(caseItem, shared)}</Fact>
          <Fact label={t.language}>{caseItem.language ?? shared.languageNotRecorded}</Fact>
          <Fact label={t.referral}>
            <span className="whitespace-pre-line">{caseItem.notes?.trim() || t.referralEmpty}</span>
          </Fact>
          <Fact label={t.consentStatus}>
            <span className="flex flex-wrap items-center justify-between gap-3">
              <span>{consentLabel(localConsent, shared)}</span>
              {isConsentGranted ? (
                <Button
                  variant="ghost"
                  onClick={handleWithdrawConsent}
                  disabled={consentBusy}
                  className="text-[color:var(--color-danger-text)] hover:bg-[color:var(--color-danger-bg)]"
                >
                  {t.withdraw}
                </Button>
              ) : null}
            </span>
          </Fact>
          <Fact label={t.reportLatest}>
            <span className="flex flex-wrap items-center justify-between gap-3">
              <StatusBadge status={caseItem.latest_report_status ?? "Not started"} />
              <Link href="/reports" className="inline-flex min-h-11 items-center text-sm font-semibold text-brand underline decoration-brand/30 underline-offset-4 hover:decoration-brand">
                {t.openReports}
              </Link>
            </span>
          </Fact>
          <Fact label={t.owner}>{t.careTeamNote}</Fact>
        </dl>
      </Panel>

      {canDelete || deleteFailed ? (
        <div className="flex flex-wrap items-center justify-between gap-3 px-1 text-sm text-ink-muted" data-testid="case-delete">
          {deleteFailed ? (
            <p role="alert" className="font-medium text-[color:var(--color-danger-text)]">{t.remove.failed}</p>
          ) : (
            <p>{t.remove.hint}</p>
          )}
          {canDelete ? (
            <Button
              variant="ghost"
              onClick={() => setDeleteDialogOpen(true)}
              className="text-[color:var(--color-danger-text)] hover:bg-[color:var(--color-danger-bg)]"
            >
              {t.remove.action}
            </Button>
          ) : null}
        </div>
      ) : null}

      <SafetyNotice>
        {safety.DECISION_SUPPORT_ONLY} {t.safetyNote}
      </SafetyNotice>
    </div>
  );
}

/** One part of the case page: a heading, an optional line under it, and its content. */
function Panel({ id, title, description, children }: { id?: string; title: string; description?: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-title` : undefined} className="scroll-mt-6 rounded-panel border border-line bg-surface px-5 py-6 sm:px-7">
      <h2 id={id ? `${id}-title` : undefined} className="text-lg font-semibold text-ink">{title}</h2>
      {description ? <p className="mt-1 max-w-[62ch] text-sm leading-6 text-ink-muted">{description}</p> : null}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 border-b border-line py-3.5 last:border-b-0 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)] sm:items-center sm:gap-6">
      <dt className="text-sm font-semibold text-ink">{label}</dt>
      <dd className="min-w-0 text-sm leading-6 text-ink">{children}</dd>
    </div>
  );
}

/** Consent in a word, coloured by what it allows: recorded, waiting, or withdrawn. */
function ConsentChip({ state, label }: { state: string; label: string }) {
  const tone =
    state === "granted"
      ? "border-brand-border bg-brand-soft text-brand-strong"
      : state === "withdrawn"
        ? "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]"
        : "border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]";
  return (
    <span className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 text-[13px] font-semibold ${tone}`}>
      <ShieldCheck size={14} aria-hidden="true" />
      {label}
    </span>
  );
}

const SESSION_HISTORY_PREVIEW = 4;

function SessionHistory({ timeline }: { timeline: BackendTimelineEvent[] }) {
  const t = useMessages(casesMessages).detail;
  const { locale } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? timeline : timeline.slice(0, SESSION_HISTORY_PREVIEW);

  return (
    <div className="space-y-3">
      <DataTable
        caption={t.historyCaption}
        columns={[
          { key: "session", header: t.historyColumns.session },
          { key: "date", header: t.historyColumns.date },
          { key: "status", header: t.historyColumns.status },
          { key: "nextAction", header: t.historyColumns.nextAction }
        ]}
        rows={visible.map((event) => ({
          id: event.event_id,
          session: <span className="font-medium">{event.label}</span>,
          date: formatDateTime(event.occurred_at, locale),
          status: <StatusBadge status={event.status} />,
          nextAction: (
            <Link
              href={`/sessions/${encodeURIComponent(event.target_id)}?view=intake`}
              className="inline-flex min-h-11 items-center gap-2 rounded-card border border-line px-4 py-2 font-medium text-ink transition hover:border-brand-strong hover:bg-brand-soft"
            >
              {t.openSession}
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          )
        }))}
      />
      {timeline.length > SESSION_HISTORY_PREVIEW && (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className="inline-flex min-h-11 items-center gap-2 rounded-card px-2 text-sm font-medium text-brand-strong transition hover:bg-brand-soft"
        >
          {expanded ? t.showFewer : t.showAll(timeline.length)}
        </button>
      )}
    </div>
  );
}
