"use client";

import { useState } from "react";

import { findingsPartsMessages } from "@/features/sessions/findings/findings-parts.messages";
import { useFindingsLabel } from "@/features/sessions/findings/use-findings-label";
import { useMessages } from "@/i18n/locale-provider";
import { INTERPRETATION_HINT } from "@/lib/clinical-safety-copy";
import { useSafetyCopy } from "@/lib/safety-copy";
import type { FeatureSignal } from "@/lib/workflow";

/**
 * Full extracted-feature decision panel for the Findings view.
 *
 * Shows every language-sample feature at once, grouped by clinical meaning,
 * so the therapist can scan all values in one place to support their
 * interpretation. Dense hairline rows keep the list scannable without the
 * vertical cost of card-per-feature layouts, and each row discloses the
 * method, reference evidence, and limitations behind its value on demand.
 */
export function FeatureDecisionGrid({ signals }: { signals: FeatureSignal[] }) {
  const [expandedFeature, setExpandedFeature] = useState<string | null>(null);
  const t = useMessages(findingsPartsMessages).grid;
  const label = useFindingsLabel();
  const safety = useSafetyCopy();

  const groups = decisionGroupIds.map((id) => ({
    id,
    ...t.groups[id],
    signals: signals.filter((signal) => groupId(signal.featureName) === id),
  }));

  // Groups with nothing in them are left out; every value that was extracted is shown.
  const shown = groups.filter((group) => group.signals.length > 0);
  // Said once for the panel rather than on every value.
  const anyReference = signals.some((signal) => signal.referenceText && signal.referenceText !== NO_REFERENCE);

  return (
    <section
      aria-labelledby="feature-decision-grid-title"
      data-testid="feature-decision-grid"
      className="rounded-panel border border-line bg-surface px-5 py-6 sm:px-7"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="feature-decision-grid-title" className="text-lg font-semibold text-ink">{t.title}</h2>
        <span className="text-sm text-ink-muted">{t.signals(signals.length)}</span>
      </div>
      <p className="mt-1 max-w-[62ch] text-sm leading-6 text-ink-muted">{t.body}</p>

      <div className="mt-6 space-y-7">
        {shown.map((group) => (
          <section key={group.id} aria-label={group.label}>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-line pb-2">
              <h3 className="text-[15px] font-semibold text-ink">{group.label}</h3>
              <p className="text-[13px] leading-5 text-ink-muted">{group.caution}</p>
            </div>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {group.signals.map((signal) => {
                const expanded = expandedFeature === signal.featureName;
                const hint = signal.interpretationHint && signal.interpretationHint !== INTERPRETATION_HINT
                  ? signal.interpretationHint
                  : signal.description;
                return (
                  <div
                    key={signal.featureName}
                    data-testid={`feature-grid-${signal.featureName}`}
                    className={`flex flex-col rounded-card border border-line bg-surface-muted/60 p-3.5 sm:p-4 ${expanded ? "sm:col-span-2 xl:col-span-3" : ""}`}
                  >
                    <dt className="text-sm font-semibold text-ink">{signal.displayName}</dt>
                    {/* A value that could not be computed says so in words, not as a code. */}
                    {computed(signal.value) ? (
                      <dd className="mt-1 font-display text-[1.75rem] font-semibold leading-none text-ink tabular-nums sm:text-[2rem]">
                        {signal.value}
                        {signal.unit ? <span className="ml-1.5 text-sm font-medium text-ink-muted">{signal.unit}</span> : null}
                      </dd>
                    ) : (
                      <dd className="mt-1 flex items-baseline gap-2">
                        <span aria-hidden="true" className="font-display text-[1.75rem] font-semibold leading-none text-ink-subtle sm:text-[2rem]">—</span>
                        <span className="text-sm font-medium text-ink-muted">{t.notComputed}</span>
                      </dd>
                    )}
                    {hint ? <dd className="mt-2 text-[13px] leading-5 text-ink-muted">{hint}</dd> : null}
                    {signal.referenceText && signal.referenceText !== NO_REFERENCE ? (
                      <dd className="mt-1 text-[13px] leading-5 text-ink-muted">{label(signal.referenceText)}</dd>
                    ) : null}
                    <dd className="mt-auto pt-2">
                      <button
                        type="button"
                        className="-ml-1 inline-flex min-h-11 items-center px-1 text-[13px] font-semibold text-brand-strong underline decoration-brand/30 underline-offset-4 hover:decoration-brand"
                        aria-expanded={expanded}
                        onClick={() => setExpandedFeature(expanded ? null : signal.featureName)}
                      >
                        {expanded ? t.hide : t.show}
                      </button>
                    </dd>
                    {expanded ? (
                      <dd className="mt-1 grid gap-3 border-t border-line pt-3 text-sm leading-6 text-ink-muted sm:grid-cols-3">
                        <div>
                          <h4 className="font-semibold text-ink">{t.method}</h4>
                          <p className="mt-1">{signal.calculationMethod}</p>
                          {signal.referenceText ? <p className="mt-1">{label(signal.referenceText)}</p> : null}
                        </div>
                        {signal.limitations.length ? (
                          <div>
                            <h4 className="font-semibold text-ink">{t.limitations}</h4>
                            <ul className="mt-1 list-disc space-y-1 pl-5">
                              {signal.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        <div>
                          <h4 className="font-semibold text-ink">{t.caution}</h4>
                          <p className="mt-1">{signal.clinicalInterpretationCaution}</p>
                        </div>
                      </dd>
                    ) : null}
                  </div>
                );
              })}
            </dl>
          </section>
        ))}
      </div>

      <div className="mt-6 space-y-1 border-t border-line pt-4 text-[13px] leading-5 text-ink-muted">
        {anyReference ? null : <p>{label(NO_REFERENCE)}</p>}
        <p>{safety.INTERPRETATION_HINT}</p>
        <p>{t.footer}</p>
      </div>
    </section>
  );
}

const NO_REFERENCE = "Reference comparison unavailable";

function computed(value: string | undefined): boolean {
  const text = value?.trim().toLowerCase() ?? "";
  return text !== "" && text !== "not_available" && text !== "n/a" && text !== "none";
}

const decisionGroupIds = ["language-sample", "lexical-use", "interaction", "speech-intelligibility", "data-quality"] as const;

function groupId(featureName: string): (typeof decisionGroupIds)[number] {
  const name = featureName.toLowerCase();
  if (/(unclear|confidence|missing|timing|timestamp|quality|completeness|coverage)/.test(name)) return "data-quality";
  if (/(echolalia|repetition|pronoun|intellig|speech|phon|articul)/.test(name)) return "speech-intelligibility";
  if (/(question|turn|response|speaker|interaction|adult_utterance|child_utterance)/.test(name)) return "interaction";
  if (/(ttr|type_token|lexic|vocab|distinct|different_word|ndw|total_word)/.test(name)) return "lexical-use";
  return "language-sample";
}
