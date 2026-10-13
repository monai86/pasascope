import { expect, test, type Page } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "desktop-compact", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

async function setMockRole(page: Page, role: "therapist") {
  await page.addInitScript((requestedRole) => {
    window.sessionStorage.setItem("pasascope.mock-access-session.v1", JSON.stringify({
      role: requestedRole,
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  }, role);
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document: document.documentElement.scrollWidth,
    offenders: Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .map((element) => ({ element, rect: element.getBoundingClientRect() }))
      .filter(({ rect }) => rect.left < -1 || rect.right > window.innerWidth + 1)
      .slice(0, 10)
      .map(({ element, rect }) => ({
        tag: element.tagName.toLowerCase(),
        text: element.textContent?.trim().replace(/\s+/g, " ").slice(0, 60) ?? "",
        left: Math.round(rect.left),
        right: Math.round(rect.right),
      })),
  }));
  expect(dimensions.document, JSON.stringify(dimensions.offenders)).toBeLessThanOrEqual(dimensions.viewport);
}

for (const viewport of viewports) {
  test(`Settings shows one category at a time at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await setMockRole(page, "therapist");
    await page.goto("/settings", { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
    const therapistNavigation = page.getByRole("navigation", { name: "Settings categories mobile" });
    await expect(therapistNavigation.locator('a[aria-current="page"]')).toHaveText("Account");
    if (viewport.width < 768) {
      await expect(therapistNavigation.getByRole("link", { name: "Account", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Account", exact: true })).toBeHidden();
      await expectNoHorizontalOverflow(page);
      await capturePairedEvidence(page, "settings", viewport);
      await therapistNavigation.getByRole("link", { name: "Account", exact: true }).click();
      await expect(page.getByRole("button", { name: "All settings categories" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Account", exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole("heading", { name: "Account", exact: true })).toBeVisible();
      await expectNoHorizontalOverflow(page);
      await capturePairedEvidence(page, "settings", viewport);
    }
    await expect(page.getByRole("link", { name: "Team", exact: true })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Team", exact: true })).toHaveCount(0);
    await expectNoHorizontalOverflow(page);
  });
}
