import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { capturePairedEvidence } from "./evidence-screenshots";

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 1366 },
  { name: "small-desktop", width: 1280, height: 800 },
  { name: "desktop", width: 1440, height: 900 },
];

const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://127.0.0.1:${backendPort}/api/v1`;
const authHeaders = {
  "X-Mock-Role": "therapist",
  "X-Mock-User-Id": "therapist-demo",
  "X-Organization-Id": "pilot_org_001",
};

async function setTherapistSession(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("pasascope.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });
}

async function createResponsiveTranscript(request: APIRequestContext, viewportName: string) {
  const caseResponse = await request.post(`${backendBaseUrl}/cases`, {
    headers: authHeaders,
    data: {
      child_code: `RESP-${viewportName}`,
      age_months: 60,
      language: "English",
      consent_status: "granted",
    },
  });
  expect(caseResponse.ok(), await caseResponse.text()).toBe(true);
  const caseId = (await caseResponse.json()).case_id as string;
  const sessionResponse = await request.post(`${backendBaseUrl}/cases/${caseId}/sessions`, {
    headers: authHeaders,
    data: { session_date: "2026-07-21", session_type: "language_sample" },
  });
  expect(sessionResponse.ok(), await sessionResponse.text()).toBe(true);
  const sessionId = (await sessionResponse.json()).session_id as string;
  const transcriptResponse = await request.post(`${backendBaseUrl}/sessions/${sessionId}/transcripts/manual`, {
    headers: authHeaders,
    data: {
      text: [
        "THER: What do you see in the picture?",
        "CHI: I see the blue car.",
        "THER: Tell me more about the car.",
        "CHI: The car goes to the house.",
      ].join("\n"),
      language: "English",
    },
  });
  expect(transcriptResponse.ok(), await transcriptResponse.text()).toBe(true);
  return sessionId;
}

for (const viewport of viewports) {
  test(`Transcript workbench keeps editing, QA and saving within reach at ${viewport.name}`, async ({ page, request }) => {
    let evidenceCaptured = false;
    await page.setViewportSize(viewport);
    await setTherapistSession(page);
    const sessionId = await createResponsiveTranscript(request, viewport.name);
    await page.goto(`/sessions/${sessionId}?view=transcript`, { waitUntil: "networkidle" });

    await expect(page.getByRole("heading", { name: "Review Transcript", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Session context" })).toBeVisible();

    if (await page.getByRole("option", { name: "Transcript line 1", exact: true }).count() === 0) {
      await page.getByRole("button", { name: "Add line" }).click();
    }
    const line = page.getByRole("option", { name: "Transcript line 1", exact: true });
    await line.getByLabel("Utterance text 1", { exact: true }).fill("The child points to the blue car.");
    await expect(line).toHaveAttribute("aria-selected", "true");
    await expect(line.getByRole("button", { name: "More actions for line 1" })).toBeVisible();

    await page.waitForTimeout(250);
    const dimensions = await page.evaluate(() => ({
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);

    // One column at every width: the lines take the editor's full width.
    const widths = await page.evaluate(() => {
      const workspace = document.querySelector<HTMLElement>("[data-testid='transcript-workbench']")!;
      const editor = document.querySelector<HTMLElement>("[role='listbox'][aria-label='Transcript lines']")!;
      return { workspace: workspace.getBoundingClientRect().width, editor: editor.getBoundingClientRect().width };
    });
    expect(widths.editor / widths.workspace).toBeGreaterThanOrEqual(0.95);

    // QA results open in place, below the lines.
    await page.getByTestId("mobile-transcript-qa-details").locator("summary").click();
    await expect(page.getByTestId("transcript-qa-panel")).toBeVisible();
    await page.getByTestId("mobile-transcript-qa-details").locator("summary").click();

    if (viewport.width < 768) {
      await page.locator("#main-content").evaluate((main) => main.scrollTo(0, 0));
      await line.getByLabel("Utterance text 1").scrollIntoViewIfNeeded();
      const mobileContract = await page.evaluate(() => {
        const mobileHeader = document.querySelector<HTMLElement>("header")!;
        const actions = document.querySelector<HTMLElement>("[data-testid='mobile-transcript-primary-actions']")!;
        const bar = actions.parentElement!;
        const firstUtterance = document.querySelector<HTMLElement>("textarea[aria-label='Utterance text 1']")!;
        const mobileBrand = mobileHeader.querySelector<HTMLElement>("span")!;
        const barRect = bar.getBoundingClientRect();
        const utteranceRect = firstUtterance.getBoundingClientRect();
        return {
          mobileHeaderTop: mobileHeader.getBoundingClientRect().top,
          mobileBrandTop: mobileBrand.getBoundingClientRect().top,
          barPosition: getComputedStyle(bar).position,
          barTop: barRect.top,
          barBottom: barRect.bottom,
          firstUtteranceTop: utteranceRect.top,
          firstUtteranceBottom: utteranceRect.bottom,
          viewportHeight: window.innerHeight,
        };
      });
      expect(mobileContract.mobileHeaderTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.mobileBrandTop).toBeGreaterThanOrEqual(0);
      // Save and QA stay on screen while the lines are edited.
      expect(mobileContract.barPosition).toBe("sticky");
      expect(mobileContract.barTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.barBottom).toBeLessThanOrEqual(mobileContract.viewportHeight + 1);
      expect(mobileContract.firstUtteranceTop).toBeGreaterThanOrEqual(0);
      expect(mobileContract.firstUtteranceBottom).toBeLessThanOrEqual(mobileContract.barTop);

      await capturePairedEvidence(page, "transcript", viewport);
      evidenceCaptured = true;

      const lastLine = page.locator("[role='option'][aria-label^='Transcript line']").last();
      await lastLine.evaluate((node) => node.scrollIntoView({ block: "center" }));
      const overlap = await page.evaluate(() => {
        const rows = [...document.querySelectorAll<HTMLElement>("[role='option'][aria-label^='Transcript line']")];
        const lastRow = rows.at(-1)!;
        const bar = document.querySelector<HTMLElement>("[data-testid='mobile-transcript-primary-actions']")!.parentElement!;
        return lastRow.getBoundingClientRect().bottom - bar.getBoundingClientRect().top;
      });
      expect(overlap).toBeLessThanOrEqual(0);
    }

    if (!evidenceCaptured) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await capturePairedEvidence(page, "transcript", viewport);
    }
  });
}
