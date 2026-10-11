import { cookies } from "next/headers";

import { LOCALE_COOKIE, resolveLocale, type Locale } from "@/i18n/config";
import { selectMessages, type MessageCatalog } from "@/i18n/messages";

/**
 * The language chosen for this request. Reading the cookie makes the calling
 * route render per request, which is what a per-visitor language needs.
 */
export async function getRequestLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  return resolveLocale(cookieStore.get(LOCALE_COOKIE)?.value);
}

export async function getMessages<T>(catalog: MessageCatalog<T>): Promise<T> {
  return selectMessages(catalog, await getRequestLocale());
}
