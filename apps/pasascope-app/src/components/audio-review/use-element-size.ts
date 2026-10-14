"use client";

import { useEffect, useState, type RefObject } from "react";

/** The element's rendered size in CSS pixels, kept current as the layout changes. */
export function useElementSize(ref: RefObject<HTMLElement | null>): { width: number; height: number } {
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const measure = () => {
      const rect = element.getBoundingClientRect();
      setSize((current) =>
        current.width === rect.width && current.height === rect.height ? current : { width: rect.width, height: rect.height },
      );
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);

  return size;
}

/**
 * Sizes a canvas's backing store to its box at the screen's pixel density and
 * returns a context drawing in CSS pixels, so marks and labels stay sharp and
 * undistorted at any width instead of being stretched from a fixed bitmap.
 */
export function prepareCanvas(canvas: HTMLCanvasElement, width: number, height: number): CanvasRenderingContext2D | null {
  let context: CanvasRenderingContext2D | null = null;
  try {
    context = canvas.getContext("2d");
  } catch {
    return null;
  }
  if (!context) return null;
  const ratio = typeof window === "undefined" ? 1 : Math.min(window.devicePixelRatio || 1, 3);
  const pixelWidth = Math.max(1, Math.round(width * ratio));
  const pixelHeight = Math.max(1, Math.round(height * ratio));
  if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
  if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
  context.setTransform?.(ratio, 0, 0, ratio, 0, 0);
  return context;
}
