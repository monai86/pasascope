import Link from "next/link";

import { ActionButton } from "@/components/action-button";
import { StatusBadge } from "@/components/status-badge";
import {
  todayQueueGroups,
  type TodayWorkbenchModel,
} from "@/features/work-queue/today-workbench-model";

export type TodayWorkbenchViewState =
  | { status: "loading" }
  | { status: "error"; retry: () => void }
  | { status: "ready"; model: TodayWorkbenchModel };

export function TodayWorkbenchView({
  state,
  compactContext,
}: {
  state: TodayWorkbenchViewState;
  compactContext?: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <header className="rounded-2xl border border-line bg-surface flex flex-col gap-4 p-4 sm:p-5 md:flex-row md:items-end md:justify-between shadow-xs">
        <div className="min-w-0">
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-border bg-brand-soft px-3 py-1 text-xs font-semibold text-brand mb-2.5 lg:hidden">
            <span className="h-2 w-2 rounded-full bg-highlight" />
            <span>Active Clinician Caseload</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">Work Queue</h1>
          <p className="mt-1.5 max-w-[70ch] text-sm leading-relaxed text-ink-muted">
            What needs your decision next, in one prioritized list. Queue status is operational, not a clinical conclusion.
          </p>
        </div>
        <ActionButton href="/cases?intent=start-session" className="w-full shrink-0 sm:w-auto font-bold">
          Start session
        </ActionButton>
      </header>

      {state.status === "loading" ? <TodayLoadingState /> : null}
      {state.status === "error" ? <TodayErrorState retry={state.retry} /> : null}
      {state.status === "ready" ? <TodayReadyState model={state.model} /> : null}
      {compactContext ? <div className="xl:hidden">{compactContext}</div> : null}
    </div>
  );
}

function TodayLoadingState() {
  return (
    <section className="rounded-2xl border border-line bg-surface p-6 shadow-xs" role="status" aria-live="polite">
      <p className="font-semibold text-ink">Loading today’s work queue…</p>
      <div className="mt-4 grid gap-3" aria-hidden="true">
        {[0, 1, 2].map((item) => <div key={item} className="h-24 animate-pulse rounded-xl bg-surface-muted motion-reduce:animate-none" />)}
      </div>
    </section>
  );
}

function TodayErrorState({ retry }: { retry: () => void }) {
  return (
    <section className="rounded-2xl border border-[color:var(--color-danger-border)] bg-surface p-6 shadow-xs" role="alert">
      <div className="flex items-start gap-3">
        <div>
          <h2 className="text-lg font-bold text-ink">We couldn’t load your work queue</h2>
          <p className="mt-1 text-sm leading-6 text-ink-muted">
            Check your connection and try again.
          </p>
          <button type="button" onClick={retry} className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl border border-brand-border bg-brand-soft px-4 text-sm font-semibold text-brand hover:bg-brand hover:text-white transition">
            Retry work queue
          </button>
        </div>
      </div>
    </section>
  );
}

