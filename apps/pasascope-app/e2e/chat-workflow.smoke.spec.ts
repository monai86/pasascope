import { expect, test, type Page } from "@playwright/test";

// A transcript with two lines whose speaker is not known, as a recording
// transcribed without speaker separation would have.
const transcript = [
  "@UTF8",
  "@Begin",
  "@Languages:\ttha",
  "@Participants:\tCHI Target_Child, THER Therapist",
  "@ID:\ttha|sample|CHI|||||Target_Child|||",
  "@ID:\ttha|sample|THER|||||Therapist|||",
  "*THER:\twhat do you see .",
  "*CHI:\tI see a red car .",
  "*UNK:\ttell me more .",
  "*CHI:\tthe car goes fast .",
  "*UNK:\twhere does it go .",
  "*CHI:\tit goes home .",
  "@End",
  "",
].join("\n");

async function expectNoSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

async function startSessionForNewCase(page: Page, code: string) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "What would you like to do today?" })).toBeVisible();

  await page.getByTestId("home-card-record").click();
  await page.getByTestId("start-new-case").click();
  const form = page.getByTestId("start-new-case-form");
  await form.getByLabel("Case code").fill(code);
  await form.getByLabel("Age: years").fill("4");
  await form.getByLabel("Age: months").fill("2");
  await form.getByRole("button", { name: "Create case" }).click();

  // A new case has no consent, and no session may exist before it is given.
  const consent = page.getByTestId("start-consent");
  await expect(consent).toBeVisible();
  await expect(consent.getByRole("button", { name: "Confirm and continue" })).toBeDisabled();
  await consent.getByRole("checkbox").check();
  await consent.getByRole("button", { name: "Confirm and continue" }).click();

  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=chat.*mode=recording/);
  await expect(page.getByTestId("chat-ask-audio")).toBeVisible();
}

test.describe("chat shell", () => {
  test("home offers the four destinations and three ways to begin", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "What would you like to do today?" })).toBeVisible();
    const navigation = page.getByRole("navigation", { name: "Primary navigation" });
    await expect(navigation.getByRole("link")).toHaveText(["Home", "Cases", "Reports", "Settings"]);
    await expect(page.getByRole("navigation", { name: "Bottom navigation" })).toHaveCount(0);
    await expect(page.getByTestId("home-card-record")).toBeVisible();
    await expect(page.getByTestId("home-card-upload")).toBeVisible();
    await expect(page.getByTestId("home-card-resume")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent sessions" })).toBeVisible();
  });

  test("a session goes from a new case to a report draft in one conversation", async ({ page }) => {
    await startSessionForNewCase(page, `E2E-${Date.now()}`);

    await page.locator('[data-testid="session-composer"] input[type="file"]').setInputFiles({
      name: "sample.cha",
      mimeType: "text/plain",
      buffer: Buffer.from(transcript, "utf8"),
    });

    const ready = page.getByTestId("chat-transcript-ready");
    await expect(ready).toContainText("2 lines still have no speaker");
    await ready.getByRole("button", { name: "The rest are the therapist" }).click();

    const complete = page.getByTestId("chat-speakers-complete");
    await expect(complete).toContainText("Every line now has a speaker");
    await complete.getByRole("button", { name: "Extract the language measures" }).click();

    const measures = page.getByTestId("chat-measures");
    await expect(measures.getByTestId("measure-mlu")).toHaveText(/\d/);
    await expect(measures).toContainText("Therapist interpretation required.");
    // Extraction stays in the conversation.
    await expect(page).toHaveURL(/view=chat/);

    await measures.getByRole("button", { name: "Draft the report" }).click();
    await expect(page).toHaveURL(/view=report/);

    await page.getByRole("link", { name: "Back to the conversation" }).click();
    await expect(page).toHaveURL(/view=chat/);
    await expect(page.getByTestId("chat-report-ready")).toBeVisible();
    await expect(page.getByTestId("reply-open-report")).toBeVisible();

    // The thread is rebuilt from the session's saved state, not from memory.
    await page.reload();
    await expect(page.getByTestId("chat-transcript-ready")).toBeVisible();
    await expect(page.getByTestId("chat-measures").getByTestId("measure-mlu")).toHaveText(/\d/);
    await expect(page.getByTestId("chat-report-ready")).toBeVisible();
  });

  test("a typed note is saved to the session and shown again after a reload", async ({ page }) => {
    await startSessionForNewCase(page, `E2E-NOTE-${Date.now()}`);

    await page.getByRole("textbox", { name: "Session note" }).fill("Played with toy cars");
    await page.getByRole("button", { name: "Save note" }).click();
    await expect(page.getByText("Saved as a session note.")).toBeVisible();

    await page.reload();
    await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();
    await expect(page.getByText("Played with toy cars")).toBeVisible();
  });

  for (const viewport of [
    { name: "phone", width: 390, height: 844 },
    { name: "tablet", width: 834, height: 1100 },
  ]) {
    test(`fits a ${viewport.name} without sideways scrolling`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/");

      await expect(page.getByRole("heading", { name: "What would you like to do today?" })).toBeVisible();
      await expectNoSidewaysScroll(page);

      // Navigation is a drawer here; it opens, traps focus and closes on Escape.
      const menu = page.getByRole("button", { name: "Open navigation menu" });
      await menu.click();
      await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Cases" })).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(menu).toBeFocused();

      // The recent sessions panel is a sheet opened from the header.
      await page.getByRole("button", { name: "Recent sessions" }).click();
      await expect(page.getByRole("heading", { name: "Recent sessions" })).toBeVisible();
      await page.keyboard.press("Escape");
      await expectNoSidewaysScroll(page);
    });
  }
});
