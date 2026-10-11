import { useId } from "react";

import { cn } from "@/lib/cn";
import { Label } from "@/components/ui/label";

export type FieldControlProps = {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
};

/**
 * A labelled form control with optional hint and error. The control receives
 * the ids that tie it to its label, hint and error, so an error message is
 * announced with the field it belongs to.
 */
export function Field({
  label,
  hint,
  error,
  required = false,
  className,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  className?: string;
  children: (control: FieldControlProps) => React.ReactNode;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={id}>
        {label}
        {required ? <span aria-hidden="true" className="ml-0.5 text-[color:var(--color-danger-text)]">*</span> : null}
      </Label>
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? true : undefined })}
      {hint ? <p id={hintId} className="text-xs leading-5 text-ink-subtle">{hint}</p> : null}
      {error ? <p id={errorId} role="alert" className="text-xs font-medium leading-5 text-[color:var(--color-danger-text)]">{error}</p> : null}
    </div>
  );
}
