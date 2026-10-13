"use client";

import * as React from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/cn";
import { useFocusTrap } from "@/components/ui/use-focus-trap";

/**
 * A modal dialog. Focus is trapped inside while it is open and returns to the
 * control that opened it; Escape and the backdrop both close it.
 */
export function Dialog({
  open,
  onOpenChange,
  labelledBy,
  describedBy,
  className,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Id of the element that titles the dialog, usually its DialogTitle. */
  labelledBy?: string;
  describedBy?: string;
  className?: string;
  children: React.ReactNode;
}) {
  const panelRef = useFocusTrap<HTMLDivElement>(open, () => onOpenChange(false));

  React.useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 sm:p-6">
      <div className="shell-scrim fixed inset-0" onClick={() => onOpenChange(false)} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        className={cn(
          "relative z-10 w-full max-w-lg rounded-panel border border-line bg-surface p-6 shadow-floating focus:outline-none",
          className,
        )}
      >
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1.5 pr-10 text-left", className)} {...props} />;
}

export function DialogTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2 className={cn("text-xl font-semibold text-ink", className)} {...props}>
      {children}
    </h2>
  );
}

export function DialogDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm leading-6 text-ink-muted", className)} {...props} />;
}

export function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)} {...props} />;
}

export function DialogClose({ onClose, label = "Close dialog" }: { onClose: () => void; label?: string }) {
  return (
    <button
      type="button"
      onClick={onClose}
      aria-label={label}
      className="absolute right-3 top-3 grid h-11 w-11 place-items-center rounded-full text-ink-subtle transition hover:bg-surface-soft hover:text-ink focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]"
    >
      <X size={18} aria-hidden="true" />
    </button>
  );
}
