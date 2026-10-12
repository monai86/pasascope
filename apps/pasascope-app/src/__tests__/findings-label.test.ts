import { describe, expect, it } from "vitest";

import { findingsLabel } from "@/features/sessions/findings/use-findings-label";

describe("derived Findings labels", () => {
  it("leaves English untouched", () => {
    expect(findingsLabel("Pass · 96%", "en")).toBe("Pass · 96%");
  });

  it("translates fixed labels and keeps measured values", () => {
    expect(findingsLabel("Not generated", "th")).toBe("ยังไม่ได้สร้าง");
    expect(findingsLabel("Pass · 96%", "th")).toBe("ผ่าน · 96%");
    expect(findingsLabel("Version 3", "th")).toBe("เวอร์ชัน 3");
  });

  it("passes backend text through unchanged", () => {
    expect(findingsLabel("Check line 12 for an unclear segment.", "th")).toBe("Check line 12 for an unclear segment.");
  });
});
