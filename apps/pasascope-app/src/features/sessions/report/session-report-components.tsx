import { ArrowRight, Heart, Star } from "lucide-react";

import type { WorkflowState } from "@/lib/workflow";
import { useStatusText } from "@/features/sessions/state/use-status-text";

export const reportSectionDefinitions = [
  {
    icon: Star,
    title: "Strengths",
    tone: "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
    items: ["Reviewed transcript available", "Feature summary prepared for therapist interpretation"],
  },
  {
    icon: Heart,
    title: "Needs Support",
    tone: "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
    items: ["Confirm transcript wording", "Review suggested next steps before sharing"],
  },
  {
    icon: ArrowRight,
    title: "Next Steps",
    tone: "bg-brand-soft text-brand",
    items: ["Edit draft report language", "Finalize only after therapist review"],
  },
];

export function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  const text = useStatusText();
  if (!state.statusMessage && !state.error) return null;
  const isError = Boolean(state.error);
  const isSuccess = Boolean(state.statusMessage && !isError);
  if (isSuccess && backendUnavailable) return null;
  const className = isError
    ? "rounded-panel border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] p-4 text-sm text-[color:var(--color-danger-text)] animate-fade-in"
    : isSuccess
      ? "rounded-panel border border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] p-4 text-sm text-[color:var(--color-success-text)] animate-fade-in"
      : "demo-note rounded-panel p-4 text-sm";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{text(state.statusMessage)}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{text(state.error)}</p> : null}
    </div>
  );
}

export function ReportProvenanceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-line bg-surface-muted p-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">{label}</dt>
      <dd className="mt-1 [overflow-wrap:anywhere] text-sm font-bold text-ink">{value}</dd>
    </div>
  );
}
