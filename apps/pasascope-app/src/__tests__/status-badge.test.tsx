import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/status-badge";

function badgeFor(text: string): HTMLElement {
  const badge = screen.getByText(text).closest<HTMLElement>("[data-tone]");
  if (!badge) throw new Error(`No status badge contains "${text}"`);
  return badge;
}

describe("StatusBadge component pipeline statuses and normalization", () => {
  it.each([
    ["Awaiting Consent", "attention"],
    ["Ready for Audio", "info"],
    ["Transcribing", "info"],
    ["CHA Generating", "info"],
    ["ML Pending", "attention"],
    ["Review Required", "warning"],
    ["Needs Review", "warning"],
    ["Report Ready", "success"],
    ["Ready", "success"],
    ["Attested", "success"],
    ["Signed Off", "solid"],
    ["Failed", "danger"],
    ["Draft", "neutral"],
    ["Withdrawn", "neutral"],
  ])("renders %s with the %s tone", (status, tone) => {
    render(<StatusBadge status={status} />);
    expect(badgeFor(status)).toHaveAttribute("data-tone", tone);
    expect(badgeFor(status)).not.toHaveAttribute("data-pulse");
  });

  it.each([
    ["Recording", "highlight"],
    ["Uploading", "info"],
  ])("pulses while %s is in progress", (status, tone) => {
    render(<StatusBadge status={status} />);
    expect(badgeFor(status)).toHaveAttribute("data-tone", tone);
    expect(badgeFor(status)).toHaveAttribute("data-pulse", "true");
  });

  it("pairs every status with an icon so state is not carried by colour alone", () => {
    render(<StatusBadge status="Report Ready" />);
    const icon = badgeFor("Report Ready").querySelector("svg");
    expect(icon).not.toBeNull();
    expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  it("never renders a success state in green", () => {
    render(<StatusBadge status="Report Ready" />);
    expect(badgeFor("Report Ready").className).not.toMatch(/green|emerald|teal/);
  });

  it.each([
    ["awaiting_consent", "Awaiting Consent", "attention"],
    ["ml_pending", "ML Pending", "attention"],
    ["review_required", "Review Required", "warning"],
    ["report_ready", "Report Ready", "success"],
    ["ready_for_audio", "Ready for Audio", "info"],
    ["recording", "Recording", "highlight"],
    ["uploading", "Uploading", "info"],
    ["transcribing", "Transcribing", "info"],
    ["cha_generating", "CHA Generating", "info"],
  ])("normalizes %s to %s", (input, label, tone) => {
    render(<StatusBadge status={input} />);
    expect(badgeFor(label)).toHaveAttribute("data-tone", tone);
  });

  it("renders unknown/unmatched statuses with draft styles but keeps original text", () => {
    render(<StatusBadge status="Unknown Status" />);
    expect(badgeFor("Unknown Status")).toHaveAttribute("data-tone", "neutral");
  });

  it("properly capitalizes draft when casing variation is provided", () => {
    render(<StatusBadge status="draft" />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });
});
