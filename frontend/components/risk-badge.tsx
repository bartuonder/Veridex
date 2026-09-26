import { ClauseFinding } from "@/lib/api";

const RISK_BADGE_CLASS: Record<ClauseFinding["risk_level"], string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-green-100 text-green-800",
};

const RISK_CARD_CLASS: Record<ClauseFinding["risk_level"], string> = {
  critical: "border-red-200",
  high: "border-orange-200",
  medium: "border-amber-200",
  low: "border-green-200",
};

export function riskCardClass(level: ClauseFinding["risk_level"]): string {
  return RISK_CARD_CLASS[level];
}

export function RiskBadge({ level }: { level: ClauseFinding["risk_level"] }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${RISK_BADGE_CLASS[level]}`}
    >
      {level}
    </span>
  );
}
