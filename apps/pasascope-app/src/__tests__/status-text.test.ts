import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { STATUS_MESSAGES_TH } from "@/features/sessions/state/status-messages.th";
import { statusText } from "@/features/sessions/state/use-status-text";

const sources = [
  "src/features/sessions/components/session-workspace-model.tsx",
  "src/features/sessions/report/use-session-report.ts",
].map((file) => readFileSync(path.resolve(process.cwd(), file), "utf8")).join("\n");

// Plain string literals assigned to statusMessage or error; templated and
// backend-supplied messages are out of scope and pass through untranslated.
const literalMessages = Array.from(
  new Set(Array.from(sources.matchAll(/(?:statusMessage|error): "([^"]+)"/g), (match) => match[1])),
);

describe("session status messages in Thai", () => {
  it("has a Thai entry for every literal status or error message", () => {
    expect(literalMessages.length).toBeGreaterThan(30);
    expect(literalMessages.filter((message) => !STATUS_MESSAGES_TH[message])).toEqual([]);
  });

  it("leaves English untouched and passes unknown text through", () => {
    expect(statusText("Report finalized.", "en")).toBe("Report finalized.");
    expect(statusText("Report finalized.", "th")).toBe("ลงนามรายงานแล้ว");
    expect(statusText("Backend said something new.", "th")).toBe("Backend said something new.");
    expect(statusText(undefined, "th")).toBeUndefined();
  });
});
