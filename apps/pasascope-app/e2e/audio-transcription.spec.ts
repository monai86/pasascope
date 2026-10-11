import { expect, test, type Page } from "@playwright/test";

// Chromium's fake microphone. With PASASCOPE_E2E_ASR_AUDIO set to a WAV file the
// recording carries that audio; otherwise Chromium supplies a test tone.
const recordingFile = process.env.PASASCOPE_E2E_ASR_AUDIO;
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const mockHeaders = { "X-User-Id": "therapist-demo", "X-Mock-Role": "therapist" };

test.use({
  permissions: ["microphone"],
  launchOptions: {
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      ...(recordingFile ? [`--use-file-for-fake-audio-capture=${recordingFile}%noloop`] : []),
    ],
  },
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("pasascope.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
    window.sessionStorage.removeItem("pasascope.therapist.workflow.v1");
  });
});

async function localWhisperAvailable(page: Page): Promise<boolean> {
  const response = await page.request.get(
    `http://127.0.0.1:${backendPort}/api/v1/transcription-providers`,
    { headers: mockHeaders },
  );
  const providers = (await response.json()) as Array<{ provider_id: string; available: boolean }>;
  return providers.some((provider) => provider.provider_id === "local_whisper" && provider.available);
}

async function recordInBrowser(page: Page, milliseconds: number) {
  await page.goto("/cases?intent=start-session");
  await page.getByRole("radio").first().check();
  await page.getByRole("button", { name: "Start session" }).click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=intake/);
  for (const [label, value] of [["Child or client", "Demo child"], ["Clinician", "Demo Therapist"], ["Session date", "2026-07-17"]]) {
    const input = page.getByLabel(label);
    if (!(await input.inputValue()).trim()) await input.fill(value);
  }
  await page.getByRole("button", { name: "Continue to Source Material" }).click();
  await page.getByRole("button", { name: "Record in browser" }).click();
  await page.getByRole("button", { name: "Start recording" }).click();
  await page.waitForTimeout(milliseconds);
  await page.getByRole("button", { name: "Stop recording" }).click();
}

test("a recording is not uploaded when speech recognition is switched off", async ({ page }) => {
  test.skip(await localWhisperAvailable(page), "This server has local Whisper enabled.");
  const uploads: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && request.url().includes("/audio/")) uploads.push(request.url());
  });

  await recordInBrowser(page, 1500);
  await page.getByRole("button", { name: "Upload for transcription" }).click();

  const panel = page.getByRole("region", { name: "Transcription job status" });
  await expect(panel).toContainText("Provider unavailable");
  await expect(panel).toContainText("Speech recognition is not enabled on this server");
  await expect(panel.getByRole("button", { name: "Use manual paste instead" })).toBeVisible();
  // Nothing was sent, and no synthetic transcript was produced in its place.
  expect(uploads).toEqual([]);
  await expect(panel).not.toContainText("Draft transcript ready");
});

test("a recording becomes a Whisper draft that still needs review", async ({ page }) => {
  test.skip(!recordingFile, "Set PASASCOPE_E2E_ASR_AUDIO to a speech WAV file to run this test.");
  test.skip(!(await localWhisperAvailable(page)), "Start the API with PASASCOPE_ASR_LOCAL_WHISPER_ENABLED=true.");
  test.setTimeout(600_000);

  await recordInBrowser(page, 18_000);
  await page.getByRole("button", { name: "Upload for transcription" }).click();

  const panel = page.getByRole("region", { name: "Transcription job status" });
  await expect(panel).toContainText("Draft transcript ready", { timeout: 540_000 });
  await expect(panel).toContainText("Transcribed by: Whisper (on this server)");
  await expect(panel).toContainText("Therapist review required");

  await panel.getByRole("button", { name: "Review transcript" }).click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=transcript/);
  await expect(page.getByText("Draft ASR transcript — therapist review required.")).toBeVisible();
  await expect(page.getByText("No waveform is available")).toHaveCount(0);
  await expect(page.getByTestId("continue-to-attestation-button")).toBeVisible();
});
