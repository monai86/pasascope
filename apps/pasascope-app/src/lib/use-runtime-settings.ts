"use client";

import { useEffect, useState } from "react";

import { ApiError, getRuntimeSettings, type RuntimeSettings } from "@/lib/api";
import { confirmed, type RemoteState } from "@/services/adapters/remote-state";

let runtimeSettingsRequest: Promise<RuntimeSettings> | null = null;

// A host that sleeps when idle answers with a gateway error while it wakes,
// which takes about a minute. Keep asking for a little longer than that.
const RETRY_DELAYS_MS = [2000, 4000, 8000, 8000, 8000, 15000, 15000, 15000];

function isTemporary(error: unknown): boolean {
  return error instanceof ApiError && (error.status >= 500 || error.status === 429 || error.status === 408);
}

async function requestRuntimeSettings(): Promise<RuntimeSettings> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await getRuntimeSettings();
    } catch (error) {
      if (attempt >= RETRY_DELAYS_MS.length || !isTemporary(error)) throw error;
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[attempt]));
    }
  }
}

function loadRuntimeSettings(): Promise<RuntimeSettings> {
  if (!runtimeSettingsRequest) {
    runtimeSettingsRequest = requestRuntimeSettings().catch((error: unknown) => {
      runtimeSettingsRequest = null;
      throw error;
    });
  }
  return runtimeSettingsRequest;
}

export function resetRuntimeSettingsCache(): void {
  runtimeSettingsRequest = null;
}

export function useRuntimeSettings(): RemoteState<RuntimeSettings> {
  const [runtimeSettings, setRuntimeSettings] = useState<RemoteState<RuntimeSettings>>({
    status: "loading",
    mode: "backend",
  });

  useEffect(() => {
    let cancelled = false;
    void loadRuntimeSettings()
      .then((settings) => {
        if (!cancelled) setRuntimeSettings(confirmed(settings));
      })
      .catch(() => {
        if (!cancelled) {
          setRuntimeSettings({
            status: "error",
            mode: "backend",
            message: "Runtime settings unavailable",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return runtimeSettings;
}
