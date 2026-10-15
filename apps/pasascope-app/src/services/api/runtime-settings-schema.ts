import { z } from "zod";

const availability = z.enum(["available", "unavailable"]);
const experimentalAvailability = z.enum(["available", "experimental", "unavailable"]);
const optionalAvailability = z.enum(["available", "disabled", "unavailable"]);

export const runtimeSettingsSchema = z.object({
  mock_mode: z.boolean(),
  auth_mode: z.enum(["mock", "supabase"]),
  model_version: z.string(),
  feature_schema: z.string(),
  guideline_mapping: z.string(),
  user_roles: z.array(z.string()),
  access_model: z.object({
    invitation_only: z.boolean(),
    // Public app mode: anyone who signs up gets a personal workspace, and
    // review gates may be open (no attestation or sign-off step).
    public_signup: z.boolean().optional(),
    review_gates: z.enum(["strict", "open"]).optional(),
    required_app_aal: z.enum(["aal1", "aal2"]),
    // Both need the API to manage accounts with the project's service role key.
    two_step_verification: z.enum(["optional", "unavailable"]).optional(),
    account_deletion: availability.optional(),
    active_organization_session: z.string(),
    production_mock_mode: z.string(),
  }).optional(),
  data_retention: z.string(),
  consent_policy: z.string(),
  capabilities: z.object({
    cases: availability,
    audio_upload: experimentalAvailability,
    transcription: experimentalAvailability,
    transcript_qa: availability,
    feature_extraction: availability,
    ai_review: optionalAvailability,
    report_drafting: optionalAvailability,
    pdf_export: availability,
  }),
  pipeline_settings: z.object({
    audio_processing: z.string(),
    transcription_provider: z.string().nullable().optional(),
    transcription_external: z.boolean().optional(),
    job_queue_mode: z.string(),
    repository_mode: z.string(),
    storage_mode: z.string(),
    ai_review_policy: z.string().optional(),
    ai_report_drafting_enabled: z.boolean().optional(),
  }),
});

export type RuntimeSettings = z.infer<typeof runtimeSettingsSchema>;
