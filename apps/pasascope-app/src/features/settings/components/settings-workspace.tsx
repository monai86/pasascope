"use client";

import { useEffect, useState } from "react";

import { TherapistSettings } from "@/features/settings/components/therapist-settings";
import { SettingsNavigation } from "@/features/settings/components/settings-navigation";
import {
  SETTINGS_SECTIONS,
  resolveSettingsSection,
  type SettingsSection,
} from "@/features/settings/services/settings-access";

type SettingsWorkspaceProps = {
  requestedSection?: unknown;
  requestedSectionExplicit?: boolean;
};

export function SettingsWorkspace({
  requestedSection = "account",
  requestedSectionExplicit = false,
}: SettingsWorkspaceProps) {
  const [section, setSection] = useState<SettingsSection>(() => resolveSettingsSection(requestedSection));
  const [mobileIndexOpen, setMobileIndexOpen] = useState(!requestedSectionExplicit);

  useEffect(() => {
    setSection(resolveSettingsSection(requestedSection));
    setMobileIndexOpen(!requestedSectionExplicit);
  }, [requestedSection, requestedSectionExplicit]);

  useEffect(() => {
    function restoreSectionFromHistory() {
      const requested = new URLSearchParams(window.location.search).get("section");
      setSection(resolveSettingsSection(requested));
      setMobileIndexOpen(requested === null);
    }
    window.addEventListener("popstate", restoreSectionFromHistory);
    return () => window.removeEventListener("popstate", restoreSectionFromHistory);
  }, []);

  function selectSection(nextSection: SettingsSection) {
    setSection(nextSection);
    setMobileIndexOpen(false);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("section", nextSection);
      url.searchParams.delete("scope");
      url.searchParams.delete("notice");
      window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }
  }

  return (
    <section
      className="grid min-w-0 gap-4 md:grid-cols-[220px_minmax(0,1fr)] md:items-start"
      data-testid="settings-workspace"
      data-mobile-view={mobileIndexOpen ? "categories" : "detail"}
    >
      <SettingsNavigation
        sections={SETTINGS_SECTIONS}
        selected={section}
        onSelect={selectSection}
        mobileIndexOpen={mobileIndexOpen}
        onOpenMobileIndex={() => setMobileIndexOpen(true)}
      />
      <div className={`${mobileIndexOpen ? "hidden md:block" : "block"} min-w-0`}>
        <TherapistSettings section={section} />
      </div>
    </section>
  );
}
