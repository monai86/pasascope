"use client";

import { STATUS_MESSAGES_TH } from "@/features/sessions/state/status-messages.th";
import type { Locale } from "@/i18n/config";
import { useLocale } from "@/i18n/locale-provider";

/** A session status or error message in one interface language; unknown text passes through. */
export function statusText(message: string | undefined, locale: Locale): string | undefined {
  if (!message || locale === "en") return message;
  return STATUS_MESSAGES_TH[message] ?? message;
}

/** Translates session status and error messages into the current interface language. */
export function useStatusText(): (message: string | undefined) => string | undefined {
  const { locale } = useLocale();
  return (message) => statusText(message, locale);
}
