"use client";

import { useEffect } from "react";

export interface KeyboardReviewOptions {
  onPlayPause?: () => void;
  onReplayActive?: () => void;
  onToggleLoop?: () => void;
  onAssignSpeaker?: (speaker: "CHI" | "THER" | "MOT" | "FAT") => void;
  onAdvanceLine?: () => void;
  onPreviousLine?: () => void;
  isEnabled?: boolean;
}

const SPEAKER_BY_DIGIT = {
  Digit1: "CHI",
  Digit2: "THER",
  Digit3: "MOT",
  Digit4: "FAT",
} as const;

/**
 * Keyboard shortcuts for audio review. None of them takes over a browser
 * shortcut: Cmd/Ctrl with a digit switches tabs and Cmd/Ctrl+L focuses the
 * address bar, so those combinations are left alone and the review actions
 * use Alt (Option) instead.
 *
 *   Space              play or pause (not while typing in a field)
 *   Alt+R              replay the active utterance
 *   Alt+L              toggle loop
 *   Alt+1 … Alt+4      assign CHI, THER, MOT, FAT to the active utterance
 *   Cmd/Ctrl+Enter     mark verified and advance
 *
 * Alt shortcuts are matched on the physical key (`code`), because Option
 * changes the character a key produces on macOS.
 */
export function useKeyboardReview({
  onPlayPause,
  onReplayActive,
  onToggleLoop,
  onAssignSpeaker,
  onAdvanceLine,
  onPreviousLine,
  isEnabled = true,
}: KeyboardReviewOptions) {
  useEffect(() => {
    if (!isEnabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;
      const isAltOnly = e.altKey && !isCmdOrCtrl;
      const target = e.target as HTMLElement | null;
      const isTextInput =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);

      if (isAltOnly && e.code === "KeyR") {
        e.preventDefault();
        onReplayActive?.();
        return;
      }

      if (isAltOnly && e.code === "KeyL") {
        e.preventDefault();
        onToggleLoop?.();
        return;
      }

      if (isAltOnly && e.code in SPEAKER_BY_DIGIT) {
        e.preventDefault();
        onAssignSpeaker?.(SPEAKER_BY_DIGIT[e.code as keyof typeof SPEAKER_BY_DIGIT]);
        return;
      }

      // Spacebar: Play/Pause (only when not typing in text input)
      if (e.code === "Space" && !isTextInput && !isCmdOrCtrl && !e.altKey) {
        e.preventDefault();
        onPlayPause?.();
        return;
      }

      // Cmd/Ctrl + Enter: Mark verified & advance line
      if (isCmdOrCtrl && e.key === "Enter") {
        e.preventDefault();
        onAdvanceLine?.();
        return;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    isEnabled,
    onPlayPause,
    onReplayActive,
    onToggleLoop,
    onAssignSpeaker,
    onAdvanceLine,
    onPreviousLine,
  ]);
}
