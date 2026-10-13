import { AppShell } from "@/components/app-shell";
import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

type CasesPageProps = {
  searchParams?: Promise<{ intent?: string | string[]; case_id?: string | string[]; q?: string | string[] }>;
};

export default async function CasesPage({ searchParams }: CasesPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const intent = resolvedSearchParams?.intent === "start-session" ? "start-session" : undefined;
  const caseIdParam = resolvedSearchParams?.case_id;
  const preselectedCaseId = typeof caseIdParam === "string" && caseIdParam.trim()
    ? caseIdParam
    : undefined;

  const queryParam = resolvedSearchParams?.q;
  const initialQuery = typeof queryParam === "string" ? queryParam.trim().slice(0, 120) : "";

  return (
    <AppShell active="Cases">
      <CasesWorkspaceClient intent={intent} preselectedCaseId={preselectedCaseId} initialQuery={initialQuery} />
    </AppShell>
  );
}
