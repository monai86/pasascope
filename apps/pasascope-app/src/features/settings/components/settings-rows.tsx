"use client";

import Link from "next/link";
import type { ReactNode } from "react";

/**
 * One line of a section: what it is on the left, with a short explanation
 * under it, and the value or control on the right. Stacked on a phone.
 * A single control sits level with its name; a form of several fields is
 * read from the top, so its name stays at the top beside the first field.
 */
export function Row({
  label,
  hint,
  labelFor,
  align = "center",
  children,
}: {
  label: string;
  hint?: string;
  labelFor?: string;
  align?: "center" | "top";
  children: ReactNode;
}) {
  const Name = labelFor ? "label" : "span";
  return (
    <div className={`grid gap-3 border-b border-line py-5 sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)] sm:gap-8 ${align === "top" ? "sm:items-start" : "sm:items-center"}`}>
      <div className="min-w-0">
        {label ? <Name {...(labelFor ? { htmlFor: labelFor } : {})} className="block text-sm font-semibold text-ink">{label}</Name> : null}
        {hint ? <p className="mt-1 text-[13px] leading-5 text-ink-muted">{hint}</p> : null}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Rows under their own heading, set apart from the settings above them. */
export function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="pt-8">
      <h3 className="border-b border-line pb-3 text-base font-semibold text-ink">{title}</h3>
      {children}
    </div>
  );
}

export function Value({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-6 text-ink">{children}</p>;
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-6 text-ink-muted">{children}</p>;
}

export function TextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="mt-5 inline-flex min-h-11 items-center text-sm font-semibold text-brand underline decoration-brand/30 underline-offset-4 transition-colors hover:decoration-brand motion-reduce:transition-none"
    >
      {children}
    </Link>
  );
}

export function FormStatus({
  status,
  errorId,
}: {
  status: { kind: "idle" | "saving" | "saved" | "error"; message?: string };
  errorId?: string;
}) {
  if (status.kind === "error") {
    return <p id={errorId} role="alert" className="text-sm font-medium text-[color:var(--color-danger-text)]">{status.message}</p>;
  }
  // Kept in the page at no height while empty, so the announcement is heard when it fills.
  return (
    <p role="status" aria-live="polite" className="text-sm font-medium text-ink-muted empty:h-0">
      {status.kind === "saved" ? status.message : ""}
    </p>
  );
}
