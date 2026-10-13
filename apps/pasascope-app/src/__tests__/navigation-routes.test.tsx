import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import HomePage from "@/app/page";
import { BottomNav } from "@/components/bottom-nav";
import { Sidebar } from "@/components/sidebar";

const redirectMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

vi.mock("@/components/work-queue-dashboard", () => ({
  WorkQueueDashboard: () => <div>Home screen entry</div>,
}));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock" },
  }),
}));

vi.mock("@/lib/use-supabase-access-session", () => ({
  useSupabaseAccessSession: () => null,
}));

// Shell destinations in the order the shared navigation model declares them.
const CANONICAL_NAV_HREFS = [
  "/today",
  "/cases",
  "/cases?intent=start-session",
  "/reports",
  "/settings",
] as const;

// The desktop sidebar lists the same destinations in the same order, starting
// from Today (the single home), plus the desktop-only clinic overview.
const DESKTOP_SIDEBAR_HREFS = [
  "/today",
  "/dashboard",
  "/cases",
  "/cases?intent=start-session",
  "/reports",
  "/settings",
] as const;

describe("canonical workbench navigation", () => {
  beforeEach(() => {
    redirectMock.mockReset();
  });

  test.each([
    {
      surface: "desktop",
      navLabel: "Primary navigation",
      expectedHrefs: [...DESKTOP_SIDEBAR_HREFS],
      renderNavigation: (activeSessionId?: string) => (
        <Sidebar active="Today" activeSessionId={activeSessionId} />
      ),
    },
    {
      surface: "mobile",
      navLabel: "Bottom navigation",
      expectedHrefs: [...CANONICAL_NAV_HREFS],
      renderNavigation: (activeSessionId?: string) => (
        <BottomNav active="Today" activeSessionId={activeSessionId} />
      ),
    },
  ])("$surface navigation exposes exactly one canonical route set", ({ navLabel, expectedHrefs, renderNavigation }) => {
    render(renderNavigation());

    // The full ordered destination list is asserted, not just the presence of a
    // few links, so adding, removing, or reordering a shell destination fails
    // here instead of silently drifting past the documented route model.
    const navigation = screen.getByRole("navigation", { name: navLabel });
    const hrefs = within(navigation)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefs).toEqual(expectedHrefs);

    expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Today" })).toHaveAttribute("href", "/today");
    expect(screen.getByRole("link", { name: "Cases" })).toHaveAttribute("href", "/cases");
    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute("href", "/cases?intent=start-session");
    expect(screen.getByRole("link", { name: "Reports" })).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
  });

  test("the clinic overview stays reachable on desktop and hidden on mobile", () => {
    const desktop = render(<Sidebar active="Dashboard" />);

    const desktopDashboard = screen.getByRole("link", { name: "Dashboard" });
    expect(desktopDashboard).toHaveAttribute("href", "/dashboard");
    expect(desktopDashboard).toHaveAttribute("aria-current", "page");
    desktop.unmount();

    render(<BottomNav active="Dashboard" />);

    expect(screen.queryByRole("link", { name: "Dashboard" })).not.toBeInTheDocument();
  });

  test.each([
    ["desktop", (activeSessionId: string) => <Sidebar active="Session" activeSessionId={activeSessionId} />],
    ["mobile", (activeSessionId: string) => <BottomNav active="Session" activeSessionId={activeSessionId} />],
  ])("%s navigation deep-links only to the explicitly active session", (_surface, renderNavigation) => {
    render(renderNavigation("session_approved_001"));

    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      "/sessions/session_approved_001",
    );
    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute("aria-current", "page");
  });

  test.each(["", "   ", "../audit", "session/other", "session?view=report"])(
    "does not construct a Session deep link from unsafe identifier %j",
    (activeSessionId) => {
      render(<Sidebar active="Session" activeSessionId={activeSessionId} />);

      expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
        "href",
        "/cases?intent=start-session",
      );
    },
  );

  test.each([
    ["desktop", (activeCaseId?: string) => <Sidebar active="Cases" activeCaseId={activeCaseId} />],
    ["mobile", (activeCaseId?: string) => <BottomNav active="Cases" activeCaseId={activeCaseId} />],
  ])("%s Session link carries the known case into start-session", (_surface, renderNavigation) => {
    render(renderNavigation("case_approved_001"));

    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      "/cases?intent=start-session&case_id=case_approved_001",
    );
  });

  test.each([
    "",
    "   ",
    "../audit",
    "case id with spaces",
  ])("drops an unsafe case id %j from the Session link", (activeCaseId) => {
    render(<Sidebar active="Cases" activeCaseId={activeCaseId} />);

    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      "/cases?intent=start-session",
    );
  });

  test("prefers the active session over case context for the Session link", () => {
    render(<Sidebar active="Session" activeSessionId="session_approved_001" activeCaseId="case_approved_001" />);

    expect(screen.getByRole("link", { name: "Session" })).toHaveAttribute(
      "href",
      "/sessions/session_approved_001",
    );
  });

  test("the root route is the home screen of whichever shell is running", () => {
    render(<>{HomePage()}</>);

    expect(redirectMock).not.toHaveBeenCalled();
    expect(screen.getByText("Home screen entry")).toBeInTheDocument();
  });

  test("the root route redirects to Today in a build that opted out of the chat shell", () => {
    vi.stubEnv("NEXT_PUBLIC_CHAT_SHELL", "false");
    try {
      HomePage();
    } finally {
      vi.unstubAllEnvs();
    }

    expect(redirectMock).toHaveBeenCalledOnce();
    expect(redirectMock).toHaveBeenCalledWith("/today");
  });
});
