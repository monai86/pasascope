"use client";

import type { Locale } from "@/i18n/config";
import { useLocale } from "@/i18n/locale-provider";
import { GATE_REASON_PREFIXES_TH, GATE_REASONS_TH } from "@/lib/workflow-gate-reasons.th";

/** A blocked-action reason from `workflow-gates.ts`, in one interface language. */
export function gateReason(reason: string | undefined, locale: Locale): string | undefined {
  if (!reason || locale === "en") return reason;
  const exact = GATE_REASONS_TH[reason];
  if (exact) return exact;
  const prefix = GATE_REASON_PREFIXES_TH.find(([english]) => reason.startsWith(english));
  // An unknown reason stays in English rather than disappearing.
  return prefix ? `${prefix[1]}${reason.slice(prefix[0].length)}` : reason;
}

/** Translates blocked-action reasons into the current interface language. */
export function useGateReason(): (reason: string | undefined) => string | undefined {
  const { locale } = useLocale();
  return (reason) => gateReason(reason, locale);
}
