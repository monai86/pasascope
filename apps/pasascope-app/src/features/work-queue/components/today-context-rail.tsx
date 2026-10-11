"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import type { TodayWorkbenchViewState } from "@/features/work-queue/components/today-workbench-view";
import { todayMessages } from "@/features/work-queue/today.messages";
import { useMessages } from "@/i18n/locale-provider";

export function TodayContextRail({ state, titleId }: { state: TodayWorkbenchViewState; titleId: string }) {
  const t = useMessages(todayMessages).context;

  return (
    <section className="rounded-panel border border-line bg-surface p-5 shadow-soft" aria-labelledby={titleId}>
      <h2 id={titleId} className="text-base font-semibold text-ink">{t.title}</h2>
      {state.status === "loading" ? <p className="mt-4 text-sm text-ink-muted">{t.loading}</p> : null}
      {state.status === "error" ? (
        <p className="mt-4 rounded-control border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">
          {t.error}
        </p>
      ) : null}
      {state.status === "ready" ? (
        <div className="mt-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted">{t.recentCases}</h3>
          {state.model.recentCases.length ? (
            <ul className="mt-2 divide-y divide-line">
              {state.model.recentCases.map((caseItem) => (
                <li key={caseItem.caseId}>
                  <Link
                    href={`/cases/${encodeURIComponent(caseItem.caseId)}`}
                    className="group flex min-h-11 items-center justify-between gap-3 py-3 text-sm"
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-ink transition group-hover:text-brand">{caseItem.caseLabel}</span>
                      <span className="mt-1 block"><StatusBadge status={caseItem.workflowStatus} /></span>
                    </span>
                    <ChevronRight aria-hidden="true" size={18} className="shrink-0 text-brand" />
                  </Link>
                </li>
              ))}
            </ul>
          ) : <p className="mt-2 text-sm text-ink-muted">{t.empty}</p>}
        </div>
      ) : null}
    </section>
  );
}
