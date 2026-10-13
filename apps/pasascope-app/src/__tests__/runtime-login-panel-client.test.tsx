import { act, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";
import { resetRuntimeSettingsCache } from "@/lib/use-runtime-settings";

test("holds the form's place while the API has not answered, and says when it is slow", async () => {
  vi.useFakeTimers();
  // A request that never settles, as while a sleeping host wakes.
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => {})));

  try {
    render(<RuntimeLoginPanelClient />);

    const panel = screen.getByRole("status");
    expect(panel).toHaveTextContent("Getting sign-in ready…");
    // Full width, so it cannot collapse to a sliver beside the heading.
    expect(panel).toHaveClass("w-full");
    expect(screen.getByText(/starting up/)).toHaveClass("invisible");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });

    expect(screen.getByText(/starting up/)).not.toHaveClass("invisible");
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  } finally {
    vi.useRealTimers();
    // The unanswered request is shared between consumers; later tests need their own.
    resetRuntimeSettingsCache();
  }
});

test("does not expose mock login when runtime settings are malformed", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    mock_mode: true,
    auth_mode: "mock",
    capabilities: { cases: "maybe" },
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  })));

  render(<RuntimeLoginPanelClient />);

  expect(await screen.findByRole("heading", { name: "Runtime settings unavailable" })).toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Mock login form" })).not.toBeInTheDocument();
});

test("does not expose mock login for an unknown runtime auth mode", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    ...validRuntimeSettings,
    auth_mode: "oidc",
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  })));

  render(<RuntimeLoginPanelClient />);

  expect(await screen.findByRole("heading", { name: "Runtime settings unavailable" })).toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Mock login form" })).not.toBeInTheDocument();
});

const validRuntimeSettings = {
  mock_mode: false,
  auth_mode: "supabase",
  model_version: "v2-mock",
  feature_schema: "pasascope-app.1",
  guideline_mapping: "review-support-only",
  user_roles: ["therapist"],
  data_retention: "configured",
  consent_policy: "required",
  capabilities: {
    cases: "available",
    audio_upload: "unavailable",
    transcription: "unavailable",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "disabled",
    pdf_export: "unavailable",
  },
  pipeline_settings: {
    audio_processing: "experimental_async",
    job_queue_mode: "redis",
    repository_mode: "sql",
    storage_mode: "supabase_private",
  },
};
