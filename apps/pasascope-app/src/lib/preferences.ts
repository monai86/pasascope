"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Choices a therapist makes for this browser. They are kept on this device
 * only, so they follow the browser rather than the account.
 */
export type Preferences = {
  textSize: "standard" | "large";
  motion: "system" | "reduce";
  /** The language a new case starts with. */
  caseLanguage: "Thai" | "English";
};

export const DEFAULT_PREFERENCES: Preferences = {
  textSize: "standard",
  motion: "system",
  caseLanguage: "Thai",
};

const STORAGE_KEY = "pasascope.preferences.v1";
const CHANGE_EVENT = "pasascope:preferences-changed";

function pick<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

export function loadPreferences(): Preferences {
  if (typeof window === "undefined") return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const stored = raw ? (JSON.parse(raw) as Partial<Record<keyof Preferences, unknown>>) : {};
    return {
      textSize: pick(stored.textSize, ["standard", "large"], DEFAULT_PREFERENCES.textSize),
      motion: pick(stored.motion, ["system", "reduce"], DEFAULT_PREFERENCES.motion),
      caseLanguage: pick(stored.caseLanguage, ["Thai", "English"], DEFAULT_PREFERENCES.caseLanguage),
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

/** Puts the display choices on the document, where the stylesheet reads them. */
export function applyPreferences(preferences: Preferences, root: HTMLElement = document.documentElement): void {
  if (preferences.textSize === "large") root.dataset.textSize = "large";
  else delete root.dataset.textSize;
  if (preferences.motion === "reduce") root.dataset.motion = "reduce";
  else delete root.dataset.motion;
}

export function savePreferences(next: Preferences): void {
  applyPreferences(next);
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Storage can be unavailable (private window, blocked site data); the
    // choice still applies until the page is closed.
  }
  window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: next }));
}

/** The current preferences and a way to change one of them. */
export function usePreferences(): [Preferences, <K extends keyof Preferences>(key: K, value: Preferences[K]) => void] {
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);

  useEffect(() => {
    setPreferences(loadPreferences());
    const onChange = (event: Event) => setPreferences((event as CustomEvent<Preferences>).detail);
    window.addEventListener(CHANGE_EVENT, onChange);
    return () => window.removeEventListener(CHANGE_EVENT, onChange);
  }, []);

  const update = useCallback(<K extends keyof Preferences>(key: K, value: Preferences[K]) => {
    const next = { ...loadPreferences(), [key]: value };
    savePreferences(next);
    setPreferences(next);
  }, []);

  return [preferences, update];
}

/** Applies the stored display choices once the page has loaded. */
export function PreferencesBootstrap(): null {
  useEffect(() => {
    applyPreferences(loadPreferences());
  }, []);
  return null;
}
