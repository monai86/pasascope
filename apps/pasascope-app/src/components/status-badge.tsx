"use client";

import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  AudioLines,
  BadgeCheck,
  Ban,
  CheckCircle2,
  CircleDot,
  Clock,
  FileCheck2,
  FileCode2,
  Loader,
  Mic,
  PencilLine,
  Upload,
  XCircle,
} from "lucide-react";

import { statusMessages } from "@/components/status.messages";
import { badgeToneClasses, type BadgeTone } from "@/components/ui/badge";
import { useMessages } from "@/i18n/locale-provider";
import { cn } from "@/lib/cn";

export type WorkflowStatus =
  | "Draft"
  | "Needs Review"
  | "Attested"
  | "Processing"
  | "Failed"
  | "Ready"
  | "Signed Off"
  | "Withdrawn"
  | "Awaiting Consent"
  | "Ready for Audio"
  | "Recording"
  | "Uploading"
  | "Transcribing"
  | "CHA Generating"
  | "ML Pending"
  | "Review Required"
  | "Report Ready";

type StatusPresentation = { tone: BadgeTone; icon: LucideIcon; pulse?: boolean };

// Each status has an icon as well as a tone, so the state survives greyscale
// printing and colour-vision differences.
const presentation: Record<WorkflowStatus, StatusPresentation> = {
  Draft: { tone: "neutral", icon: PencilLine },
  "Needs Review": { tone: "warning", icon: AlertTriangle },
  Attested: { tone: "success", icon: CheckCircle2 },
  Processing: { tone: "info", icon: Loader },
  Failed: { tone: "danger", icon: XCircle },
  Ready: { tone: "success", icon: CheckCircle2 },
  "Signed Off": { tone: "solid", icon: BadgeCheck },
  Withdrawn: { tone: "neutral", icon: Ban },
  "Awaiting Consent": { tone: "attention", icon: Clock },
  "Ready for Audio": { tone: "info", icon: Mic },
  Recording: { tone: "highlight", icon: CircleDot, pulse: true },
  Uploading: { tone: "info", icon: Upload, pulse: true },
  Transcribing: { tone: "info", icon: AudioLines },
  "CHA Generating": { tone: "info", icon: FileCode2 },
  "ML Pending": { tone: "attention", icon: Clock },
  "Review Required": { tone: "warning", icon: AlertTriangle },
  "Report Ready": { tone: "success", icon: FileCheck2 },
};

function canonicalize(value: string): string {
  return value.toLowerCase().replace(/[_-]/g, " ").replace(/\s+/g, " ").trim();
}

function matchStatus(status: string): WorkflowStatus | null {
  const keys = Object.keys(presentation) as WorkflowStatus[];
  if (keys.includes(status as WorkflowStatus)) return status as WorkflowStatus;
  const canonicalInput = canonicalize(status);
  return keys.find((key) => canonicalize(key) === canonicalInput) ?? null;
}

export function StatusBadge({ status }: { status: string }) {
  const labels = useMessages(statusMessages);
  const matched = matchStatus(status);
  // An unrecognised status keeps its own text and takes the neutral draft look.
  const { tone, icon: Icon, pulse } = presentation[matched ?? "Draft"];

  return (
    <span
      data-tone={tone}
      data-pulse={pulse ? "true" : undefined}
      className={cn(
        "inline-flex min-h-8 min-w-24 items-center justify-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold",
        badgeToneClasses[tone],
        pulse && "animate-pulse motion-reduce:animate-none",
      )}
    >
      <Icon size={14} aria-hidden="true" className="shrink-0" />
      <span>{matched ? labels[matched] : status}</span>
    </span>
  );
}
