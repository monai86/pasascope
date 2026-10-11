"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE,
  LOCALE_COOKIE_MAX_AGE_SECONDS,
  type Locale,
} from "@/i18n/config";
import { selectMessages, type MessageCatalog } from "@/i18n/messages";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

// A component rendered without a provider (an isolated unit test, a story)
// still needs a language. The unit-test setup pins this to English.
let localeWithoutProvider: Locale = DEFAULT_LOCALE;

export function setLocaleWithoutProviderForTests(locale: Locale) {
  localeWithoutProvider = locale;
}

export function LocaleProvider({
  initialLocale,
  children,
}: {
  initialLocale: Locale;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    // The cookie is what the server reads on the next request, so the first
    // byte of every later page is already in the chosen language.
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${LOCALE_COOKIE_MAX_AGE_SECONDS}; samesite=lax`;
    document.documentElement.lang = next;
  }, []);

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (context) return context;
  return { locale: localeWithoutProvider, setLocale: () => {} };
}

/** The current language's entry of a feature catalog. */
export function useMessages<T>(catalog: MessageCatalog<T>): T {
  return selectMessages(catalog, useLocale().locale);
}
