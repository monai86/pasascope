import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

import { cn } from "@/lib/cn";

/** Nothing to show yet. Always offer the action that would change that. */
export function EmptyState({
  title,
  description,
  action,
  icon: Icon = Inbox,
  className,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <section className={cn("rounded-panel border border-line bg-surface px-5 py-10 text-center", className)}>
      <span className="mx-auto grid h-14 w-14 place-items-center rounded-card bg-brand-soft text-brand">
        <Icon size={26} aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-xl font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-ink-muted">{description}</p>
      {action ? <div className="mt-5 flex flex-wrap justify-center gap-3">{action}</div> : null}
    </section>
  );
}
