import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "brand" | "solid" | "success" | "info" | "warning" | "attention" | "danger" | "highlight";

// State is never carried by colour alone: pair a tone with an icon or a label
// that names the state. There is no green tone; success is blue with a check.
export const badgeToneClasses: Record<BadgeTone, string> = {
  neutral: "border-line bg-surface-muted text-ink-muted",
  brand: "border-brand-border bg-brand-soft text-brand-strong",
  solid: "border-brand bg-brand text-white",
  success:
    "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  info: "border-[color:var(--color-info-border)] bg-[color:var(--color-info-bg)] text-[color:var(--color-info-text)]",
  warning:
    "border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  attention:
    "border-[color:var(--color-attention-border)] bg-[color:var(--color-attention-bg)] text-[color:var(--color-warning-text)]",
  danger:
    "border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
  highlight: "border-highlight-border bg-highlight-soft text-highlight-text",
};

export function Badge({
  className,
  tone = "neutral",
  icon: Icon,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone; icon?: LucideIcon }) {
  return (
    <span
      data-tone={tone}
      className={cn(
        "inline-flex min-h-7 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        badgeToneClasses[tone],
        className,
      )}
      {...props}
    >
      {Icon ? <Icon size={14} aria-hidden="true" className="shrink-0" /> : null}
      {children}
    </span>
  );
}
