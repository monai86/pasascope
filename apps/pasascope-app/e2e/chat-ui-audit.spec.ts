import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { UI_AUDIT_HARD_GATES, uiDesignAuditBattery } from "./support/ui-audit-battery";

/**
 * The UI design audit for the chat shell: the same battery and hard gates as
 * `ui-design-audit.spec.ts` (heading skips, text under 12px, icon-only buttons
 * without a name, touch targets under 40px, sideways overflow), run over the
 * chat home, the start-session conversation and a session conversation at
 * each of its stages, on a phone and on a desktop.
 */
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://127.0.0.1:${backendPort}`;
const caseId = "case_demo_001";

const mockHeaders = {
  "X-Mock-Role": "therapist",
  "X-Mock-User-Id": "therapist-demo",
  "X-Organization-Id": "pilot_org_001",
  "content-type": "application/json",
};

const transcript = [
  "THER: what do you see",
  "CHI: I see a red car",
  "THER: tell me more",
  "CHI: the car goes fast",
  "CHI: I want car again",
].join("\n");

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1280, height: 800 },
];

let emptySessionId = "";
let reportSessionId = "";

async function createSession(request: APIRequestContext): Promise<string> {
  const response = await request.post(`${backendBaseUrl}/api/v1/cases/${caseId}/sessions`, {
    headers: mockHeaders,
    data: { session_date: "2026-10-13", session_type: "therapy_session", notes: "" },
  });
  expect(response.ok(), `create session: ${response.status()} ${await response.text()}`).toBeTruthy();
  return (await response.json()).session_id;
}

test.beforeAll(async ({ request }) => {
  emptySessionId = await createSession(request);
  reportSessionId = await createSession(request);

  const saved = await request.post(`${backendBaseUrl}/api/v1/sessions/${reportSessionId}/transcripts/manual`, {
    headers: mockHeaders,
    data: { text: transcript, language: "English", replace_existing: true },
  });
  expect(saved.ok(), `save transcript: ${saved.status()} ${await saved.text()}`).toBeTruthy();
  const transcriptId = (await saved.json()).transcript_id;

  const features = await request.post(`${backendBaseUrl}/api/v1/transcripts/${transcriptId}/extract-features`, {
    headers: mockHeaders,
    data: {},
  });
  expect(features.ok(), `extract features: ${features.status()} ${await features.text()}`).toBeTruthy();

  const report = await request.post(`${backendBaseUrl}/api/v1/sessions/${reportSessionId}/reports/draft`, {
    headers: mockHeaders,
    data: {},
  });
  expect(report.ok(), `draft report: ${report.status()} ${await report.text()}`).toBeTruthy();
});

async function expectAuditGatesPass(page: Page, surface: string) {
  await page.waitForTimeout(300);
  const audit = (await page.evaluate(uiDesignAuditBattery)) as Record<string, unknown>;
  for (const gate of UI_AUDIT_HARD_GATES) {
    if (gate === "overflow") {
      expect(audit[gate], `${surface}: horizontal overflow detected`).toBe(false);
    } else {
      expect(audit[gate], `${surface}: ${gate} violations: ${JSON.stringify(audit[gate], null, 2)}`).toEqual([]);
    }
  }
  // Every screen has exactly one top-level heading, seen or only announced.
  await expect(page.getByRole("heading", { level: 1 }), `${surface}: one h1`).toHaveCount(1);
}

for (const viewport of viewports) {
  test(`chat shell passes the UI audit gates at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const at = (surface: string) => `${surface}@${viewport.name}`;

    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.getByTestId("home-card-record")).toBeVisible();
    await expectAuditGatesPass(page, at("home"));

    await page.getByTestId("home-card-record").click();
    await expect(page.getByTestId("start-pick-case")).toBeVisible();
    await expectAuditGatesPass(page, at("start-pick-case"));

    await page.getByTestId("start-new-case").click();
    await expect(page.getByTestId("start-new-case-form")).toBeVisible();
    await expectAuditGatesPass(page, at("start-new-case"));

    await page.goto(`/sessions/${emptySessionId}?view=chat&mode=audio`, { waitUntil: "networkidle" });
    await expect(page.getByTestId("chat-ask-audio")).toBeVisible();
    await expectAuditGatesPass(page, at("session-ask-audio"));

    await page.goto(`/sessions/${emptySessionId}?view=chat&mode=recording`, { waitUntil: "networkidle" });
    await expect(page.getByTestId("chat-ask-audio")).toBeVisible();
    await expectAuditGatesPass(page, at("session-recorder"));

    await page.goto(`/sessions/${reportSessionId}?view=chat`, { waitUntil: "networkidle" });
    await expect(page.getByTestId("chat-report-ready")).toBeVisible();
    await expectAuditGatesPass(page, at("session-report-ready"));

    // The side panel is a column on desktop and a sheet on a phone.
    if (viewport.name === "mobile") {
      await page.getByRole("button", { name: "Session details" }).click();
      await expect(page.getByRole("heading", { name: "Notes" })).toBeVisible();
      await expectAuditGatesPass(page, at("session-details-sheet"));
    }
  });
}
