import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SessionContextHeader } from "@/features/sessions/components/session-context-header";

describe("SessionContextHeader", () => {
  it("shows persisted clinical context, explicit data mode, and canonical Session views", () => {
    render(
      <SessionContextHeader
        title="Session Intake"
        description="Prepare the session for therapist review."
        context={{
          sessionId: "session-1",
          caseId: "case-1024",
          caseLabel: "C-1024",
          sourceLabel: "Uploaded audio",
          consentStatus: "granted",
          workflowStatus: "Draft",
          dataMode: "backend",
          activeView: "intake",
        }}
      />,
    );

    expect(screen.getByRole("region", { name: "Session context" })).toBeInTheDocument();
    expect(screen.getAllByText("C-1024").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Consent granted")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cases" })).toHaveAttribute("href", "/cases");
    expect(screen.getByRole("link", { name: "C-1024" })).toHaveAttribute("href", "/cases/case-1024");
    expect(screen.getByRole("link", { name: "Intake" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute(
      "href",
      "/sessions/session-1?view=transcript",
    );
    expect(screen.getByRole("link", { name: "Findings" })).toHaveAttribute(
      "href",
      "/sessions/session-1?view=findings",
    );
    expect(screen.getByRole("link", { name: "Report" })).toHaveAttribute(
      "href",
      "/sessions/session-1?view=report",
    );
  });

  it("renders unavailable instead of fabricating missing context", () => {
    render(
      <SessionContextHeader
        title="Session Intake"
        description="Prepare the session for therapist review."
        context={{ activeView: "intake", dataMode: "unavailable" }}
      />,
    );

    expect(screen.getAllByText("Unavailable").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute(
      "href",
      "/cases?intent=start-session",
    );
  });

  it("compresses transcript context into a workbench header without the page-level eyebrow", () => {
    render(
      <SessionContextHeader
        density="compact"
        title="Review Transcript"
        description="Confirm speaker labels before downstream review."
        context={{
          sessionId: "session-compact",
          caseId: "case-compact",
          caseLabel: "Case C-18",
          sourceLabel: "Uploaded audio",
          workflowStatus: "Needs review",
          dataMode: "backend",
          activeView: "transcript",
        }}
      />,
    );

    const context = screen.getByRole("region", { name: "Session context" });
    expect(context).toHaveAttribute("data-density", "compact");
    expect(screen.getByRole("heading", { level: 1, name: "Review Transcript" })).toBeInTheDocument();
    expect(screen.queryByText("Clinical decision-support prototype")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Case C-18" })).toHaveAttribute("href", "/cases/case-compact");
  });
});

describe("SessionContextHeader step completion", () => {
  const base = {
    sessionId: "session-1",
    caseId: "case-1024",
    caseLabel: "C-1024",
    dataMode: "backend" as const,
  };

  it("ticks only the steps the session has actually finished", () => {
    render(
      <SessionContextHeader
        title="Findings"
        description="Review extracted features."
        context={{ ...base, activeView: "findings", completion: { intake: true, transcript: false, findings: false, report: false } }}
      />,
    );

    // The Transcript step sits before the active Findings step, but the
    // transcript was never attested, so it must not look done.
    expect(screen.getByRole("link", { name: "Intake" })).toHaveAttribute("data-step-state", "complete");
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute("data-step-state", "pending");
    expect(screen.getByRole("link", { name: "Findings" })).toHaveAttribute("data-step-state", "current");
    expect(screen.getByRole("link", { name: "Report" })).toHaveAttribute("data-step-state", "pending");
  });

  it("describes a finished step to assistive technology without renaming its link", () => {
    render(
      <SessionContextHeader
        title="Review Transcript"
        description="Confirm speaker labels."
        context={{ ...base, activeView: "transcript", completion: { intake: true } }}
      />,
    );

    expect(screen.getByRole("link", { name: "Intake" })).toHaveAccessibleDescription("Step complete");
    expect(screen.getByRole("link", { name: "Transcript" })).not.toHaveAccessibleDescription("Step complete");
  });

  it("ticks nothing when completion is unknown", () => {
    render(
      <SessionContextHeader
        title="Report Summary"
        description="Review and sign."
        context={{ ...base, activeView: "report" }}
      />,
    );

    for (const name of ["Intake", "Transcript", "Findings"]) {
      expect(screen.getByRole("link", { name })).toHaveAttribute("data-step-state", "pending");
    }
  });
});
