"use client";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { CaseDetail } from "@/features/cases/components/case-detail";
import { CaseList } from "@/features/cases/components/case-list";
import { StartSessionSelector } from "@/features/cases/components/start-session-selector";
import { casesMessages } from "@/features/cases/cases.messages";
import { useCasesWorkspace } from "@/features/cases/hooks/use-cases-workspace";
import { useMessages } from "@/i18n/locale-provider";
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
  const t = useMessages(casesMessages).workspace;
  const runtimeSettings = useConfirmedRuntimeSettings();
  const mockSession = useMockAccessSession();
  const supabaseSession = useSupabaseAccessSession();
  const confirmedRole = runtimeSettings?.auth_mode === "mock"
    ? mockSession?.role
    : runtimeSettings?.auth_mode === "supabase"
      && supabaseSession?.stage === "authenticated"
      ? supabaseSession.role
      : undefined;
  const canFilterByClinician = confirmedRole === "clinical_supervisor";
  const canCreateCase = confirmedRole === "therapist";

  if (model.status === "loading") {
    return <CaseListSkeleton />;
  }

  if (model.status === "unavailable") {
    return (
      <ErrorState
        className="bg-surface"
        title={t.unavailableTitle}
        description={t.unavailableBody}
        retryLabel={t.retry}
        onRetry={model.retry}
      />
    );
  }

  if (model.status === "error") {
    return (
      <ErrorState
        className="bg-surface"
        title={t.errorTitle}
        description={t.errorBody}
        retryLabel={t.retry}
        onRetry={model.retry}
        action={<Button href="/cases" variant="ghost">{t.backToCases}</Button>}
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
  const t = useMessages(casesMessages).workspace;
  return (
    <section className="workspace-panel p-4" role="status" aria-live="polite">
      <span className="sr-only">{t.loading}</span>
      <div className="space-y-3 animate-pulse motion-reduce:animate-none" aria-hidden="true">
        <div className="h-12 rounded-card bg-surface-muted" />
        <div className="h-12 rounded-card bg-surface-muted" />
        <div className="h-12 rounded-card bg-surface-muted" />
      </div>
    </section>
  );
}
