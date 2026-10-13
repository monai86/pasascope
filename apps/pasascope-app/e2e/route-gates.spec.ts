import { expect, test } from "@playwright/test";

// These are checked at the HTTP level on purpose. A Suspense boundary above a
// page (a root `loading.tsx`, for one) starts streaming a 200 before the page
// can call notFound() or redirect(), which turns a real 404 into a soft one
// and a redirect into in-page navigation. The gates below must stay hard.

test.describe("the removed demo routes stay gone", () => {
  for (const route of ["/demo", "/demo/dashboard", "/demo/report", "/demo/design-system", "/reports/preview"]) {
    test(`${route} answers 404`, async ({ request }) => {
      const response = await request.get(route, { maxRedirects: 0 });

      expect(response.status()).toBe(404);
      const body = await response.text();
      expect(body).not.toContain("Sample data demonstration");
      expect(body).not.toContain("Sample layout with invented data");
    });
  }
});

test("an unknown route answers 404 with a way back", async ({ page }) => {
  const response = await page.goto("/this-route-does-not-exist");

  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "This page does not exist" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Go to home" })).toHaveAttribute("href", "/");
});

test("the retired assistant and dashboard routes lead home", async ({ request }) => {
  for (const route of ["/assistant", "/dashboard"]) {
    const response = await request.get(route, { maxRedirects: 0 });

    expect(response.status(), route).toBe(307);
    expect(response.headers().location, route).toMatch(/^(https?:\/\/[^/]+)?\/$/);
  }
});

test("the root route is the home screen itself, not a redirect", async ({ request, page }) => {
  const response = await request.get("/", { maxRedirects: 0 });
  expect(response.status()).toBe(200);

  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('[data-shell="chat"]')).toBeVisible();
});
