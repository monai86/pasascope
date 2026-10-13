import { defineConfig, devices } from "@playwright/test";

import { englishLocaleState } from "./e2e/support/locale-state";

function resolvePort(envValue: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(envValue ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const frontendPort = resolvePort(process.env.PLAYWRIGHT_FRONTEND_PORT, 3100);
const backendPort = resolvePort(process.env.PLAYWRIGHT_BACKEND_PORT, 8000);
// Benchmarks need a production build (see webServer below), so they only run
// when explicitly requested: `npx playwright test benchmarks/...`.
const benchmarkRun = process.argv.some((argument) => argument.includes("benchmarks/"));
const allowedOrigins = [
  `http://127.0.0.1:${frontendPort}`,
  `http://localhost:${frontendPort}`,
].join(",");

export default defineConfig({
  testDir: ".",
  globalSetup: "./e2e/support/warm-therapist-routes.ts",
  testMatch: [
    "e2e/**/*.spec.ts",
    ...(benchmarkRun ? ["benchmarks/**/*.spec.ts"] : []),
  ],
  // The chat-shell specs need servers started differently and have their own config.
  testIgnore: ["e2e/chat-*.spec.ts"],
  timeout: 120_000,
  // The suite runs against a dev server, which can reload a page while it
  // compiles; a test caught by that is tried again in CI and reported as
  // flaky when it then passes, apart from the ones that fail every time.
  retries: process.env.CI ? 2 : 0,
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
      command: `PYTHONPATH=.:../..:../../src PASASCOPE_REPOSITORY_MODE=memory PASASCOPE_CORS_ALLOWED_ORIGINS=${allowedOrigins} python3 -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "../api",
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: benchmarkRun
        ? `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run build && NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run start -- --hostname 127.0.0.1 --port ${frontendPort}`
        : `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${backendPort}/api/v1 npm run dev -- --webpack --hostname 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
