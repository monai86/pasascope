"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText } from "lucide-react";

import { BackendAvailabilityBanner, useBackendAvailability } from "@/components/backend-availability-banner";
import { Skeleton } from "@/components/skeleton";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SafetyNote } from "@/components/workbench-ui";
import { ReportsLibrary } from "@/features/reports/components/reports-library";
import { reportsMessages } from "@/features/reports/reports.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
import { listBackendReports, type BackendReport } from "@/lib/workflow";

export function ReportsWorkspaceClient() {
  const t = useMessages(reportsMessages);
  const safety = useSafetyCopy();
  const { backendUnavailable, setBackendUnavailable } = useBackendAvailability();
  const [reports, setReports] = useState<BackendReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const loaded = await listBackendReports();
        if (cancelled) return;
        setReports(loaded);
        setBackendUnavailable(false);
      } catch {
        if (cancelled) return;
        setBackendUnavailable(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [attempt, setBackendUnavailable]);

  const retry = useCallback(() => {
    setLoading(true);
    setAttempt((current) => current + 1);
  }, []);

  return (
    <div className="space-y-5">
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-ink">{t.title}</h1>
          <p className="mt-1.5 max-w-[70ch] text-sm leading-relaxed text-ink-muted">{t.description}</p>
        </div>
        <Button href="/cases?intent=start-session" variant="secondary" className="w-full shrink-0 sm:w-auto">
          {t.startSession}
        </Button>
      </header>

      {loading ? (
        <Card className="p-5" role="status" aria-live="polite">
          <span className="sr-only">{t.loading}</span>
          <Skeleton className="h-6 w-2/5" />
          <div className="mt-4 grid gap-3 sm:grid-cols-3" aria-hidden="true">
            {[0, 1, 2].map((item) => <Skeleton key={item} className="h-16" />)}
          </div>
          <div className="mt-5 space-y-3" aria-hidden="true">
            {[0, 1, 2].map((item) => <Skeleton key={item} className="h-14 w-full" />)}
          </div>
        </Card>
      ) : null}

      {!loading && backendUnavailable ? (
        <ErrorState
          className="bg-surface"
          title={t.loadFailed.title}
          description={t.loadFailed.description}
          retryLabel={t.loadFailed.retry}
          onRetry={retry}
        />
      ) : null}

      {!loading && !backendUnavailable && reports.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={t.empty.title}
          description={t.empty.description}
          action={<Button href="/cases?intent=start-session">{t.empty.action}</Button>}
        />
      ) : null}

      {!loading && !backendUnavailable && reports.length > 0 ? <ReportsLibrary reports={reports} /> : null}

      <SafetyNote>{safety.EXPORT_ELIGIBILITY_NOTE}</SafetyNote>
    </div>
  );
}
