"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { settingsMessages } from "@/features/settings/settings.messages";
import type { SettingsSection } from "@/features/settings/services/settings-access";
import { useMessages } from "@/i18n/locale-provider";

const ADMIN_SECTIONS = new Set<SettingsSection>([
  "team",
  "invitations",
  "audit",
  "privacy_operations",
  "integration_status",
]);

type SettingsNavigationProps = {
  sections: readonly SettingsSection[];
  selected: SettingsSection;
  onSelect: (section: SettingsSection) => void;
  mobileIndexOpen?: boolean;
  onOpenMobileIndex?: () => void;
};

export function SettingsNavigation({
  sections,
  selected,
  onSelect,
  mobileIndexOpen = true,
  onOpenMobileIndex,
}: SettingsNavigationProps) {
  const t = useMessages(settingsMessages).nav;
  const sharedSections = sections.filter((section) => !ADMIN_SECTIONS.has(section));
  const adminSections = sections.filter((section) => ADMIN_SECTIONS.has(section));

  return (
    <nav aria-label={t.label}>
      {!mobileIndexOpen ? (
        <button
          type="button"
          className="flex min-h-11 w-full items-center gap-2 rounded-card border border-line bg-surface px-3 text-left text-sm font-semibold text-ink md:hidden"
          onClick={onOpenMobileIndex}
        >
          <ChevronLeft size={17} aria-hidden="true" />
          {t.allCategories}
        </button>
      ) : null}
      <div className={`${mobileIndexOpen ? "block" : "hidden md:block"} sticky top-24 rounded-card border border-line bg-surface p-2`}>
        <div className="md:hidden">
          <p className="px-3 pb-3 pt-1 text-sm leading-6 text-ink-muted">{t.choose}</p>
        </div>
          <SettingsNavGroup label={t.workspace} sections={sharedSections} selected={selected} onSelect={onSelect} />
          {adminSections.length > 0 ? (
            <div className="mt-3 border-t border-line pt-3">
              <SettingsNavGroup label={t.administration} sections={adminSections} selected={selected} onSelect={onSelect} />
            </div>
          ) : null}
      </div>
    </nav>
  );
}

function SettingsNavGroup({
  label,
  onSelect,
  sections,
  selected,
}: Pick<SettingsNavigationProps, "sections" | "selected" | "onSelect"> & { label: string }) {
  const sectionLabels = useMessages(settingsMessages).sections;
  return (
    <div>
      <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-[0.12em] text-ink-muted">{label}</p>
      <ul className="grid gap-1">
        {sections.map((section) => {
          const isSelected = section === selected;
          return (
            <li key={section}>
              <a
                href={`/settings?section=${section}`}
                aria-current={isSelected ? "page" : undefined}
                className={`flex min-h-11 items-center rounded-xl border-l-3 px-3.5 py-2 text-sm font-semibold transition ${
                  isSelected
                    ? "border-brand bg-brand-soft text-brand"
                    : "border-transparent text-ink hover:bg-surface-soft hover:text-ink"
                }`}
                onClick={(event) => {
                  event.preventDefault();
                  onSelect(section);
                }}
              >
                <span className="flex-1">{sectionLabels[section]}</span>
                <ChevronRight size={16} aria-hidden="true" className="text-ink-subtle md:hidden" />
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
