import { defineConfig, devices } from "@playwright/test";

import { englishLocaleState } from "./e2e/support/locale-state";

function resolvePort(envValue: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(envValue ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const frontendPort = resolvePort(process.env.PLAYWRIGHT_CHAT_PORT, 3102);
const backendPort = resolvePort(process.env.PLAYWRIGHT_CHAT_BACKEND_PORT, 8002);
const allowedOrigins = [
  `http://127.0.0.1:${frontendPort}`,
  `http://localhost:${frontendPort}`,
].join(",");

/**
 * Dedicated config for the chat shell. The shell renders when the API runs the
 * public workflow (public sign-up, open review gates), which the default
 * suite's backend does not, and a second dev server cannot run beside the main
 * one under Next 16's single-dev-server lock. So these specs have their own
 * servers.
 *
 * Run with:
 *   npx playwright test -c playwright.chat.config.ts
 */
export default defineConfig({
  testDir: ".",
  testMatch: ["e2e/chat-workflow.smoke.spec.ts", "e2e/chat-ui-audit.spec.ts"],
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: "on-first-retry",
    ...devices["Desktop Chrome"],
    storageState: englishLocaleState(),
  },
  webServer: [
    {
      command: `PYTHONPATH=.:../..:../../src PASASCOPE_REPOSITORY_MODE=memory PASASCOPE_PUBLIC_SIGNUP=true PASASCOPE_REVIEW_GATES=open PASASCOPE_SUPABASE_REQUIRE_MFA=false PASASCOPE_SUPABASE_REQUIRE_INVITATION=false PASASCOPE_CORS_ALLOWED_ORIGINS=${allowedOrigins} python3 -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "../api",
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run dev -- --webpack --hostname 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
