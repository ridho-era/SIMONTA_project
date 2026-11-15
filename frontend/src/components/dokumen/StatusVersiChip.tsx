import { CircleCheck, Clock, RotateCcw, type LucideIcon } from "lucide-react";

import type { StatusVersi } from "../../lib/types";

const GAYA: Record<StatusVersi, { label: string; kelas: string; icon: LucideIcon }> = {
  menunggu_review: { label: "Menunggu Review", kelas: "bg-info-bg text-info", icon: Clock },
  perlu_revisi: { label: "Perlu Revisi", kelas: "bg-warning-bg text-warning", icon: RotateCcw },
  disetujui: { label: "Disetujui", kelas: "bg-tint text-primary", icon: CircleCheck },
};

export function StatusVersiChip({ status }: { status: StatusVersi }) {
  const { label, kelas, icon: Icon } = GAYA[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-label font-semibold ${kelas}`}>
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}