import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PrivacyScreen } from "@/components/privacy-screen";
import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import type { TranscriptLine } from "@/lib/workflow";

function renderEditor(lines: TranscriptLine[], onChange = vi.fn()) {
  render(
    <TranscriptEditorPanel
      lines={lines}
      qaStatus="not_run"
      qaIssues={[]}
      attested={false}
      busy={false}
      saveStatus="saved"
      onChange={onChange}
      onSaveDraft={vi.fn()}
      onRunQa={vi.fn()}
      onAttest={vi.fn()}
      onExport={vi.fn()}
    />
  );
  return onChange;
}

describe("assigning speakers to a draft without speaker separation", () => {
  const draft: TranscriptLine[] = [
    { lineId: "line-1", speaker: "UNK", text: "What do you see?" },
    { lineId: "line-2", speaker: "THER", text: "Look here." },
    { lineId: "line-3", speaker: "UNK", text: "A blue car." }
  ];

  it("sets only the unassigned lines to the chosen speaker", () => {
    const onChange = renderEditor(draft);

    expect(screen.getByText("2 lines have no speaker.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Child (CHI)" }));

    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ lineId: "line-1", speaker: "CHI" }),
      draft[1],
      expect.objectContaining({ lineId: "line-3", speaker: "CHI" })
    ]);
  });

  it("is not offered when every line has a speaker", () => {
    renderEditor([{ lineId: "line-1", speaker: "CHI", text: "A blue car." }]);

    expect(screen.queryByRole("button", { name: "Child (CHI)" })).not.toBeInTheDocument();
  });
});

describe("privacy page", () => {
  it("says what is stored, that recordings go to an external service, and how to remove data", () => {
    render(<PrivacyScreen />);

    expect(screen.getByRole("heading", { level: 1, name: "Privacy" })).toBeInTheDocument();
    expect(screen.getByText(/sent to an external transcription service \(currently Groq\)/)).toBeInTheDocument();
    expect(screen.getByText(/Withdrawing consent on a case removes its recordings/)).toBeInTheDocument();
    expect(screen.getByText(/Do not type a child's real name/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to sign in" })).toHaveAttribute("href", "/login");
  });
});
