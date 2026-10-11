import { beforeEach, describe, expect, it } from "vitest";

import { migrateRenamedStorageKeys } from "@/lib/storage-key-migration";
import { MOCK_ACCESS_SESSION_KEY } from "@/lib/mock-access-session";
import { WORKFLOW_STORAGE_KEY } from "@/lib/workflow";

describe("storage keys written under the previous project name", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("are carried over to the current keys once", () => {
    window.sessionStorage.setItem("lingualens.therapist.workflow.v1", "{\"sessionId\":\"open-session\"}");
    window.localStorage.setItem("lingualens.supabase-organization-hint.v1", "{\"organizationId\":\"org-1\"}");

    migrateRenamedStorageKeys();

    expect(window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY)).toBe("{\"sessionId\":\"open-session\"}");
    expect(window.localStorage.getItem("pasascope.supabase-organization-hint.v1")).toBe("{\"organizationId\":\"org-1\"}");
    expect(window.sessionStorage.getItem("lingualens.therapist.workflow.v1")).toBeNull();
    expect(window.localStorage.getItem("lingualens.supabase-organization-hint.v1")).toBeNull();
  });

  it("never overwrite a value already stored under the current key", () => {
    window.sessionStorage.setItem(MOCK_ACCESS_SESSION_KEY, "current");
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", "stale");

    migrateRenamedStorageKeys();

    expect(window.sessionStorage.getItem(MOCK_ACCESS_SESSION_KEY)).toBe("current");
    expect(window.sessionStorage.getItem("lingualens.mock-access-session.v1")).toBeNull();
  });

  it("use the pasascope prefix", () => {
    expect(MOCK_ACCESS_SESSION_KEY).toBe("pasascope.mock-access-session.v1");
    expect(WORKFLOW_STORAGE_KEY).toBe("pasascope.therapist.workflow.v1");
  });
});
