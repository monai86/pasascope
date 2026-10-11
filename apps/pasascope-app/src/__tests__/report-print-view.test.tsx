import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReportPrintView } from "@/features/reports/components/report-print-view";

const notFoundMock = vi.hoisted(() => vi.fn(() => {
  throw new Error("NEXT_NOT_FOUND");
}));

vi.mock("next/navigation", () => ({
  notFound: notFoundMock,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn(), prefetch: vi.fn() }),
}));

function stubExport(respond: (url: string) => Response) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/settings")) {
      return new Response(JSON.stringify({ mock_mode: true, auth_mode: "mock" }), { status: 200, headers: { "content-type": "application/json" } });
    }
    return respond(url);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  notFoundMock.mockClear();
});

describe("signed report print view", () => {
  it("shows exactly the HTML the export endpoint returns for the requested report", async () => {
    const fetchMock = stubExport(() => new Response(JSON.stringify({
      filename: "report-42.html",
      content: "<h1>Signed progress report</h1><script>window.pwned = true</script>",
      content_type: "text/html",
    }), { status: 200, headers: { "content-type": "application/json" } }));

    render(<ReportPrintView reportId="report-42" />);

    const frame = await screen.findByTestId("signed-report-frame");
    expect(frame.getAttribute("srcdoc")).toContain("Signed progress report");
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/reports/report-42/export?format=html"))).toBe(true);
    expect(screen.getByRole("button", { name: "Print or save as PDF" })).toBeEnabled();
  });

  it("renders the report in a sandbox that cannot run scripts", async () => {
    stubExport(() => new Response(JSON.stringify({ filename: "r.html", content: "<p>Report</p>", content_type: "text/html" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    }));

    render(<ReportPrintView reportId="report-42" />);

    const sandbox = (await screen.findByTestId("signed-report-frame")).getAttribute("sandbox") ?? "";
    expect(sandbox).not.toContain("allow-scripts");
    expect(sandbox).toContain("allow-modals");
  });

  it("reports a refused export as a failure and offers a retry, with no substitute content", async () => {
    let attempts = 0;
    stubExport(() => {
      attempts += 1;
      return new Response(JSON.stringify({ detail: "Report is not signed." }), { status: 409, headers: { "content-type": "application/json" } });
    });

    render(<ReportPrintView reportId="draft-report" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("This report cannot be printed");
    expect(screen.queryByTestId("signed-report-frame")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Print or save as PDF" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(attempts).toBe(2));
  });

  it("asks for a signed report instead of showing a sample when no report is named", () => {
    const fetchMock = stubExport(() => new Response("{}", { status: 200 }));

    render(<ReportPrintView />);

    expect(screen.getByRole("heading", { name: "Choose a signed report to print" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Reports" })).toHaveAttribute("href", "/reports");
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/export"))).toBe(false);
  });
});

describe("sample report preview route", () => {
  it("does not exist outside demo mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "");
    const { default: ReportPreviewPage } = await import("@/app/reports/preview/page");

    expect(() => ReportPreviewPage()).toThrow("NEXT_NOT_FOUND");
    expect(notFoundMock).toHaveBeenCalledOnce();
  });

  it("labels the sample as invented data when demo mode is on", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true");
    const { default: ReportPreviewPage } = await import("@/app/reports/preview/page");

    render(ReportPreviewPage());

    expect(screen.getByRole("status")).toHaveTextContent("Sample layout with invented data");
    expect(notFoundMock).not.toHaveBeenCalled();
  });
});
