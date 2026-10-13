import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { routerPush } from "@/__tests__/setup";
import { SessionChatWorkspace } from "@/features/sessions/components/session-workspace-model";
import { resetRuntimeSettingsCache } from "@/lib/use-runtime-settings";

// The API in public mode: sign-up open and no review gates, which is where the chat shell runs.
const PUBLIC_SETTINGS = {
  mock_mode: true,
  auth_mode: "mock",
  model_version: "test",
  feature_schema: "test",
  guideline_mapping: "review-support-only",
  user_roles: ["therapist"],
  access_model: {
    invitation_only: false,
    public_signup: true,
    review_gates: "open",
    required_app_aal: "aal1",
    active_organization_session: "personal",
    production_mock_mode: "forbidden",
  },
  data_retention: "test",
  consent_policy: "test",
  capabilities: {
    cases: "available",
    audio_upload: "experimental",
    transcription: "experimental",
    transcript_qa: "available",
    feature_extraction: "available",
    ai_review: "disabled",
    report_drafting: "available",
    pdf_export: "available",
  },
  pipeline_settings: {
    audio_processing: "test",
    job_queue_mode: "test",
    repository_mode: "memory",
    storage_mode: "test",
  },
};

const TRANSCRIPT = {
  transcript_id: "T1",
  session_id: "S1",
  case_id: "C1",
  version: 1,
  source: "asr_draft:local_whisper",
  raw_text: "@Begin\n@Languages:\ttha\n@Participants:\tCHI Child Target_Child, THER Therapist\n*THER:\twhat is this .\n*CHI:\ta red car .\n@End",
  therapist_attested: false,
  qa_status: "NOT_RUN",
  qa_issues: [],
  utterances: [
    { utterance_id: "u1", speaker: "THER", text: "what is this ." },
    { utterance_id: "u2", speaker: "CHI", text: "a red car ." },
  ],
};

const FEATURES = {
  feature_set_id: "F1",
  transcript_version: 1,
  features: [
    { name: "mean_length_of_utterance_words", value: 2.8 },
    { name: "total_word_count", value: 129 },
    { name: "number_of_different_words", value: 61 },
    { name: "child_utterance_count", value: 46 },
  ],
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
}

type Route = (url: string, init?: RequestInit) => Response | Promise<Response> | undefined;

function stubApi(routes: Route) {
  const calls: Array<{ url: string; method: string }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, method: init?.method ?? "GET" });
      if (url.endsWith("/settings")) return json(PUBLIC_SETTINGS);
      if (url.endsWith("/health")) return json({ status: "ok" });
      if (url.endsWith("/cases/C1")) return json({ case_id: "C1", child_code: "C-1001", consent_status: "granted" });
      if (url.endsWith("/sessions/S1/audio")) return json([]);
      if (url.includes("/ml-readiness")) return json({ ready: false, provider_id: "mock", reason_codes: [], reasons: [] });
      if (url.includes("/feature-trend")) return json({ features: [], cases: [] });
      return routes(url, init) ?? new Response("not found", { status: 404 });
    }),
  );
  return calls;
}

beforeEach(() => {
  window.sessionStorage.clear();
  resetRuntimeSettingsCache();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("session conversation controller", () => {
  it("picks up a transcription that was running before the page was reloaded", async () => {
    // The job's answer is held back until the test has seen the waiting state.
    let finishJob!: () => void;
    const jobFinished = new Promise<void>((resolve) => { finishJob = resolve; });
    let finished = false;
    stubApi((url) => {
      if (url.endsWith("/sessions/S1")) return json({ session_id: "S1", case_id: "C1", notes: "" });
      if (url.endsWith("/sessions/S1/status")) return json({ transcription_job: { job_id: "J1", status: "processing" } });
      if (url.endsWith("/jobs/J1")) {
        return jobFinished.then(() => {
          finished = true;
          return json({ job_id: "J1", status: "needs_review", message: "", details: { asr_draft: { transcript_id: "T1" } } });
        });
      }
      if (url.endsWith("/sessions/S1/transcript")) return finished ? json(TRANSCRIPT) : undefined;
      return undefined;
    });

    render(<SessionChatWorkspace sessionId="S1" />);

    // The job is still running, so the conversation waits instead of asking for audio again.
    expect(await screen.findByTestId("chat-transcribing", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.queryByTestId("chat-ask-audio")).toBeNull();

    finishJob();

    const ready = await screen.findByTestId("chat-transcript-ready", {}, { timeout: 5000 });
    expect(within(ready).getByText(/Transcription is done: 2 lines\./)).toBeInTheDocument();
    expect(screen.queryByTestId("chat-transcribing")).toBeNull();
  });

  it("asks for audio when the last transcription job failed", async () => {
    stubApi((url) => {
      if (url.endsWith("/sessions/S1")) return json({ session_id: "S1", case_id: "C1", notes: "" });
      if (url.endsWith("/sessions/S1/status")) return json({ transcription_job: { job_id: "J1", status: "failed" } });
      return undefined;
    });

    render(<SessionChatWorkspace sessionId="S1" mode="audio" />);

    expect(await screen.findByTestId("chat-ask-audio")).toBeInTheDocument();
    expect(screen.queryByTestId("chat-transcribing")).toBeNull();
  });

  it("extracts the measures and shows them without leaving the conversation", async () => {
    const calls = stubApi((url, init) => {
      if (url.endsWith("/sessions/S1")) return json({ session_id: "S1", case_id: "C1", transcript_id: "T1", notes: "" });
      if (url.endsWith("/transcripts/T1")) return json(TRANSCRIPT);
      if (url.endsWith("/transcripts/T1/extract-features") && init?.method === "POST") return json(FEATURES);
      if (url.endsWith("/sessions/S1/features")) return json(FEATURES);
      if (url.endsWith("/features/definitions")) return json([]);
      return undefined;
    });

    render(<SessionChatWorkspace sessionId="S1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Extract the language measures" }));

    const measures = await screen.findByTestId("chat-measures");
    expect(within(measures).getByTestId("measure-mlu")).toHaveTextContent("2.8");
    expect(within(measures).getByTestId("measure-total-words")).toHaveTextContent("129");
    expect(within(measures).getByText(/from 46 child utterances/)).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
    expect(calls.filter((call) => call.method === "POST" && call.url.endsWith("/extract-features"))).toHaveLength(1);
  });

  it("shows the session's saved notes and adds a typed note to them", async () => {
    let savedNotes = "";
    stubApi((url, init) => {
      if (url.endsWith("/sessions/S1") && init?.method === "PATCH") {
        savedNotes = JSON.parse(String(init.body)).notes;
        return json({ session_id: "S1", case_id: "C1", notes: savedNotes });
      }
      if (url.endsWith("/sessions/S1")) return json({ session_id: "S1", case_id: "C1", transcript_id: "T1", notes: "Played with toy cars" });
      if (url.endsWith("/transcripts/T1")) return json(TRANSCRIPT);
      return undefined;
    });

    render(<SessionChatWorkspace sessionId="S1" />);

    await screen.findByTestId("chat-transcript-ready");
    fireEvent.change(screen.getByRole("textbox", { name: "Session note" }), { target: { value: "Tired today" } });
    fireEvent.click(screen.getByRole("button", { name: "Save note" }));

    await waitFor(() => expect(savedNotes).toBe("Played with toy cars\nTired today"));
    expect(await screen.findByText(/Saved as a session note/)).toBeInTheDocument();
  });
});
