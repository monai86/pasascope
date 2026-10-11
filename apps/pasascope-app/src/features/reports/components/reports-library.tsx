"use client";

import { ExternalLink, FileText, Lock, RefreshCw, ShieldCheck } from "lucide-react";

import { DataTable } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { reportsMessages } from "@/features/reports/reports.messages";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import type { BackendReport } from "@/lib/workflow";

type ReportGroupKey = "review" | "regenerate" | "signed";

type ReportGroup = {
  key: ReportGroupKey;
  reports: BackendReport[];
  icon: typeof FileText;
};

type LibraryCopy = ReturnType<typeof useLibraryCopy>;

function useLibraryCopy() {
  const t = useMessages(reportsMessages);
  const { locale } = useLocale();
  return {
    t,
    date: (value?: string) => (value ? formatDate(value, locale) || t.unavailable : t.unavailable),
    title: (report: BackendReport) => report.title ?? report.report_type ?? report.report_id ?? t.untitled,
    action(report: BackendReport) {
      if (!report.session_id?.trim()) return t.actions.findSession;
      if (isSignedReport(report)) return t.actions.viewSigned;
      if (isStaleReport(report)) return t.actions.regenerate;
      if (`${report.status ?? ""}`.toLowerCase().includes("failed")) return t.actions.reviewBlocked;
      return t.actions.reviewDraft;
    },
  };
}

export function ReportsLibrary({ reports }: { reports: BackendReport[] }) {
  const copy = useLibraryCopy();
  const { t } = copy;
  const groups: ReportGroup[] = [
    { key: "review", reports: reports.filter((report) => !isSignedReport(report) && !isStaleReport(report)), icon: FileText },
    { key: "regenerate", reports: reports.filter(isStaleReport), icon: RefreshCw },
    { key: "signed", reports: reports.filter(isSignedReport), icon: Lock },
  ];

  return (
    <div className="space-y-5" aria-label={t.libraryLabel}>
      <Card className="p-5">
        <h2 className="text-lg font-semibold text-ink">{t.status.heading}</h2>
        <dl className="mt-4 grid gap-3 sm:grid-cols-3">
          <LibraryMetric label={t.status.needsReview} value={groups[0].reports.length} />
          <LibraryMetric label={t.status.needsRegeneration} value={groups[1].reports.length} />
          <LibraryMetric label={t.status.signed} value={groups[2].reports.length} signed />
        </dl>
        <p className="mt-4 rounded-control border border-[color:var(--color-attention-border)] bg-[color:var(--color-attention-bg)] p-3 text-sm font-medium text-[color:var(--color-warning-text)]">
          {t.status.note}
        </p>
      </Card>

      {groups.map((group) => {
        const Icon = group.icon;
        const groupCopy = t.groups[group.key];
        return (
          <section key={group.key} aria-labelledby={`report-group-${group.key}`} className="min-w-0 rounded-panel border border-line bg-surface p-5 shadow-soft">
            <div className="flex items-start gap-3">
              <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-brand-soft text-brand">
                <Icon size={20} />
              </span>
              <div>
                <h2 id={`report-group-${group.key}`} className="text-xl font-semibold text-ink">{groupCopy.title}</h2>
                <p className="mt-1 text-sm leading-6 text-ink-muted">{groupCopy.description}</p>
              </div>
            </div>

            {group.reports.length ? (
              <>
                <div className="mt-4 hidden xl:block">
                  <DataTable
                    caption={t.table.caption(groupCopy.title)}
                    rowTestId="report-library-row"
                    columns={[
                      { key: "report", header: t.table.report },
                      { key: "updated", header: t.table.updated },
                      { key: "version", header: t.table.version },
                      { key: "status", header: t.table.status },
                      { key: "action", header: t.table.action }
                    ]}
                    rows={group.reports.map((report) => ({
                      id: report.report_id ?? `${report.session_id}-${report.title}`,
                      report: (
                        <div className="min-w-0">
                          <p className="truncate font-medium text-ink">{copy.title(report)}</p>
                          <p className="mt-0.5 truncate text-xs text-ink-muted">
                            {t.caseAndSession(report.case_id ?? t.unavailable, report.session_id ?? t.unavailable)}
                          </p>
                        </div>
                      ),
                      updated: copy.date(report.updated_at),
                      version: report.version == null ? t.unavailable : t.versionLabel(report.version),
                      status: <StatusBadge status={reportStatus(report)} />,
                      action: <ReportActionLink report={report} copy={copy} />,
                    }))}
                  />
                </div>
                <ul className="mt-4 space-y-0 xl:hidden" aria-label={groupCopy.title}>
                  {group.reports.map((report) => (
                    <li key={report.report_id ?? `${report.session_id}-${report.title}`} data-testid="report-library-row" className="border-b border-line py-3 last:border-b-0">
                      <ReportLibraryMobileRow report={report} copy={copy} />
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-4 rounded-card border border-dashed border-line-strong bg-surface-soft p-4 text-sm text-ink-muted">
                {t.emptyGroup}
              </p>
            )}
          </section>
        );
      })}
    </div>
  );
}

function ReportActionLink({ report, copy }: { report: BackendReport; copy: LibraryCopy }) {
  return (
    <Button href={reportHref(report)} variant="secondary" className="shrink-0">
      {copy.action(report)}
      <ExternalLink size={16} aria-hidden="true" />
    </Button>
  );
}

function ReportLibraryMobileRow({ report, copy }: { report: BackendReport; copy: LibraryCopy }) {
  const { t } = copy;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="min-w-0 truncate font-semibold text-ink">{copy.title(report)}</h3>
          <StatusBadge status={reportStatus(report)} />
        </div>
        <p className="mt-0.5 truncate text-xs text-ink-muted">
          {t.caseOnly(report.case_id ?? t.unavailable)} · {copy.date(report.updated_at)}
          {report.version == null ? "" : ` · ${t.versionLabel(report.version)}`}
        </p>
      </div>
      <ReportActionLink report={report} copy={copy} />
    </div>
  );
}

function LibraryMetric({ label, value, signed = false }: { label: string; value: number; signed?: boolean }) {
  return (
    <div className="rounded-card border border-line bg-surface-soft p-3">
      <dt className="text-sm font-medium text-ink-muted">{label}</dt>
      <dd className="mt-1 flex items-center gap-2 font-display text-2xl font-semibold text-ink">
        {signed ? <ShieldCheck size={18} aria-hidden="true" className="text-brand" /> : null}
        {value}
      </dd>
    </div>
  );
}

function reportStatus(report: BackendReport) {
  return isSignedReport(report) ? "Signed Off" : isStaleReport(report) ? "Stale" : report.status ?? "Draft";
}

function isSignedReport(report: BackendReport) {
  const status = `${report.status ?? ""} ${report.therapist_signoff_status ?? ""}`.toLowerCase();
  return status.includes("signed") || status.includes("final");
}

function isStaleReport(report: BackendReport) {
  return `${report.status ?? ""}`.trim().toLowerCase() === "stale";
}

function reportHref(report: BackendReport) {
  return resolveSessionHref("report", report.session_id?.trim(), {
    caseId: report.case_id,
    reportId: report.report_id,
  });
}
