import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

export type SegmentedOption<T extends string> = {
  value: T;
  label: string;
  icon?: LucideIcon;
  /** Overrides the visible label for assistive technology. */
  ariaLabel?: string;
};

/**
 * A small set of mutually exclusive choices shown side by side. Each option is
 * a toggle button, so the selected one is announced as pressed.
 */
export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  size = "md",
  className,
}: {
  /** Names the group for assistive technology. */
  label: string;
  options: ReadonlyArray<SegmentedOption<T>>;
  value: T;
  onChange: (value: T) => void;
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <div role="group" aria-label={label} className={cn("inline-flex items-center gap-1 rounded-full border border-line bg-surface-muted p-1", className)}>
      {options.map((option) => {
        const selected = option.value === value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            aria-label={option.ariaLabel}
            onClick={() => onChange(option.value)}
            className={cn(
              "inline-flex items-center justify-center gap-1.5 rounded-full font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none",
              size === "sm" ? "min-h-10 min-w-11 px-3 text-xs" : "min-h-11 px-4 text-sm",
              selected ? "bg-surface text-brand shadow-soft" : "text-ink-muted hover:text-ink",
            )}
          >
            {Icon ? <Icon size={16} aria-hidden="true" /> : null}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
