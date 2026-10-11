"use client";

import { ShieldCheck } from "lucide-react";

import { cn } from "@/lib/cn";
import { useSafetyCopy } from "@/lib/safety-copy";

export function SafetyNotice({
  children,
  className = ""
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  const safety = useSafetyCopy();

  return (
    <aside className={cn("rounded-card border border-line bg-surface-muted px-4 py-3 text-sm text-ink-muted", className)}>
      <div className="flex items-start gap-3">
        <ShieldCheck size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-brand" />
        <p className="leading-6">{children ?? safety.SAFETY_NOTICE_DEFAULT}</p>
      </div>
    </aside>
  );
}
