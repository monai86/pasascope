import { expect, test, type Page } from "@playwright/test";

// Chromium's fake microphone supplies a test tone, so the recorder in the
// conversation can be driven without a real device.
const backendPort = process.env.PLAYWRIGHT_CHAT_BACKEND_PORT ?? "8002";
const mockHeaders = { "X-User-Id": "therapist-demo", "X-Mock-Role": "therapist" };

test.use({
  permissions: ["microphone"],
  launchOptions: {
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  },
});

async function transcriptionAvailable(page: Page): Promise<boolean> {
  const response = await page.request.get(
    `http://127.0.0.1:${backendPort}/api/v1/transcription-providers`,
    { headers: mockHeaders },
  );
  const providers = (await response.json()) as Array<{ provider_id: string; available: boolean }>;
  return providers.some((provider) => provider.provider_id !== "mock" && provider.provider_id !== "manual" && provider.available);
}

test("a recording made in the conversation is not uploaded when speech recognition is switched off", async ({ page }) => {
  test.skip(await transcriptionAvailable(page), "This server has a transcription provider enabled.");
  const uploads: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && request.url().includes("/audio/")) uploads.push(request.url());
  });

  // The seeded demo case already has consent, so choosing it opens the session.
  await page.goto("/");
  await page.getByTestId("home-card-record").click();
  await page.getByTestId("start-pick-case").getByRole("button", { name: /Demo child/ }).click();
  await expect(page).toHaveURL(/\/sessions\/[^/?]+\?view=chat.*mode=recording/);

  const ask = page.getByTestId("chat-ask-audio");
  await ask.getByRole("button", { name: "Start recording" }).click();
  await page.waitForTimeout(1500);
  await ask.getByRole("button", { name: "Stop recording" }).click();

  // Nothing leaves the page until the therapist says so.
  const confirm = page.getByTestId("chat-confirm-upload");
  await expect(confirm).toContainText("Send this audio for transcription?");
  await expect(page.getByTestId("chat-audio")).toContainText("Session audio");
  expect(uploads).toEqual([]);

  await confirm.getByRole("button", { name: "Send for transcription" }).click();

  const failed = page.getByTestId("chat-transcription-failed");
  await expect(failed).toContainText("Speech recognition is not switched on for this server");
  // Nothing was sent, and no stand-in transcript was produced.
  expect(uploads).toEqual([]);
  await expect(page.getByTestId("chat-transcript-ready")).toHaveCount(0);

  await failed.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByTestId("chat-ask-audio")).toBeVisible();
});
