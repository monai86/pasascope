import { describe, expect, it } from "vitest";

import {
  buildChatHome,
  caseLabel,
  filterCases,
  filterSessionRows,
  hasConsent,
} from "@/features/chat-home/chat-home-model";
import type { BackendCase, DashboardRecentSession } from "@/lib/workflow";

function session(overrides: Partial<DashboardRecentSession>): DashboardRecentSession {
  return {
    session_id: "s1",
    case_id: "case-1",
    case_label: "C-1001",
    session_date: "2026-10-12",
    status: "Draft",
    has_transcript: false,
    has_features: false,
    has_ml_review: false,
    has_report: false,
    ...overrides,
  };
}

describe("chat home model", () => {
  it("names each session by what it is waiting for", () => {
    const { rows } = buildChatHome([
      session({ session_id: "audio" }),
      session({ session_id: "processing", status: "Processing" }),
      session({ session_id: "failed", status: "Failed" }),
      session({ session_id: "transcript", status: "Needs Review", has_transcript: true }),
      session({ session_id: "measures", has_transcript: true, has_features: true }),
      session({ session_id: "report", has_transcript: true, has_features: true, has_report: true }),
    ]);

    expect(rows.map((row) => [row.sessionId, row.stage, row.tone])).toEqual([
      ["audio", "audio", "action"],
      ["processing", "processing", "progress"],
      ["failed", "failed", "attention"],
      ["transcript", "transcript", "action"],
      ["measures", "measures", "action"],
      ["report", "report", "action"],
    ]);
  });

  it("opens every session in its conversation", () => {
    const { rows } = buildChatHome([session({ session_id: "s-9", case_id: "case-9" })]);
    expect(rows[0].href).toBe("/sessions/s-9?view=chat&case_id=case-9");
  });

  it("offers the most recent session with a step still open to pick up", () => {
    const model = buildChatHome([
      session({ session_id: "done", has_transcript: true, has_features: true, has_report: true }),
      session({ session_id: "open", has_transcript: true }),
      session({ session_id: "older" }),
    ]);
    expect(model.resume?.sessionId).toBe("open");
  });

  it("has nothing to pick up when every session has its report", () => {
    expect(buildChatHome([session({ has_report: true })]).resume).toBeNull();
    expect(buildChatHome([]).resume).toBeNull();
  });

  it("leaves out sessions whose consent was withdrawn", () => {
    expect(buildChatHome([session({ status: "Withdrawn" })]).rows).toEqual([]);
  });

  it("filters sessions and cases by what the therapist types", () => {
    const { rows } = buildChatHome([session({ case_label: "Tonkla" }), session({ session_id: "s2", case_label: "Mali" })]);
    expect(filterSessionRows(rows, " ton ").map((row) => row.caseLabel)).toEqual(["Tonkla"]);
    expect(filterSessionRows(rows, "")).toHaveLength(2);

    const cases: BackendCase[] = [
      { case_id: "a", child_code: "PS-0142", nickname: "Tonkla", consent_status: "granted" },
      { case_id: "b", child_code: "PS-0147", consent_status: "pending" },
    ];
    expect(filterCases(cases, "0147").map((item) => item.case_id)).toEqual(["b"]);
    expect(filterCases(cases, "tonk").map((item) => item.case_id)).toEqual(["a"]);
    expect(caseLabel(cases[1])).toBe("PS-0147");
    expect(hasConsent(cases[0])).toBe(true);
    expect(hasConsent(cases[1])).toBe(false);
  });
});
