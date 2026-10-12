"use client";

import type { Locale } from "@/i18n/config";
import { useLocale } from "@/i18n/locale-provider";
import { FINDINGS_LABELS_TH } from "@/features/sessions/findings/findings-labels.th";

const VERSION = /^Version (.+)$/;
const WITH_MEASURE = /^(Pass|Warning)( · \d+%)$/;

/** A derived Findings label in one interface language; unknown text passes through. */
export function findingsLabel(label: string, locale: Locale): string {
  if (locale === "en") return label;
  const exact = FINDINGS_LABELS_TH[label];
  if (exact) return exact;
  const version = VERSION.exec(label);
  if (version) return `เวอร์ชัน ${version[1]}`;
  const measured = WITH_MEASURE.exec(label);
  if (measured) return `${FINDINGS_LABELS_TH[measured[1]]}${measured[2]}`;
  return label;
}

/** Translates derived Findings labels into the current interface language. */
export function useFindingsLabel(): (label: string) => string {
  const { locale } = useLocale();
  return (label) => findingsLabel(label, locale);
}
