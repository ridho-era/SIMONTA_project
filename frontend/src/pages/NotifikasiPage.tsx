import { useEffect, useState, type FormEvent } from "react";
import { Bell, BellRing, CalendarClock, CheckCheck, Clock3, Loader2, Mail, RotateCcw, Save } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import {
  useDaftarNotifikasi,
  usePengaturanNotifikasi,
  usePratinjauPengingat,
  usePulihkanDefaultNotifikasi,
  useSimpanPengaturanNotifikasi,
  useTandaiNotifikasiDibaca,
  useTandaiSemuaNotifikasiDibaca,
} from "../hooks/useNotifikasi";
import { formatTanggal, formatWaktu } from "../lib/format";
import { pesanDariError } from "../lib/galat";
import type { NotifikasiItem, PengaturanNotifikasiData } from "../lib/types";

type Filter = "semua" | "belum_dibaca";

function Toggle({
  id,
  label,
  checked,
  onChange,
  description,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  description?: string;
}) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start gap-3 rounded-lg border border-line bg-surface p-3">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 size-4 shrink-0 accent-primary"
      />
      <span className="min-w-0">
        <span className="block text-body font-semibold text-ink">{label}</span>
        {description && <span className="mt-0.5 block text-label text-muted">{description}</span>}
      </span>
    </label>
  );
}

function tujuanNotifikasi(item: NotifikasiItem, role: "mahasiswa" | "dosen"): string | null {
  const path = item.tautan.trim();
  if (!path.startsWith(`/${role}/`)) return null;
  return path;
}

