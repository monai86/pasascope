import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { gateReason } from "@/lib/gate-reason";
import { GATE_REASONS_TH } from "@/lib/workflow-gate-reasons.th";

const source = readFileSync(path.resolve(process.cwd(), "src/lib/workflow-gates.ts"), "utf8");
const literalReasons = Array.from(source.matchAll(/return "([^"]+)";/g), (match) => match[1]);

describe("blocked-action reasons in Thai", () => {
  it("has a Thai entry for every literal reason in workflow-gates", () => {
    expect(literalReasons.length).toBeGreaterThan(15);
    expect(literalReasons.filter((reason) => !GATE_REASONS_TH[reason])).toEqual([]);
  });

  it("has no entry for a reason that no longer exists", () => {
    expect(Object.keys(GATE_REASONS_TH).filter((reason) => !literalReasons.includes(reason))).toEqual([]);
  });

  it("leaves English untouched and passes undefined through", () => {
    expect(gateReason("Run transcript QA before attesting.", "en")).toBe("Run transcript QA before attesting.");
    expect(gateReason(undefined, "th")).toBeUndefined();
  });

  it("keeps the backend-supplied tail of the readiness reason", () => {
    expect(gateReason("Evidence readiness check is blocked: reference data missing", "th")).toBe(
      "การตรวจความพร้อมของหลักฐานยังไม่ผ่าน: reference data missing",
    );
  });

  it("falls back to the English reason when there is no Thai entry", () => {
    expect(gateReason("Some new reason.", "th")).toBe("Some new reason.");
  });
});