function TodayReadyState({ model }: { model: TodayWorkbenchModel }) {
  if (model.items.length === 0) {
    return (
      <section className="rounded-2xl border border-line bg-surface p-8 text-center shadow-xs" aria-live="polite">
        <h2 className="text-xl font-bold text-ink">No work requires attention right now.</h2>
        <p className="mt-2 text-sm text-ink-muted">Start a session or review a case when you’re ready.</p>
        <ActionButton href="/cases?intent=start-session" className="mt-5 font-bold">
          Start a session
        </ActionButton>
      </section>
    );
  }

  return (
    <div data-testid="today-primary-workbench" className="space-y-3">
      <TodayNextUp model={model} />
      <dl
        className="flex snap-x snap-proximity gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-3 sm:gap-4 sm:overflow-visible sm:pb-0"
        aria-label="Work queue summary"
      >
        <QueueMetric label="Needs action" value={model.summary.needsAction} />
        <QueueMetric label="Ready for review" value={model.summary.readyForReview} />
        <QueueMetric label="Ready for sign-off" value={model.summary.readyForSignoff} />
      </dl>

      <section className="rounded-2xl border border-line bg-surface overflow-hidden shadow-xs" aria-labelledby="prioritized-queue-title">
        <div className="px-5 py-3 border-b border-line">
          <h2 id="prioritized-queue-title" className="text-xl font-bold text-ink">Prioritized queue</h2>
        </div>

        <div>
          {todayQueueGroups.map((group) => {
            const items = model.items.filter((item) => item.group === group.key);
            if (!items.length) return null;
            return (
              <section
                key={group.key}
                aria-labelledby={`today-group-${group.key}`}
                className="border-b border-line last:border-b-0"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2 bg-surface px-5 py-2">
                  <div className="min-w-0 lg:flex lg:items-baseline lg:gap-3">
                    <h3 id={`today-group-${group.key}`} className="shrink-0 text-sm font-bold text-ink">{group.label}</h3>
                    <p className="mt-0.5 hidden text-xs leading-5 text-ink-muted sm:block lg:mt-0 lg:truncate">{group.description}</p>
                  </div>
                  <span className="rounded-full bg-surface-muted px-2.5 py-0.5 text-xs font-semibold text-ink-muted">{items.length} {items.length === 1 ? "item" : "items"}</span>
                </div>
                <div className="divide-y divide-line">
                  {items.map((item) => <TodayQueueRow key={item.id} item={item} />)}
                </div>
              </section>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function TodayNextUp({ model }: { model: TodayWorkbenchModel }) {
  const item = model.items[0];
  if (!item) return null;
  return (
    <section
      data-testid="today-next-up"
      aria-labelledby="today-next-up-title"
      className="overflow-hidden rounded-2xl border border-brand-border bg-gradient-to-br from-[color:var(--color-brand-soft)]/60 via-white to-white p-4 sm:p-5 shadow-xs"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-highlight animate-pulse" />
            <p id="today-next-up-title" className="text-xs font-bold uppercase tracking-wider text-brand">
              Next up for you
            </p>
          </div>
          <h2 className="mt-1.5 text-xl font-bold text-ink">
            {item.caseLabel} · {item.taskType}
          </h2>
          <p className="mt-1 max-w-[70ch] text-sm leading-relaxed text-ink-muted">{item.reason}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={item.workflowStatus} />
            <span className="rounded-full bg-surface-muted px-2.5 py-0.5 text-xs font-medium text-ink-muted">{item.reviewPriority}</span>
            <span className="text-xs text-ink-muted">{formatDate(item.sessionDate)}</span>
          </div>
        </div>
        <Link
          href={item.href}
          className="inline-flex min-h-12 w-full shrink-0 items-center justify-center gap-2 rounded-xl bg-highlight px-5 text-sm font-bold text-white shadow-xs transition hover:bg-highlight-text active:scale-[0.99] lg:w-auto"
        >
          {item.actionLabel}
        </Link>
      </div>
    </section>
  );
}

function TodayQueueRow({ item }: { item: TodayWorkbenchModel["items"][number] }) {
  return (
    <article
      data-testid="today-queue-row"
      className="flex flex-col gap-2 px-5 py-3.5 sm:px-5 lg:flex-row lg:items-center lg:gap-4 lg:py-2.5 hover:bg-[color:var(--color-surface)]/50 transition"
    >
      <div className="min-w-0 lg:w-48">
        <h4 className="truncate font-bold text-ink">{item.caseLabel}</h4>
        <p className="mt-0.5 text-xs text-ink-muted">{formatDate(item.sessionDate)}</p>
      </div>
      <div className="min-w-0 lg:w-56">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={item.workflowStatus} />
          <span className="text-xs font-medium text-ink-muted">{item.reviewPriority}</span>
        </div>
        <p className="mt-1 truncate text-xs text-ink font-semibold">{item.taskType}</p>
      </div>
      <p className="min-w-0 flex-1 text-sm leading-5 text-ink lg:line-clamp-1">{item.reason}</p>
      <Link
        href={item.href}
        className="inline-flex min-h-10 w-full shrink-0 items-center justify-center gap-2 rounded-xl border border-brand-border bg-brand-soft px-4 text-xs font-bold text-brand transition hover:bg-brand hover:text-white lg:w-auto shadow-2xs"
      >
        {item.actionLabel}
      </Link>
    </article>
  );
}

function QueueMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex min-w-0 flex-1 snap-start items-baseline justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-2.5 shadow-xs sm:min-w-0 sm:flex-none">
      <dt className="text-xs font-bold uppercase tracking-wider text-ink-muted">{label}</dt>
      <dd className="text-xl font-extrabold text-ink">{value}</dd>
    </div>
  );
}

function formatDate(value?: string) {
  if (!value) return "Not scheduled";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? "Unavailable" : parsed.toLocaleDateString();
}