export default function NotifikasiPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Filter>("semua");
  const [draft, setDraft] = useState<PengaturanNotifikasiData | null>(null);
  const [pesanSukses, setPesanSukses] = useState<string | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const daftar = useDaftarNotifikasi(filter);
  const pengaturan = usePengaturanNotifikasi();
  const simpan = useSimpanPengaturanNotifikasi();
  const pulihkan = usePulihkanDefaultNotifikasi();
  const tandaiSatu = useTandaiNotifikasiDibaca();
  const tandaiSemua = useTandaiSemuaNotifikasiDibaca();
  const pratinjau = usePratinjauPengingat();
  const dosen = user?.role === "dosen";

  useEffect(() => {
    if (pengaturan.data) setDraft(pengaturan.data);
  }, [pengaturan.data]);

  if (!user || user.role === "admin") return <PageFrame title="Notifikasi & pengaturan"><EmptyState>Menu ini hanya tersedia untuk mahasiswa dan dosen.</EmptyState></PageFrame>;
  const role = user.role;

  function ubah<K extends keyof PengaturanNotifikasiData>(field: K, value: PengaturanNotifikasiData[K]) {
    setDraft((lama) => (lama ? { ...lama, [field]: value } : lama));
    setPesanSukses(null);
    setGalat(null);
  }

  async function simpanPengaturan(event: FormEvent) {
    event.preventDefault();
    if (!draft) return;
    setGalat(null);
    setPesanSukses(null);
    try {
      const payload: Partial<PengaturanNotifikasiData> = {
        pengingat_aktif: draft.pengingat_aktif,
        h_minus_7: draft.h_minus_7,
        h_minus_3: draft.h_minus_3,
        h_minus_1: draft.h_minus_1,
        kanal_aplikasi: draft.kanal_aplikasi,
        kanal_email: draft.kanal_email,
        ringkasan_mingguan: draft.ringkasan_mingguan,
        dokumen_feedback_aktif: draft.dokumen_feedback_aktif,
        jadwal_bimbingan_aktif: draft.jadwal_bimbingan_aktif,
        jam_kirim: draft.jam_kirim,
        zona_waktu: "Asia/Jakarta",
      };
      await simpan.mutateAsync(payload);
      pratinjau.reset();
      setPesanSukses("Pengaturan notifikasi berhasil disimpan.");
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  async function pulihkanDefault() {
    setGalat(null);
    setPesanSukses(null);
    try {
      await pulihkan.mutateAsync();
      pratinjau.reset();
      setPesanSukses("Pengaturan telah dipulihkan ke nilai default.");
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  async function bukaNotifikasi(item: NotifikasiItem) {
    if (!item.dibaca_pada) {
      try {
        await tandaiSatu.mutateAsync(item.id);
      } catch (error) {
        setGalat(pesanDariError(error));
      }
    }
    const tujuan = tujuanNotifikasi(item, role);
    if (tujuan) navigate(tujuan);
  }

  async function bukaPratinjau() {
    setGalat(null);
    try {
      await pratinjau.mutateAsync();
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  const hasilPratinjau = pratinjau.data?.hasil ?? [];

  return (
    <PageFrame
      title="Notifikasi & pengaturan"
      subtitle={dosen ? "Pemberitahuan bimbingan dan preferensi kanal untuk akun dosen." : "Pusat pemberitahuan dan pengingat milestone tugas akhir Anda."}
    >
      <div className="space-y-6">
        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-heading font-semibold text-primary">Pusat notifikasi</h2>
              <p className="mt-1 text-label text-muted">Menampilkan maksimal 100 notifikasi terbaru.</p>
            </div>
            <button
              type="button"
              onClick={() => void tandaiSemua.mutateAsync().catch((error) => setGalat(pesanDariError(error)))}
              disabled={!daftar.data?.jumlah_belum_dibaca || tandaiSemua.isPending}
              className={secondaryButtonClass}
            >
              {tandaiSemua.isPending ? <Loader2 className="size-4 animate-spin" /> : <CheckCheck className="size-4" />}
              Tandai semua dibaca
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter notifikasi">
            {([ ["semua", "Semua"], ["belum_dibaca", "Belum dibaca"] ] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                aria-pressed={filter === key}
                className={`rounded-full border px-4 py-2 text-label font-semibold ${filter === key ? "border-primary bg-tint text-primary" : "border-line text-muted hover:bg-page"}`}
              >
                {label}{key === "belum_dibaca" && daftar.data ? ` (${daftar.data.jumlah_belum_dibaca})` : ""}
              </button>
            ))}
          </div>

          {daftar.isLoading ? (
            <p role="status" className="mt-5 text-body text-muted">Memuat notifikasi…</p>
          ) : daftar.isError ? (
            <div className="mt-5"><EmptyState>Notifikasi belum dapat dimuat. Muat ulang halaman atau coba lagi.</EmptyState></div>
          ) : daftar.data?.hasil.length ? (
            <ul className="mt-4 divide-y divide-line">
              {daftar.data.hasil.map((item) => {
                const bisaDibuka = Boolean(tujuanNotifikasi(item, role));
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => void bukaNotifikasi(item)}
                      className="flex w-full items-start gap-3 py-4 text-left hover:bg-page/70"
                    >
                      <span className={`mt-0.5 grid size-9 shrink-0 place-items-center rounded-full ${item.dibaca_pada ? "bg-page text-muted" : "bg-tint text-primary"}`}>
                        {item.dibaca_pada ? <Bell className="size-4" /> : <BellRing className="size-4" />}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="text-body font-semibold text-ink">{item.judul}</span>
                          {!item.dibaca_pada && <span className="rounded-full bg-info-bg px-2 py-0.5 text-label font-semibold text-info">Belum dibaca</span>}
                        </span>
                        <span className="mt-1 block text-label font-semibold text-primary-2">{item.jenis_label}</span>
                        {item.isi && <span className="mt-1 block text-body text-muted">{item.isi}</span>}
                        <span className="mt-2 flex flex-wrap items-center gap-1 text-label text-muted">
                          <Clock3 className="size-3.5" />{formatWaktu(item.dibuat_pada)}
                          {bisaDibuka && <span className="ml-2 font-semibold text-primary">Buka detail →</span>}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="mt-5"><EmptyState>{filter === "belum_dibaca" ? "Tidak ada notifikasi yang belum dibaca." : "Belum ada pemberitahuan untuk akun ini."}</EmptyState></div>
          )}
        </section>

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="flex items-start gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-tint text-primary"><CalendarClock className="size-5" /></span>
            <div>
              <h2 className="text-heading font-semibold text-primary">Pengaturan pengingat otomatis</h2>
              <p className="mt-1 text-label text-muted">Pengingat dihitung dari tanggal target milestone aktif. Sistem memakai kunci unik agar pengingat tidak terkirim ganda, termasuk saat target berubah. Pengingat H-x yang sudah lewat tidak dikirim susulan.</p>
            </div>
          </div>

          {pengaturan.isLoading ? (
            <p role="status" className="mt-5 text-body text-muted">Memuat pengaturan…</p>
          ) : pengaturan.isError ? (
            <div className="mt-5">
              <EmptyState>Pengaturan belum dapat dimuat.</EmptyState>
              <button type="button" onClick={() => void pengaturan.refetch()} className={`${secondaryButtonClass} mt-3`}>Coba lagi</button>
            </div>
          ) : !draft ? (
            <p role="status" className="mt-5 text-body text-muted">Menyiapkan pengaturan…</p>
          ) : (
            <form onSubmit={(event) => void simpanPengaturan(event)} className="mt-5 space-y-5">
              <Toggle id="pengingat-aktif" label="Aktifkan pengingat deadline" description="Hanya berlaku untuk milestone aktif yang sudah memiliki target." checked={draft.pengingat_aktif} onChange={(value) => ubah("pengingat_aktif", value)} />

              <fieldset disabled={!draft.pengingat_aktif} className="space-y-3 disabled:opacity-50">
                <legend className="mb-2 text-body font-semibold text-ink">Waktu pengingat</legend>
                <div className="grid gap-3 sm:grid-cols-3">
                  <Toggle id="offset-h7" label="H-7" description="Tujuh hari sebelum target" checked={draft.h_minus_7} onChange={(value) => ubah("h_minus_7", value)} />
                  <Toggle id="offset-h3" label="H-3" description="Tiga hari sebelum target" checked={draft.h_minus_3} onChange={(value) => ubah("h_minus_3", value)} />
                  <Toggle id="offset-h1" label="H-1" description="Satu hari sebelum target" checked={draft.h_minus_1} onChange={(value) => ubah("h_minus_1", value)} />
                </div>
              </fieldset>

              <div>
                <h3 className="mb-2 text-body font-semibold text-ink">Kanal pemberitahuan</h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Toggle id="kanal-aplikasi" label="Dalam aplikasi" description="Muncul di pusat notifikasi dan badge lonceng." checked={draft.kanal_aplikasi} onChange={(value) => ubah("kanal_aplikasi", value)} />
                  <Toggle id="kanal-email" label="Email akademik" description="Notifikasi dikirim ke alamat email akademik akun." checked={draft.kanal_email} onChange={(value) => ubah("kanal_email", value)} />
                  <Toggle id="kanal-ringkasan" label="Ringkasan mingguan Senin" description="Email ringkasan aktivitas tujuh hari terakhir setiap Senin pukul 08.00 WIB." checked={draft.ringkasan_mingguan} onChange={(value) => ubah("ringkasan_mingguan", value)} />
                </div>
              </div>

              {dosen && (
                <div>
                  <h3 className="mb-2 text-body font-semibold text-ink">Jenis pemberitahuan dosen</h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Toggle id="dokumen-feedback" label="Dokumen baru & feedback" description="Pemberitahuan ketika mahasiswa mengirim dokumen atau review diterbitkan." checked={draft.dokumen_feedback_aktif} onChange={(value) => ubah("dokumen_feedback_aktif", value)} />
                    <Toggle id="jadwal-aktif" label="Jadwal bimbingan" description="Permohonan, persetujuan, penolakan, dan perubahan jadwal." checked={draft.jadwal_bimbingan_aktif} onChange={(value) => ubah("jadwal_bimbingan_aktif", value)} />
                  </div>
                  <p className="mt-2 text-label text-muted">Pengaturan pengingat pada akun dosen berlaku untuk seluruh mahasiswa bimbingan Anda. Setiap mahasiswa juga tetap dapat mengatur pengingat pribadinya sendiri.</p>
                </div>
              )}

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="jam-kirim" className="mb-1.5 block text-body font-semibold text-ink">Jam pengiriman</label>
                  <input id="jam-kirim" type="time" className={inputClass} value={draft.jam_kirim.slice(0, 5)} onChange={(event) => ubah("jam_kirim", event.target.value)} disabled={!draft.pengingat_aktif} required />
                  <p className="mt-1 text-label text-muted">Jam yang sama digunakan untuk H-7, H-3, dan H-1.</p>
                </div>
                <div>
                  <label htmlFor="zona-waktu" className="mb-1.5 block text-body font-semibold text-ink">Zona waktu</label>
                  <input id="zona-waktu" className={inputClass} value="WIB — Asia/Jakarta" readOnly />
                </div>
              </div>

              {galat && <p role="alert" className="rounded-md bg-danger-bg p-3 text-body text-danger">{galat}</p>}
              {pesanSukses && <p role="status" className="rounded-md bg-tint p-3 text-body text-primary">{pesanSukses}</p>}

              <div className="flex flex-wrap gap-2">
                <button type="submit" disabled={simpan.isPending} className={primaryButtonClass}>
                  {simpan.isPending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                  Simpan pengaturan
                </button>
                <button type="button" onClick={() => void pulihkanDefault()} disabled={pulihkan.isPending} className={secondaryButtonClass}>
                  {pulihkan.isPending ? <Loader2 className="size-4 animate-spin" /> : <RotateCcw className="size-4" />}
                  Pulihkan default
                </button>
              </div>
            </form>
          )}
        </section>

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-tint text-primary"><Clock3 className="size-5" /></span>
              <div>
                <h2 className="text-heading font-semibold text-primary">Pratinjau pengingat</h2>
                <p className="mt-1 text-label text-muted">Jadwal aktual dihitung langsung dari target milestone aktif dan preferensi tersimpan.</p>
              </div>
            </div>
            <button type="button" onClick={() => void bukaPratinjau()} disabled={pratinjau.isPending} className={secondaryButtonClass}>
              {pratinjau.isPending ? <Loader2 className="size-4 animate-spin" /> : <CalendarClock className="size-4" />}
              Pratinjau pengingat
            </button>
          </div>

          {pratinjau.isError && <p role="alert" className="mt-4 text-body text-danger">Pratinjau belum dapat dimuat.</p>}
          {pratinjau.data && (
            <div className="mt-4">
              {!pratinjau.data.aktif ? (
                <EmptyState>Pengingat otomatis sedang tidak aktif.</EmptyState>
              ) : hasilPratinjau.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[620px] border-collapse text-left text-body">
                    <thead><tr className="border-b border-line text-label text-muted"><th className="py-2 pr-3">Mahasiswa</th><th className="py-2 pr-3">Milestone</th><th className="py-2 pr-3">Pengingat</th><th className="py-2 pr-3">Target</th><th className="py-2">Dikirim</th></tr></thead>
                    <tbody>
                      {hasilPratinjau.map((item, index) => (
                        <tr key={`${item.milestone_id}-${item.offset_hari}-${index}`} className="border-b border-line last:border-0">
                          <td className="py-3 pr-3"><span className="font-semibold text-ink">{item.mahasiswa}</span><span className="block text-label text-muted">{item.identifier}</span></td>
                          <td className="py-3 pr-3">{item.milestone}</td>
                          <td className="py-3 pr-3 font-semibold text-primary">H-{item.offset_hari}</td>
                          <td className="py-3 pr-3">{formatTanggal(item.target)}</td>
                          <td className="py-3">{formatWaktu(item.jadwal_kirim)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState>Belum ada jadwal pengingat mendatang. Pastikan milestone aktif sudah memiliki target dan offset dipilih.</EmptyState>
              )}
            </div>
          )}
        </section>

        <p className="flex items-start gap-2 text-label text-muted"><Mail className="mt-0.5 size-4 shrink-0" />Email development menggunakan console backend sehingga isi email tampil pada terminal worker. Pengiriman SMTP aktif setelah backend dikonfigurasi untuk production.</p>
      </div>
    </PageFrame>
  );
}
