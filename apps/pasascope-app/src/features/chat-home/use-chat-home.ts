"use client";

import { useCallback, useMemo, useState } from "react";

import { buildChatHome, type ChatHomeModel } from "@/features/chat-home/chat-home-model";
import type { BackendCase, DashboardRecentSession } from "@/lib/workflow";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";

type ChatHomePayload = {
  recentSessions: DashboardRecentSession[];
  cases: BackendCase[];
};

export type ChatHomeState =
  | { status: "loading" }
  | { status: "error"; retry: () => void }
  | { status: "ready"; model: ChatHomeModel; cases: BackendCase[]; reload: () => void };

async function loadChatHome(_identity: string, signal: AbortSignal): Promise<ChatHomePayload> {
  const { getDashboardSummary, listBackendCases } = await import("@/lib/workflow");
  const [summary, cases] = await Promise.all([getDashboardSummary({ signal }), listBackendCases({ signal })]);
  // A malformed payload is an error, never an inferred empty workspace.
  if (!Array.isArray(summary?.recent_sessions) || !Array.isArray(cases)) {
    throw new Error("Chat home payload did not match the summary/cases contract.");
  }
  return { recentSessions: summary.recent_sessions, cases };
}

/**
 * Recent sessions and the caller's cases, for the chat home screen. A reload
 * keeps showing what was last read until the new answer arrives, so a
 * conversation in progress on the page is not torn down under the therapist.
 */
export function useChatHome(): ChatHomeState {
  const [requestVersion, setRequestVersion] = useState(0);
  const resource = useRemoteResource(`chat-home:${requestVersion}`, loadChatHome);
  const reload = useCallback(() => setRequestVersion((current) => current + 1), []);
  const fresh = resource.status === "success" || resource.status === "stale" ? resource.data : null;
  const [kept, setKept] = useState<ChatHomePayload | null>(null);
  if (fresh && fresh !== kept) setKept(fresh);
  const data = fresh ?? kept;
  const model = useMemo(() => (data ? buildChatHome(data.recentSessions) : null), [data]);

  if (data && model) return { status: "ready", model, cases: data.cases, reload };
  if (resource.status === "error" || resource.status === "unavailable") return { status: "error", retry: reload };
  return { status: "loading" };
}
