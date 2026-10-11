import * as React from "react";

import { cn } from "@/lib/cn";

export const controlClasses =
  "w-full rounded-control border border-line-strong bg-surface px-3.5 text-sm text-ink placeholder:text-ink-subtle transition focus-visible:border-brand focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:bg-surface-muted disabled:opacity-70 aria-[invalid=true]:border-[color:var(--color-danger-text)] motion-reduce:transition-none";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(controlClasses, "min-h-11 py-2", className)} {...props} />
));
Input.displayName = "Input";
