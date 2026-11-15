import { useEffect, useState, type FormEvent } from "react";
import { CircleAlert, Loader2 } from "lucide-react";

import { useSetujuiJadwal, useTolakJadwal, useUsulkanWaktuJadwal } from "../../hooks/useJadwal";
import { pesanDariError } from "../../lib/galat";
import { formatWaktu } from "../../lib/format";
import type { BimbinganItem } from "../../lib/types";
import { Drawer } from "../Drawer";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../ui";

type Aksi = "setujui" | "tolak" | "usulkan";

function keInputTanggal(iso: string): string {
  const tanggal = new Date(iso);
  const lokal = new Date(tanggal.getTime() - tanggal.getTimezoneOffset() * 60_000);
  return lokal.toISOString().slice(0, 16);
}

function keIso(nilai: string): string {
  return new Date(nilai).toISOString();
}

interface Props {
  open: boolean;
  onClose: () => void;
  permohonan: BimbinganItem | null;
}

export function JadwalKonfirmasiDrawer({ open, onClose, permohonan }: Props) {
  const setujui = useSetujuiJadwal();
  const tolak = useTolakJadwal();
  const usulkan = useUsulkanWaktuJadwal();
  const [aksi, setAksi] = useState<Aksi>("setujui");
  const [lokasi, setLokasi] = useState("");
  const [alasan, setAlasan] = useState("");
  const [mulai, setMulai] = useState("");
  const [selesai, setSelesai] = useState("");
  const [galat, setGalat] = useState<string | null>(null);
  const pending = setujui.isPending || tolak.isPending || usulkan.isPending;

  useEffect(() => {
    if (!open || !permohonan) return;
    setAksi("setujui");
    setLokasi(permohonan.lokasi_atau_tautan);
    setAlasan("");
    setMulai(keInputTanggal(permohonan.mulai));
    setSelesai(keInputTanggal(permohonan.selesai));
    setGalat(null);
    setujui.reset();
    tolak.reset();
    usulkan.reset();
  }, [open, permohonan?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!permohonan) return null;
  const item = permohonan;

  async function kirim(e: FormEvent) {
    e.preventDefault();
    setGalat(null);
    try {
      if (aksi === "setujui") {
        await setujui.mutateAsync({ id: item.id, lokasi_atau_tautan: lokasi.trim() });
      } else if (aksi === "tolak") {
        await tolak.mutateAsync({ id: item.id, alasan: alasan.trim() });
      } else {
        await usulkan.mutateAsync({
          id: item.id,
          mulai: keIso(mulai),
          selesai: keIso(selesai),
          lokasi_atau_tautan: lokasi.trim(),
        });
      }
      onClose();
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  return (
    <Drawer open={open} onClose={onClose} title="Konfirmasi jadwal bimbingan">
      <div className="space-y-2 rounded-lg bg-page p-4">
        <p className="text-body font-semibold text-ink">{item.mahasiswa.nama_lengkap} · {item.mahasiswa.identifier}</p>
        <p className="text-body text-muted">{item.tugas_akhir.judul}</p>
        <p className="text-body text-ink">{formatWaktu(item.mulai)} – {formatWaktu(item.selesai)}</p>
        <p className="text-body text-muted">{item.mode_label}{item.agenda ? ` · ${item.agenda}` : ""}</p>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2">
        {([
          ["setujui", "Setujui"],
          ["tolak", "Tolak"],
          ["usulkan", "Usulkan waktu"],
        ] as const).map(([nilai, label]) => (
          <button
            key={nilai}
            type="button"
            onClick={() => { setAksi(nilai); setGalat(null); }}
            aria-pressed={aksi === nilai}
            className={`min-h-10 rounded-md border px-2 text-label font-semibold ${aksi === nilai ? "border-primary bg-tint text-primary" : "border-line bg-surface text-muted"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <form onSubmit={kirim} className="mt-5 space-y-4">
        {aksi === "setujui" && (
          <div>
            <label htmlFor="jadwal-lokasi-konfirmasi" className="mb-1.5 block text-body font-medium text-ink">
              {item.mode === "daring" ? "Tautan rapat" : "Lokasi bimbingan"}
            </label>
            <input
              id="jadwal-lokasi-konfirmasi"
              className={inputClass}
              value={lokasi}
              onChange={(e) => setLokasi(e.target.value)}
              placeholder={item.mode === "daring" ? "https://..." : "Ruang atau lokasi bimbingan"}
              required
              maxLength={500}
            />
          </div>
        )}

        {aksi === "tolak" && (
          <div>
            <label htmlFor="jadwal-alasan-penolakan" className="mb-1.5 block text-body font-medium text-ink">Alasan penolakan</label>
            <textarea
              id="jadwal-alasan-penolakan"
              className={`${inputClass} h-28 py-2`}
              value={alasan}
              onChange={(e) => setAlasan(e.target.value)}
              required
              maxLength={2000}
            />
          </div>
        )}

        {aksi === "usulkan" && (
          <>
            <div>
              <label htmlFor="jadwal-usulan-mulai" className="mb-1.5 block text-body font-medium text-ink">Waktu mulai yang diusulkan</label>
              <input id="jadwal-usulan-mulai" type="datetime-local" className={inputClass} value={mulai} onChange={(e) => setMulai(e.target.value)} required />
            </div>
            <div>
              <label htmlFor="jadwal-usulan-selesai" className="mb-1.5 block text-body font-medium text-ink">Waktu selesai yang diusulkan</label>
              <input id="jadwal-usulan-selesai" type="datetime-local" className={inputClass} value={selesai} onChange={(e) => setSelesai(e.target.value)} required />
            </div>
            <div>
              <label htmlFor="jadwal-usulan-lokasi" className="mb-1.5 block text-body font-medium text-ink">{item.mode === "daring" ? "Tautan rapat (opsional)" : "Lokasi (opsional)"}</label>
              <input id="jadwal-usulan-lokasi" className={inputClass} value={lokasi} onChange={(e) => setLokasi(e.target.value)} maxLength={500} />
            </div>
            <p className="text-label text-muted">Usulan waktu tetap berstatus Menunggu Konfirmasi. Mahasiswa menerima pemberitahuan atas perubahan waktu.</p>
          </>
        )}

        {galat && <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger"><CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" /><span>{galat}</span></div>}
        <button type="submit" disabled={pending || (aksi === "tolak" && !alasan.trim()) || (aksi === "setujui" && !lokasi.trim())} className={primaryButtonClass}>
          {pending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {aksi === "setujui" ? "Setujui jadwal" : aksi === "tolak" ? "Kirim penolakan" : "Kirim usulan waktu"}
        </button>
        <button type="button" onClick={onClose} className={`${secondaryButtonClass} w-full`}>Tutup</button>
      </form>
    </Drawer>
  );
}
