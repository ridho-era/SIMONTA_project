import { CalendarClock, CircleCheck, CircleDot, Lock, TriangleAlert, type LucideIcon } from "lucide-react";

import type { MilestoneStatus } from "../../lib/types";

const GAYA: Record<MilestoneStatus, { label: string; kelas: string; icon: LucideIcon }> = {
  disetujui: { label: "Disetujui", kelas: "bg-tint text-primary", icon: CircleCheck },
  aktif: { label: "Aktif", kelas: "bg-info-bg text-info", icon: CircleDot },
  terlambat: { label: "Terlambat · tahap aktif", kelas: "bg-danger-bg text-danger", icon: TriangleAlert },
  terkunci: { label: "Terkunci", kelas: "border border-line bg-page text-muted", icon: Lock },
  belum_terjadwal: {
    label: "Belum terjadwal",
    kelas: "border border-dashed border-line bg-surface text-muted",
    icon: CalendarClock,
  },
};

export function MilestoneStatusChip({ status }: { status: MilestoneStatus }) {
  const { label, kelas, icon: Icon } = GAYA[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-label font-semibold ${kelas}`}>
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}