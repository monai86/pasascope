"use client";

import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";

import { Breadcrumbs } from "@/components/breadcrumbs";
import { PageHeader } from "@/components/page-header";
import { useMessages } from "@/i18n/locale-provider";
import { sessionMessages } from "@/features/sessions/session.messages";
import {
  resolveSessionHref,
  sessionViews,
  type SessionView,
} from "@/features/sessions/state/session-view";
import { useWorkflowStatusLabel } from "@/components/status-badge";
import { useReportLabel } from "@/features/sessions/findings/use-findings-label";

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
  const statusLabel = useWorkflowStatusLabel();
  const reportStatusLabel = useReportLabel();
  const details = [
    { label: h.fields.case, value: displayValue(context.caseLabel) },
    { label: h.fields.session, value: displayValue(context.sessionId) },
    { label: h.fields.source, value: displayValue(context.sourceLabel) },
    { label: h.fields.consent, value: context.consentStatus?.trim() ? h.consent(context.consentStatus.trim()) : h.unavailable },
    { label: h.fields.status, value: context.workflowStatus?.trim() ? reportStatusLabel(statusLabel(context.workflowStatus.trim())) : h.unavailable },
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
    // A working page: the way back, what this page is, and which case it is for.
    // The rest of the session's facts live on the conversation and the case.
    const consent = context.consentStatus?.trim() ? h.consent(context.consentStatus.trim()) : null;
    return (
      <section aria-label={h.contextLabel} data-density="compact" className="space-y-3">
        <div>
          <BackToConversation context={context} />
          <h1 className="font-display text-2xl font-semibold leading-tight text-ink sm:text-[1.75rem]">{title}</h1>
          <p className="mt-1 text-sm leading-6 text-ink-muted">
            <span>{displayValue(context.caseLabel)}</span>
            {consent ? <span> · {consent}</span> : null}
            <span className="sr-only"> {description}</span>
          </p>
        </div>
        <SessionViewNavigation context={context} compact />
      </section>
    );
  }

  return (
    <section aria-label={h.contextLabel} className="space-y-4" data-density="default">
      <BackToConversation context={context} />
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

/** A full page is a detour from the session's conversation, so it offers the way back first. */
function BackToConversation({ context }: { context: SessionContext }) {
  const t = useMessages(sessionMessages).header;
  if (!context.sessionId) return null;
  return (
    <Link
      href={resolveSessionHref("chat", context.sessionId, { caseId: context.caseId })}
      className="mb-2 inline-flex min-h-11 items-center gap-2 rounded-full pr-3 text-sm font-semibold text-ink transition hover:underline focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none"
    >
      <ArrowLeft size={18} aria-hidden="true" />
      {t.backToConversation}
    </Link>
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
                href={resolveSessionHref(view === "intake" ? "chat" : view, context.sessionId)}
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
                  {view === "intake" ? t.header.conversation : t.views[view]}
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
