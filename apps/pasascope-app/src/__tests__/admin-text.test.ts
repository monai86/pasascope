import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { adminText } from "@/features/settings/admin-text";
import { ADMIN_TEXT_TH } from "@/features/settings/admin-text.th";

const files = [
  "src/features/settings/components/settings-workspace.tsx",
  "src/features/settings/components/settings-presentational.tsx",
  "src/features/settings/components/care-team-administration.tsx",
];

function decode(text: string) {
  return text.replace(/&amp;/g, "&").replace(/&apos;/g, "'").replace(/\s+/g, " ").trim();
}

// Literal text marked for translation: <T>text</T>, tr("text"), string props
// that the presentational components translate, and plain setMessage("text").
function markedText(source: string): string[] {
  const patterns = [
    /<T>([^<{]+)<\/T>/g,
    /\btr\("([^"]+)"\)/g,
    /\b(?:label|value|title|description|empty)="([A-Z][^"]*)"/g,
    /setMessage\("([^"]+)"\)/g,
  ];
  return patterns.flatMap((pattern) => Array.from(source.matchAll(pattern), (match) => decode(match[1])));
}

describe("organization-administration Settings in Thai", () => {
  const marked = Array.from(new Set(files.flatMap((file) => markedText(readFileSync(path.resolve(process.cwd(), file), "utf8")))));

  it("has a Thai entry for every literal marked for translation", () => {
    expect(marked.length).toBeGreaterThan(60);
    expect(marked.filter((text) => !ADMIN_TEXT_TH[text])).toEqual([]);
  });

  it("leaves English untouched and passes backend text through", () => {
    expect(adminText("Create invitation", "en")).toBe("Create invitation");
    expect(adminText("Create invitation", "th")).toBe("สร้างคำเชิญ");
    expect(adminText("some_backend_value", "th")).toBe("some_backend_value");
  });
});
