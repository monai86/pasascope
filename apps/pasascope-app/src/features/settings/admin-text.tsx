"use client";

import { ADMIN_TEXT_TH } from "@/features/settings/admin-text.th";
import type { Locale } from "@/i18n/config";
import { useLocale } from "@/i18n/locale-provider";

/** Organization-administration text in one interface language; unknown text passes through. */
export function adminText(text: string, locale: Locale): string {
  if (locale === "en") return text;
  return ADMIN_TEXT_TH[text.replace(/\s+/g, " ").trim()] ?? text;
}

/** Translates organization-administration text into the current interface language. */
export function useAdminText(): (text: string) => string {
  const { locale } = useLocale();
  return (text) => adminText(text, locale);
}

/** Marks a piece of organization-administration text for translation where it is rendered. */
export function T({ children }: { children: string }) {
  return <>{adminText(children, useLocale().locale)}</>;
}
