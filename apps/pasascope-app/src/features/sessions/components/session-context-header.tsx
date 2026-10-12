"use client";

import Link from "next/link";
import { Check } from "lucide-react";

import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageHeader } from "@/components/page-header";
import { useMessages } from "@/i18n/locale-provider";
import { sessionMessages } from "@/features/sessions/session.messages";
import {
  resolveSessionHref,
  sessionViews,
  type SessionView,
} from "@/features/sessions/state/session-view";

export type SessionDataMode = "backend" | "local_draft" | "unavailable";

export type SessionContext = {
  sessionId?: string;
  caseId?: string;
  caseLabel?: string;
  sourceLabel?: string;
  consentStatus?: string;
  workflowStatus?: string;
  dataMode: SessionDataMode;
  activeView: SessionView;
  /**
   * Which steps the session has actually finished, from persisted workflow
   * state. A step is ticked only when this says so; where it is absent
   * nothing is ticked, because a step's position proves nothing about it.
   */
  completion?: Partial<Record<SessionView, boolean>>;
};

export type SessionContextHeaderProps = {
  title: string;
  description: string;
  meta?: string[];
  context: SessionContext;
  density?: "default" | "compact";
};

export function SessionContextHeader({
  title,
  description,
  meta,
  context,
  density = "default",
}: SessionContextHeaderProps) {
  const t = useMessages(sessionMessages);
  const h = t.header;
  const displayValue = (value?: string) => value?.trim() || h.unavailable;
  const details = [
    { label: h.fields.case, value: displayValue(context.caseLabel) },
    { label: h.fields.session, value: displayValue(context.sessionId) },
    { label: h.fields.source, value: displayValue(context.sourceLabel) },
    { label: h.fields.consent, value: context.consentStatus?.trim() ? h.consent(context.consentStatus.trim()) : h.unavailable },
    { label: h.fields.status, value: displayValue(context.workflowStatus) },
    { label: h.fields.connection, value: h.connection[context.dataMode] },
  ];

  const breadcrumbs = [
    { label: h.casesCrumb, href: "/cases" },
    ...(context.caseLabel
      ? [{ label: context.caseLabel, href: context.caseId ? `/cases/${encodeURIComponent(context.caseId)}` : undefined }]
      : []),
    { label: t.views[context.activeView] },
  ];

  if (density === "compact") {
    return (
      <section aria-label={h.contextLabel} data-density="compact">
        <Breadcrumbs items={breadcrumbs} />
        <div className="grid gap-2 rounded-panel border border-line bg-surface px-3 py-2 sm:gap-3 sm:px-4 sm:py-3 xl:grid-cols-[minmax(14rem,0.7fr)_minmax(0,1.3fr)] xl:items-center">
          <div className="min-w-0">
            <h1 className="text-lg font-semibold leading-tight text-ink sm:text-xl">{title}</h1>
            <p className="sr-only mt-1 text-sm leading-5 text-ink-muted sm:not-sr-only sm:block">{description}</p>
          </div>
          <dl className="hidden min-w-0 gap-x-4 gap-y-2 md:grid md:grid-cols-2 lg:grid-cols-3 xl:flex xl:flex-wrap xl:justify-end">
            {details.map((detail) => (
              <div key={detail.label} className="min-w-0 text-sm">
                <dt className="inline text-xs font-semibold uppercase tracking-[0.08em] text-ink-subtle">
                  {detail.label}
                  <span aria-hidden="true"> · </span>
                </dt>
                <dd className="inline break-words font-medium text-ink">{detail.value}</dd>
              </div>
            ))}
          </dl>
          <details className="responsive-details min-w-0 rounded-card border border-line md:hidden">
            <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-3 py-2 marker:content-none">
              <span className="flex min-w-0 items-baseline gap-1 overflow-hidden text-sm font-medium text-ink">
                <span className="shrink-0 text-xs font-semibold uppercase tracking-[0.08em] text-ink-subtle">{h.fields.case}</span>
                <span className="min-w-0 truncate">{displayValue(context.caseLabel)}</span>
              </span>
              <span className="shrink-0 text-xs font-semibold text-brand-strong">{h.details}</span>
            </summary>
            <dl className="grid grid-cols-2 gap-3 border-t border-line p-3">
              {details.map((detail) => (
                <div key={detail.label} className="min-w-0 text-sm">
                  <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-subtle">{detail.label}</dt>
                  <dd className="mt-0.5 break-words font-medium text-ink">{detail.value}</dd>
                </div>
              ))}
            </dl>
          </details>
        </div>
        <SessionViewNavigation context={context} compact />
      </section>
    );
  }

  return (
    <section aria-label={h.contextLabel} className="space-y-4" data-density="default">
      <Breadcrumbs items={breadcrumbs} />
      <PageHeader title={title} description={description} meta={meta} />
      <div className="rounded-shell border border-line bg-surface p-4 sm:p-5">
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {details.map((detail) => (
            <div key={detail.label} className="min-w-0">
              <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-subtle">
                {detail.label}
              </dt>
              <dd className="mt-1 break-words text-sm font-medium leading-5 text-ink">
                {detail.value}
              </dd>
            </div>
          ))}
        </dl>
        <SessionViewNavigation context={context} />
      </div>
    </section>
  );
}

function SessionViewNavigation({ context, compact = false }: { context: SessionContext; compact?: boolean }) {
  const t = useMessages(sessionMessages);
  return (
    <nav
      aria-label={t.header.viewsLabel}
      className={`${compact ? "border-t px-1 py-2 sm:px-2" : "mt-4 border-t pt-4"} border-line`}
    >
      <ol className="grid grid-cols-4 gap-1 sm:gap-2" role="list">
        {sessionViews.map((view, index) => {
          const active = view === context.activeView;
          const completed = Boolean(context.completion?.[view]);
          const stateId = `session-step-${view}-state`;
          return (
            <li key={view} className="flex min-w-0 items-center">
              <Link
                href={resolveSessionHref(view, context.sessionId)}
                aria-current={active ? "page" : undefined}
                aria-describedby={completed ? stateId : undefined}
                data-step-state={completed ? "complete" : active ? "current" : "pending"}
                className="group flex min-h-11 min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-full px-1 text-center transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none sm:flex-row sm:gap-2"
              >
                <span
                  aria-hidden="true"
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-semibold transition-colors motion-reduce:transition-none sm:h-7 sm:w-7 ${
                    completed
                      ? "bg-brand text-white"
                      : active
                        ? "border-2 border-brand bg-brand-soft text-brand-strong"
                        : "border border-line-strong bg-surface text-ink-muted"
                  }`}
                >
                  {completed ? <Check size={14} strokeWidth={3} aria-hidden="true" /> : index + 1}
                </span>
                <span
                  className={`min-w-0 truncate text-xs font-semibold sm:text-sm ${
                    active ? "text-brand-strong" : completed ? "text-ink" : "text-ink-muted"
                  }`}
                >
                  {t.views[view]}
                </span>
              </Link>
              {/* Describes the tick without changing the link's name. */}
              {completed ? <span id={stateId} className="sr-only">{t.header.stepComplete}</span> : null}
              {index < sessionViews.length - 1 ? (
                <span
                  aria-hidden="true"
                  className={`hidden h-0.5 w-4 shrink-0 rounded-full sm:block ${completed ? "bg-brand" : "bg-line"}`}
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
