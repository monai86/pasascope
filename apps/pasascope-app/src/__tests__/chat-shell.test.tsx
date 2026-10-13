import { render, screen, waitFor, within } from "@testing-library/react";
import { History } from "lucide-react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/app-shell";
import { ChatShellHeader, ChatShellPanel } from "@/components/chat-shell/chat-shell-context";

const settings = vi.hoisted(() => ({
  data: { auth_mode: "mock", access_model: { public_signup: true, review_gates: "open" } } as Record<string, unknown>,
}));

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({ status: "success", mode: "backend", data: settings.data }),
}));

const PUBLIC = { auth_mode: "mock", access_model: { public_signup: true, review_gates: "open" } };
const STRICT = { auth_mode: "mock", access_model: { public_signup: false, review_gates: "strict" } };

function renderShell(children: React.ReactNode = <div>Content</div>, active: "Today" | "Session" = "Today") {
  return render(<AppShell active={active}>{children}</AppShell>);
}

/** The chat frame is a lazily loaded chunk; this waits until it has rendered. */
async function renderChatShell(children?: React.ReactNode, active?: "Today" | "Session") {
  vi.stubEnv("NEXT_PUBLIC_CHAT_SHELL", "true");
  const view = renderShell(children, active);
  await screen.findByRole("navigation", { name: "Primary navigation" });
  return view;
}

afterEach(() => {
  vi.unstubAllEnvs();
  settings.data = PUBLIC;
});

describe("chat shell", () => {
  it("replaces the workbench frame when the flag is on and the API runs the public workflow", async () => {
    const { container } = await renderChatShell();

    expect(container.querySelector('[data-shell="chat"]')).not.toBeNull();
    const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
    // The full ordered list: adding, removing or reordering a destination fails here.
    expect(within(navigation).getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
      "/",
      "/cases",
      "/reports",
      "/settings",
    ]);
    expect(within(navigation).getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("navigation", { name: "Bottom navigation" })).toBeNull();
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("marks Cases as current on a session, which belongs to its case", async () => {
    await renderChatShell(<div>Content</div>, "Session");

    const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(within(navigation).getByRole("link", { name: "Cases" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps the workbench when the flag is off", () => {
    const { container } = renderShell();

    expect(container.querySelector('[data-shell="chat"]')).toBeNull();
    expect(screen.getByRole("navigation", { name: "Bottom navigation" })).toBeInTheDocument();
  });

  it("keeps the workbench when the API still enforces review gates", () => {
    vi.stubEnv("NEXT_PUBLIC_CHAT_SHELL", "true");
    settings.data = STRICT;
    const { container } = renderShell();

    expect(container.querySelector('[data-shell="chat"]')).toBeNull();
    expect(screen.getByRole("navigation", { name: "Bottom navigation" })).toBeInTheDocument();
  });

  it("gives a page its side panel, with a named button to open it as a sheet", async () => {
    await renderChatShell(
      <ChatShellPanel triggerLabel="Recent sessions" triggerIcon={History}>
        <p>Panel content</p>
      </ChatShellPanel>,
    );

    const trigger = await screen.findByRole("button", { name: "Recent sessions" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    const panel = document.getElementById(trigger.getAttribute("aria-controls") ?? "");
    expect(panel).not.toBeNull();
    expect(within(panel as HTMLElement).getByText("Panel content")).toBeInTheDocument();
  });

  it("has no panel button on a page without a side panel", async () => {
    await renderChatShell();

    expect(screen.queryByRole("button", { name: "Recent sessions" })).toBeNull();
  });

  it("lets a conversation put its own title and a way back in the header", async () => {
    await renderChatShell(<ChatShellHeader backHref="/" title="C-1001" subtitle="Step 2 of 4" />);

    await waitFor(() => expect(screen.getByRole("link", { name: "Back to home" })).toHaveAttribute("href", "/"));
    expect(screen.getByText("C-1001")).toBeInTheDocument();
    expect(screen.getByText("Step 2 of 4")).toBeInTheDocument();
  });
});
