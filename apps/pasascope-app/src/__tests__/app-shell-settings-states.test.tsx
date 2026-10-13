import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";

const settingsState = vi.hoisted(() => ({ current: { status: "loading", mode: "backend" } as Record<string, unknown> }));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => settingsState.current,
}));

describe("AppShell before the API has answered", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a loading state, not a refusal, while settings load", () => {
    settingsState.current = { status: "loading", mode: "backend" };
    render(<AppShell><div>Workspace content</div></AppShell>);

    expect(screen.getByRole("status")).toHaveTextContent("Opening your workspace");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText("Workspace content")).not.toBeInTheDocument();
    expect(screen.getByText(/starting up/)).toHaveClass("invisible");

    act(() => {
      vi.advanceTimersByTime(4000);
    });

    expect(screen.getByText(/starting up/)).not.toHaveClass("invisible");
  });

  it("offers a retry when the settings could not be confirmed, and still hides the workspace", () => {
    settingsState.current = { status: "error", mode: "backend", message: "Runtime settings unavailable" };
    render(<AppShell><div>Workspace content</div></AppShell>);

    expect(screen.getByRole("heading", { name: "The workspace could not be opened" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to login" })).toHaveAttribute("href", "/login");
    expect(screen.queryByText("Workspace content")).not.toBeInTheDocument();
  });
});
