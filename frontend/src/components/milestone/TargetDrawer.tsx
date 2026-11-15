import { useEffect, useState, type FormEvent } from "react";
import { CircleAlert, Loader2 } from "lucide-react";

import { useTetapkanTarget } from "../../hooks/useMilestone";
import { formatAngka } from "../../lib/angka";
import { formatTanggal } from "../../lib/format";
import { pesanDariError } from "../../lib/galat";
import type { MilestoneRingkas } from "../../lib/types";
import { Drawer } from "../Drawer";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../ui";

interface Props {
  open: boolean;
  onClose: () => void;
  milestone: MilestoneRingkas;
  /** Teks identitas mahasiswa untuk ditampilkan, mis. "Nama (NPM)". Berasal dari data F-12. */
  mahasiswa?: string;
}

export function TargetDrawer({ open, onClose, milestone, mahasiswa }: Props) {
  const mutasi = useTetapkanTarget();
  const [nilai, setNilai] = useState(milestone.target ?? "");
  const [galat, setGalat] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setNilai(milestone.target ?? "");
      setGalat(null);
      mutasi.reset();
    }
  }, [open, milestone.id, milestone.target]); // eslint-disable-line react-hooks/exhaustive-deps

  async function simpan(target: string | null) {
    setGalat(null);
    try {
      await mutasi.mutateAsync({ id: milestone.id, target });
      onClose();
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (nilai) void simpan(nilai);
  }

  return (
    <Drawer open={open} onClose={onClose} title="Tetapkan target">
      <p className="text-body text-muted">
        {mahasiswa ? `${mahasiswa} · ` : ""}
        {milestone.nama} · Bobot {formatAngka(milestone.bobot)}%
      </p>
      <p className="mt-1 text-body text-ink">
        Target saat ini: {milestone.target ? formatTanggal(milestone.target) : "belum ditetapkan"}
      </p>

      {milestone.status === "disetujui" ? (
        <p className="mt-6 rounded-md bg-info-bg p-3 text-label text-info">
          Milestone sudah diverifikasi; target tidak dapat diubah.
        </p>
      ) : (
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {galat && (
            <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger">
              <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <span>{galat}</span>
            </div>
          )}
          <div>
            <label htmlFor="target-tanggal" className="mb-1.5 block text-body font-medium text-ink">
              Tanggal target
            </label>
            <input
              id="target-tanggal"
              type="date"
              value={nilai}
              onChange={(e) => setNilai(e.target.value)}
              required
              className={inputClass}
            />
          </div>
          <p className="text-label text-muted">Mahasiswa menerima notifikasi saat target berubah.</p>
          <button
            type="submit"
            disabled={mutasi.isPending || !nilai || nilai === milestone.target}
            className={primaryButtonClass}
          >
            {mutasi.isPending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            Simpan target
          </button>
          {milestone.target && (
            <button
              type="button"
              onClick={() => void simpan(null)}
              disabled={mutasi.isPending}
              className={`${secondaryButtonClass} w-full`}
            >
              Hapus target
            </button>
          )}
          <button type="button" onClick={onClose} className={`${secondaryButtonClass} w-full`}>
            Batal
          </button>
        </form>
      )}
    </Drawer>
  );
}