"use client";

import { useEffect, useRef, type RefObject } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Keeps keyboard focus inside a container while it is active: focus moves in
 * on activation, Tab and Shift+Tab wrap at the edges, Escape calls `onEscape`,
 * and focus returns to the element that had it when the trap is released.
 */
export function useFocusTrap<T extends HTMLElement>(
  active: boolean,
  onEscape?: () => void,
): RefObject<T | null> {
  const containerRef = useRef<T | null>(null);
  const onEscapeRef = useRef(onEscape);

  useEffect(() => {
    onEscapeRef.current = onEscape;
  }, [onEscape]);

  useEffect(() => {
    const container = containerRef.current;
    if (!active || !container) return;

    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusable = () =>
      Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((element) => !element.closest("[inert]"));

    const first = focusable()[0];
    if (first) first.focus();
    else {
      container.tabIndex = -1;
      container.focus();
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onEscapeRef.current?.();
        return;
      }
      if (event.key !== "Tab") return;

      const elements = focusable();
      if (elements.length === 0) {
        event.preventDefault();
        return;
      }
      const firstElement = elements[0];
      const lastElement = elements[elements.length - 1];
      const current = document.activeElement;
      if (event.shiftKey && (current === firstElement || !container?.contains(current))) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && (current === lastElement || !container?.contains(current))) {
        event.preventDefault();
        firstElement.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [active]);

  return containerRef;
}
