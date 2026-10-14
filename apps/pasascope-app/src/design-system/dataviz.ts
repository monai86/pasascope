/**
 * Colours that carry data rather than chrome: who is speaking, and the marks
 * drawn on the audio workbench. This is the single source for the waveform
 * canvases, their legend and the utterance list, so a speaker has one colour
 * everywhere.
 *
 * Speaker identity uses two hues, coral for the child and blue for the
 * clinician, checked for colour-vision separation on each surface with the
 * dataviz palette validator (all pairs, protanopia and deuteranopia):
 *
 *   navy  #0F1B33: #F0566A, #2E9BE6  -> worst pair ΔE 19.1, contrast >= 3:1
 *   white #FFFFFF: #F0566A, #0A66D6  -> worst pair ΔE 19.9, contrast >= 3:1
 *
 * A third hue was tried and rejected: violet collapses into the blue (ΔE 1.6
 * for protanopia) and amber into the coral. Every other speaker is therefore
 * a neutral, and the speaker code is always shown as text beside the colour,
 * so identity never depends on colour alone.
 */

export type SpeakerRole = "child" | "clinician" | "other";

export type SpeakerSurface = "navy" | "light";

/** CHAT speaker codes arrive with or without the leading asterisk. */
export function speakerRole(speaker: string): SpeakerRole {
  const code = speaker.trim().replace(/^\*/, "").toUpperCase();
  if (code === "CHI") return "child";
  if (code === "INV" || code === "THER") return "clinician";
  return "other";
}

export const SPEAKER_COLOURS: Readonly<Record<SpeakerSurface, Readonly<Record<SpeakerRole, string>>>> = {
  navy: { child: "#F0566A", clinician: "#2E9BE6", other: "#9FB2D3" },
  light: { child: "#F0566A", clinician: "#0A66D6", other: "#586890" },
};

export const SPEAKER_ROLE_LABELS: Readonly<Record<SpeakerRole, string>> = {
  child: "CHI (Child)",
  clinician: "INV (Clinician)",
  other: "Other speaker",
};

export function speakerColour(speaker: string, surface: SpeakerSurface): string {
  return SPEAKER_COLOURS[surface][speakerRole(speaker)];
}

/** Marks drawn on the navy waveform canvases. */
export const WORKBENCH_CANVAS = {
  background: "#0F1B33",
  grid: "#2A3D63",
  axisLabel: "#9FB2D3",
  segmentLabel: "#FFFFFF",
  // White, so the playhead is never mistaken for a coral child segment.
  playhead: "#FFFFFF",
  peaks: "#7CC8F8",
  viewport: "#FFFFFF",
} as const;

/** `#RRGGBB` as an `rgba()` string, for translucent segment fills. */
export function withAlpha(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const channel = (start: number) => Number.parseInt(value.slice(start, start + 2), 16);
  return `rgba(${channel(0)}, ${channel(2)}, ${channel(4)}, ${alpha})`;
}
