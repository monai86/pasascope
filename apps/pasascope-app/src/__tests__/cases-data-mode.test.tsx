import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

beforeEach(() => {
  vi.unstubAllGlobals();
});

test("shows unavailable state without sample cases when backend loading fails", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => {
    throw new Error("offline");
  }));

  render(<CasesWorkspaceClient />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Cases are unavailable");
  expect(screen.queryByText("Demo child")).not.toBeInTheDocument();
});

test("does not substitute the first sample case for an unknown case id", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("not found", { status: 404 })));

  render(<CasesWorkspaceClient caseId="missing-case" />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Case could not be loaded");
  expect(screen.queryByText("Demo child")).not.toBeInTheDocument();
});

test.each(["timeline", "goals"])(
  "fails closed when the case %s request fails",
  async (failedResource) => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case-001")) {
        return new Response(JSON.stringify({
          case_id: "case-001",
          child_code: "C-001",
          nickname: "Backend child",
          consent_status: "granted",
        }), { status: 200 });
      }
      if (url.endsWith(`/cases/case-001/${failedResource}`)) {
        return new Response("secondary read failed", { status: 503 });
      }
      if (url.endsWith("/cases/case-001/timeline") || url.endsWith("/cases/case-001/goals")) {
        return new Response("[]", { status: 200 });
      }
      throw new Error(`Unexpected request: ${url}`);
    }));

    render(<CasesWorkspaceClient caseId="case-001" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Case could not be loaded");
    expect(screen.queryByText("No sessions recorded yet for this case.")).not.toBeInTheDocument();
    expect(screen.queryByText("No communication goals recorded yet.")).not.toBeInTheDocument();
    expect(screen.queryByText("Add communication goals when the care plan is ready.")).not.toBeInTheDocument();
  },
);

test("lets the therapist retry when cases cannot be loaded", async () => {
  let attempts = 0;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/cases")) {
      attempts += 1;
      if (attempts === 1) throw new Error("offline");
      return new Response(JSON.stringify([]), { status: 200, headers: { "content-type": "application/json" } });
    }
    return new Response(JSON.stringify({ mock_mode: true, auth_mode: "mock" }), { status: 200, headers: { "content-type": "application/json" } });
  }));

  render(<CasesWorkspaceClient />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Cases are unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));

  await waitFor(() => expect(attempts).toBe(2));
  expect(await screen.findByRole("heading", { name: "No cases yet" })).toBeInTheDocument();
});

test("offers the way back to Cases when a single case cannot be loaded", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("not found", { status: 404 })));

  render(<CasesWorkspaceClient caseId="missing-case" />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Case could not be loaded");
  expect(screen.getByRole("link", { name: "Back to Cases" })).toHaveAttribute("href", "/cases");
});

test("tells an empty caseload apart from filters that match nothing", async () => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith("/cases")) {
      return new Response(JSON.stringify([
        { case_id: "case-1", child_code: "C-1001", consent_status: "granted", language: "Thai" },
      ]), { status: 200, headers: { "content-type": "application/json" } });
    }
    return new Response(JSON.stringify({ mock_mode: true, auth_mode: "mock" }), { status: 200, headers: { "content-type": "application/json" } });
  }));

  render(<CasesWorkspaceClient />);

  const search = await screen.findByRole("searchbox", { name: "Search cases" });
  fireEvent.change(search, { target: { value: "no such case" } });

  expect(screen.getByRole("heading", { name: "No cases match these filters" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "No cases yet" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

  expect(search).toHaveValue("");
  expect(screen.queryByRole("heading", { name: "No cases match these filters" })).not.toBeInTheDocument();
});
