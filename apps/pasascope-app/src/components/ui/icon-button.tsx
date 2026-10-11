import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

/**
 * A 44px square control that shows only an icon. `label` is required: it is
 * the control's accessible name and its tooltip.
 */
export function IconButton({
  icon: Icon,
  label,
  className,
  type = "button",
  ...props
}: {
  icon: LucideIcon;
  label: string;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label">) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={cn(
        "grid h-11 w-11 shrink-0 place-items-center rounded-full border border-line bg-surface text-ink-muted transition hover:border-brand-border hover:bg-brand-soft hover:text-brand focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none",
        className,
      )}
      {...props}
    >
      <Icon size={18} aria-hidden="true" />
    </button>
  );
}
