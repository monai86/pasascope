import { resolveSessionHref } from "@/features/sessions/state/session-view";
import type { BackendCase, BackendReport } from "@/lib/workflow";

export type TodayQueueGroupKey =
  | "needs_action"
  | "processing"
  | "ready_for_review"
  | "ready_for_signoff"
  | "recently_completed";

/**
 * What the next step for a case is. The view turns a kind into its task
 * name, reason and action label in the interface language, so this model
 * carries no display text of its own.
 */
export type TodayTaskKind =
  | "report_regeneration"
  | "report_safety_review"
  | "signed_report"
  | "report_signoff"
  | "report_review"
  | "session_processing"
  | "transcript_review_attested"
  | "transcript_review"
  | "session_followup"
  | "session_intake"
  | "start_session";

export type TodayQueueItem = {
  id: string;
  caseId: string;
  caseLabel: string;
  sessionDate?: string;
  kind: TodayTaskKind;
  workflowStatus: string;
  /** Lower-cased backend priority, e.g. "low", "moderate", "high". */
  reviewPriority: string;
  group: TodayQueueGroupKey;
  href: string;
};

export type TodayRecentCase = {
  caseId: string;
  caseLabel: string;
  latestActivity?: string;
  workflowStatus: string;
};

export type TodayWorkbenchModel = {
  items: TodayQueueItem[];
  recentCases: TodayRecentCase[];
  summary: {
    needsAction: number;
    readyForReview: number;
    readyForSignoff: number;
  };
};

/** Queue groups in the order they are shown and ranked. */
export const todayQueueGroups: readonly TodayQueueGroupKey[] = [
  "needs_action",
  "processing",
  "ready_for_review",
  "ready_for_signoff",
  "recently_completed",
];

const groupRank = new Map(todayQueueGroups.map((group, index) => [group, index]));

export function buildTodayWorkbench(
  cases: BackendCase[],
  reports: BackendReport[],
): TodayWorkbenchModel {
  const latestReportByCase = latestReportsByCase(reports);
  const items = cases
    .map((caseItem) => buildCaseQueueItem(caseItem, latestReportByCase.get(caseItem.case_id)))
    .sort((left, right) => {
      const groupDifference = (groupRank.get(left.group) ?? 0) - (groupRank.get(right.group) ?? 0);
      if (groupDifference !== 0) return groupDifference;
      return timestamp(right.sessionDate) - timestamp(left.sessionDate);
    });

  const recentCases = [...cases]
    .sort((left, right) => timestamp(right.updated_at ?? right.latest_session_date) - timestamp(left.updated_at ?? left.latest_session_date))
    .slice(0, 4)
    .map((caseItem) => ({
      caseId: caseItem.case_id,
      caseLabel: caseLabel(caseItem),
      latestActivity: caseItem.updated_at ?? caseItem.latest_session_date,
      workflowStatus: normalizedDisplayStatus(caseItem.latest_session_status),
    }));

  return {
    items,
    recentCases,
    summary: {
      needsAction: items.filter((item) => item.group === "needs_action").length,
      readyForReview: items.filter((item) => item.group === "ready_for_review").length,
      readyForSignoff: items.filter((item) => item.group === "ready_for_signoff").length,
    },
  };
}

function buildCaseQueueItem(caseItem: BackendCase, report?: BackendReport): TodayQueueItem {
  const reportStatus = normalizeStatus(report?.status ?? caseItem.latest_report_status);
  const sessionStatus = normalizeStatus(caseItem.latest_session_status);
  const base = {
    id: report?.report_id ? `report:${report.report_id}` : `case:${caseItem.case_id}`,
    caseId: caseItem.case_id,
    caseLabel: caseLabel(caseItem),
    sessionDate: caseItem.latest_session_date,
    reviewPriority: normalizeStatus(caseItem.review_priority) || "low",
  };

  if (reportStatus === "stale") {
    return {
      ...base,
      kind: "report_regeneration",
      workflowStatus: "Stale",
      group: "needs_action",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (isFailed(reportStatus)) {
    return {
      ...base,
      kind: "report_safety_review",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      group: "needs_action",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (isSigned(reportStatus)) {
    return {
      ...base,
      kind: "signed_report",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      group: "recently_completed",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (report && isReadyForSignoff(reportStatus, report.therapist_signoff_status)) {
    return {
      ...base,
      kind: "report_signoff",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      group: "ready_for_signoff",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (report && ["draft", "needs review", "needs_review"].includes(reportStatus)) {
    return {
      ...base,
      kind: "report_review",
      workflowStatus: normalizedDisplayStatus(reportStatus),
      group: "ready_for_review",
      href: reportHref(report, caseItem.case_id),
    };
  }
  if (sessionStatus === "processing") {
    return {
      ...base,
      kind: "session_processing",
      workflowStatus: "Processing",
      group: "processing",
      href: caseHref(caseItem.case_id),
    };
  }
  if (["needs review", "needs_review", "attested", "ready"].includes(sessionStatus)) {
    return {
      ...base,
      kind: sessionStatus === "attested" ? "transcript_review_attested" : "transcript_review",
      workflowStatus: normalizedDisplayStatus(sessionStatus),
      group: "ready_for_review",
      href: caseHref(caseItem.case_id),
    };
  }
  if (isFailed(sessionStatus)) {
    return {
      ...base,
      kind: "session_followup",
      workflowStatus: normalizedDisplayStatus(sessionStatus),
      group: "needs_action",
      href: caseHref(caseItem.case_id),
    };
  }
  return {
    ...base,
    kind: caseItem.latest_session_date ? "session_intake" : "start_session",
    workflowStatus: normalizedDisplayStatus(caseItem.latest_session_status || "Not started"),
    group: "needs_action",
    href: caseItem.latest_session_date ? caseHref(caseItem.case_id) : `/cases?intent=start-session&case_id=${encodeURIComponent(caseItem.case_id)}`,
  };
}

function latestReportsByCase(reports: BackendReport[]) {
  const result = new Map<string, BackendReport>();
  for (const report of reports) {
    if (!report.case_id) continue;
    const existing = result.get(report.case_id);
    if (!existing || timestamp(report.updated_at ?? report.created_at) >= timestamp(existing.updated_at ?? existing.created_at)) {
      result.set(report.case_id, report);
    }
  }
  return result;
}

function reportHref(report: BackendReport | undefined, caseId: string) {
  return resolveSessionHref("report", report?.session_id?.trim(), {
    caseId,
    reportId: report?.report_id,
  });
}

function caseHref(caseId: string) {
  return `/cases/${encodeURIComponent(caseId)}`;
}

function caseLabel(caseItem: BackendCase) {
  return caseItem.anonymized_child_code
    || caseItem.child_code
    || caseItem.display_label
    || `Case ${caseItem.case_id.slice(-6)}`;
}

function normalizeStatus(value?: string) {
  return `${value ?? ""}`.trim().toLowerCase();
}

function normalizedDisplayStatus(value?: string) {
  const normalized = `${value ?? ""}`.trim().replaceAll("_", " ");
  if (!normalized) return "Not started";
  return normalized.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isFailed(status: string) {
  return status.includes("failed") || status.includes("blocked") || status === "withdrawn";
}

function isSigned(status: string) {
  return status.includes("signed") || status.includes("finalized");
}

function isReadyForSignoff(status: string, signoffStatus?: string) {
  const signoff = normalizeStatus(signoffStatus);
  return status === "ready" || status === "reviewed" || signoff.includes("ready");
}

function timestamp(value?: string) {
  if (!value) return 0;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}
