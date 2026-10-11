import { expect, test, type APIRequestContext, type Locator } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const desktopViewports = [
  { name: "desktop-compact", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

const requiredViewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  ...desktopViewports,
];

async function visibleCount(locator: Locator) {
  return locator.evaluateAll((elements) => elements.filter((element) => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }).length);
}

const backendBaseUrl = `http://127.0.0.1:${process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000"}/api/v1`;
const authHeaders = {
  "X-Mock-Role": "therapist",
  "X-Mock-User-Id": "therapist-demo",
  "X-Organization-Id": "pilot_org_001",
};

// One queue row per case. Seed enough cases for the density check so it does
// not depend on which specs ran earlier. Each case gets a session so it never
// shows up as a second "Start session" row.
async function seedQueueCases(request: APIRequestContext, prefix: string) {
  for (const index of [1, 2, 3, 4]) {
    const created = await request.post(`${backendBaseUrl}/cases`, {
      headers: authHeaders,
      data: { child_code: `${prefix}-${index}`, age_months: 60, language: "English", consent_status: "granted" },
    });
    expect(created.ok(), await created.text()).toBe(true);
    const caseId = (await created.json()).case_id as string;
    const session = await request.post(`${backendBaseUrl}/cases/${caseId}/sessions`, {
      headers: authHeaders,
      data: { session_date: "2026-07-21", session_type: "language_sample" },
    });
    expect(session.ok(), await session.text()).toBe(true);
  }
}

for (const viewport of desktopViewports) {
  test(`Today keeps the prioritized workbench dominant at ${viewport.name}`, async ({ page, request }) => {
    await seedQueueCases(request, `TODAY-${viewport.name}`);
    await page.setViewportSize(viewport);
    await page.goto("/today");
    await expect(page.getByRole("heading", { name: "Today", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Prioritized queue" })).toBeVisible();

    const primaryWorkbench = page.getByTestId("today-primary-workbench");
    const contextualRail = page.locator("aside").filter({ hasText: "Today context" });
    await expect(primaryWorkbench).toBeVisible();
    await expect(contextualRail).toBeVisible();

    const primaryBox = await primaryWorkbench.boundingBox();
    const railBox = await contextualRail.boundingBox();
    expect(primaryBox).not.toBeNull();
    expect(railBox).not.toBeNull();
    expect(primaryBox!.width).toBeGreaterThanOrEqual(railBox!.width * 1.8);

    const queueRowsAboveFold = await page.getByTestId("today-queue-row").evaluateAll((rows) => rows.filter((row) => {
      const rect = row.getBoundingClientRect();
      return rect.top < window.innerHeight && rect.bottom > 0;
    }).length);
    expect(queueRowsAboveFold).toBeGreaterThanOrEqual(viewport.height <= 800 ? 3 : 4);

    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
  });
}

for (const viewport of requiredViewports) {
  test(`Today renders one focused action and one contextual surface at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/today");
    await expect(page.getByRole("heading", { name: "Today", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Prioritized queue" })).toBeVisible();

    const startSession = page.getByRole("link", { name: "Start session", exact: true });
    expect(await visibleCount(startSession)).toBe(1);
    expect((await startSession.boundingBox())?.height).toBeGreaterThanOrEqual(44);
    expect(await visibleCount(page.getByRole("heading", { name: "Today context" }))).toBe(1);
    expect(await visibleCount(page.getByRole("heading", { name: "Quick Actions" }))).toBe(0);
    expect(await visibleCount(page.getByRole("heading", { name: "Today's sessions" }))).toBe(0);
    expect(await visibleCount(page.getByRole("heading", { name: "Recent results" }))).toBe(0);
    await expect(page.getByText(/What needs your decision next, in one prioritized list/)).toBeVisible();
    await expect(page.getByText(/Backend confirmed/)).toHaveCount(0);

    const queueRows = page.getByTestId("today-queue-row");
    expect(await queueRows.count()).toBeGreaterThan(0);
    for (let index = 0; index < await queueRows.count(); index += 1) {
      await expect(queueRows.nth(index).getByRole("link")).toHaveCount(1);
    }

    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);

    await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
    await capturePairedEvidence(page, "today", viewport);
  });
}
