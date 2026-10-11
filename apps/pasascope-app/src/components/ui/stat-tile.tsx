import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

export type StatTileTone = "neutral" | "brand" | "attention";

const iconToneClasses: Record<StatTileTone, string> = {
  neutral: "bg-surface-muted text-ink-muted",
  brand: "bg-brand-soft text-brand",
  attention: "bg-[color:var(--color-attention-bg)] text-[color:var(--color-warning-text)]",
};

/** A count with its label: the large numeral leads, as in a dashboard tile. */
export function StatTile({
  label,
  value,
  helper,
  icon: Icon,
  tone = "neutral",
  className,
}: {
  label: string;
  value: string | number;
  helper?: string;
  icon?: LucideIcon;
  tone?: StatTileTone;
  className?: string;
}) {
  return (
    <section className={cn("rounded-card border border-line bg-surface p-4 shadow-soft", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-display text-3xl font-semibold leading-none text-ink">{value}</p>
          <p className="mt-2 text-sm font-medium text-ink-muted">{label}</p>
        </div>
        {Icon ? (
          <span className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-control", iconToneClasses[tone])}>
            <Icon size={20} aria-hidden="true" />
          </span>
        ) : null}
      </div>
      {helper ? <p className="mt-3 text-xs leading-5 text-ink-subtle">{helper}</p> : null}
    </section>
  );
}
