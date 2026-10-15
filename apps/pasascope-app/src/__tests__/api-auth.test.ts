import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  apiBlob,
  apiRequest,
  apiUploadBlob,
  getRuntimeSettings,
  resetApiRuntimeSettingsCacheForTests,
} from "@/lib/api";
import { exportBackendReport, exportReviewedCha } from "@/lib/workflow";

const getSession = vi.fn();
const refreshSession = vi.fn();

const runtimeCapabilities = {
  cases: "available",
  audio_upload: "experimental",
  transcription: "experimental",
  transcript_qa: "available",
  feature_extraction: "available",
  ai_review: "disabled",
  report_drafting: "disabled",
  pdf_export: "unavailable",
} as const;

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession,
      refreshSession,
    },
  }),
}));

describe("api auth headers", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
    getSession.mockReset();
    refreshSession.mockReset().mockResolvedValue({ data: {}, error: null });
    resetApiRuntimeSettingsCacheForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("sends bearer auth and no organization header in supabase runtime", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("pasascope.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBeNull();
      expect(headers.get("X-User-Id")).toBeNull();
      return jsonResponse({ ok: true });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiRequest("/protected");
    expect(getSession).not.toHaveBeenCalled();
  });

  it("sends bearer auth headers for blob downloads in supabase runtime", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "therapist",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("pasascope.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBeNull();
      return new Response(new Blob(["audio-bytes"], { type: "audio/webm" }), {
        status: 200,
        headers: { "Content-Type": "audio/webm" },
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    const blob = await apiBlob("/audio/audio_001/file");
    expect(blob.type).toBe("audio/webm");
    expect(getSession).not.toHaveBeenCalled();
  });

  it("falls back to the persisted Supabase auth-token when the app session token cache is empty", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "org_admin",
      aal: "aal2",
    }));
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      access_token: "persisted-supabase-access-token",
      aal: "aal2",
      user: {
        id: "user_therapist_001",
        email: "clinician@clinic.example",
      },
    }));

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer persisted-supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBeNull();
      return jsonResponse({ ok: true });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiRequest("/protected");
    expect(window.sessionStorage.getItem("pasascope.supabase-session-token.v1")).toBe("persisted-supabase-access-token");
  });

  it("prefers the persisted Supabase auth token over a stale app token cache", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      userId: "user_therapist_001",
      email: "clinician@clinic.example",
      role: "org_admin",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("pasascope.supabase-session-token.v1", "stale-access-token");
    window.localStorage.setItem("sb-cbhwxklvcpgizeqriqxi-auth-token", JSON.stringify({
      access_token: "fresh-persisted-supabase-access-token",
      aal: "aal2",
      user: {
        id: "user_therapist_001",
        email: "clinician@clinic.example",
      },
    }));

    getSession.mockResolvedValue({
      data: {
        session: {
          access_token: "fresh-browser-supabase-access-token",
        },
      },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer fresh-persisted-supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBeNull();
      return jsonResponse({ ok: true });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiRequest("/protected");
    expect(window.sessionStorage.getItem("pasascope.supabase-session-token.v1")).toBe("fresh-persisted-supabase-access-token");
  });

  it("falls back to demo user headers in mock runtime", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: true,
          auth_mode: "mock",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "local_only",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("X-User-Id")).toBe("therapist-demo");
      expect(headers.get("Authorization")).toBeNull();
      return jsonResponse({ ok: true });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiRequest("/protected");
  });

  it("sends bearer auth for relative backend blob uploads in supabase runtime", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("pasascope.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBeNull();
      expect(headers.get("content-type")).toBe("audio/webm");
      return new Response(null, { status: 200 });
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    await apiUploadBlob("/audio/audio_001/upload-file", new Blob(["audio"], { type: "audio/webm" }));
    expect(getSession).not.toHaveBeenCalled();
  });

  it("does not add app auth headers to absolute signed upload URLs", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBeNull();
      expect(headers.get("X-Organization-Id")).toBeNull();
      expect(headers.get("content-type")).toBe("audio/webm");
      return new Response(null, { status: 200 });
    });

    vi.stubGlobal("fetch", fetchMock);

    await apiUploadBlob("https://storage.example.test/upload", new Blob(["audio"], { type: "audio/webm" }));
  });

  it("uploads Supabase signed URLs as multipart form data without app auth headers", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBeNull();
      expect(headers.get("X-Organization-Id")).toBeNull();
      expect(headers.get("content-type")).toBeNull();
      expect(init?.method).toBe("PUT");
      expect(init?.body).toBeInstanceOf(FormData);
      expect((init?.body as FormData).get("file")).toBeInstanceOf(File);
      return new Response(null, { status: 200 });
    });

    vi.stubGlobal("fetch", fetchMock);

    await apiUploadBlob(
      "https://project-ref.supabase.co/storage/v1/object/upload/sign/clinical-audio/audio/obj_123.webm?token=signed",
      new Blob(["audio"], { type: "audio/webm" }),
    );
  });

  it("sends bearer auth for report export and reviewed CHA export in supabase runtime", async () => {
    window.sessionStorage.setItem("pasascope.supabase-access-session.v1", JSON.stringify({
      stage: "authenticated",
      aal: "aal2",
    }));
    window.sessionStorage.setItem("pasascope.supabase-session-token.v1", "supabase-access-token");

    getSession.mockResolvedValue({
      data: { session: null },
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v2-mock",
          feature_schema: "pasascope-app.1",
          guideline_mapping: "review-support-only",
          user_roles: ["therapist", "clinical_supervisor", "org_admin"],
          access_model: {
            invitation_only: true,
            required_app_aal: "aal2",
            active_organization_session: "explicit_selection_when_ambiguous",
            production_mock_mode: "forbidden",
          },
          data_retention: "test-retention",
          consent_policy: "test-consent",
          capabilities: runtimeCapabilities,
          pipeline_settings: {
            audio_processing: "test-audio",
            job_queue_mode: "test-queue",
            repository_mode: "test-repository",
            storage_mode: "test-storage",
          },
        });
      }

      const headers = new Headers(init?.headers);
      expect(headers.get("Authorization")).toBe("Bearer supabase-access-token");
      expect(headers.get("X-Organization-Id")).toBeNull();

      if (url.includes("/reports/REPORT-001/export")) {
        return jsonResponse({
          filename: "report.md",
          content: "# Report",
          content_type: "text/markdown",
        });
      }

      if (url.endsWith("/transcripts/TRANSCRIPT-001/export-cha")) {
        return jsonResponse({
          filename: "reviewed.cha",
          cha_text: "@Begin\n@End\n",
        });
      }

      return jsonResponse({});
    });

    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeSettings();
    const report = await exportBackendReport("REPORT-001", "markdown");
    const transcript = await exportReviewedCha("TRANSCRIPT-001");

    expect(report.filename).toBe("report.md");
    expect(transcript.filename).toBe("reviewed.cha");
    expect(getSession).not.toHaveBeenCalled();
  });
  it("fetches the session again when the API asks for the second step", async () => {
    window.sessionStorage.setItem("pasascope.supabase-session-token.v1", "aal1-token");
    getSession.mockResolvedValue({ data: { session: null } });
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/settings")) {
        return jsonResponse({
          mock_mode: false,
          auth_mode: "supabase",
          model_version: "v",
          feature_schema: "s",
          guideline_mapping: "g",
          user_roles: ["therapist"],
          access_model: { invitation_only: false, required_app_aal: "aal1", active_organization_session: "x", production_mock_mode: "forbidden" },
          data_retention: "d",
          consent_policy: "c",
          capabilities: runtimeCapabilities,
          pipeline_settings: { audio_processing: "a", job_queue_mode: "q", repository_mode: "r", storage_mode: "s" },
        });
      }
      return new Response(JSON.stringify({ detail: "Two-step verification is required for this account." }), { status: 403 });
    }));

    await getRuntimeSettings();
    await expect(apiRequest("/cases")).rejects.toMatchObject({ status: 403 });

    await vi.waitFor(() => expect(refreshSession).toHaveBeenCalledTimes(1));
  });
});

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
