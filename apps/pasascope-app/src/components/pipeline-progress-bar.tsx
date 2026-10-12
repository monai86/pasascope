"use client";

import { Check } from "lucide-react";

import { pipelineMessages } from "@/components/pipeline.messages";
import { useMessages } from "@/i18n/locale-provider";

export type PipelineState =
  | "awaiting_consent"
  | "ready_for_audio"
  | "uploading"
  | "transcribing"
  | "cha_generating"
  | "review_required"
  | "ml_pending"
  | "report_ready";

/** The source path chosen in Session Intake; narrows which pipeline stages apply. */
export type PipelinePath = "recording" | "audio" | "cha" | "paste";

const pipelineStages: Array<{ id: PipelineState }> = [
  { id: "awaiting_consent" },
  { id: "ready_for_audio" },
  { id: "uploading" },
  { id: "transcribing" },
  { id: "cha_generating" },
  { id: "review_required" },
  { id: "ml_pending" },
  { id: "report_ready" }
];

/**
 * Ordered, source-relevant subsets of the full pipeline. Paste and CHA inputs
 * never upload audio or run ASR, so those stages are omitted; the recording
 * path keeps Upload and ASR; the audio path keeps Upload (ASR remains a
 * separate experimental step). Omitting `path` renders the full pipeline.
 */
const pathStageIds: Record<PipelinePath, PipelineState[]> = {
  recording: [
    "awaiting_consent",
    "ready_for_audio",
    "uploading",
    "transcribing",
    "review_required",
    "ml_pending",
    "report_ready"
  ],
  audio: [
    "awaiting_consent",
    "ready_for_audio",
    "uploading",
    "review_required",
    "ml_pending",
    "report_ready"
  ],
  cha: [
    "awaiting_consent",
    "ready_for_audio",
    "review_required",
    "ml_pending",
    "report_ready"
  ],
  paste: [
    "awaiting_consent",
    "ready_for_audio",
    "review_required",
    "ml_pending",
    "report_ready"
  ]
};

export function canonicalPipelineStageForStatus(statusLower: string): PipelineState {
  if (statusLower === "awaiting consent") return "awaiting_consent";
  if (statusLower === "ready for audio") return "ready_for_audio";
  if (statusLower === "recording" || statusLower === "uploading") return "uploading";
  if (statusLower === "transcribing") return "transcribing";
  if (statusLower === "cha generating") return "cha_generating";
  if (statusLower === "needs review" || statusLower === "review required" || statusLower === "in review") {
    return "review_required";
  }
  if (statusLower === "ml pending" || statusLower === "attested") return "ml_pending";
  if (statusLower === "report ready" || statusLower === "ready" || statusLower === "signed off") return "report_ready";
  return "awaiting_consent";
}

type PipelineProgressBarProps = {
  currentStatus: string;
  path?: PipelinePath;
};

export function PipelineProgressBar({ currentStatus, path }: PipelineProgressBarProps) {
  const t = useMessages(pipelineMessages);
  const stages = path
    ? pathStageIds[path]
        .map((id) => pipelineStages.find((stage) => stage.id === id))
        .filter((stage): stage is { id: PipelineState } => Boolean(stage))
    : pipelineStages;
  const statusLower = (currentStatus || "").toLowerCase().replace(/_/g, " ").trim();
  const canonicalStage = canonicalPipelineStageForStatus(statusLower);

  let activeIndex = stages.findIndex((stage) => stage.id === canonicalStage);
  if (activeIndex === -1) {
    // The status refers to a stage that does not exist on this path; highlight
    // the nearest preceding stage that does, falling back to the first stage.
    const canonicalIndex = pipelineStages.findIndex((stage) => stage.id === canonicalStage);
    activeIndex = stages.reduce((nearest, stage, idx) => (
      pipelineStages.findIndex((full) => full.id === stage.id) <= canonicalIndex ? idx : nearest
    ), -1);
    if (activeIndex === -1) activeIndex = 0;
  }

  return (
    <section className="grid gap-4 rounded-panel border border-line bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.1em] text-ink-subtle">
          {t.title}
        </h2>
        <p className="text-xs font-medium text-brand-strong">
          {t.stage(activeIndex + 1, stages.length, t.stages[stages[activeIndex].id])}
        </p>
      </div>
      <div
        className="relative grid grid-cols-2 gap-3 sm:flex sm:items-start sm:justify-between sm:gap-0"
        role="img"
        aria-label={t.progress(t.stages[stages[activeIndex].id])}
      >
        {/* Progress bar line background */}
        <div className="absolute left-0 top-4 hidden h-0.5 w-full bg-line sm:block" />
        {/* Active progress bar line */}
        <div
          className="motion-panel absolute left-0 top-4 hidden h-0.5 bg-brand-strong transition-all sm:block"
          style={{ width: `${(activeIndex / (stages.length - 1)) * 100}%` }}
        />

        {stages.map((stage, idx) => {
          const isCompleted = idx < activeIndex;
          const isActive = idx === activeIndex;

          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center">
              <span
                className={`motion-panel rounded-full border-2 text-xs font-semibold transition-all ${
                  isCompleted
                    ? "border-brand-strong bg-brand-strong text-white"
                    : isActive
                    ? "border-brand-strong bg-white text-brand-strong ring-4 ring-brand-soft"
                    : "border-line bg-white text-ink-muted"
                } grid h-8 w-8 place-items-center`}
              >
                {isCompleted ? <Check size={14} aria-hidden="true" /> : idx + 1}
              </span>
              <span
                className={`mt-2 text-center text-2xs font-semibold uppercase sm:max-w-20 ${
                  isActive
                    ? "text-ink"
                    : "text-ink-muted"
                }`}
              >
                {t.stages[stage.id]}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
