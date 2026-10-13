"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";
import { Activity, ArrowRight, CalendarDays, CircleDot, Gauge, ShieldCheck, Users } from "lucide-react";

import { ActionButton } from "@/components/action-button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { CaregiverConsentForm } from "@/components/caregiver-consent-form";
import { DataTable } from "@/components/data-table";
import { LanguageProgressChart } from "@/features/dashboard/components/language-progress-chart";
import { PageHeader } from "@/components/page-header";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";
import { SafetyNotice } from "@/components/safety-notice";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import type { CaseDetailViewModel } from "@/features/cases/hooks/use-cases-workspace";
import { statusMessages } from "@/components/status.messages";
import { casesMessages, type CaseStage } from "@/features/cases/cases.messages";
import { formatDateTime } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
import { useGateReason } from "@/lib/gate-reason";
import { grantConsentBlockedReason } from "@/lib/workflow-gates";
import { deleteBackendCase, type BackendCase, type BackendGoal, type BackendTimelineEvent } from "@/lib/workflow";

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

function clinicianLabel(userId: string) {
  if (userId === "therapist-demo") return "Demo Therapist";
  return userId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function primaryClinician(caseItem: BackendCase, shared: Shared) {
  if (caseItem.primary_therapist_user_id) return clinicianLabel(caseItem.primary_therapist_user_id);
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? clinicianLabel(assigned[0]) : shared.notAssigned;
}

function clinicianList(caseItem: BackendCase, shared: Shared) {
  const assigned = caseItem.care_team_user_ids ?? [];
  return assigned.length ? assigned.map(clinicianLabel).join(", ") : shared.noClinicianAssigned;
}

function childInitials(caseItem: BackendCase) {
  const label = caseLabel(caseItem);
  const words = label.split(/\s+/).filter(Boolean);
  return words.slice(0, 2).map((word) => word[0]?.toUpperCase() ?? "").join("") || codeLabel(caseItem).slice(-2);
}

function consentLabel(value: string | undefined, shared: Shared) {
  if (!value) return shared.consentUnknown;
  return shared.consentStates[value.toLowerCase()] ?? value;
}

// Only tasks the therapist can act on from here; goals cannot be added in this app yet.
function buildUpcomingTasks(timeline: BackendTimelineEvent[], consent: string, tasks: Copy["detail"]["tasks"]) {
  const result: string[] = [];
  if (consent && consent.toLowerCase() !== "granted") result.push(tasks.consent);
  if (timeline.some((event) => event.status === "Needs Review")) result.push(tasks.review);
  if (!result.length) result.push(tasks.fallback);
  return result;
}

function getLocalWorkflowStage(caseItem: BackendCase, consent: string): CaseStage {
  if (consent && consent.toLowerCase() !== "granted") return "consent";
  if (caseItem.latest_session_status === "Needs Review") return "transcript";
  if (caseItem.latest_report_status === "Ready") return "signOff";
  if (caseItem.latest_session_status === "Attested") return "drafting";
  if (caseItem.latest_session_date) return "session";
  return "intake";
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
  const statusLabels = useMessages(statusMessages) as Record<string, string>;
  const safety = useSafetyCopy();
  const gate = useGateReason();
  const statusLabel = (status?: string) => (status ? statusLabels[status] ?? status : statusLabels.Draft);
  const isConsentGranted = localConsent.toLowerCase() === "granted";
  const localWorkflowStage = shared.stages[getLocalWorkflowStage(caseItem, localConsent)];
  const snapshot = [
    { label: t.workflowStage, value: localWorkflowStage, helper: statusLabel(caseItem.latest_session_status) },
    { label: t.latestSession, value: caseItem.latest_session_date ?? shared.notStarted, helper: statusLabel(caseItem.latest_session_status) },
    { label: t.reportStatus, value: statusLabel(caseItem.latest_report_status), helper: safety.THERAPIST_REVIEW_SIGNOFF_REQUIRED },
  ];
  const tasks = buildUpcomingTasks(timeline, localConsent, t.tasks);

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

  return (
    <div className="space-y-6">
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
      <PageHeader
        title={caseLabel(caseItem)}
        description={t.description}
        meta={[
          t.caseCode(codeLabel(caseItem)),
          ageLabel(caseItem, shared),
          localWorkflowStage,
          primaryClinician(caseItem, shared)
        ]}
        actions={
          <ActionButton
            href={isConsentGranted ? `/cases?intent=start-session&case_id=${encodeURIComponent(caseItem.case_id)}` : "#"}
            disabled={!isConsentGranted}
            className={!isConsentGranted ? "opacity-50 cursor-not-allowed" : ""}
          >
            {t.createSession}
          </ActionButton>
        }
      />

      {canDelete ? (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-ink-muted" data-testid="case-delete">
          <p>{t.remove.hint}</p>
          <ActionButton
            type="button"
            tone="secondary"
            onClick={() => setDeleteDialogOpen(true)}
            className="hover:border-[color:var(--color-danger-text)] hover:bg-[color:var(--color-danger-bg)] hover:text-[color:var(--color-danger-text)]"
          >
            {t.remove.action}
          </ActionButton>
        </div>
      ) : null}
      {deleteFailed ? (
        <p
          role="alert"
          className="rounded-control border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-4 py-3 text-sm font-medium text-[color:var(--color-danger-text)]"
        >
          {t.remove.failed}
        </p>
      ) : null}

      <PipelineProgressBar currentStatus={localConsent === "granted" ? "ready_for_audio" : "awaiting_consent"} />

      <section className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-soft text-xl font-bold text-brand border border-[color:var(--color-brand-border)]/60 shadow-2xs">
              {childInitials(caseItem)}
            </div>
            <div>
              <h2 className="text-xl font-bold text-ink">{t.profile}</h2>
              <p className="mt-0.5 text-xs text-ink-muted font-mono">
                {codeLabel(caseItem)} · {caseItem.language ?? shared.languageNotRecorded}
              </p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <HeaderMeta label={t.caseStatus} value={localWorkflowStage} icon={Activity} />
            <HeaderMeta label={t.primaryTherapist} value={primaryClinician(caseItem, shared)} icon={Users} />
            <HeaderMeta label={t.consentStatus} value={consentLabel(localConsent, shared)} icon={ShieldCheck} />
            <HeaderMeta label={t.latestSession} value={caseItem.latest_session_date ?? shared.notStarted} icon={CalendarDays} />
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_var(--rail-width)]">
        <div className="min-w-0 space-y-6">
          {!isConsentGranted ? (
            <div className="grid gap-4">
              <section className="grid gap-3 rounded-2xl border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-5 shadow-2xs">
                <div className="flex items-start gap-3">
                  <CircleDot className="mt-1 h-5 w-5 shrink-0 text-[color:var(--color-warning-text)]" aria-hidden="true" />
                  <div className="grid gap-1">
                    <h2 className="text-base font-bold text-[color:var(--color-warning-text)]">
                      {t.consentRequiredTitle}
                    </h2>
                    <p className="text-xs leading-relaxed text-[color:var(--color-warning-text)]">
                      {t.consentRequiredBody}
                    </p>
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-line bg-surface grid gap-4 p-6 shadow-2xs">
                <div className="grid gap-1 pb-3 border-b border-[color:var(--color-border)]/60">
                  <h2 className="text-base font-bold text-ink">
                    {t.consentFormTitle}
                  </h2>
                  <p className="text-xs text-ink-muted">
                    {t.consentFormBody}
                  </p>
                </div>

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
              </section>
            </div>
          ) : (
            <section className="grid gap-4 rounded-2xl border border-brand-border bg-brand-soft p-5 shadow-2xs">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="inline-flex min-h-8 items-center gap-2 rounded-xl border border-brand-border bg-brand px-3 text-xs font-bold text-white shadow-2xs">
                    <ShieldCheck size={14} aria-hidden="true" />
                    {t.consentActive}
                  </span>
                  <p className="text-xs font-bold text-brand">
                    {t.consentActiveBody}
                  </p>
                </div>
                <ActionButton
                  type="button"
                  tone="secondary"
                  onClick={handleWithdrawConsent}
                  disabled={consentBusy}
                  className="hover:border-[color:var(--color-danger-text)] hover:bg-[color:var(--color-danger-bg)] hover:text-[color:var(--color-danger-text)]"
                >
                  {t.withdraw}
                </ActionButton>
              </div>
            </section>
          )}

          {consentMsg && (
            <p className={`rounded-xl border px-4 py-3 text-xs font-semibold ${
              consentMsg.includes("Failed") || consentMsg.includes("Could not")
                ? "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]"
                : "border-brand-border bg-brand-soft text-brand"
            }`}>
              {consentMsg}
            </p>
          )}

          <section className="grid gap-6 lg:grid-cols-2">
            <InfoCard title={t.overview}>
              <DetailRow label={t.childLabel} value={caseLabel(caseItem)} />
              <DetailRow label={t.age} value={ageLabel(caseItem, shared)} />
              <DetailRow label={t.language} value={caseItem.language ?? shared.languageNotRecorded} />
              <DetailRow label={t.referral} value={caseItem.notes?.trim() || t.referralEmpty} />
            </InfoCard>

            <InfoCard title={t.careTeam}>
              <DetailRow label={t.primaryClinician} value={primaryClinician(caseItem, shared)} />
              <DetailRow label={t.assignedClinicians} value={clinicianList(caseItem, shared)} />
              <p className="mt-4 text-sm leading-6 text-ink-muted">
                {t.careTeamNote}
              </p>
            </InfoCard>

            <InfoCard title={t.goals}>
              {goals.length ? (
                <div className="space-y-3">
                  {goals.map((goal) => (
                    <div key={goal.goal_id} className="rounded-card border border-line bg-surface-muted p-4">
                      <p className="font-medium text-ink">{goal.title}</p>
                      <p className="mt-1 text-sm text-ink-muted">
                        {goal.target?.trim() || t.goalTargetEmpty}
                      </p>
                      {goal.notes?.trim() ? (
                        <p className="mt-2 text-sm leading-6 text-ink-muted">{goal.notes}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-6 text-ink-muted">{t.goalsEmpty}</p>
              )}
            </InfoCard>
          </section>

          <InfoCard title={t.sessions}>
            {timeline.length ? (
              <SessionHistory timeline={timeline} />
            ) : (
              <p className="text-sm leading-6 text-ink-muted">{t.sessionsEmpty}</p>
            )}
          </InfoCard>

          <InfoCard title={t.languageProgress}>
            <LanguageProgressChart trends={model.featureTrend} />
          </InfoCard>

          <InfoCard title={t.reports}>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <StatusBadge status={caseItem.latest_report_status ?? "Not started"} />
                <p className="mt-3 text-sm leading-6 text-ink-muted">
                  {t.reportNote(safety.THERAPIST_SIGNOFF_CLAUSE)}
                </p>
              </div>
              <ActionButton href="/reports" tone="secondary">{t.openReports}</ActionButton>
            </div>
          </InfoCard>

          <section className="grid gap-6 lg:grid-cols-2">
            <InfoCard title={t.upcomingTasks}>
              <ul className="space-y-3 text-sm leading-6 text-ink-muted">
                {tasks.map((task) => (
                  <li key={task} className="flex gap-3">
                    <CircleDot size={18} className="mt-1 shrink-0 text-brand-strong" aria-hidden="true" />
                    <span>{task}</span>
                  </li>
                ))}
              </ul>
            </InfoCard>

            <InfoCard title={t.recentNotes}>
              <p className="text-sm leading-6 text-ink-muted">
                {caseItem.notes?.trim() || t.notesEmpty}
              </p>
            </InfoCard>
          </section>

          <SafetyNotice>
            {safety.DECISION_SUPPORT_ONLY} {t.safetyNote}
          </SafetyNotice>
        </div>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
            <h2 className="text-base font-bold text-ink pb-3 border-b border-[color:var(--color-border)]/60">{t.progress}</h2>
            <div className="mt-4 grid gap-3">
              {snapshot.map((item) => (
                <StatCard key={item.label} label={item.label} value={item.value} helper={item.helper} icon={Gauge} />
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
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

function HeaderMeta({
  label,
  value,
  icon: Icon
}: {
  label: string;
  value: string;
  icon: typeof Activity;
}) {
  return (
    <div className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface-muted)]/50 px-4 py-3 shadow-2xs">
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-ink-subtle">
        <Icon size={14} aria-hidden="true" className="text-brand" />
        <span>{label}</span>
      </div>
      <p className="mt-1.5 text-sm font-bold text-ink">{value}</p>
    </div>
  );
}

function InfoCard({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
      <h2 className="text-base font-bold text-ink pb-3 border-b border-[color:var(--color-border)]/60">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-[color:var(--color-border)]/60 py-3 last:border-b-0">
      <p className="text-xs font-bold uppercase tracking-wider text-ink-subtle">{label}</p>
      <p className="mt-1 text-sm font-medium leading-relaxed text-ink">{value}</p>
    </div>
  );
}
