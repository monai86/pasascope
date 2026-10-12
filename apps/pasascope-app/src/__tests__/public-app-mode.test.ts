import { afterEach, describe, expect, it } from "vitest";

import { sessionCompletion } from "@/features/sessions/state/session-completion";
import {
  buildSupabaseBrowserAuthSnapshotFromSession,
  deriveSupabaseAccessSession,
  PUBLIC_SIGNUP_FLAG,
  type SupabaseSessionLike,
} from "@/lib/supabase-browser-auth";
import { createInitialWorkflowState, type WorkflowState } from "@/lib/workflow";
import { runtimeSettingsSchema } from "@/services/api/runtime-settings-schema";

// A session as Supabase returns it for someone who has just signed up: no
// organization, role or membership claims.
const newUser = {
  access_token: "token",
  aal: "aal1",
  user: { id: "user-a", email: "user-a@example.test", app_metadata: {}, user_metadata: { full_name: "User A" } },
} as unknown as SupabaseSessionLike;

function state(overrides: Partial<WorkflowState>): WorkflowState {
  return { ...createInitialWorkflowState(), ...overrides };
}

afterEach(() => {
  window.sessionStorage.clear();
});

describe("public sign-up", () => {
  it("treats a new user as signed out while the app is invitation-only", () => {
    expect(buildSupabaseBrowserAuthSnapshotFromSession(newUser)).toBeNull();
  });

  it("gives a new user a personal workspace when public sign-up is on", () => {
    window.sessionStorage.setItem(PUBLIC_SIGNUP_FLAG, "true");

    const snapshot = buildSupabaseBrowserAuthSnapshotFromSession(newUser);

    expect(snapshot).toMatchObject({
      userId: "user-a",
      displayName: "User A",
      appMetadata: { role: "therapist", membership_active: true, organization_id: "personal_user-a" },
    });
  });

  it("lets that user into the app without MFA when the API does not require it", () => {
    window.sessionStorage.setItem(PUBLIC_SIGNUP_FLAG, "true");
    window.sessionStorage.setItem("pasascope.mfa_optional", "true");

    const access = deriveSupabaseAccessSession(buildSupabaseBrowserAuthSnapshotFromSession(newUser));

    expect(access).toMatchObject({ stage: "authenticated", organizationId: "personal_user-a", role: "therapist" });
  });

  it("ignores organization claims in the token, as the API does", () => {
    window.sessionStorage.setItem(PUBLIC_SIGNUP_FLAG, "true");
    const withClaims = {
      ...newUser,
      user: { ...newUser!.user, app_metadata: { organization_id: "someone_elses_org", role: "org_admin" } },
    } as unknown as SupabaseSessionLike;

    expect(buildSupabaseBrowserAuthSnapshotFromSession(withClaims)?.appMetadata).toMatchObject({
      organization_id: "personal_user-a",
      role: "therapist",
    });
  });
});

describe("runtime settings", () => {
  const base = {
    mock_mode: true,
    auth_mode: "supabase",
    model_version: "v",
    feature_schema: "s",
    guideline_mapping: "g",
    user_roles: ["therapist"],
    data_retention: "d",
    consent_policy: "c",
    capabilities: {
      cases: "available",
      audio_upload: "experimental",
      transcription: "experimental",
      transcript_qa: "available",
      feature_extraction: "available",
      ai_review: "disabled",
      report_drafting: "disabled",
      pdf_export: "unavailable",
    },
    pipeline_settings: { audio_processing: "a", job_queue_mode: "memory", repository_mode: "sql", storage_mode: "local_private" },
  };
  const access = { invitation_only: false, required_app_aal: "aal1", active_organization_session: "x", production_mock_mode: "local_only" };

  it("accepts the public app fields", () => {
    const parsed = runtimeSettingsSchema.parse({ ...base, access_model: { ...access, public_signup: true, review_gates: "open" } });
    expect(parsed.access_model).toMatchObject({ public_signup: true, review_gates: "open" });
  });

  it("still accepts an API that does not send them", () => {
    expect(runtimeSettingsSchema.parse({ ...base, access_model: access }).access_model?.public_signup).toBeUndefined();
  });
});

describe("step completion with open gates", () => {
  it("counts an analysed transcript as finished without attestation", () => {
    const analysed = state({ backendTranscriptId: "t1", featuresExtracted: true, analysisStatus: "completed" });

    expect(sessionCompletion(analysed).transcript).toBe(false);
    expect(sessionCompletion(analysed, true).transcript).toBe(true);
  });

  it("counts a current draft as the finished report without sign-off", () => {
    const drafted = state({ featuresExtracted: true, reportStatus: "draft" });

    expect(sessionCompletion(drafted).report).toBe(false);
    expect(sessionCompletion(drafted, true).report).toBe(true);
  });

  it("does not count a report that was never generated", () => {
    expect(sessionCompletion(state({ reportStatus: "not_started" }), true).report).toBe(false);
  });
});
