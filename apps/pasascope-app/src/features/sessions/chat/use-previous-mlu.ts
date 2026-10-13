"use client";

import type { DashboardFeatureTrends } from "@/lib/workflow";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";

const MLU_KEY = "mlu_words";

/**
 * The MLU of the session before this one in the same case, from the points
 * the backend computed. `null` when this is the first session with measures,
 * or when either value is missing.
 */
export function previousMluOf(trends: DashboardFeatureTrends, sessionId: string): number | null {
  for (const series of trends.cases ?? []) {
    const index = series.points.findIndex((point) => point.session_id === sessionId);
    if (index <= 0) continue;
    const value = series.points[index - 1]?.values?.[MLU_KEY];
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }
  return null;
}

async function loadTrend(identity: string, signal: AbortSignal): Promise<DashboardFeatureTrends | null> {
  const [caseId] = identity.split("|");
  if (!caseId) return null;
  const { getCaseFeatureTrend } = await import("@/lib/workflow");
  return getCaseFeatureTrend(caseId, { signal });
}

/**
 * Reads the previous session's MLU once measures exist. `featureSetId` is part
 * of the identity so a fresh extraction reads the trend again.
 */
export function usePreviousMlu(caseId: string | undefined, sessionId: string | undefined, featureSetId: string | undefined): number | null {
  const enabled = Boolean(caseId && sessionId && featureSetId);
  const resource = useRemoteResource(enabled ? `${caseId}|${featureSetId}` : "|", loadTrend);
  if (!enabled || !sessionId || resource.status !== "success" || !resource.data) return null;
  return previousMluOf(resource.data, sessionId);
}
