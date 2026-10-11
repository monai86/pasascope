"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WifiOff } from "lucide-react";

import { defineMessages } from "@/i18n/messages";
import { useMessages } from "@/i18n/locale-provider";
import { checkBackendAvailability } from "@/lib/api";

const bannerMessages = defineMessages({
  en: {
    title: "Backend unavailable — local workspace mode",
    body: "Changes are stored locally only and may not persist across devices or server restarts.",
  },
  th: {
    title: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ — กำลังทำงานบนเครื่องนี้เท่านั้น",
    body: "การเปลี่ยนแปลงถูกเก็บไว้ในเครื่องนี้เท่านั้น และอาจไม่อยู่เมื่อเปลี่ยนเครื่องหรือเมื่อเซิร์ฟเวอร์เริ่มใหม่",
  },
});

export function useBackendAvailability() {
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const explicitAvailability = useRef<boolean | undefined>(undefined);
  const setExplicitBackendUnavailable = useCallback((unavailable: boolean) => {
    explicitAvailability.current = unavailable;
    setBackendUnavailable(unavailable);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void checkBackendAvailability().then((available) => {
      if (!cancelled && explicitAvailability.current === undefined) {
        setBackendUnavailable(!available);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { backendUnavailable, setBackendUnavailable: setExplicitBackendUnavailable };
}

export function BackendAvailabilityBanner({ unavailable }: { unavailable: boolean }) {
  const t = useMessages(bannerMessages);
  if (!unavailable) return null;
  return (
    <div
      className="mb-5 rounded-card border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-4 text-[color:var(--color-warning-text)]"
      role="status"
    >
      <div className="flex items-start gap-3">
        <WifiOff className="mt-0.5 shrink-0" size={20} aria-hidden="true" />
        <div>
          <p className="font-semibold">{t.title}</p>
          <p className="mt-1 text-sm">{t.body}</p>
        </div>
      </div>
    </div>
  );
}
