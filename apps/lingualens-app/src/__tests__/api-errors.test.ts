import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  DEFAULT_PRODUCTION_RUNTIME_SETTINGS,
  getRuntimeSettings,
  resetApiRuntimeSettingsCacheForTests,
} from "@/lib/api";

afterEach(() => {
  vi.unstubAllGlobals();
  resetApiRuntimeSettingsCacheForTests();
});

describe("ApiError", () => {
  it("shows the v1 detail text instead of the raw JSON payload", () => {
    const body = JSON.stringify({ detail: "Case consent has been withdrawn." });
    const error = new ApiError(400, body);

    expect(error.message).toBe("Case consent has been withdrawn.");
    expect(error.body).toBe(body);
    expect(error.status).toBe(400);
  });

  it("shows the v2 error message", () => {
    const error = new ApiError(403, JSON.stringify({ error: { code: "forbidden", message: "Access to this resource is not permitted." } }));

    expect(error.message).toBe("Access to this resource is not permitted.");
  });

  it("does not dump validation error lists on the user", () => {
    const error = new ApiError(422, JSON.stringify({ detail: [{ loc: ["body", "consent_status"], msg: "Extra inputs are not permitted" }] }));

    expect(error.message).toBe("The request was not valid.");
  });

  it("keeps plain-text bodies and falls back to the status when empty", () => {
    expect(new ApiError(502, "Bad gateway").message).toBe("Bad gateway");
    expect(new ApiError(500, "").message).toBe("API request failed: 500");
  });
});

describe("runtime settings fallback", () => {
  it("assumes the strictest access model when the backend cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    const settings = await getRuntimeSettings();

    expect(settings).toBe(DEFAULT_PRODUCTION_RUNTIME_SETTINGS);
    expect(settings.access_model?.required_app_aal).toBe("aal2");
    expect(settings.access_model?.invitation_only).toBe(true);
    expect(settings.capabilities.audio_upload).toBe("unavailable");
    expect(settings.capabilities.transcription).toBe("unavailable");
  });
});
