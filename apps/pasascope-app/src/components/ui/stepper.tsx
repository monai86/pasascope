import Link from "next/link";
import { Check, Lock } from "lucide-react";

import { cn } from "@/lib/cn";

export type StepState = "complete" | "current" | "available" | "locked";

export type StepItem = {
  id: string;
  label: string;
  state: StepState;
  /** When set, the step is a link; locked steps never link. */
  href?: string;
};

/**
 * A numbered progress rail. A step is ticked only when the work behind it is
 * done, which the caller decides; position in the list never implies it.
 */
export function Stepper({
  label,
  steps,
  stateLabels,
  className,
}: {
  /** Names the rail for assistive technology. */
  label: string;
  steps: ReadonlyArray<StepItem>;
  /** Spoken name of each state, in the interface language. */
  stateLabels: Record<StepState, string>;
  className?: string;
}) {
  return (
    <nav aria-label={label} className={className}>
      <ol className="flex items-stretch gap-1 sm:gap-2" role="list">
        {steps.map((step, index) => {
          const isCurrent = step.state === "current";
          const isComplete = step.state === "complete";
          const isLocked = step.state === "locked";
          const marker = (
            <span
              aria-hidden="true"
              className={cn(
                "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-semibold transition-colors motion-reduce:transition-none",
                isComplete && "bg-brand text-white",
                isCurrent && "border-2 border-brand bg-brand-soft text-brand-strong",
                step.state === "available" && "border border-line-strong bg-surface text-ink-muted",
                isLocked && "border border-line bg-surface-muted text-ink-subtle",
              )}
            >
              {isComplete ? <Check size={14} strokeWidth={3} /> : isLocked ? <Lock size={12} /> : index + 1}
            </span>
          );
          const text = (
            <span className={cn("min-w-0 truncate text-xs font-semibold sm:text-sm", isCurrent ? "text-brand-strong" : isLocked ? "text-ink-subtle" : "text-ink")}>
              {step.label}
              <span className="sr-only"> ({stateLabels[step.state]})</span>
            </span>
          );
          const itemClasses =
            "flex min-h-11 min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-control px-1 text-center sm:flex-row sm:gap-2";

          return (
            <li key={step.id} className="flex min-w-0 flex-1 items-center gap-1 sm:gap-2">
              {step.href && !isLocked ? (
                <Link
                  href={step.href}
                  aria-current={isCurrent ? "step" : undefined}
                  className={cn(itemClasses, "transition-colors hover:bg-surface-soft focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none")}
                >
                  {marker}
                  {text}
                </Link>
              ) : (
                <span aria-current={isCurrent ? "step" : undefined} aria-disabled={isLocked || undefined} className={itemClasses}>
                  {marker}
                  {text}
                </span>
              )}
              {index < steps.length - 1 ? (
                <span aria-hidden="true" className={cn("hidden h-0.5 w-4 shrink-0 rounded-full sm:block", isComplete ? "bg-brand" : "bg-line")} />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
