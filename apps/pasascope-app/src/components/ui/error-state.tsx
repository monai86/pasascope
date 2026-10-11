import { AlertTriangle, RotateCw } from "lucide-react";

import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

/**
 * Something could not be loaded. Says what failed and gives a way forward:
 * retry when the caller can, and any other route out as `action`.
 */
export function ErrorState({
  title,
  description,
  retryLabel,
  onRetry,
  action,
  className,
}: {
  title: string;
  description: string;
  retryLabel?: string;
  onRetry?: () => void;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      role="alert"
      className={cn(
        "rounded-panel border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-5 py-6",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle size={22} aria-hidden="true" className="mt-0.5 shrink-0 text-[color:var(--color-danger-text)]" />
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{description}</p>
          {onRetry || action ? (
            <div className="mt-4 flex flex-wrap gap-3">
              {onRetry && retryLabel ? (
                <Button variant="secondary" icon={RotateCw} onClick={onRetry}>
                  {retryLabel}
                </Button>
              ) : null}
              {action}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
