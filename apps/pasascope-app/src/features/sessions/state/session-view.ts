export const sessionViews = ["intake", "transcript", "findings", "report"] as const;

export type SessionView = (typeof sessionViews)[number];

/**
 * What `?view=` may name. The four workflow steps, plus the conversation that
 * carries a session from audio to measures in the chat shell.
 */
export type SessionRouteView = SessionView | "chat";

export type SessionViewIdentity = {
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
};

const sessionIdPattern = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

export function resolveSessionView(value?: unknown): SessionView {
  return typeof value === "string" && sessionViews.includes(value as SessionView)
    ? (value as SessionView)
    : "intake";
}

export function resolveSessionRouteView(value?: unknown): SessionRouteView {
  return value === "chat" ? "chat" : resolveSessionView(value);
}

/** The full-page step a workflow view opens. Intake has no page of its own: it is the conversation. */
export function resolveWorkspaceFeature(view?: SessionView): "transcript" | "findings" {
  return view === "findings" ? "findings" : "transcript";
}

export function resolveLegacySessionHref(
  view: SessionView,
  sessionId?: unknown,
): string {
  return resolveSessionHref(view, sessionId);
}

export function resolveSessionHref(
  view: SessionRouteView,
  sessionId?: unknown,
  identity: SessionViewIdentity = {},
): string {
  if (
    typeof sessionId !== "string"
    || !sessionIdPattern.test(sessionId)
  ) {
    // No usable session yet: route through the deliberate start-session flow,
    // carrying the known case so the selector preselects it (Phase B pattern).
    if (identity.caseId && sessionIdPattern.test(identity.caseId)) {
      return `/cases?intent=start-session&case_id=${encodeURIComponent(identity.caseId)}`;
    }
    return "/cases?intent=start-session";
  }

  const params = new URLSearchParams({ view });
  if (identity.caseId) params.set("case_id", identity.caseId);
  if (identity.transcriptId) params.set("transcript_id", identity.transcriptId);
  if (identity.reportId) params.set("report_id", identity.reportId);
  return `/sessions/${encodeURIComponent(sessionId)}?${params.toString()}`;
}
