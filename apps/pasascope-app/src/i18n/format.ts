import { INTL_LOCALE, type Locale } from "@/i18n/config";

type DateInput = Date | string | number;

function toDate(value: DateInput): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * Formats a date in the interface language. An unparseable value yields an
 * empty string so a caller never shows "Invalid Date" to a clinician.
 */
export function formatDate(
  value: DateInput,
  locale: Locale,
  options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" },
): string {
  const date = toDate(value);
  return date ? new Intl.DateTimeFormat(INTL_LOCALE[locale], options).format(date) : "";
}

export function formatDateTime(value: DateInput, locale: Locale): string {
  return formatDate(value, locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(value: number, locale: Locale, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(INTL_LOCALE[locale], options).format(value);
}
