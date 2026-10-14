import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import type { TranscriptLine } from "@/lib/workflow";

const lines: TranscriptLine[] = [
  { lineId: "line-1", speaker: "THER", text: "What do you see?", startMs: 100, endMs: 900 },
  { lineId: "line-2", speaker: "CHI", text: "A blue car.", startMs: 950, endMs: 1600 }
];

describe("TranscriptEditorPanel", () => {
  it("renders line fields and supports editing, adding, deleting, and unclear status", () => {
    const onChange = vi.fn();
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

    expect(screen.getByLabelText("Timestamp for line 1")).toHaveValue("00:00.100 – 00:00.900");
    expect(screen.getByLabelText("Speaker for line 1")).toHaveValue("THER");
    expect(screen.getByLabelText("Utterance text 1")).toHaveValue("What do you see?");
    expect(screen.getAllByText("Not checked").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Timestamp for line 1"), { target: { value: "00:00.200 – 00:01.100" } });
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ lineId: "line-1", startMs: 200, endMs: 1100 }),
      lines[1]
    ]);

    fireEvent.change(screen.getByLabelText("Utterance text 1"), { target: { value: "What can you see?" } });
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ lineId: "line-1", text: "What can you see?" }),
      lines[1]
    ]);

    fireEvent.change(screen.getByLabelText("Speaker for line 2"), { target: { value: "PAR" } });
    expect(onChange).toHaveBeenLastCalledWith([
      lines[0],
      expect.objectContaining({ lineId: "line-2", speaker: "PAR" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 2" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Mark unclear" }));
    expect(onChange).toHaveBeenLastCalledWith([
      lines[0],
      expect.objectContaining({ lineId: "line-2", unclear: true })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Add line" }));
    expect(onChange).toHaveBeenLastCalledWith([
      ...lines,
      expect.objectContaining({ speaker: "UNK", text: "" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 2" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete line" }));
    expect(onChange).toHaveBeenLastCalledWith([lines[0]]);
  });

  it("supports split and adjacent merge actions", () => {
    const onChange = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={[
          { lineId: "line-1", speaker: "CHI", text: "blue car goes fast" },
          { lineId: "line-2", speaker: "CHI", text: "down the road" }
        ]}
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

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Split line" }));
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ speaker: "CHI" }),
      expect.objectContaining({ speaker: "CHI" }),
      expect.objectContaining({ lineId: "line-2" })
    ]);

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Merge with next" }));
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ text: "blue car goes fast down the road" })
    ]);
  });

  function renderEditor(editorLines: TranscriptLine[], extra: { audioUrl?: string } = {}) {
    const onChange = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={editorLines}
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
        {...extra}
      />
    );
    return onChange;
  }

  const unknownLines: TranscriptLine[] = [
    { lineId: "u-1", speaker: "UNK", text: "what is this cookies", startMs: 0, endMs: 2000 },
    { lineId: "u-2", speaker: "THER", text: "good job" },
    { lineId: "u-3", speaker: "UNK", text: "more" }
  ];

  it("splits a line at the cursor, divides its time in proportion, and keeps the speaker", () => {
    const onChange = renderEditor(unknownLines);
    const text = screen.getByLabelText("Utterance text 1") as HTMLTextAreaElement;
    text.setSelectionRange(13, 13);

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Split line" }));

    expect(onChange).toHaveBeenLastCalledWith([
      { lineId: "u-1", speaker: "UNK", text: "what is this", startMs: 0, endMs: 1300 },
      expect.objectContaining({ speaker: "UNK", text: "cookies", startMs: 1300, endMs: 2000 }),
      unknownLines[1],
      unknownLines[2]
    ]);

    text.setSelectionRange(4, 4);
    fireEvent.keyDown(text, { key: "Enter", ctrlKey: true });
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ text: "what", endMs: 400 }),
      expect.objectContaining({ text: "is this cookies", startMs: 400 }),
      unknownLines[1],
      unknownLines[2]
    ]);
  });

  it("sets the speaker of a line with one button and moves to the next line without a speaker", () => {
    const onChange = renderEditor(unknownLines);

    const child = screen.getByRole("button", { name: "Set line 1 to Child" });
    expect(child).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Set line 2 to Therapist" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(child);

    expect(onChange).toHaveBeenLastCalledWith([
      { ...unknownLines[0], speaker: "CHI" },
      unknownLines[1],
      unknownLines[2]
    ]);
    expect(screen.getByRole("option", { name: "Transcript line 3" })).toHaveAttribute("aria-selected", "true");
  });

  it("assigns speakers and moves between lines from the keyboard, but not while typing", () => {
    const onChange = renderEditor(unknownLines);
    const list = screen.getByRole("listbox", { name: "Transcript lines" });

    fireEvent.keyDown(list, { key: "2" });
    expect(onChange).toHaveBeenLastCalledWith([
      { ...unknownLines[0], speaker: "THER" },
      unknownLines[1],
      unknownLines[2]
    ]);
    expect(screen.getByRole("option", { name: "Transcript line 3" })).toHaveAttribute("aria-selected", "true");

    fireEvent.keyDown(list, { key: "ArrowUp" });
    expect(screen.getByRole("option", { name: "Transcript line 2" })).toHaveAttribute("aria-selected", "true");
    expect(list).toHaveAttribute("aria-activedescendant", "transcript-line-u-2");

    onChange.mockClear();
    fireEvent.keyDown(screen.getByLabelText("Utterance text 2"), { key: "1" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("plays one line from its own button and stops at the end of that line", () => {
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
    const pause = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
    try {
      renderEditor(unknownLines, { audioUrl: "blob:session-audio" });
      expect(screen.queryByRole("button", { name: "Play line 2" })).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Play line 1" }));
      const audio = screen.getByLabelText("Workspace audio playback") as HTMLAudioElement;
      expect(play).toHaveBeenCalledTimes(1);

      audio.currentTime = 1.5;
      fireEvent.timeUpdate(audio);
      expect(pause).not.toHaveBeenCalled();
      audio.currentTime = 2.1;
      fireEvent.timeUpdate(audio);
      expect(pause).toHaveBeenCalledTimes(1);
    } finally {
      play.mockRestore();
      pause.mockRestore();
    }
  });

  it("exposes draft, QA, attestation, and export actions with report gate context", () => {
    const onSaveDraft = vi.fn();
    const onRunQa = vi.fn();
    const onAttest = vi.fn();
    const onExport = vi.fn();
    const { rerender } = render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
        onAttest={onAttest}
        onExport={onExport}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    fireEvent.click(screen.getByRole("button", { name: "Run QA" }));
    fireEvent.click(screen.getByText("More review actions"));
    fireEvent.click(screen.getByRole("button", { name: "Export reviewed .cha" }));
    expect(onSaveDraft).toHaveBeenCalled();
    expect(onRunQa).toHaveBeenCalled();
    expect(onExport).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeDisabled();

    rerender(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="warning"
        qaIssues={["Child sample has fewer than 3 utterances."]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={onSaveDraft}
        onRunQa={onRunQa}
        onAttest={onAttest}
        onExport={onExport}
      />
    );

    expect(screen.getAllByText("Warning").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Attest transcript" }));
    expect(onAttest).toHaveBeenCalled();
  });

  it("explains why attestation is blocked until QA has run, via an inline reason linked with aria-describedby", () => {
    const { rerender } = render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText("More review actions"));
    const attestButton = screen.getByRole("button", { name: "Attest transcript" });
    expect(attestButton).toBeDisabled();
    expect(attestButton).toHaveAttribute("aria-describedby", "transcript-attest-reason");
    expect(screen.getByText("Run transcript QA before attesting.")).toBeInTheDocument();

    rerender(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="pass"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeEnabled();
    expect(screen.queryByText("Run transcript QA before attesting.")).not.toBeInTheDocument();
  });

  it("keeps attestation retry available after a transient backend unavailable state", () => {
    const onAttest = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="pass"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        backendUnavailable
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={onAttest}
        onExport={vi.fn()}
      />
    );

    const attestButton = screen.getByRole("button", { name: "Attest transcript" });
    expect(attestButton).toBeEnabled();
    fireEvent.click(attestButton);
    expect(onAttest).toHaveBeenCalled();
  });

  it("uses one compact filter control, keeps desktop review columns, and filters rows by review state", () => {
    render(
      <TranscriptEditorPanel
        lines={[
          { lineId: "line-1", speaker: "THER", text: "What do you see?", startMs: 0, endMs: 800 },
          { lineId: "line-2", speaker: "UNK", text: "maybe this line needs a speaker", startMs: 810, endMs: 1500 },
          { lineId: "line-3", speaker: "CHI", text: "[note] Verify timestamp with caregiver context.", startMs: 1510, endMs: 1900 },
          { lineId: "line-4", speaker: "CHI", text: "xxx", unclear: true }
        ]}
        qaStatus="warning"
        qaIssues={["Short transcript."]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    const filter = screen.getByRole("combobox", { name: "Show lines" });
    expect(filter).toHaveValue("all");
    expect(within(filter).getByRole("option", { name: /All lines/ })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: /Needs a look/ })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: /Low confidence/ })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: /No speaker/ })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: /Possible error/ })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: /Notes/ })).toBeInTheDocument();

    // One header names the columns; a line that needs a look carries one mark saying why.
    expect(screen.getAllByText("Time").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Speaker").length).toBeGreaterThan(0);
    expect(screen.getAllByText("What was said").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /Mark line/ })).not.toBeInTheDocument();

    fireEvent.change(filter, { target: { value: "missing_speaker" } });
    expect(screen.getByLabelText("Speaker for line 2")).toBeInTheDocument();
    expect(screen.queryByLabelText("Speaker for line 1")).not.toBeInTheDocument();

    fireEvent.change(filter, { target: { value: "notes" } });
    expect(screen.getByDisplayValue("[note] Verify timestamp with caregiver context.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Speaker for line 2")).not.toBeInTheDocument();

    fireEvent.change(filter, { target: { value: "all" } });
    expect(screen.getByLabelText("Speaker for line 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Speaker for line 2")).toBeInTheDocument();
  });

  it("shows the sticky bottom review actions and keeps export disabled when there are no lines", () => {
    render(
      <TranscriptEditorPanel
        lines={[]}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="idle"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText("More review actions"));
    expect(screen.getByRole("button", { name: "Speaker Tools" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Note" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attest transcript" })).toBeDisabled();
    const exportButton = screen.getByRole("button", { name: "Export reviewed .cha" });
    expect(exportButton).toBeDisabled();
    expect(exportButton).toHaveAttribute("aria-describedby", "transcript-export-reason");
    expect(screen.getByText("Add transcript lines before exporting.")).toBeInTheDocument();
  });

  it("keeps the mobile primary bar focused on save and QA while secondary review actions are collapsed", () => {
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    const primaryBar = screen.getByTestId("mobile-transcript-primary-actions");
    expect(within(primaryBar).getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(within(primaryBar).getByRole("button", { name: "Run QA" })).toBeInTheDocument();
    expect(within(primaryBar).queryByRole("button", { name: "Attest transcript" })).not.toBeInTheDocument();
    expect(within(primaryBar).queryByRole("button", { name: "Export reviewed .cha" })).not.toBeInTheDocument();

    const qaDetails = screen.getByTestId("mobile-transcript-qa-details");
    const secondaryActions = screen.getByTestId("mobile-transcript-secondary-actions");
    expect(qaDetails).not.toHaveAttribute("open");
    expect(secondaryActions).not.toHaveAttribute("open");
    fireEvent.click(within(secondaryActions).getByText("More review actions"));
    expect(within(secondaryActions).getByRole("button", { name: "Attest transcript" })).toBeInTheDocument();
    expect(within(secondaryActions).getByRole("button", { name: "Export reviewed .cha" })).toBeInTheDocument();
  });

  it("explains why QA is blocked until transcript edits are saved", () => {
    const { rerender } = render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="unsaved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByText("Save transcript edits before running QA.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();

    rerender(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.queryByText("Save transcript edits before running QA.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run QA" })).toBeEnabled();
  });

  it("marks the directly editable selected line and moves secondary actions into an overflow menu", async () => {
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    const firstLine = screen.getByRole("option", { name: "Transcript line 1" });
    fireEvent.focus(screen.getByLabelText("Utterance text 1"));
    expect(firstLine).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("button", { name: "Split line 1" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "More actions for line 1" }));
    expect(screen.getByRole("menuitem", { name: "Split line" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Merge with next" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Mark unclear" })).toBeVisible();
    expect(screen.getByRole("menuitem", { name: "Delete line" })).toBeVisible();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
    await waitFor(() => expect(screen.getByRole("button", { name: "More actions for line 1" })).toHaveFocus());
  });

  it("scrolls a newly selected line into view without moving focus from its editor", async () => {
    const scrollIntoView = vi.fn();
    const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollIntoView
    });

    try {
      render(
        <TranscriptEditorPanel
          lines={lines}
          qaStatus="not_run"
          qaIssues={[]}
          attested={false}
          busy={false}
          saveStatus="saved"
          onChange={vi.fn()}
          onSaveDraft={vi.fn()}
          onRunQa={vi.fn()}
          onAttest={vi.fn()}
          onExport={vi.fn()}
        />
      );

      const secondLineEditor = screen.getByLabelText("Utterance text 2");
      act(() => secondLineEditor.focus());

      await waitFor(() => {
        expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest", inline: "nearest" });
      });
      expect(secondLineEditor).toHaveFocus();
      expect(screen.getByRole("option", { name: "Transcript line 2" })).toHaveAttribute("aria-selected", "true");
    } finally {
      Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
        configurable: true,
        value: originalScrollIntoView
      });
    }
  });

  it("does not intercept browser-default keyboard shortcuts", () => {
    const onSaveDraft = vi.fn();
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="unsaved"
        onChange={vi.fn()}
        onSaveDraft={onSaveDraft}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    fireEvent.keyDown(window, { key: "s", metaKey: true });
    fireEvent.keyDown(window, { key: "l", metaKey: true });

    expect(onSaveDraft).not.toHaveBeenCalled();
  });

  it("lets tablet and desktop users switch or collapse the Audio and QA inspector", () => {
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy={false}
        saveStatus="saved"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "QA" }));
    expect(screen.getByRole("button", { name: "QA" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Hide audio and QA" }));
    expect(screen.getByTestId("transcript-audio-inspector")).toHaveClass("hidden");
    fireEvent.click(screen.getByRole("button", { name: "Show audio and QA" }));
    expect(screen.getByRole("button", { name: "Hide audio and QA" })).toBeInTheDocument();
  });

  it("announces save state changes through a polite live region", () => {
    render(
      <TranscriptEditorPanel
        lines={lines}
        qaStatus="not_run"
        qaIssues={[]}
        attested={false}
        busy
        saveStatus="saving"
        onChange={vi.fn()}
        onSaveDraft={vi.fn()}
        onRunQa={vi.fn()}
        onAttest={vi.fn()}
        onExport={vi.fn()}
      />
    );

    expect(screen.getByRole("status", { name: "Transcript save status" })).toHaveTextContent("Saving transcript");
  });
});
