"use client";

import { LockKeyhole, WifiOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PracticeDashboardView } from "@/features/dashboard/components/practice-dashboard-view";
import { dashboardMessages } from "@/features/dashboard/dashboard.messages";
import { useMessages } from "@/i18n/locale-provider";
import { ApiError } from "@/lib/api";
import { getDashboardSummary, type DashboardSummary } from "@/lib/workflow";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";

type DashboardLoad = { kind: "summary"; summary: DashboardSummary } | { kind: "denied" };

// The summary is loaded in the browser: the session token lives there, so a
// server-side fetch could only ever reach the API unauthenticated.
async function loadDashboard(_identity: string, signal: AbortSignal): Promise<DashboardLoad> {
  try {
    return { kind: "summary", summary: await getDashboardSummary({ signal }) };
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return { kind: "denied" };
    }
    throw error;
  }
}

export function PracticeDashboardClient() {
  const t = useMessages(dashboardMessages);
  const resource = useRemoteResource("dashboard:summary", loadDashboard);

  if (resource.status === "success" && resource.data.kind === "summary") {
    return <PracticeDashboardView summary={resource.data.summary} />;
  }
  if (resource.status === "loading" || resource.status === "idle") {
    return (
      <div className="mx-auto flex min-h-[50dvh] w-full max-w-4xl items-center px-4 py-10 sm:px-6">
        <p role="status" className="text-sm text-ink-muted">{t.loading}</p>
      </div>
    );
  }
  return <DashboardUnavailable denied={resource.status === "success"} />;
}

function DashboardUnavailable({ denied }: { denied: boolean }) {
  const t = useMessages(dashboardMessages).unavailable;

  return (
    <div className="mx-auto flex min-h-[50dvh] w-full max-w-3xl items-center py-6">
      <section className="w-full rounded-panel border border-line bg-surface p-6 text-ink shadow-soft sm:p-8" role="alert">
        <Badge tone="attention" icon={denied ? LockKeyhole : WifiOff}>{denied ? t.signInChip : t.offlineChip}</Badge>
        <p className="sr-only">{t.label}</p>
        <h1 className="mt-3 text-2xl font-semibold text-ink sm:text-3xl">{t.title}</h1>
        <p className="mt-2 text-sm leading-6 text-ink-muted">{denied ? t.denied : t.offline}</p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button href="/today">{t.backToToday}</Button>
          <Button href="/cases" variant="secondary">{t.openCases}</Button>
        </div>
      </section>
    </div>
  );
}
