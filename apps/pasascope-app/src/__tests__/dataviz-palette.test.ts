import { describe, expect, it } from "vitest";

import { SPEAKER_COLOURS, speakerColour, speakerRole, withAlpha, WORKBENCH_CANVAS } from "@/design-system/dataviz";
import { contrastRatio, isGreenish, parseHex } from "./support/palette-scan";

const SURFACES = { navy: "#0F1B33", light: "#FFFFFF" } as const;

describe("speaker palette", () => {
  it("classifies CHAT speaker codes with or without the asterisk", () => {
    expect(speakerRole("CHI")).toBe("child");
    expect(speakerRole("*chi")).toBe("child");
    expect(speakerRole("*INV")).toBe("clinician");
    expect(speakerRole("MOT")).toBe("other");
    expect(speakerRole("")).toBe("other");
  });

  it("gives a speaker one colour per surface", () => {
    expect(speakerColour("*CHI", "navy")).toBe(SPEAKER_COLOURS.navy.child);
    expect(speakerColour("INV", "light")).toBe(SPEAKER_COLOURS.light.clinician);
  });

  it("pins the validated colours", () => {
    // Changing a value means re-running the dataviz palette validator with
    // `--pairs all` on both surfaces; see the note in dataviz.ts.
    expect(SPEAKER_COLOURS).toEqual({
      navy: { child: "#F0566A", clinician: "#2E9BE6", other: "#9FB2D3" },
      light: { child: "#F0566A", clinician: "#0A66D6", other: "#586890" },
    });
  });

  it("uses no green for any speaker or canvas mark", () => {
    const colours = [...Object.values(SPEAKER_COLOURS.navy), ...Object.values(SPEAKER_COLOURS.light), ...Object.values(WORKBENCH_CANVAS)];
    for (const colour of colours) {
      expect(isGreenish(parseHex(colour)), colour).toBe(false);
    }
  });

  it("keeps every speaker mark at 3:1 or better against its surface", () => {
    for (const surface of ["navy", "light"] as const) {
      for (const [role, colour] of Object.entries(SPEAKER_COLOURS[surface])) {
        expect(contrastRatio(colour, SURFACES[surface]), `${role} on ${surface}`).toBeGreaterThanOrEqual(3);
      }
    }
  });

  it("separates the child and clinician by hue, not only by lightness", () => {
    for (const surface of ["navy", "light"] as const) {
      const child = parseHex(SPEAKER_COLOURS[surface].child);
      const clinician = parseHex(SPEAKER_COLOURS[surface].clinician);
      // Coral is red-dominant and the clinician blue is blue-dominant.
      expect(child.r).toBeGreaterThan(child.b);
      expect(clinician.b).toBeGreaterThan(clinician.r);
    }
  });

  it("keeps the playhead distinct from the coral child segments", () => {
    expect(WORKBENCH_CANVAS.playhead).not.toBe(SPEAKER_COLOURS.navy.child);
    expect(contrastRatio(WORKBENCH_CANVAS.playhead, WORKBENCH_CANVAS.background)).toBeGreaterThanOrEqual(7);
  });

  it("builds translucent fills from a hex colour", () => {
    expect(withAlpha("#F0566A", 0.25)).toBe("rgba(240, 86, 106, 0.25)");
  });
});
