import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";
import {
  parseSettingsSection,
  resolveSettingsSection,
} from "@/features/settings/services/settings-access";
import { saveMockAccessSession } from "@/lib/mock-access-session";

beforeEach(() => {
  window.sessionStorage.clear();
  window.localStorage.clear();
  window.history.replaceState({}, "", "/settings");
  saveMockAccessSession({ role: "therapist", organizationId: "pilot_org_001", aal: "aal2" });
});

afterEach(cleanup);

describe("Settings", () => {
  it("uses a mobile category index before drilling into one selected settings page", () => {
    render(<SettingsWorkspaceClient />);

    const workspace = screen.getByTestId("settings-workspace");
    expect(workspace).toHaveAttribute("data-mobile-view", "categories");

    const mobileNavigation = screen.getByRole("navigation", { name: "Settings categories mobile" });
    fireEvent.click(within(mobileNavigation).getByRole("link", { name: "Privacy & Security" }));
    expect(workspace).toHaveAttribute("data-mobile-view", "detail");

    fireEvent.click(screen.getByRole("button", { name: "All settings categories" }));
    expect(workspace).toHaveAttribute("data-mobile-view", "categories");
  });

  it("lists every category, shows one at a time and keeps the choice in the address", () => {
    render(<SettingsWorkspaceClient />);

    const navigation = screen.getByRole("navigation", { name: "Settings categories mobile" });
    // The full ordered list: adding, removing or reordering a category fails here.
    expect(within(navigation).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Account",
      "Organization",
      "Accessibility & Display",
      "Notifications",
      "Privacy & Security",
      "Export",
      "Help",
    ]);
    expect(screen.getByRole("heading", { name: "Account" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Account" })).toHaveAttribute("aria-current", "page");

    fireEvent.click(screen.getByRole("link", { name: "Accessibility & Display" }));
    expect(screen.getByRole("heading", { name: "Accessibility & Display" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Account" })).not.toBeInTheDocument();
    expect(window.location.search).toBe("?section=accessibility");
  });

  it("opens the requested category as a detail page", () => {
    render(<SettingsWorkspaceClient initialSection="privacy" initialSectionExplicit />);

    expect(screen.getByTestId("settings-workspace")).toHaveAttribute("data-mobile-view", "detail");
    expect(screen.getByRole("link", { name: "Privacy & Security" })).toHaveAttribute("aria-current", "page");
  });

  it("opens Account for a missing, unknown or retired administrator section", () => {
    for (const requested of [undefined, "", "nonsense", "team", "invitations", "audit", ["account"]]) {
      expect(resolveSettingsSection(requested)).toBe("account");
    }
    expect(parseSettingsSection("team")).toBeNull();
    expect(resolveSettingsSection("export")).toBe("export");
  });

  it("still answers to the two older section names", () => {
    expect(parseSettingsSection("profile")).toBe("account");
    expect(parseSettingsSection("credentials")).toBe("privacy");
  });
});
