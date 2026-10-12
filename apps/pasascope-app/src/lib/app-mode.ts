"use client";

import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export type AppMode = {
  /** Anyone can sign up and gets a personal workspace; no organizations, invitations or MFA. */
  publicSignup: boolean;
  /** No transcript attestation or report sign-off step; analysis and export are available directly. */
  openGates: boolean;
  /** Recordings are sent outside this deployment to be transcribed. */
  externalTranscription: boolean;
};

const STRICT: AppMode = { publicSignup: false, openGates: false, externalTranscription: false };

/** How the running API is configured; strict until the settings have loaded. */
export function useAppMode(): AppMode {
  const settings = useRuntimeSettings();
  if (settings.status !== "success") return STRICT;
  const access = settings.data.access_model;
  return {
    publicSignup: access?.public_signup === true,
    openGates: access?.review_gates === "open",
    externalTranscription: settings.data.pipeline_settings?.transcription_external === true,
  };
}
