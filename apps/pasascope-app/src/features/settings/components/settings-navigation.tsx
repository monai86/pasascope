"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { settingsMessages } from "@/features/settings/settings.messages";
import type { SettingsSection } from "@/features/settings/services/settings-access";
import { useMessages } from "@/i18n/locale-provider";

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
      <div className={`${mobileIndexOpen ? "block" : "hidden md:block"} md:sticky md:top-6`}>
        <p className="px-1 pb-3 text-sm leading-6 text-ink-muted md:hidden">{t.choose}</p>
        <SettingsNavList sections={sections} selected={selected} onSelect={onSelect} />
      </div>
    </nav>
  );
}

function SettingsNavList({
  onSelect,
  sections,
  selected,
}: Pick<SettingsNavigationProps, "sections" | "selected" | "onSelect">) {
  const sectionLabels = useMessages(settingsMessages).sections;
  return (
    // On a phone each category is a row to tap; on a wider screen the list is
    // a quiet rail beside the page, like the app's own navigation.
    <ul className="grid gap-2 md:gap-0.5">
      {sections.map((section) => {
        const isSelected = section === selected;
        return (
          <li key={section}>
            <a
              href={`/settings?section=${section}`}
              aria-current={isSelected ? "page" : undefined}
              className={`flex min-h-12 items-center gap-3 rounded-full border px-5 text-[15px] transition-colors motion-reduce:transition-none md:min-h-11 md:px-4 ${
                isSelected
                  ? "border-transparent bg-surface font-semibold text-ink shadow-chat-card"
                  : "border-line bg-surface text-ink md:border-transparent md:bg-transparent md:text-ink-muted md:hover:bg-surface md:hover:text-ink"
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
  );
}
