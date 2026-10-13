import { chromium, type FullConfig } from "@playwright/test";

// Every route a spec opens or is taken to by a click.
// A dynamic segment only has to match the route; "warm-up" is no real record.
const routes = [
  "/login",
  "/",
  "/today",
  "/cases",
  "/cases?intent=start-session",
  "/cases/warm-up",
  "/reports",
  "/settings",
  "/privacy",
  "/sessions/warm-up?view=chat",
  "/sessions/warm-up?view=transcript",
  "/sessions/warm-up?view=findings",
  "/sessions/warm-up?view=report",
  "/this-route-does-not-exist",
];

/**
 * The dev server compiles a route, and the scripts a page loads later, on
 * first use. A compile that finishes while a test is on another page reloads
 * that page: a click that should have gone to the new route lands back on the
 * old one, and the test waits for something that never appears. Opening every
 * route once in a real browser before the tests start, signed in as the tests
 * are, keeps those compiles and their reloads out of the run.
 */
export default async function warmTherapistRoutes(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use.baseURL;
  if (!baseURL) return;
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ baseURL });
    await page.addInitScript(() => {
      window.sessionStorage.setItem(
        "pasascope.mock-access-session.v1",
        JSON.stringify({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" }),
      );
    });
    for (const route of routes) {
      await page.goto(route, { waitUntil: "networkidle", timeout: 120_000 }).catch(() => undefined);
    }
  } finally {
    await browser.close();
  }
}
