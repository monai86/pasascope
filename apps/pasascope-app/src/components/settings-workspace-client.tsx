"use client";

import { SettingsWorkspace } from "@/features/settings/components/settings-workspace";
import type { SettingsSection } from "@/features/settings/services/settings-access";

type SettingsWorkspaceClientProps = {
  initialSection?: SettingsSection;
  initialSectionExplicit?: boolean;
};

export function SettingsWorkspaceClient({
  initialSection = "account",
  initialSectionExplicit = false,
}: SettingsWorkspaceClientProps) {
  return (
    <SettingsWorkspace
      requestedSection={initialSection}
      requestedSectionExplicit={initialSectionExplicit}
    />
  );
}
