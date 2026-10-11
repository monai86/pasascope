import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  contrastRatio,
  findGreen,
  findLegacyStyling,
  findUndefinedProperties,
  isGreenish,
  parseHex,
  readSource,
  readTokens,
  styleSources,
} from "./support/palette-scan";

/**
 * The palette contract: no green anywhere, every colour through a design
 * token, and every text/fill pairing at WCAG AA.
 *
 * The redesign moves screens to the new palette a surface at a time. Files
 * that have not been moved yet are listed in palette-migration-pending.json.
 * That list may only shrink: a listed file that has become clean fails the
 * suite until its entry is removed, and a file that is not listed may not
 * offend at all. `PALETTE_WRITE_PENDING=1` rewrites the list from the current
 * tree and exists for the removal step, never to admit a new offender.
 */
const PENDING_FILE = "src/__tests__/support/palette-migration-pending.json";

type PendingLists = { green: string[]; legacy: string[] };

function scan(find: (path: string, text: string) => string[]): Map<string, string[]> {
  const offendersByFile = new Map<string, string[]>();
  for (const path of styleSources()) {
    const offenders = find(path, readSource(path));
    if (offenders.length) offendersByFile.set(path, offenders);
  }
  return offendersByFile;
}

const greenByFile = scan(findGreen);
const legacyByFile = scan(findLegacyStyling);

if (process.env.PALETTE_WRITE_PENDING === "1") {
  const lists: PendingLists = { green: [...greenByFile.keys()], legacy: [...legacyByFile.keys()] };
  writeFileSync(resolve(process.cwd(), PENDING_FILE), `${JSON.stringify(lists, null, 2)}\n`);
}

const pending = JSON.parse(readFileSync(resolve(process.cwd(), PENDING_FILE), "utf8")) as PendingLists;

function describeOffenders(offendersByFile: Map<string, string[]>, allowed: readonly string[]): string[] {
  return [...offendersByFile]
    .filter(([path]) => !allowed.includes(path))
    .map(([path, offenders]) => `${path}: ${[...new Set(offenders)].slice(0, 6).join(", ")}`);
}

function cleanedButStillListed(offendersByFile: Map<string, string[]>, listed: readonly string[]): string[] {
  return listed.filter((path) => !offendersByFile.has(path));
}

describe("palette contract", () => {
  it("recognises greens and teals by value and leaves the blue palette alone", () => {
    for (const green of ["#265347", "#0f766e", "#10b981", "#ecfdf5", "#34d399", "#06b6d4", "#84cc16"]) {
      expect(isGreenish(parseHex(green)), green).toBe(true);
    }
    for (const allowed of ["#0a66d6", "#7cc8f8", "#f0566a", "#16233f", "#f59e0b", "#f4f8fd", "#ffffff"]) {
      expect(isGreenish(parseHex(allowed)), allowed).toBe(false);
    }
  });

  it("renders no green outside the screens still waiting to be migrated", () => {
    expect(describeOffenders(greenByFile, pending.green)).toEqual([]);
  });

  it("uses design tokens outside the screens still waiting to be migrated", () => {
    expect(describeOffenders(legacyByFile, pending.legacy)).toEqual([]);
  });

  it("lists only files that still need migrating", () => {
    expect(cleanedButStillListed(greenByFile, pending.green)).toEqual([]);
    expect(cleanedButStillListed(legacyByFile, pending.legacy)).toEqual([]);
  });

  it("defines every custom property the app references", () => {
    const tokens = readTokens();
    const offenders = styleSources().flatMap((path) =>
      findUndefinedProperties(readSource(path), tokens).map((name) => `${path}: ${name}`),
    );
    expect(offenders).toEqual([]);
  });

  it("keeps the token palette itself free of green", () => {
    const greens = [...readTokens()]
      .filter(([, value]) => /^#[0-9a-f]{3,8}$/i.test(value) && isGreenish(parseHex(value)))
      .map(([name, value]) => `${name}: ${value}`);
    expect(greens).toEqual([]);
  });

  it("meets WCAG AA for every text and fill pairing the system allows", () => {
    const tokens = readTokens();
    const token = (name: string) => {
      const value = tokens.get(name);
      if (!value || !value.startsWith("#")) throw new Error(`${name} is not a hex colour token`);
      return value;
    };

    // [text, fill, minimum ratio]. 4.5 is body text; 3 is the floor for
    // non-text marks such as the coral highlight dot against a surface.
    const pairings: Array<[string, string, number]> = [
      ["--color-text-strong", "--color-surface-strong", 4.5],
      ["--color-text-strong", "--color-page-bg", 4.5],
      ["--color-text-strong", "--color-surface-muted", 4.5],
      ["--color-text-muted", "--color-surface-strong", 4.5],
      ["--color-text-muted", "--color-page-bg", 4.5],
      ["--color-text-muted", "--color-surface-muted", 4.5],
      ["--color-text-subtle", "--color-surface-strong", 4.5],
      ["--color-text-subtle", "--color-page-bg", 4.5],
      ["--color-text-subtle", "--color-surface", 4.5],
      ["--color-text-subtle", "--color-surface-muted", 4.5],
      ["--color-surface-strong", "--color-brand", 4.5],
      ["--color-surface-strong", "--color-brand-hover", 4.5],
      ["--color-surface-strong", "--color-brand-strong", 4.5],
      ["--color-surface-strong", "--color-navy", 4.5],
      ["--color-brand", "--color-surface-strong", 4.5],
      ["--color-brand", "--color-page-bg", 4.5],
      ["--color-brand", "--color-surface", 4.5],
      ["--color-brand", "--color-brand-soft", 4.5],
      ["--color-brand-strong", "--color-brand-soft", 4.5],
      ["--color-brand-strong", "--color-sky-soft", 4.5],
      ["--color-text-strong", "--color-highlight", 4.5],
      ["--color-highlight-text", "--color-surface-strong", 4.5],
      ["--color-highlight-text", "--color-highlight-soft", 4.5],
      ["--color-highlight", "--color-surface-strong", 3],
      ["--color-success-text", "--color-success-bg", 4.5],
      ["--color-warning-text", "--color-warning-bg", 4.5],
      ["--color-warning-text", "--color-attention-bg", 4.5],
      ["--color-danger-text", "--color-danger-bg", 4.5],
      ["--color-info-text", "--color-info-bg", 4.5],
    ];

    const failures = pairings
      .map(([text, fill, minimum]) => ({ text, fill, minimum, ratio: contrastRatio(token(text), token(fill)) }))
      .filter(({ ratio, minimum }) => ratio < minimum)
      .map(({ text, fill, minimum, ratio }) => `${text} on ${fill}: ${ratio.toFixed(2)} < ${minimum}`);

    expect(failures).toEqual([]);
  });

  it("keeps coral off white body text", () => {
    const tokens = readTokens();
    // White on coral is about 3.4:1, so coral fills carry navy text or an icon.
    expect(contrastRatio("#ffffff", tokens.get("--color-highlight") ?? "")).toBeLessThan(4.5);
    expect(contrastRatio(tokens.get("--color-text-strong") ?? "", tokens.get("--color-highlight") ?? "")).toBeGreaterThanOrEqual(4.5);
  });
});
