import Link from "next/link";

import type { TodayWorkbenchViewState } from "@/features/work-queue/components/today-workbench-view";

export function TodayContextRail({ state, titleId }: { state: TodayWorkbenchViewState; titleId: string }) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-xs" aria-labelledby={titleId}>
      <div>
        <h2 id={titleId} className="text-base font-bold text-ink">Today context</h2>
      </div>
      {state.status === "loading" ? <p className="mt-4 text-sm text-ink-muted">Recent cases will appear in a moment.</p> : null}
      {state.status === "error" ? <p className="mt-4 rounded-xl border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">Connection unavailable — recent cases are not shown right now.</p> : null}
      {state.status === "ready" ? (
        <div className="mt-5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">Recent cases</h3>
          {state.model.recentCases.length ? (
            <ul className="mt-2 divide-y divide-line">
              {state.model.recentCases.map((caseItem) => (
                <li key={caseItem.caseId}>
                  <Link href={`/cases/${encodeURIComponent(caseItem.caseId)}`} className="flex min-h-11 items-center justify-between gap-3 py-3 text-sm transition hover:text-brand">
                    <span className="min-w-0">
                      <span className="block font-bold text-ink">{caseItem.caseLabel}</span>
                      <span className="block text-xs text-ink-muted">{caseItem.workflowStatus}</span>
                    </span>
                    <span aria-hidden="true" className="shrink-0 text-brand font-bold">→</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : <p className="mt-2 text-sm text-ink-muted">No recent cases yet.</p>}
        </div>
      ) : null}
    </section>
  );
}
