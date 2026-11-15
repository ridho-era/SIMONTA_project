import { useEffect, useState, type FormEvent } from "react";
import { CircleAlert, Loader2 } from "lucide-react";

import { useVerifikasiMilestone } from "../../hooks/useMilestone";
import { formatAngka } from "../../lib/angka";
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

export function VerifikasiDrawer({ open, onClose, milestone, mahasiswa }: Props) {
  const mutasi = useVerifikasiMilestone();
  const [tingkat, setTingkat] = useState("100");
  const [galat, setGalat] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTingkat("100");
      setGalat(null);
      mutasi.reset();
    }
  }, [open, milestone.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const angka = Number(tingkat);
  const valid = tingkat.trim() !== "" && Number.isInteger(angka) && angka >= 0 && angka <= 100;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid) return;
    setGalat(null);
    try {
      await mutasi.mutateAsync({ id: milestone.id, tingkat: angka });
      onClose();
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  const alasanTidakBisa =
    milestone.status === "disetujui"
      ? "Milestone ini sudah diverifikasi."
      : !milestone.tahap_aktif
        ? "Verifikasi hanya dapat dilakukan pada tahap aktif. Verifikasi tahap sebelumnya lebih dulu."
        : null;

  return (
    <Drawer open={open} onClose={onClose} title="Verifikasi milestone">
      <p className="text-body text-muted">
        {mahasiswa ? `${mahasiswa} · ` : ""}
        {milestone.nama} · Bobot {formatAngka(milestone.bobot)}%
      </p>

      {alasanTidakBisa ? (
        <p className="mt-6 rounded-md bg-info-bg p-3 text-label text-info">{alasanTidakBisa}</p>
      ) : (
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {galat && (
            <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger">
              <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <span>{galat}</span>
            </div>
          )}
          <div>
            <label htmlFor="verifikasi-tingkat" className="mb-1.5 block text-body font-medium text-ink">
              Tingkat penyelesaian (0–100)
            </label>
            <input
              id="verifikasi-tingkat"
              type="number"
              min={0}
              max={100}
              step={1}
              value={tingkat}
              onChange={(e) => setTingkat(e.target.value)}
              required
              className={inputClass}
            />
          </div>
          <p className="text-label text-muted">
            {valid
              ? `Kontribusi ke progres: ${formatAngka((milestone.bobot * angka) / 100)}%. `
              : "Isi bilangan bulat 0 sampai 100. "}
            Verifikasi menambah progres mahasiswa, tercatat dengan waktu dan pelaku, dan mengirim notifikasi. Tindakan
            ini tidak dapat dibatalkan dari sini.
          </p>
          <button type="submit" disabled={mutasi.isPending || !valid} className={primaryButtonClass}>
            {mutasi.isPending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            Verifikasi milestone
          </button>
          <button type="button" onClick={onClose} className={`${secondaryButtonClass} w-full`}>
            Batal
          </button>
        </form>
      )}
    </Drawer>
  );
}