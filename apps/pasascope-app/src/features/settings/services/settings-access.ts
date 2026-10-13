export type SettingsSection =
  | "account"
  | "organization"
  | "accessibility"
  | "notifications"
  | "privacy"
  | "export"
  | "help";

export const SETTINGS_SECTIONS = Object.freeze([
  "account",
  "organization",
  "accessibility",
  "notifications",
  "privacy",
  "export",
  "help",
] as const satisfies readonly SettingsSection[]);

export function isSettingsSection(section: unknown): section is SettingsSection {
  return SETTINGS_SECTIONS.includes(section as SettingsSection);
}

/** The section a `?section=` value names, with the two older names it still answers to. */
export function parseSettingsSection(section: unknown): SettingsSection | null {
  if (section === "profile") return "account";
  if (section === "credentials") return "privacy";
  return isSettingsSection(section) ? section : null;
}

/** Anything that is not a section, including the retired administrator ones, opens Account. */
export function resolveSettingsSection(requestedSection: unknown): SettingsSection {
  return parseSettingsSection(requestedSection) ?? "account";
}
