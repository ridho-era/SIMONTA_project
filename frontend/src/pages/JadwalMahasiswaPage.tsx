import { useEffect, useState, type FormEvent } from "react";
import { CalendarDays, CircleAlert, Clock3, Loader2, MapPin, Video } from "lucide-react";

import { Drawer } from "../components/Drawer";
import { EmptyState } from "../components/EmptyState";
import { StatusJadwalChip } from "../components/jadwal/StatusJadwalChip";
import { PageFrame } from "../components/PageFrame";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import { useAjukanJadwal, useJadwalMahasiswa, useRescheduleJadwal } from "../hooks/useJadwal";
import { pesanDariError } from "../lib/galat";
import { formatWaktu } from "../lib/format";
import type { BimbinganItem, JadwalMahasiswaData, ModeBimbingan } from "../lib/types";

type Tab = "mendatang" | "riwayat";

function keInputTanggal(iso: string): string {
  const tanggal = new Date(iso);
  const lokal = new Date(tanggal.getTime() - tanggal.getTimezoneOffset() * 60_000);
  return lokal.toISOString().slice(0, 16);
}

function keIso(nilai: string): string {
  return new Date(nilai).toISOString();
}

function FormJadwalDrawer({
  open,
  onClose,
  data,
  jadwalLama,
}: {
  open: boolean;
  onClose: () => void;
  data: JadwalMahasiswaData;
  jadwalLama: BimbinganItem | null;
}) {
  const ajukan = useAjukanJadwal();
  const reschedule = useRescheduleJadwal();
  const [dosenId, setDosenId] = useState("");
  const [mulai, setMulai] = useState("");
  const [selesai, setSelesai] = useState("");
  const [mode, setMode] = useState<ModeBimbingan>("luring");
  const [lokasi, setLokasi] = useState("");
  const [agenda, setAgenda] = useState("");
  const [galat, setGalat] = useState<string | null>(null);
  const pending = ajukan.isPending || reschedule.isPending;

  useEffect(() => {
    if (!open) return;
    setDosenId(jadwalLama ? String(jadwalLama.dosen.id) : "");
    setMulai(jadwalLama ? keInputTanggal(jadwalLama.mulai) : "");
    setSelesai(jadwalLama ? keInputTanggal(jadwalLama.selesai) : "");
    setMode(jadwalLama?.mode ?? "luring");
    setLokasi(jadwalLama?.lokasi_atau_tautan ?? "");
    setAgenda(jadwalLama?.agenda ?? "");
    setGalat(null);
    ajukan.reset();
    reschedule.reset();
  }, [open, jadwalLama?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function kirim(e: FormEvent) {
    e.preventDefault();
    setGalat(null);
    const awal = new Date(mulai);
    const akhir = new Date(selesai);
    if (!Number.isFinite(awal.getTime()) || !Number.isFinite(akhir.getTime())) {
      setGalat("Tanggal dan waktu mulai serta selesai wajib diisi.");
      return;
    }
    if (awal.getTime() <= Date.now()) {
      setGalat("Jadwal tidak boleh berada di masa lalu.");
      return;
    }
    if (akhir.getTime() <= awal.getTime()) {
      setGalat("Jam selesai harus setelah jam mulai.");
      return;
    }
    const payload = {
      mulai: keIso(mulai),
      selesai: keIso(selesai),
      mode,
      lokasi_atau_tautan: lokasi.trim(),
      agenda: agenda.trim(),
    };
    try {
      if (jadwalLama) {
        await reschedule.mutateAsync({ id: jadwalLama.id, ...payload });
      } else {
        if (!dosenId) {
          setGalat("Pilih dosen tujuan terlebih dahulu.");
          return;
        }
        await ajukan.mutateAsync({ dosen_id: Number(dosenId), ...payload });
      }
      onClose();
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  return (
    <Drawer open={open} onClose={onClose} title={jadwalLama ? "Ajukan reschedule" : "Ajukan jadwal bimbingan"}>
      <form onSubmit={kirim} className="space-y-4">
        {jadwalLama ? (
          <div className="rounded-md bg-page p-3 text-body text-ink">
            Jadwal pengganti untuk bimbingan bersama <strong>{jadwalLama.dosen.nama_lengkap}</strong>.
          </div>
        ) : (
          <div>
            <label htmlFor="jadwal-dosen-tujuan" className="mb-1.5 block text-body font-medium text-ink">Dosen tujuan</label>
            <select id="jadwal-dosen-tujuan" className={inputClass} value={dosenId} onChange={(e) => setDosenId(e.target.value)} required>
              <option value="">Pilih dosen pembimbing/penguji</option>
              {data.dosen_tujuan.map((item) => (
                <option key={item.id} value={item.id}>{item.nama_lengkap} · {item.peran_label} · NIP {item.identifier}</option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label htmlFor="jadwal-mulai" className="mb-1.5 block text-body font-medium text-ink">Tanggal dan waktu mulai</label>
          <input id="jadwal-mulai" type="datetime-local" className={inputClass} value={mulai} onChange={(e) => setMulai(e.target.value)} required />
        </div>
        <div>
          <label htmlFor="jadwal-selesai" className="mb-1.5 block text-body font-medium text-ink">Tanggal dan waktu selesai</label>
          <input id="jadwal-selesai" type="datetime-local" className={inputClass} value={selesai} onChange={(e) => setSelesai(e.target.value)} required />
        </div>
        <div>
          <label htmlFor="jadwal-mode" className="mb-1.5 block text-body font-medium text-ink">Mode bimbingan</label>
          <select id="jadwal-mode" className={inputClass} value={mode} onChange={(e) => setMode(e.target.value as ModeBimbingan)}>
            <option value="luring">Luring</option>
            <option value="daring">Daring</option>
          </select>
        </div>
        <div>
          <label htmlFor="jadwal-lokasi" className="mb-1.5 block text-body font-medium text-ink">{mode === "daring" ? "Tautan rapat (opsional, dapat dilengkapi dosen)" : "Lokasi (opsional, dapat dilengkapi dosen)"}</label>
          <input id="jadwal-lokasi" className={inputClass} value={lokasi} onChange={(e) => setLokasi(e.target.value)} maxLength={500} placeholder={mode === "daring" ? "https://..." : "Lokasi yang diusulkan"} />
        </div>
        <div>
          <label htmlFor="jadwal-agenda" className="mb-1.5 block text-body font-medium text-ink">Agenda bimbingan</label>
          <textarea id="jadwal-agenda" className={`${inputClass} min-h-28 py-2`} value={agenda} onChange={(e) => setAgenda(e.target.value)} maxLength={2000} placeholder="Tuliskan hal yang ingin dibahas." />
        </div>
        {galat && <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger"><CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" /><span>{galat}</span></div>}
        <p className="text-label text-muted">Permohonan akan berstatus Menunggu Konfirmasi sampai dosen memprosesnya.</p>
        <button type="submit" disabled={pending || (!jadwalLama && !dosenId)} className={primaryButtonClass}>
          {pending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {jadwalLama ? "Kirim permohonan reschedule" : "Kirim permohonan"}
        </button>
        <button type="button" onClick={onClose} className={`${secondaryButtonClass} w-full`}>Batal</button>
      </form>
    </Drawer>
  );
}

function KartuJadwal({ item, onReschedule, riwayat = false }: { item: BimbinganItem; onReschedule?: () => void; riwayat?: boolean }) {
  return (
    <li className="rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-body font-semibold text-ink">{item.dosen.nama_lengkap} · {item.dosen.peran_label}</p>
          <p className="mt-1 text-label text-muted">NIP {item.dosen.identifier}</p>
        </div>
        <StatusJadwalChip status={item.status} />
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <p className="flex items-start gap-2 text-body text-ink"><CalendarDays className="mt-0.5 size-4 shrink-0 text-primary-2" aria-hidden="true" />{formatWaktu(item.mulai)}</p>
        <p className="flex items-start gap-2 text-body text-ink"><Clock3 className="mt-0.5 size-4 shrink-0 text-primary-2" aria-hidden="true" />Selesai {formatWaktu(item.selesai)}</p>
        <p className="flex items-start gap-2 text-body text-ink">
          {item.mode === "daring" ? <Video className="mt-0.5 size-4 shrink-0 text-primary-2" aria-hidden="true" /> : <MapPin className="mt-0.5 size-4 shrink-0 text-primary-2" aria-hidden="true" />}
          <span>
            {item.mode_label} · {item.lokasi_atau_tautan ? (
              item.mode === "daring" && /^https?:\/\//i.test(item.lokasi_atau_tautan) ? (
                <a href={item.lokasi_atau_tautan} target="_blank" rel="noopener noreferrer" className="font-semibold text-primary underline">Buka tautan rapat</a>
              ) : item.lokasi_atau_tautan
            ) : item.mode === "daring" ? "Tautan menunggu konfirmasi dosen" : "Lokasi menunggu konfirmasi dosen"}
          </span>
        </p>
        {item.agenda && <p className="text-body text-muted sm:col-span-2">Agenda: {item.agenda}</p>}
      </div>
      {item.alasan_penolakan && <p className="mt-3 rounded-md bg-danger-bg p-3 text-body text-danger">Alasan penolakan: {item.alasan_penolakan}</p>}
      {item.menggantikan && <p className="mt-2 text-label text-muted">Permohonan ini menggantikan jadwal #{item.menggantikan}.</p>}
      {!riwayat && onReschedule && (item.status === "menunggu_konfirmasi" || item.status === "disetujui") && (
        <button type="button" onClick={onReschedule} className={`${secondaryButtonClass} mt-4`}>Ajukan reschedule</button>
      )}
    </li>
  );
}

export default function JadwalMahasiswaPage() {
  const { data, isLoading, isError, refetch, isFetching } = useJadwalMahasiswa();
  const [tab, setTab] = useState<Tab>("mendatang");
  const [formTerbuka, setFormTerbuka] = useState(false);
  const [jadwalLama, setJadwalLama] = useState<BimbinganItem | null>(null);

  if (isLoading) return <PageFrame title="Jadwal bimbingan"><p role="status" className="text-body text-muted">Memuat jadwal bimbingan…</p></PageFrame>;
  if (isError || !data) {
    return <PageFrame title="Jadwal bimbingan"><EmptyState><p>Jadwal bimbingan belum dapat dimuat.</p><button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button></EmptyState></PageFrame>;
  }
  if (!data.tugas_akhir) {
    return <PageFrame title="Jadwal bimbingan" subtitle="Ajukan dan pantau jadwal konsultasi dengan dosen yang ditugaskan."><EmptyState>Tugas akhir aktif belum terdaftar. Hubungi admin Prodi terlebih dahulu.</EmptyState></PageFrame>;
  }

  const daftar = tab === "mendatang" ? data.mendatang : data.riwayat;

  return (
    <PageFrame title="Jadwal bimbingan" subtitle="Ajukan waktu konsultasi dan pantau konfirmasi dari dosen. ">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-2" role="tablist" aria-label="Daftar jadwal">
            <button type="button" role="tab" aria-selected={tab === "mendatang"} onClick={() => setTab("mendatang")} className={`rounded-md px-4 py-2 text-body font-semibold ${tab === "mendatang" ? "bg-tint text-primary" : "border border-line text-muted"}`}>Mendatang ({data.mendatang.length})</button>
            <button type="button" role="tab" aria-selected={tab === "riwayat"} onClick={() => setTab("riwayat")} className={`rounded-md px-4 py-2 text-body font-semibold ${tab === "riwayat" ? "bg-tint text-primary" : "border border-line text-muted"}`}>Riwayat ({data.riwayat.length})</button>
          </div>
          <button type="button" onClick={() => { setJadwalLama(null); setFormTerbuka(true); }} disabled={data.dosen_tujuan.length === 0} className={`${primaryButtonClass} sm:w-auto`}>
            <CalendarDays className="size-4" aria-hidden="true" /> Ajukan jadwal baru
          </button>
        </div>

        {data.dosen_tujuan.length === 0 && <p className="rounded-lg bg-info-bg p-3 text-body text-info">Belum ada dosen yang ditugaskan pada tugas akhir ini. Hubungi admin Prodi.</p>}

        {daftar.length === 0 ? (
          <EmptyState>{tab === "mendatang" ? "Belum ada jadwal mendatang. Ajukan jadwal bimbingan untuk memulai." : "Belum ada riwayat jadwal bimbingan."}</EmptyState>
        ) : (
          <ul className="space-y-3">
            {daftar.map((item) => <KartuJadwal key={item.id} item={item} riwayat={tab === "riwayat"} onReschedule={tab === "mendatang" ? () => { setJadwalLama(item); setFormTerbuka(true); } : undefined} />)}
          </ul>
        )}

        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2"><CalendarDays className="size-5 text-primary-2" aria-hidden="true" /><h2 className="text-heading font-semibold text-primary">Persiapan bimbingan</h2></div>
          <p className="mt-2 text-body text-muted">Siapkan daftar pertanyaan, ringkasan kemajuan tugas akhir, dan dokumen atau bagian yang ingin dibahas agar waktu bimbingan lebih terarah.</p>
        </section>
      </div>
      <FormJadwalDrawer open={formTerbuka} onClose={() => { setFormTerbuka(false); setJadwalLama(null); }} data={data} jadwalLama={jadwalLama} />
    </PageFrame>
  );
}
