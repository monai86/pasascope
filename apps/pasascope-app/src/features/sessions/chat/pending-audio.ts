/**
 * An audio file chosen on the home screen, held until the session it was
 * chosen for opens. It lives in memory only: a file cannot travel in a URL,
 * and it must not be written to browser storage. After a reload it is gone and
 * the session simply asks for the audio again.
 */
let pending: { sessionId: string; file: File } | null = null;

export function setPendingSessionAudio(sessionId: string, file: File): void {
  pending = { sessionId, file };
}

/** Hands the file over once, and only to the session it was chosen for. */
export function takePendingSessionAudio(sessionId: string): File | null {
  if (!pending || pending.sessionId !== sessionId) return null;
  const { file } = pending;
  pending = null;
  return file;
}
