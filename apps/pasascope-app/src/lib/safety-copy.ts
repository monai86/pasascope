"use client";

import type { Locale } from "@/i18n/config";
import { useLocale } from "@/i18n/locale-provider";
import { CLINICAL_SAFETY_COPY } from "@/lib/clinical-safety-copy";
import { CLINICAL_SAFETY_COPY_TH, type SafetyCopyKey } from "@/lib/clinical-safety-copy.th";

export type SafetyCopy = Readonly<Record<SafetyCopyKey, string>>;

const english = Object.fromEntries(CLINICAL_SAFETY_COPY) as SafetyCopy;

const byLocale: Record<Locale, SafetyCopy> = {
  en: english,
  th: CLINICAL_SAFETY_COPY_TH,
};

/** The clinical safety copy in one interface language. */
export function safetyCopy(locale: Locale): SafetyCopy {
  return byLocale[locale];
}

/** The clinical safety copy in the current interface language. */
export function useSafetyCopy(): SafetyCopy {
  return safetyCopy(useLocale().locale);
}
