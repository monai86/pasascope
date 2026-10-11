import { expect, test } from "@playwright/test";

// These are checked at the HTTP level on purpose. A Suspense boundary above a
// page (a root `loading.tsx`, for one) starts streaming a 200 before the page
// can call notFound() or redirect(), which turns a real 404 into a soft one
// and a redirect into in-page navigation. The gates below must stay hard.

test.describe("routes that must not exist outside demo mode", () => {
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
  await expect(page.getByRole("link", { name: "Go to Today" })).toHaveAttribute("href", "/today");
});

test("the retired assistant route redirects to Today", async ({ request }) => {
  const response = await request.get("/assistant", { maxRedirects: 0 });

  expect(response.status()).toBe(307);
  expect(response.headers().location).toMatch(/\/today$/);
});

test("the root route redirects to Today", async ({ request }) => {
  const response = await request.get("/", { maxRedirects: 0 });

  expect([307, 308]).toContain(response.status());
  expect(response.headers().location).toMatch(/\/today$/);
});
