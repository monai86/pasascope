"use client";

import dynamic from "next/dynamic";

import { SkeletonLine } from "@/components/skeleton";
import { resolveWorkspaceFeature, type SessionRouteView } from "@/features/sessions/state/session-view";
import { SessionChatWorkspace, SessionWorkflowWorkspace } from "@/features/sessions/components/session-workspace-model";
import { useChatShellEnabled } from "@/lib/ui-shell";

const SessionReportView = dynamic(
  () => import("@/features/sessions/report/session-report-view").then((module) => module.SessionReportView),
  { loading: SessionWorkspaceLoading },
);

export type SessionWorkspaceProps = {
  sessionId?: string;
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
  view?: SessionRouteView;
  mode?: string;
};

export function SessionWorkspace({ view = "intake", ...props }: SessionWorkspaceProps) {
  const chatShell = useChatShellEnabled();
  if (view === "report") {
    return <SessionReportView {...props} />;
  }
  // In the chat shell the conversation is how a session starts, so it also
  // answers links that still point at Intake. Without the chat shell,
  // `?view=chat` falls back to Intake like any other unknown view.
  if (chatShell && (view === "chat" || view === "intake")) {
    return <SessionChatWorkspace {...props} />;
  }
  return <SessionWorkflowWorkspace {...props} view={view === "chat" ? "intake" : view} />;
}

function SessionWorkspaceLoading() {
  return (
    <div
      className="rounded-panel border border-line bg-surface p-6"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Loading session workspace…</span>
      <SkeletonLine className="w-1/3" />
      <div className="mt-5 space-y-3" aria-hidden="true">
        <SkeletonLine className="w-full" />
        <SkeletonLine className="w-5/6" />
        <SkeletonLine className="w-2/3" />
      </div>
    </div>
  );
}

export { resolveWorkspaceFeature };
