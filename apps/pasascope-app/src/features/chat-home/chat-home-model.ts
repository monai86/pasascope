import { resolveSessionHref } from "@/features/sessions/state/session-view";
import type { BackendCase, DashboardRecentSession } from "@/lib/workflow";

/**
 * Where a session stands, named by what it is waiting for. The view turns a
 * stage into words in the interface language, so this model carries no
 * display text of its own.
 */
export type HomeSessionStage =
  | "audio"
  | "processing"
  | "failed"
  | "transcript"
  | "measures"
  | "report";

/** Navy: the therapist's move. Sky: the system is working. Amber: something went wrong. */
export type HomeSessionTone = "action" | "progress" | "attention";

export type HomeSessionRow = {
  sessionId: string;
  caseId: string;
  caseLabel: string;
  sessionDate: string;
  stage: HomeSessionStage;
  tone: HomeSessionTone;
  href: string;
};

export type ChatHomeModel = {
  rows: HomeSessionRow[];
  /** The most recent session with a step still open, offered as "pick up where you left off". */
  resume: HomeSessionRow | null;
};

function stageOf(session: DashboardRecentSession): HomeSessionStage {
  if (session.has_report) return "report";
  if (session.has_features) return "measures";
  if (session.has_transcript) return "transcript";
  const status = session.status.toLowerCase();
  if (status === "processing") return "processing";
  if (status === "failed") return "failed";
  return "audio";
}

function toneOf(stage: HomeSessionStage): HomeSessionTone {
  if (stage === "processing") return "progress";
  if (stage === "failed") return "attention";
  return "action";
}

export function buildChatHome(recentSessions: readonly DashboardRecentSession[]): ChatHomeModel {
  const rows = recentSessions
    .filter((session) => session.status.toLowerCase() !== "withdrawn")
    .map((session): HomeSessionRow => {
      const stage = stageOf(session);
      return {
        sessionId: session.session_id,
        caseId: session.case_id,
        caseLabel: session.case_label,
        sessionDate: session.session_date,
        stage,
        tone: toneOf(stage),
        href: resolveSessionHref("chat", session.session_id, { caseId: session.case_id }),
      };
    });

  return { rows, resume: rows.find((row) => row.stage !== "report") ?? null };
}

function matches(haystack: Array<string | undefined>, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return haystack.some((value) => value?.toLowerCase().includes(needle));
}

export function filterSessionRows(rows: readonly HomeSessionRow[], query: string): HomeSessionRow[] {
  return rows.filter((row) => matches([row.caseLabel], query));
}

export function caseLabel(caseItem: BackendCase): string {
  return caseItem.nickname ?? caseItem.child_code ?? caseItem.display_label ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

export function caseCode(caseItem: BackendCase): string {
  return caseItem.child_code ?? caseItem.anonymized_child_code ?? caseItem.case_id;
}

export function hasConsent(caseItem: BackendCase): boolean {
  return caseItem.consent_status?.toLowerCase() === "granted";
}

export function filterCases(cases: readonly BackendCase[], query: string): BackendCase[] {
  return cases.filter((caseItem) =>
    matches([caseItem.nickname, caseItem.child_code, caseItem.display_label, caseItem.anonymized_child_code], query),
  );
}
