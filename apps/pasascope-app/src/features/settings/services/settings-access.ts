export type SettingsSection = "account" | "display" | "workflow" | "privacy" | "help";

export const SETTINGS_SECTIONS = Object.freeze([
  "account",
  "display",
  "workflow",
  "privacy",
  "help",
] as const satisfies readonly SettingsSection[]);

// Older section names that links may still carry.
const RENAMED_SECTIONS: Readonly<Record<string, SettingsSection>> = {
  profile: "account",
  notifications: "account",
  credentials: "privacy",
  accessibility: "display",
  organization: "workflow",
  export: "workflow",
};

export function isSettingsSection(section: unknown): section is SettingsSection {
  return SETTINGS_SECTIONS.includes(section as SettingsSection);
}

/** The section a `?section=` value names, including the older names it still answers to. */
export function parseSettingsSection(section: unknown): SettingsSection | null {
  if (typeof section === "string" && Object.hasOwn(RENAMED_SECTIONS, section)) return RENAMED_SECTIONS[section];
  return isSettingsSection(section) ? section : null;
}

/** Anything that is not a section, including the retired administrator ones, opens Account. */
export function resolveSettingsSection(requestedSection: unknown): SettingsSection {
  return parseSettingsSection(requestedSection) ?? "account";
}
