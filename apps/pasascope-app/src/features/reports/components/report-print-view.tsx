"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, FileText, Printer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { reportsMessages } from "@/features/reports/reports.messages";
import { sessionReportService } from "@/features/sessions/report/session-report-service";
import { useMessages } from "@/i18n/locale-provider";

type PrintState =
  | { status: "loading" }
  | { status: "failed" }
  | { status: "ready"; html: string };

/**
 * Prints the signed report the backend holds. The page shows exactly the HTML
 * the export endpoint returns for this report id and nothing else, so what is
 * printed is the signed record. The backend refuses unsigned and stale
 * reports, which this page reports as a failure rather than filling in.
 */
export function ReportPrintView({ reportId }: { reportId?: string }) {
  const t = useMessages(reportsMessages).print;
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<PrintState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!reportId) return;
    let cancelled = false;
    setState({ status: "loading" });
    sessionReportService
      .export(reportId, "html")
      .then((exported) => {
        if (!cancelled) setState({ status: "ready", html: exported.content });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "failed" });
      });
    return () => {
      cancelled = true;
    };
  }, [reportId, attempt]);

  const print = useCallback(() => {
    frameRef.current?.contentWindow?.print();
  }, []);

  if (!reportId) {
    return (
      <main className="app-canvas flex min-h-dvh items-center justify-center p-4">
        <EmptyState
          className="w-full max-w-xl shadow-lift"
          icon={FileText}
          title={t.missing.title}
          description={t.missing.description}
          action={<Button href="/reports">{t.missing.action}</Button>}
        />
      </main>
    );
  }

  return (
    <main className="app-canvas flex min-h-dvh flex-col gap-4 p-4 sm:p-6">
      <header className="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-between gap-3 print:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <Button href="/reports" variant="ghost" icon={ArrowLeft}>
            {t.back}
          </Button>
          <h1 className="truncate text-xl font-semibold text-ink">{t.title}</h1>
        </div>
        <Button icon={Printer} onClick={print} disabled={state.status !== "ready"}>
          {t.print}
        </Button>
      </header>

      <div className="mx-auto w-full max-w-4xl flex-1">
        {state.status === "loading" ? (
          <p role="status" aria-live="polite" className="rounded-panel border border-line bg-surface p-6 text-sm font-medium text-ink-muted shadow-soft">
            {t.loading}
          </p>
        ) : null}
        {state.status === "failed" ? (
          <ErrorState
            className="bg-surface"
            title={t.failed.title}
            description={t.failed.description}
            retryLabel={t.failed.retry}
            onRetry={() => setAttempt((current) => current + 1)}
          />
        ) : null}
        {state.status === "ready" ? (
          // The report markup is shown in a sandbox with scripts disabled.
          // `allow-modals` lets this page open the print dialog for the frame.
          <iframe
            ref={frameRef}
            title={t.frameTitle}
            srcDoc={state.html}
            sandbox="allow-same-origin allow-modals"
            data-testid="signed-report-frame"
            className="h-[calc(100dvh-9rem)] min-h-[32rem] w-full rounded-panel border border-line bg-white shadow-soft"
          />
        ) : null}
      </div>
    </main>
  );
}
