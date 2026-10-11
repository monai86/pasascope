"use client";

import React, { useState } from "react";
import { Check, Copy, FileCode } from "lucide-react";

export interface TalkbankUtterance {
  id?: string;
  speaker?: string;
  text: string;
  startMs?: number;
  endMs?: number;
  unclear?: boolean;
  flags?: string[];
}

export interface TalkbankChatViewerProps {
  rawCha?: string;
  utterances?: TalkbankUtterance[];
  sessionId?: string;
  childId?: string;
  className?: string;
}

export function TalkbankChatViewer({
  rawCha,
  utterances = [],
  sessionId = "SESS-001",
  childId = "CHI001",
  className = "",
}: TalkbankChatViewerProps) {
  const [copied, setCopied] = useState(false);

  // Generate standard TalkBank CHAT representation if rawCha is not directly supplied
  const chatContent = React.useMemo(() => {
    if (rawCha && rawCha.trim().length > 0) {
      return rawCha;
    }
    const lines = [
      "@UTF8",
      "@Begin",
      "@Languages:\ttha, eng",
      `@Participants:\tCHI ${childId} Child, INV Clinician`,
      `@ID:\ttha|PasaScope|CHI|4;00.|male|ASD||Child||`,
      `@Media:\t${sessionId}, audio`,
      "",
    ];

    utterances.forEach((u) => {
      const spk = u.speaker || "CHI";
      let line = `*${spk}:\t${u.text}`;
      if (u.startMs !== undefined && u.endMs !== undefined && u.startMs !== null && u.endMs !== null) {
        line += ` \x15${u.startMs}_${u.endMs}\x15`;
      }
      lines.push(line);
      if (u.flags && u.flags.length > 0) {
        lines.push(`%xqa:\t[${u.flags.join(", ")}]`);
      }
    });

    lines.push("", "@End");
    return lines.join("\n");
  }, [rawCha, utterances, sessionId, childId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chatContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex flex-col rounded-xl border border-line bg-white shadow-sm ${className}`}>
      {/* Header Toolbar */}
      <div className="flex items-center justify-between border-b border-line bg-surface-soft px-4 py-2.5">
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4 text-[color:var(--color-info-text)]" />
          <span className="text-xs font-bold text-ink">
            TalkBank / CHAT Standard Syntax View
          </span>
          <span className="rounded bg-brand-soft px-1.5 py-0.5 text-xs font-semibold text-[color:var(--color-info-text)]">
            @UTF8
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex min-h-10 items-center gap-1.5 rounded-lg border border-line-strong bg-white px-3 py-1.5 text-xs font-medium text-ink shadow-xs hover:bg-surface-soft active:scale-98 transition-all"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-[color:var(--color-success-text)]" />
              <span className="text-[color:var(--color-success-text)] font-semibold">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 text-ink-muted" />
              <span>Copy CHAT</span>
            </>
          )}
        </button>
      </div>

      {/* Syntax Render Panel */}
      <div className="max-h-[500px] overflow-auto p-4 font-mono text-xs leading-relaxed text-ink selection:bg-brand-soft">
        {chatContent.split("\n").map((line, idx) => {
          if (line.startsWith("@")) {
            return (
              <div key={idx} className="text-[color:var(--color-info-text)] font-semibold py-0.5">
                {line}
              </div>
            );
          }
          if (line.startsWith("*CHI:")) {
            const parts = line.split("\t");
            const spk = parts[0];
            const rest = parts.slice(1).join("\t");
            return (
              <div key={idx} className="py-0.5 hover:bg-[color:var(--color-success-bg)] rounded px-1 -mx-1">
                <span className="font-bold text-[color:var(--color-success-text)]">{spk}</span>
                <span className="text-ink-subtle">	</span>
                <span className="text-ink font-medium">{rest}</span>
              </div>
            );
          }
          if (line.startsWith("*INV") || line.startsWith("*MOT") || line.startsWith("*FAT") || line.startsWith("*EXP")) {
            const parts = line.split("\t");
            const spk = parts[0];
            const rest = parts.slice(1).join("\t");
            return (
              <div key={idx} className="py-0.5 hover:bg-brand-soft rounded px-1 -mx-1">
                <span className="font-bold text-[color:var(--color-info-text)]">{spk}</span>
                <span className="text-ink-subtle">	</span>
                <span className="text-ink">{rest}</span>
              </div>
            );
          }
          if (line.startsWith("%")) {
            return (
              <div key={idx} className="text-ink-muted italic py-0.5 pl-4">
                {line}
              </div>
            );
          }
          return (
            <div key={idx} className="text-ink-muted py-0.5">
              {line}
            </div>
          );
        })}
      </div>
    </div>
  );
}
