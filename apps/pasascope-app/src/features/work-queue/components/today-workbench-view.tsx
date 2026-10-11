"use client";

import { ClipboardCheck, FileSearch, Inbox, ListTodo } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  todayQueueGroups,
  type TodayQueueItem,
  type TodayWorkbenchModel,
} from "@/features/work-queue/today-workbench-model";
import { todayMessages } from "@/features/work-queue/today.messages";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";

export type TodayWorkbenchViewState =
  | { status: "loading" }
  | { status: "error"; retry: () => void }
  | { status: "ready"; model: TodayWorkbenchModel };

type TodayCopy = ReturnType<typeof useTodayCopy>;

function useTodayCopy() {
  const t = useMessages(todayMessages);
  const { locale } = useLocale();
  return {
    t,
    date(value?: string) {
      if (!value) return t.notScheduled;
      return formatDate(value, locale) || t.dateUnavailable;
    },
    priority(value: string) {
      return value in t.priority ? t.priority[value as keyof typeof t.priority] : value;
    },
  };
}

export function TodayWorkbenchView({
  state,
  compactContext,
}: {
  state: TodayWorkbenchViewState;
  compactContext?: React.ReactNode;
}) {
  const copy = useTodayCopy();
  const { t } = copy;

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold text-ink">{t.title}</h1>
          <p className="mt-1.5 max-w-[70ch] text-sm leading-relaxed text-ink-muted">{t.description}</p>
        </div>
        {/* The page's one solid action is the next-up card below; this stays quiet. */}
        <Button href="/cases?intent=start-session" variant="secondary" className="w-full shrink-0 sm:w-auto">
          {t.startSession}
        </Button>
      </header>

      {state.status === "loading" ? <TodayLoadingState label={t.loading} /> : null}
      {state.status === "error" ? (
        <ErrorState
          className="bg-surface"
          title={t.error.title}
          description={t.error.description}
          retryLabel={t.error.retry}
          onRetry={state.retry}
        />
      ) : null}
      {state.status === "ready" ? <TodayReadyState model={state.model} copy={copy} /> : null}
      {compactContext ? <div className="xl:hidden">{compactContext}</div> : null}
    </div>
  );
}

function TodayLoadingState({ label }: { label: string }) {
  return (
    <section className="rounded-panel border border-line bg-surface p-6 shadow-soft" role="status" aria-live="polite">
      <p className="font-semibold text-ink">{label}</p>
      <div className="mt-4 grid gap-3" aria-hidden="true">
        {[0, 1, 2].map((item) => (
          <div key={item} className="h-24 animate-pulse rounded-card bg-surface-muted motion-reduce:animate-none" />
        ))}
      </div>
    </section>
  );
}

