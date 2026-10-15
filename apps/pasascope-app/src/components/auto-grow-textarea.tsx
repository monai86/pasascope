"use client";

import { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useRef, type TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

/**
 * A text box as tall as its words, so a long line is read whole instead of
 * scrolled inside a box. Quiet until pointed at or focused, so a list of them
 * reads as text rather than as a form.
 */
export const AutoGrowTextarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function AutoGrowTextarea({ className, value, ...props }, forwardedRef) {
    const ref = useRef<HTMLTextAreaElement | null>(null);
    useImperativeHandle(forwardedRef, () => ref.current as HTMLTextAreaElement);

    const fit = () => {
      const element = ref.current;
      // Where the browser sizes the box to its content itself, there is nothing to measure.
      if (!element || nativeSizing()) return;
      element.style.height = "auto";
      element.style.height = `${element.scrollHeight}px`;
    };
    useLayoutEffect(fit, [value]);
    useEffect(() => {
      const element = ref.current;
      if (typeof ResizeObserver === "undefined" || !element || nativeSizing()) return;
      // A narrower box wraps the words onto more lines.
      let lastWidth = 0;
      const observer = new ResizeObserver(([entry]) => {
        if (entry.contentRect.width !== lastWidth) {
          lastWidth = entry.contentRect.width;
          fit();
        }
      });
      observer.observe(element);
      return () => observer.disconnect();
    }, []);

    return (
      <textarea
        ref={ref}
        rows={1}
        value={value}
        className={cn(
          "block min-h-11 [field-sizing:content] w-full resize-none overflow-hidden rounded-control border border-transparent bg-transparent px-2.5 py-2.5 text-[15px] leading-6 text-ink outline-none transition placeholder:text-ink-subtle hover:border-line focus:border-line-strong focus:bg-surface focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] motion-reduce:transition-none",
          className,
        )}
        {...props}
      />
    );
  },
);

let fieldSizing: boolean | undefined;
function nativeSizing(): boolean {
  if (fieldSizing === undefined) {
    fieldSizing = typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
  }
  return fieldSizing;
}
