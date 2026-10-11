/**
 * Browser state that starts every Playwright context in English.
 *
 * Thai is the product default, and these suites assert English headings,
 * labels and safety copy, so the language cookie is pinned here. The
 * language-switch spec clears it to exercise the default and the toggle.
 */
export const LOCALE_COOKIE_NAME = "pasascope_locale";

export function englishLocaleState(host = "127.0.0.1") {
  return {
    cookies: [
      {
        name: LOCALE_COOKIE_NAME,
        value: "en",
        domain: host,
        path: "/",
        expires: -1,
        httpOnly: false,
        secure: false,
        sameSite: "Lax" as const,
      },
    ],
    origins: [],
  };
}
