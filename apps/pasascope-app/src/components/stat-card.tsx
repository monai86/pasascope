import type { LucideIcon } from "lucide-react";
import { Activity } from "lucide-react";

import { StatTile, type StatTileTone } from "@/components/ui/stat-tile";

type StatTone = "neutral" | "accent" | "success" | "warning";

const tileTone: Record<StatTone, StatTileTone> = {
  neutral: "neutral",
  accent: "brand",
  success: "brand",
  warning: "attention",
};

export function StatCard({
  label,
  value,
  helper,
  icon = Activity,
  tone = "neutral"
}: {
  label: string;
  value: string;
  helper?: string;
  icon?: LucideIcon;
  tone?: StatTone;
}) {
  return <StatTile label={label} value={value} helper={helper} icon={icon} tone={tileTone[tone]} />;
}
