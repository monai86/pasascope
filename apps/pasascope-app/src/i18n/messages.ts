import type { Locale } from "@/i18n/config";

export type MessageCatalog<T> = Readonly<Record<Locale, T>>;

/**
 * Declares one feature's strings in both interface languages. The Thai entry
 * must have the shape of the English one, so a key added to one language and
 * forgotten in the other is a type error rather than a blank label.
 *
 * Catalogs live beside the feature that renders them (`*.messages.ts`) so the
 * strings ship in that feature's chunk instead of the shared bundle.
 */
export function defineMessages<T>(messages: { en: T; th: NoInfer<T> }): MessageCatalog<T> {
  return messages;
}

export function selectMessages<T>(catalog: MessageCatalog<T>, locale: Locale): T {
  return catalog[locale];
}
