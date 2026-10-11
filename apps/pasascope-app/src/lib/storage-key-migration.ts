/**
 * Browser storage written before the project was renamed used a "lingualens."
 * key prefix. Copy those values to the current keys once, so an open session
 * or a saved organization choice survives the upgrade.
 */
const PREVIOUS_PREFIX = "lingualens.";
const CURRENT_PREFIX = "pasascope.";
const RENAMED_KEY_SUFFIXES = [
  "mock-access-session.v1",
  "supabase-access-session.v1",
  "supabase-organization-hint.v1",
  "supabase-browser-auth.v1",
  "supabase-session-token.v1",
  "therapist.workflow.v1",
];

export function migrateRenamedStorageKeys(storages?: Storage[]): void {
  let targets = storages;
  if (!targets) {
    if (typeof window === "undefined") return;
    try {
      targets = [window.sessionStorage, window.localStorage];
    } catch {
      return;
    }
  }
  for (const storage of targets) {
    for (const suffix of RENAMED_KEY_SUFFIXES) {
      try {
        const previous = storage.getItem(PREVIOUS_PREFIX + suffix);
        if (previous === null) continue;
        if (storage.getItem(CURRENT_PREFIX + suffix) === null) {
          storage.setItem(CURRENT_PREFIX + suffix, previous);
        }
        storage.removeItem(PREVIOUS_PREFIX + suffix);
      } catch {
        // Storage can be blocked or full; the page must still load.
      }
    }
  }
}

migrateRenamedStorageKeys();
