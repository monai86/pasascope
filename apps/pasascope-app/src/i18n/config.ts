export const LOCALES = ["th", "en"] as const;

export type Locale = (typeof LOCALES)[number];

/** Shown to a visitor who has never chosen a language. */
export const DEFAULT_LOCALE: Locale = "th";

export const LOCALE_COOKIE = "pasascope_locale";

export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** BCP 47 tags used for `Intl` formatting in each interface language. */
export const INTL_LOCALE: Record<Locale, string> = {
  th: "th-TH",
  en: "en-GB",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function resolveLocale(value: unknown): Locale {
  return isLocale(value) ? value : DEFAULT_LOCALE;
}
