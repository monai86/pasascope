import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

/**
 * Scanner behind the palette contract. It answers three questions about the
 * app's styling sources: does anything still render a green, does anything
 * still bypass the design tokens, and does every `var()` resolve.
 */

const TOKENS_FILE = "src/design-system/tokens.css";

// Custom properties declared at runtime rather than in tokens.css.
// Fonts are set by next/font; --progress is set inline by the recording's position slider.
const RUNTIME_PROPERTIES = new Set(["--font-noto-thai", "--font-noto", "--font-prompt", "--progress"]);

// Another company's logo keeps its own colours. The "Continue with Google"
// button draws Google's four-colour G, one segment of which is green; that is
// their mark, not part of this product's palette.
const THIRD_PARTY_MARK_COLOURS: Readonly<Record<string, readonly string[]>> = {
  "src/components/supabase-login-form-client.tsx": ["#34A853"],
};

const GREEN_PALETTES = ["green", "emerald", "teal", "lime", "cyan"];
const OTHER_PALETTES = [
  "slate", "gray", "zinc", "neutral", "stone", "red", "orange", "amber", "yellow",
  "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose",
];
const SHADE = "(?:50|[1-9]00|950)";

const GREEN_CLASS = new RegExp(`\\b(?:${GREEN_PALETTES.join("|")})-${SHADE}\\b`, "g");
const RAW_PALETTE_CLASS = new RegExp(`\\b(?:${OTHER_PALETTES.join("|")})-${SHADE}\\b`, "g");
const DARK_VARIANT = /\bdark:[a-z[]/g;
const ALIAS_PROPERTY = /--color-(?:pasa-teal|accent|primary|scope-coral|warm-butter)[a-z-]*/g;
const ALIAS_CLASS = /\b(?:text|bg|border|ring|from|to|via|fill|stroke|outline|divide|decoration)-(?:clinical|blossom|aqua|safety)\b/g;

const HEX_LONG = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6})\b/g;
const HEX_SHORT = /#[0-9a-fA-F]{3}\b/g;
const RGB_FUNCTION = /rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})/g;

export type Rgb = { r: number; g: number; b: number };

function listFiles(root: string, extensions: readonly string[]): string[] {
  const absolute = resolve(process.cwd(), root);
  if (!existsSync(absolute)) return [];
  return readdirSync(absolute, { recursive: true, encoding: "utf8" })
    .map((entry) => `${root}/${entry}`)
    .filter((entry) => extensions.some((extension) => entry.endsWith(extension)));
}

/** Every file that can put a colour on screen, tests excluded. */
export function styleSources(): string[] {
  return [
    ...listFiles("src", [".ts", ".tsx", ".css", ".svg"]).filter((entry) => !entry.includes("__tests__")),
    ...listFiles("public", [".svg"]),
    "tailwind.config.ts",
  ].sort();
}

export function readSource(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

export function parseHex(hex: string): Rgb {
  const digits = hex.replace("#", "");
  const full = digits.length === 3 ? digits.split("").map((digit) => digit + digit).join("") : digits;
  return {
    r: Number.parseInt(full.slice(0, 2), 16),
    g: Number.parseInt(full.slice(2, 4), 16),
    b: Number.parseInt(full.slice(4, 6), 16),
  };
}

/**
 * True for any colour a viewer would call green, teal or turquoise: hue from
 * yellow-green through cyan with visible saturation. Decided from the value so
 * a new green cannot slip past a list of known hex codes.
 */
export function isGreenish({ r, g, b }: Rgb): boolean {
  const red = r / 255;
  const green = g / 255;
  const blue = b / 255;
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const delta = max - min;
  const lightness = (max + min) / 2;
  if (delta === 0 || lightness > 0.975 || lightness < 0.04) return false;

  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  let hue: number;
  if (max === red) hue = ((green - blue) / delta) % 6;
  else if (max === green) hue = (blue - red) / delta + 2;
  else hue = (red - green) / delta + 4;
  hue = (hue * 60 + 360) % 360;

  return hue >= 70 && hue <= 190 && saturation > 0.15;
}

function matches(text: string, pattern: RegExp): string[] {
  return [...text.matchAll(pattern)].map((match) => match[0]);
}

/** Green palette classes and green colour literals in one source file. */
export function findGreen(path: string, text: string): string[] {
  const offenders = matches(text, GREEN_CLASS);

  const hexLiterals = matches(text, HEX_LONG);
  // A three-digit hex is only unambiguous in a stylesheet or SVG; in TSX the
  // same shape is usually a URL fragment.
  if (path.endsWith(".css") || path.endsWith(".svg")) hexLiterals.push(...matches(text, HEX_SHORT));
  const thirdPartyMark = (THIRD_PARTY_MARK_COLOURS[path] ?? []).map((colour) => colour.toLowerCase());
  for (const literal of hexLiterals) {
    if (thirdPartyMark.includes(literal.toLowerCase())) continue;
    if (isGreenish(parseHex(literal))) offenders.push(literal);
  }

  for (const match of text.matchAll(RGB_FUNCTION)) {
    const rgb = { r: Number(match[1]), g: Number(match[2]), b: Number(match[3]) };
    if (isGreenish(rgb)) offenders.push(`${match[0]})`);
  }

  return offenders;
}

/**
 * Styling that bypasses the design system: raw Tailwind palette classes,
 * `dark:` variants in a light-only product, and the names of the previous
 * palette, which were removed and must not be declared or used again.
 */
export function findLegacyStyling(_path: string, text: string): string[] {
  return [
    ...matches(text, RAW_PALETTE_CLASS),
    ...matches(text, DARK_VARIANT).map(() => "dark:"),
    ...matches(text, ALIAS_PROPERTY),
    ...matches(text, ALIAS_CLASS),
  ];
}

/** Custom properties declared in tokens.css, with `var()` aliases resolved. */
export function readTokens(): Map<string, string> {
  const raw = new Map<string, string>();
  for (const match of readSource(TOKENS_FILE).matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    raw.set(match[1], match[2].trim());
  }

  const resolveValue = (value: string, depth = 0): string => {
    const reference = /^var\(\s*(--[\w-]+)\s*\)$/.exec(value);
    if (!reference || depth > 8) return value;
    const target = raw.get(reference[1]);
    return target === undefined ? value : resolveValue(target, depth + 1);
  };

  return new Map([...raw].map(([name, value]) => [name, resolveValue(value)]));
}

/** `var(--name)` references in a file that nothing defines. */
export function findUndefinedProperties(text: string, tokens: ReadonlyMap<string, string>): string[] {
  const declaredHere = new Set([...text.matchAll(/(--[\w-]+)\s*:/g)].map((match) => match[1]));
  const undefinedNames = new Set<string>();
  for (const match of text.matchAll(/var\(\s*(--[\w-]+)/g)) {
    const name = match[1];
    if (tokens.has(name) || declaredHere.has(name) || RUNTIME_PROPERTIES.has(name) || name.startsWith("--tw-")) continue;
    undefinedNames.add(name);
  }
  return [...undefinedNames];
}

function relativeLuminance({ r, g, b }: Rgb): number {
  const channel = (value: number) => {
    const scaled = value / 255;
    return scaled <= 0.04045 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG 2 contrast ratio between two hex colours. */
export function contrastRatio(foreground: string, background: string): number {
  const first = relativeLuminance(parseHex(foreground));
  const second = relativeLuminance(parseHex(background));
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}
