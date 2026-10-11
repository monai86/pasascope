"use client";

import { loginMessages } from "@/components/login.messages";
import { MockLoginFormClient } from "@/components/mock-login-form-client";
import { SkeletonLine } from "@/components/skeleton";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { SupabaseLoginFormClient } from "@/components/supabase-login-form-client";
import { Card } from "@/components/ui/card";
import { useMessages } from "@/i18n/locale-provider";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";

export function RuntimeLoginPanelClient() {
  const t = useMessages(loginMessages).panel;
  const runtimeSettings = useRuntimeSettings();

  if (runtimeSettings.status === "loading") {
    return (
      <Card className="self-start p-5 sm:p-6" aria-live="polite">
        <span className="sr-only">{t.loading}</span>
        <SkeletonLine className="w-2/5" />
        <div className="mt-3 space-y-2" aria-hidden="true">
          <SkeletonLine className="w-3/5" />
          <SkeletonLine className="w-2/5" />
        </div>
      </Card>
    );
  }

  if (runtimeSettings.status !== "success") {
    return (
      <Card className="self-start p-5 sm:p-6" role="alert">
        <h2 className="text-lg font-semibold text-ink">{t.unavailableTitle}</h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">{t.unavailableBody}</p>
      </Card>
    );
  }

  if (runtimeSettings.data.auth_mode === "supabase") {
    return (
      <>
        <SupabaseAuthRuntimeBridge />
        <SupabaseLoginFormClient runtimeSettings={runtimeSettings.data} />
      </>
    );
  }

  return (
    <>
      <SupabaseAuthRuntimeBridge />
      <MockLoginFormClient runtimeSettings={runtimeSettings.data} />
    </>
  );
}
