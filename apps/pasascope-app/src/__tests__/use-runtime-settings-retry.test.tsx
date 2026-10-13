import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import { resetRuntimeSettingsCache, useRuntimeSettings } from "@/lib/use-runtime-settings";

const getRuntimeSettings = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getRuntimeSettings,
}));

async function advance(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("useRuntimeSettings while the API is unavailable", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetRuntimeSettingsCache();
    getRuntimeSettings.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps loading and asks again while the API is waking up", async () => {
    getRuntimeSettings
      .mockRejectedValueOnce(new ApiError(502, "Bad Gateway"))
      .mockRejectedValueOnce(new ApiError(503, "Service Unavailable"))
      .mockResolvedValueOnce({ auth_mode: "supabase" });

    const { result } = renderHook(() => useRuntimeSettings());
    await advance(2000);
    expect(result.current.status).toBe("loading");
    await advance(4000);

    expect(getRuntimeSettings).toHaveBeenCalledTimes(3);
    expect(result.current).toMatchObject({ status: "success", data: { auth_mode: "supabase" } });
  });

  it("does not repeat a request the API refused", async () => {
    getRuntimeSettings.mockRejectedValue(new ApiError(403, "Forbidden"));

    const { result } = renderHook(() => useRuntimeSettings());
    await advance(0);

    expect(getRuntimeSettings).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe("error");
  });

  it("gives up after the API has stayed down for over a minute", async () => {
    getRuntimeSettings.mockRejectedValue(new ApiError(502, "Bad Gateway"));

    const { result } = renderHook(() => useRuntimeSettings());
    await advance(74_000);
    expect(result.current.status).toBe("loading");
    await advance(2_000);

    expect(result.current.status).toBe("error");
    expect(getRuntimeSettings).toHaveBeenCalledTimes(9);
  });
});