function TodayReadyState({ model, copy }: { model: TodayWorkbenchModel; copy: TodayCopy }) {
  const { t } = copy;

  if (model.items.length === 0) {
    return (
      <div aria-live="polite">
        <EmptyState
          icon={Inbox}
          title={t.empty.title}
          description={t.empty.description}
          action={<Button href="/cases?intent=start-session">{t.empty.action}</Button>}
        />
      </div>
    );
  }

  return (
    <div data-testid="today-primary-workbench" className="space-y-4">
      <TodayNextUp item={model.items[0]} copy={copy} />

      <dl className="grid grid-cols-3 gap-2 sm:gap-4" aria-label={t.summaryLabel}>
        <QueueMetric icon={ListTodo} label={t.summary.needsAction} value={model.summary.needsAction} />
        <QueueMetric icon={FileSearch} label={t.summary.readyForReview} value={model.summary.readyForReview} />
        <QueueMetric icon={ClipboardCheck} label={t.summary.readyForSignoff} value={model.summary.readyForSignoff} />
      </dl>

      <section className="overflow-hidden rounded-panel border border-line bg-surface shadow-soft" aria-labelledby="prioritized-queue-title">
        <div className="border-b border-line px-5 py-3">
          <h2 id="prioritized-queue-title" className="text-xl font-semibold text-ink">{t.queueTitle}</h2>
        </div>

        <div>
          {todayQueueGroups.map((group) => {
            const items = model.items.filter((item) => item.group === group);
            if (!items.length) return null;
            return (
              <section key={group} aria-labelledby={`today-group-${group}`} className="border-b border-line last:border-b-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2 bg-surface-soft px-5 py-2.5">
                  <div className="min-w-0 lg:flex lg:items-baseline lg:gap-3">
                    <h3 id={`today-group-${group}`} className="shrink-0 text-sm font-semibold text-ink">{t.groups[group].label}</h3>
                    <p className="mt-0.5 hidden text-xs leading-5 text-ink-muted sm:block lg:mt-0 lg:truncate">{t.groups[group].description}</p>
                  </div>
                  <span className="rounded-full bg-surface-muted px-2.5 py-0.5 text-xs font-semibold text-ink-muted">{t.itemCount(items.length)}</span>
                </div>
                <div className="divide-y divide-line">
                  {items.map((item) => <TodayQueueRow key={item.id} item={item} copy={copy} />)}
                </div>
              </section>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function TodayNextUp({ item, copy }: { item: TodayQueueItem; copy: TodayCopy }) {
  const { t } = copy;
  const task = t.tasks[item.kind];

  return (
    <Card variant="hero" data-testid="today-next-up" aria-labelledby="today-next-up-title" role="region" className="p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p id="today-next-up-title" className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider">
            {/* The one coral mark on this page: it points at the work to do first. */}
            <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full bg-highlight ring-2 ring-white/70" />
            {t.nextUp}
          </p>
          <h2 className="mt-1.5 text-2xl font-semibold">
            {item.caseLabel} · {task.task}
          </h2>
          <p className="mt-1 max-w-[70ch] text-sm leading-relaxed">{task.reason}</p>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <StatusBadge status={item.workflowStatus} />
            <span className="rounded-full bg-navy/30 px-2.5 py-1 text-xs font-medium">{copy.priority(item.reviewPriority)}</span>
            <span className="text-xs">{copy.date(item.sessionDate)}</span>
          </div>
        </div>
        <Button
          href={item.href}
          size="lg"
          variant="secondary"
          className="w-full shrink-0 border-white bg-surface text-brand-strong shadow-lift hover:bg-brand-soft lg:w-auto"
        >
          {task.action}
        </Button>
      </div>
    </Card>
  );
}

function TodayQueueRow({ item, copy }: { item: TodayQueueItem; copy: TodayCopy }) {
  const task = copy.t.tasks[item.kind];

  return (
    <article
      data-testid="today-queue-row"
      className="flex flex-col gap-2 px-5 py-3.5 transition hover:bg-surface-soft lg:flex-row lg:items-center lg:gap-4 lg:py-3"
    >
      <div className="min-w-0 lg:w-48">
        <h4 className="truncate font-semibold text-ink">{item.caseLabel}</h4>
        <p className="mt-0.5 text-xs text-ink-muted">{copy.date(item.sessionDate)}</p>
      </div>
      <div className="min-w-0 lg:w-56">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={item.workflowStatus} />
          <span className="text-xs font-medium text-ink-muted">{copy.priority(item.reviewPriority)}</span>
        </div>
        <p className="mt-1 truncate text-xs font-semibold text-ink">{task.task}</p>
      </div>
      <p className="min-w-0 flex-1 text-sm leading-5 text-ink lg:line-clamp-1">{task.reason}</p>
      <Button href={item.href} variant="secondary" className="w-full shrink-0 lg:w-auto">
        {task.action}
      </Button>
    </article>
  );
}

function QueueMetric({ icon: Icon, label, value }: { icon: typeof Inbox; label: string; value: number }) {
  return (
    // Kept short on purpose: the queue below must stay in view on a laptop screen.
    <div className="flex min-w-0 flex-col-reverse justify-between gap-1.5 rounded-card border border-line bg-surface px-3 py-2.5 shadow-soft sm:px-4">
      <dt className="text-xs font-medium leading-4 text-ink-muted sm:text-sm">{label}</dt>
      <dd className="flex items-center justify-between gap-2">
        <span className="font-display text-2xl font-semibold leading-none text-ink">{value}</span>
        <span aria-hidden="true" className="hidden h-9 w-9 shrink-0 place-items-center rounded-control bg-brand-soft text-brand sm:grid">
          <Icon size={18} />
        </span>
      </dd>
    </div>
  );
}
