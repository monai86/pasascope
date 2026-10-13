import { AppShell } from "@/components/app-shell";
import { PageHeader } from "@/components/page-header";
import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";
import { parseSettingsSection } from "@/features/settings/services/settings-access";
import { settingsMessages } from "@/features/settings/settings.messages";
import { getMessages } from "@/i18n/server";

type SettingsPageProps = {
  searchParams?: Promise<SettingsSearchParams>;
};

type SettingsSearchParams = {
  section?: string | string[];
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const requestedSection = parseSettingsSection(resolvedSearchParams?.section);
  const t = (await getMessages(settingsMessages)).page;

  return (
    <AppShell active="Settings">
      <PageHeader
        title={t.title}
        description={t.description}
      />
      <SettingsWorkspaceClient
        initialSection={requestedSection ?? "account"}
        initialSectionExplicit={requestedSection !== null}
      />
    </AppShell>
  );
}
