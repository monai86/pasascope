"use client";

import { useState } from "react";

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

  const groups = decisionGroups.map((group) => ({
    ...group,
    signals: signals.filter((signal) => groupId(signal.featureName) === group.id),
  }));

  return (
    <section
      aria-labelledby="feature-decision-grid-title"
      data-testid="feature-decision-grid"
      className="overflow-hidden rounded-shell border border-line bg-surface"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 sm:px-5">
        <div>
          <h2 id="feature-decision-grid-title" className="text-lg font-semibold text-ink">
            Language sample at a glance
          </h2>
          <p className="mt-0.5 text-sm text-ink-muted">
            Every extracted value from this reviewed sample, grouped for quick comparison.
          </p>
        </div>
        <span className="rounded-full bg-brand-soft px-2.5 py-1 text-xs font-semibold text-brand-strong">
          {signals.length} signals
        </span>
      </div>

      <div className="border-t border-line">
        {groups.map((group) => (
          <section key={group.id} aria-label={group.label} className="border-b border-line last:border-b-0">
            <div className="bg-surface px-4 py-2 sm:px-5">
              <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
                {group.label}
              </h3>
            </div>
            <p className="border-t border-line px-4 py-2 text-xs leading-5 text-[color:var(--color-warning-text)] sm:px-5">
              {group.caution}
            </p>
            {group.signals.length ? (
              <dl className="divide-y divide-line">
                {group.signals.map((signal) => {
                  const expanded = expandedFeature === signal.featureName;
                  return (
                    <div key={signal.featureName} data-testid={`feature-grid-${signal.featureName}`} className="px-4 py-2.5 sm:px-5">
                      <div className="grid gap-1 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-baseline sm:gap-6">
                        <div className="min-w-0">
                          <dt className="font-medium text-ink">{signal.displayName}</dt>
                          <dd className="mt-0.5 text-sm leading-5 text-ink-muted">{signal.interpretationHint || signal.description}</dd>
                          {signal.referenceText ? (
                            <dd className={`mt-1 text-xs leading-5 ${signal.referenceText === "Reference comparison unavailable" ? "font-medium text-[color:var(--color-warning-text)]" : "text-ink-muted"}`}>
                              {signal.referenceText}
                            </dd>
                          ) : null}
                        </div>
                        <dd className="shrink-0 text-right text-base font-semibold tabular-nums text-ink">
                          {signal.value}
                          {signal.unit ? <span className="ml-1 text-xs font-medium text-ink-muted">{signal.unit}</span> : null}
                        </dd>
                      </div>
                      <button
                        type="button"
                        className="mt-1 -ml-2 inline-flex min-h-11 items-center px-2 text-sm font-semibold text-brand-strong underline"
                        aria-expanded={expanded}
                        onClick={() => setExpandedFeature(expanded ? null : signal.featureName)}
                      >
                        {expanded ? "Hide evidence and limitations" : "Evidence and limitations"}
                      </button>
                      {expanded ? (
                        <div className="mt-2 space-y-3 rounded-panel border border-line bg-surface p-3 text-sm text-ink-muted">
                          <div>
                            <h4 className="font-semibold text-ink">Method</h4>
                            <p className="mt-1">{signal.calculationMethod}</p>
                          </div>
                          {signal.limitations.length ? (
                            <div>
                              <h4 className="font-semibold text-ink">Limitations</h4>
                              <ul className="mt-1 list-disc space-y-1 pl-5">
                                {signal.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                              </ul>
                            </div>
                          ) : null}
                          <div>
                            <h4 className="font-semibold text-ink">Clinical interpretation caution</h4>
                            <p className="mt-1">{signal.clinicalInterpretationCaution}</p>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </dl>
            ) : (
              <p className="border-t border-line px-4 py-2.5 text-sm text-ink-muted sm:px-5">
                No features from this group in this session.
              </p>
            )}
          </section>
        ))}
      </div>

      <p className="border-t border-line bg-surface px-4 py-2.5 text-xs leading-5 text-ink-muted sm:px-5">
        Values are descriptive cues from the reviewed transcript, not diagnostic results. Compare them with therapist context.
      </p>
    </section>
  );
}

const decisionGroups = [
  { id: "language-sample", label: "Language sample", caution: "Interpret alongside sample length and elicitation context." },
  { id: "lexical-use", label: "Lexical use", caution: "Vocabulary cues depend on the reviewed transcript sample." },
  { id: "interaction", label: "Interaction", caution: "Review with speaker roles and interaction context." },
  { id: "speech-intelligibility", label: "Speech / intelligibility", caution: "Transcript cues are not a substitute for direct speech assessment." },
  { id: "data-quality", label: "Data quality", caution: "Resolve material data-quality concerns before report use." },
] as const;

function groupId(featureName: string): (typeof decisionGroups)[number]["id"] {
  const name = featureName.toLowerCase();
  if (/(unclear|confidence|missing|timing|timestamp|quality|completeness|coverage)/.test(name)) return "data-quality";
  if (/(echolalia|repetition|pronoun|intellig|speech|phon|articul)/.test(name)) return "speech-intelligibility";
  if (/(question|turn|response|speaker|interaction|adult_utterance|child_utterance)/.test(name)) return "interaction";
  if (/(ttr|type_token|lexic|vocab|distinct|different_word|ndw|total_word)/.test(name)) return "lexical-use";
  return "language-sample";
}
