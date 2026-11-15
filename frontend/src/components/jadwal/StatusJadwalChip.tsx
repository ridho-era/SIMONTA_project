import type { StatusBimbingan } from "../../lib/types";

const LABEL: Record<StatusBimbingan, { teks: string; kelas: string }> = {
  menunggu_konfirmasi: { teks: "Menunggu Konfirmasi", kelas: "bg-info-bg text-info" },
  disetujui: { teks: "Disetujui", kelas: "bg-tint text-primary" },
  ditolak: { teks: "Ditolak", kelas: "bg-danger-bg text-danger" },
  dibatalkan: { teks: "Dibatalkan", kelas: "bg-page text-muted" },
  selesai: { teks: "Selesai", kelas: "bg-page text-muted" },
};

export function StatusJadwalChip({ status }: { status: StatusBimbingan }) {
  const item = LABEL[status];
  return <span className={`inline-flex rounded-full px-3 py-1 text-label font-semibold ${item.kelas}`}>{item.teks}</span>;
}
