"use client";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { CaseDetail } from "@/features/cases/components/case-detail";
import { CaseList } from "@/features/cases/components/case-list";
import { StartSessionSelector } from "@/features/cases/components/start-session-selector";
import { useCasesWorkspace } from "@/features/cases/hooks/use-cases-workspace";
import { useConfirmedRuntimeSettings } from "@/lib/confirmed-runtime-settings";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

type CasesWorkspaceClientProps = {
  caseId?: string;
  intent?: "start-session";
  preselectedCaseId?: string;
  /** Search text carried in from the top-bar search (`/cases?q=`). */
  initialQuery?: string;
};

export function CasesWorkspaceClient({ caseId, intent, preselectedCaseId, initialQuery = "" }: CasesWorkspaceClientProps) {
  const model = useCasesWorkspace(caseId);
  const runtimeSettings = useConfirmedRuntimeSettings();
  const mockSession = useMockAccessSession();
  const supabaseSession = useSupabaseAccessSession();
  const confirmedRole = runtimeSettings?.auth_mode === "mock"
    ? mockSession?.role
    : runtimeSettings?.auth_mode === "supabase"
      && supabaseSession?.stage === "authenticated"
      ? supabaseSession.role
      : undefined;
  const canFilterByClinician = confirmedRole === "org_admin" || confirmedRole === "clinical_supervisor";
  const canCreateCase = confirmedRole === "therapist";

  if (model.status === "loading") {
    return <CaseListSkeleton />;
  }

  if (model.status === "unavailable") {
    return (
      <ErrorState
        className="bg-surface"
        title="Cases are unavailable"
        description="The backend cases service could not be reached. Try again when the service is available."
        retryLabel="Try again"
        onRetry={model.retry}
      />
    );
  }

  if (model.status === "error") {
    return (
      <ErrorState
        className="bg-surface"
        title="Case could not be loaded"
        description="The requested backend case was not returned. Check the case link or try again."
        retryLabel="Try again"
        onRetry={model.retry}
        action={<Button href="/cases" variant="ghost">Back to Cases</Button>}
      />
    );
  }

  if (model.status === "detail") {
    return <CaseDetail key={model.detail.caseItem.case_id} model={model.detail} />;
  }

  if (intent === "start-session") {
    return <StartSessionSelector cases={model.list.cases} preselectedCaseId={preselectedCaseId} />;
  }

  // Keyed by the incoming search so a new top-bar search replaces the list's own search text.
  return <CaseList key={initialQuery} model={model.list} canFilterByClinician={canFilterByClinician} canCreateCase={canCreateCase} initialQuery={initialQuery} />;
}

function CaseListSkeleton() {
  return (
    <section className="workspace-panel p-4" role="status" aria-live="polite">
      <span className="sr-only">Loading cases…</span>
      <div className="space-y-3 animate-pulse motion-reduce:animate-none" aria-hidden="true">
        <div className="h-12 rounded-card bg-surface-muted" />
        <div className="h-12 rounded-card bg-surface-muted" />
        <div className="h-12 rounded-card bg-surface-muted" />
      </div>
    </section>
  );
}
