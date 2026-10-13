import type { FullConfig } from "@playwright/test";

const routes = ["/", "/cases", "/reports", "/settings", "/sessions/warm-up?view=chat"];

/**
 * The dev server compiles a route on its first request, and a compile that
 * finishes while a test is on another page reloads that page. Asking for each
 * route once before the tests start keeps those reloads out of the run.
 */
export default async function warmChatRoutes(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use.baseURL;
  if (!baseURL) return;
  for (const route of routes) {
    await fetch(new URL(route, baseURL), { signal: AbortSignal.timeout(120_000) }).catch(() => undefined);
  }
}
