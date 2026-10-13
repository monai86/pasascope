import { apiGet, apiRequest } from "@/lib/api";
import type { BackendSession } from "@/lib/workflow";

/**
 * Backend calls only the session conversation makes. They live here, not in
 * `lib/workflow`, so routes that never open a conversation do not carry them.
 */

/** Replaces the session's notes. A report draft uses them as the therapist's notes. */
export async function updateBackendSessionNotes(sessionId: string, notes: string): Promise<BackendSession> {
  return apiRequest<BackendSession>(`/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

/**
 * The session's most recent transcription job, or null when it has none. Lets
 * a page that was reloaded mid-transcription find the job it started.
 */
export async function getSessionTranscriptionJob(sessionId: string): Promise<{ jobId: string; status: string } | null> {
  const status = await apiGet<{ transcription_job?: { job_id?: string; status?: string } | null }>(
    `/sessions/${encodeURIComponent(sessionId)}/status`,
  );
  const job = status?.transcription_job;
  return job?.job_id && job.status ? { jobId: job.job_id, status: job.status } : null;
}
