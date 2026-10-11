"use client";

import Link from "next/link";
import { Activity, FileCheck2, FolderOpen, ListChecks, MessagesSquare } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { LanguageProgressChart } from "@/features/dashboard/components/language-progress-chart";
import { dashboardMessages } from "@/features/dashboard/dashboard.messages";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { EVIDENCE_REVIEW_NOUN } from "@/lib/workflow-glossary";
import type { DashboardSummary } from "@/lib/workflow";

function consentLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function sessionStage(session: DashboardSummary["recent_sessions"][number]) {
  if (session.has_report) return "Report drafted";
  if (session.has_ml_review) return EVIDENCE_REVIEW_NOUN;
  if (session.has_features) return "Findings extracted";
  if (session.has_transcript) return "Transcript ready";
  return "Intake only";
}

export function PracticeDashboardView({ summary }: { summary: DashboardSummary }) {
  const t = useMessages(dashboardMessages);
  const { locale } = useLocale();
  const consentCounts = Object.entries(summary.cases.consent_counts).sort((a, b) => b[1] - a[1]);
  const reviewedSessions = summary.cases.with_latest_reviewed_session;

  return (
    <div className="min-w-0 space-y-6">
      <PageHeader
        eyebrow={t.eyebrow}
        title={t.title}
        description={t.description}
        meta={[
          summary.organization_id ? t.organization(summary.organization_id) : "",
          summary.generated_at ? t.updated(formatDate(summary.generated_at, locale)) : "",
        ].filter(Boolean)}
      />

      <section aria-labelledby="dashboard-stats" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <h2 id="dashboard-stats" className="sr-only">
          Caseload summary
        </h2>
        <StatCard
          label="Active cases"
          value={String(summary.cases.total)}
          helper={`${reviewedSessions} with a reviewed latest session`}
          icon={FolderOpen}
          tone="accent"
        />
        <StatCard
          label="Sessions"
          value={String(summary.sessions.total)}
          helper={`${summary.sessions.with_transcript} transcript · ${summary.sessions.with_features} features extracted`}
          icon={MessagesSquare}
          tone="neutral"
        />
        <StatCard
          label={EVIDENCE_REVIEW_NOUN}
          value={String(summary.sessions.with_ml_review)}
          helper="Sessions with an ML decision-support review"
          icon={ListChecks}
          tone="neutral"
        />
        <StatCard
          label="Reports"
          value={String(summary.reports.total)}
          helper={summary.reports.signoff_counts["Signed Off"]
            ? `${summary.reports.signoff_counts["Signed Off"]} signed off`
            : "None signed off yet"}
          icon={FileCheck2}
          tone={summary.reports.signoff_counts["Signed Off"] ? "success" : "neutral"}
        />
      </section>

      <section aria-labelledby="progress-heading" className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[color:var(--color-border)]/60">
          <div>
            <h2 id="progress-heading" className="text-base font-bold text-ink">
              Language progress
            </h2>
            <p className="mt-0.5 text-xs text-ink-muted">
              Track a language-sample feature across each case&apos;s sessions over time.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-soft border border-brand-border px-2.5 py-1 text-xs font-semibold text-brand">
            <Activity className="h-3.5 w-3.5" />
            Linguistic Trajectory
          </span>
        </div>
        <div className="pt-4">
          <LanguageProgressChart trends={summary.feature_trends} />
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section aria-labelledby="consent-heading" className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
          <h2 id="consent-heading" className="text-base font-bold text-ink pb-3 border-b border-[color:var(--color-border)]/60">
            Consent status
          </h2>
          {consentCounts.length ? (
            <ul className="mt-4 space-y-3">
              {consentCounts.map(([status, count]) => (
                <li key={status} className="flex items-center justify-between gap-3 text-sm rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
                  <span className="flex items-center gap-2 text-ink-muted font-medium">
                    <span className={`h-2 w-2 rounded-full ${status === "granted" ? "bg-brand" : "bg-[color:var(--color-warning-border)]"}`} />
                    {consentLabel(status)}
                  </span>
                  <span className="font-bold text-ink">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-ink-muted">No cases yet.</p>
          )}
        </section>

        <section aria-labelledby="pipeline-heading" className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
          <h2 id="pipeline-heading" className="text-base font-bold text-ink pb-1">
            Pipeline progress
          </h2>
          <p className="text-xs text-ink-muted pb-3 border-b border-[color:var(--color-border)]/60">
            Sessions that reached each stage of the analysis pipeline.
          </p>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-ink-muted font-medium">Transcript recorded</span>
              <span className="font-bold text-ink">{summary.sessions.with_transcript}</span>
            </li>
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-ink-muted font-medium">Features extracted</span>
              <span className="font-bold text-ink">{summary.sessions.with_features}</span>
            </li>
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-ink-muted font-medium">ML decision support</span>
              <span className="font-bold text-ink">{summary.sessions.with_ml_review}</span>
            </li>
            <li className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
              <span className="text-ink-muted font-medium">Report drafted</span>
              <span className="font-bold text-ink">{summary.sessions.with_report}</span>
            </li>
          </ul>
        </section>

        <section aria-labelledby="report-heading" className="rounded-2xl border border-line bg-surface p-6 shadow-2xs">
          <h2 id="report-heading" className="text-base font-bold text-ink pb-3 border-b border-[color:var(--color-border)]/60">
            Report sign-off
          </h2>
          {summary.reports.total ? (
            <ul className="mt-4 space-y-2.5 text-sm">
              {Object.entries(summary.reports.signoff_counts)
                .sort((a, b) => b[1] - a[1])
                .map(([status, count]) => (
                  <li key={status} className="flex items-center justify-between gap-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 px-3 py-2 border border-[color:var(--color-border)]/40">
                    <StatusBadge status={status} />
                    <span className="font-bold text-ink">{count}</span>
                  </li>
                ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm leading-6 text-ink-muted">No reports yet.</p>
          )}
        </section>
      </div>

      <section aria-labelledby="recent-heading" className="mt-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 id="recent-heading" className="text-base font-bold text-ink">
              Recent sessions
            </h2>
            <p className="text-xs text-ink-muted">Active pediatric assessment sessions and pipeline status</p>
          </div>
          <Link
            href="/cases"
            className="inline-flex min-h-10 items-center rounded-xl border border-line bg-white px-3.5 text-xs font-bold text-brand shadow-2xs transition hover:bg-brand-soft hover:border-brand-border"
          >
            View all cases
          </Link>
        </div>
        {summary.recent_sessions.length ? (
          <>
            <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-2xs hidden md:block">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line bg-[color:var(--color-surface-muted)]/60 text-left">
                    <th scope="col" className="px-5 py-3.5 font-bold text-ink text-xs uppercase tracking-wider">
                      Case
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-ink text-xs uppercase tracking-wider">
                      Date
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-ink text-xs uppercase tracking-wider">
                      Stage
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-ink text-xs uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-5 py-3.5 font-bold text-ink text-xs uppercase tracking-wider text-right">
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--color-border)]/60">
                  {summary.recent_sessions.map((session) => (
                    <tr key={session.session_id} className="transition-colors hover:bg-[color:var(--color-brand-soft)]/30">
                      <td className="px-5 py-2">
                        <Link
                          href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                          className="inline-flex min-h-10 min-w-10 items-center font-bold text-brand hover:underline"
                        >
                          {session.case_label}
                        </Link>
                      </td>
                      <td className="px-5 py-2 text-xs text-ink-muted font-mono">{session.session_date}</td>
                      <td className="px-5 py-2 text-xs font-medium text-ink">{sessionStage(session)}</td>
                      <td className="px-5 py-2">
                        <StatusBadge status={session.status} />
                      </td>
                      <td className="px-5 py-2 text-right">
                        <Link
                          href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                          className="inline-flex min-h-10 items-center rounded-xl border border-line bg-white px-3.5 text-xs font-bold text-brand shadow-2xs hover:bg-brand-soft hover:border-brand-border transition"
                        >
                          Open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="space-y-3 md:hidden">
              {summary.recent_sessions.map((session) => (
                <li key={session.session_id} className="rounded-2xl border border-line bg-surface p-4 shadow-2xs">
                  <div className="flex items-center justify-between gap-3">
                    <Link
                      href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                      className="inline-flex min-h-10 min-w-10 items-center font-bold text-brand hover:underline"
                    >
                      {session.case_label}
                    </Link>
                    <StatusBadge status={session.status} />
                  </div>
                  <p className="mt-2 text-xs text-ink-muted">
                    {session.session_date} · {sessionStage(session)}
                  </p>
                  <Link
                    href={`/sessions/${encodeURIComponent(session.session_id)}?case_id=${encodeURIComponent(session.case_id)}`}
                    className="mt-3 inline-flex min-h-10 w-full items-center justify-center rounded-xl bg-brand-soft text-xs font-bold text-brand border border-brand-border transition hover:bg-brand hover:text-white"
                  >
                    Open session
                  </Link>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div className="rounded-2xl border border-line bg-surface p-8 text-center text-sm text-ink-muted shadow-2xs">
            No sessions yet. Start a session from the Cases list to populate the pipeline.
          </div>
        )}
      </section>
    </div>
  );
}
