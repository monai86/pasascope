import { PasaScopeLogoMark } from "@/components/pasascope-logo";
import { cn } from "@/lib/cn";

/**
 * The mark as the chat shell's centrepiece: on a white tile, with two rings
 * spreading from it like sound and the bars in its lens moving as a waveform.
 * Decoration only; the page's heading names the product.
 */
export function ChatMarkStage({ className }: { className?: string }) {
  return (
    <div aria-hidden="true" className={cn("chat-mark-stage", className)}>
      <span className="chat-mark-ring" />
      <span className="chat-mark-ring" />
      <div className="chat-mark-tile">
        <PasaScopeLogoMark size="xl" />
      </div>
    </div>
  );
}
