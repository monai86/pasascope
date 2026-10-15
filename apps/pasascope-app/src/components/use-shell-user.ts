"use client";

import { shellMessages } from "@/components/shell.messages";
import { useMessages } from "@/i18n/locale-provider";
import { signOutSupabaseWorkspace } from "@/lib/supabase-workspace-logout";
import { useRuntimeSettings } from "@/lib/use-runtime-settings";
import { useSupabaseAccessSession } from "@/lib/use-supabase-access-session";

export type ShellUser = {
  /** Who is signed in, or the state of finding out. */
  name: string;
  /** Which workspace they are in. */
  workspace: string;
  showLogout: boolean;
  logOut: () => Promise<void>;
};

/** The signed-in user as the shell shows them, in either shell. */
export function useShellUser(): ShellUser {
  const t = useMessages(shellMessages);
  const runtimeSettings = useRuntimeSettings();
  const supabaseSession = useSupabaseAccessSession();
  const isSupabaseRuntime = runtimeSettings.status === "success" && runtimeSettings.data.auth_mode === "supabase";

  const name = runtimeSettings.status !== "success"
    ? runtimeSettings.status === "loading" ? t.user.verifying : t.user.unavailable
    : isSupabaseRuntime
      ? supabaseSession?.displayName ?? supabaseSession?.email ?? t.user.fallbackName
      : t.user.demoName;
  const workspace = runtimeSettings.status !== "success"
    ? runtimeSettings.status === "loading" ? t.user.confirmingWorkspace : t.user.workspaceUnavailable
    : isSupabaseRuntime
      ? t.user.personalWorkspace
      : t.user.localWorkspace;

  return {
    name,
    workspace,
    showLogout: isSupabaseRuntime || Boolean(supabaseSession?.stage && supabaseSession.stage !== "signed_out"),
    logOut: async () => {
      await signOutSupabaseWorkspace();
      window.location.assign("/");
    },
  };
}
