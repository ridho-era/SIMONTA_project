import { Link } from "react-router-dom";
import { AlertTriangle, ArrowRight, CalendarDays, FileText, GraduationCap, Users, Wallet } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { primaryButtonClass, secondaryButtonClass } from "../components/ui";
import { useDashboardMahasiswa } from "../hooks/useDashboard";
import { formatAngka } from "../lib/angka";
import { formatTanggal, formatWaktu } from "../lib/format";
import { StatusJadwalChip } from "../components/jadwal/StatusJadwalChip";

export default function DashboardMahasiswaPage() {
  const { data, isLoading, isError, refetch, isFetching } = useDashboardMahasiswa();

  if (isLoading) {
    return <PageFrame title="Dashboard"><p role="status" className="text-body text-muted">Memuat ringkasan tugas akhir…</p></PageFrame>;
  }
  if (isError || !data) {
    return (
      <PageFrame title="Dashboard">
        <EmptyState>
          <p>Dashboard belum dapat dimuat.</p>
          <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
        </EmptyState>
      </PageFrame>
    );
  }

  const progres = Math.min(100, Math.max(0, data.progres));

  return (
    <PageFrame title="Dashboard" subtitle="Ringkasan perjalanan dan aktivitas tugas akhir Anda.">
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-heading font-semibold text-ink">Selamat datang, {data.mahasiswa.nama_lengkap}.</h2>
            <p className="mt-1 text-body text-muted">NPM {data.mahasiswa.identifier}</p>
          </div>
          <Link to="/mahasiswa/dokumen" className={`${primaryButtonClass} sm:w-auto`}>
            <FileText className="size-4" aria-hidden="true" /> Unggah dokumen
          </Link>
        </div>

        {data.banner_keterlambatan && (
          <section role="alert" className="rounded-xl border border-danger/30 bg-danger-bg p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden="true" />
              <div>
                <h2 className="text-heading font-semibold text-danger">Ada milestone yang melewati tenggat</h2>
                <p className="mt-1 text-body text-ink">
                  {data.banner_keterlambatan.milestone.nama} · Tenggat {formatTanggal(data.banner_keterlambatan.target)}.
                </p>
                {data.banner_keterlambatan.sanksi_akademik && (
                  <p className="mt-1 text-body text-ink">Sanksi akademik tercatat: {data.banner_keterlambatan.sanksi_akademik}</p>
                )}
              </div>
            </div>
          </section>
        )}

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)]">
          <section className="rounded-xl bg-primary p-5 text-white sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-label font-semibold tracking-wide text-gold-soft">PROGRES TUGAS AKHIR</p>
                {data.tugas_akhir ? (
                  <>
                    <h2 className="mt-1 text-heading font-semibold">{data.tugas_akhir.judul}</h2>
                    <p className="mt-1 text-body text-white/80">{data.tugas_akhir.periode} · {data.tugas_akhir.jenis_penelitian || "Jenis penelitian belum diisi"}</p>
                  </>
                ) : (
                  <h2 className="mt-1 text-heading font-semibold">Tugas akhir belum terdaftar</h2>
                )}
              </div>
              {data.tugas_akhir && <Link to="/mahasiswa/milestone" className="text-body font-semibold text-gold-soft underline">Lihat timeline</Link>}
            </div>
            {data.tugas_akhir ? (
              <>
                <p className="mt-5 text-title font-semibold">{formatAngka(progres)}%</p>
                <div role="progressbar" aria-label="Progres tugas akhir" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progres} className="mt-2 h-2.5 overflow-hidden rounded-full bg-white/20">
                  <div className="h-full rounded-full bg-gold" style={{ width: `${progres}%` }} />
                </div>
                <div className="mt-3 flex flex-wrap justify-between gap-2 text-body text-white/85">
                  <span>{data.jumlah_diverifikasi} dari {data.total_milestone} milestone diverifikasi</span>
                  <span>{data.tahap_aktif ? `Tahap aktif: ${data.tahap_aktif.nama}` : data.total_milestone > 0 ? "Semua tahap diverifikasi" : "Milestone belum dibuat"}</span>
                </div>
                <p className="mt-3 text-label text-white/80">Progres dihitung hanya dari milestone yang diverifikasi pembimbing utama. Unggahan dokumen tidak otomatis menambah progres.</p>
              </>
            ) : (
              <div className="mt-4 rounded-lg bg-white/10 p-4 text-body text-white/90">Tugas akhir Anda belum didaftarkan. Hubungi admin Prodi.</div>
            )}
          </section>

          <section className="rounded-xl border border-line bg-surface p-5">
            <div className="flex items-center gap-2">
              <Users className="size-5 text-primary-2" aria-hidden="true" />
              <h2 className="text-heading font-semibold text-primary">Tim pembimbing</h2>
            </div>
            {data.tim_pembimbing.length === 0 ? (
              <EmptyState>Tim pembimbing belum ditetapkan.</EmptyState>
            ) : (
              <ul className="mt-4 space-y-3">
                {data.tim_pembimbing.map((item) => (
                  <li key={`${item.id}-${item.peran}`} className="border-b border-line pb-3 last:border-0 last:pb-0">
                    <p className="text-body font-semibold text-ink">{item.nama_lengkap}</p>
                    <p className="text-label text-muted">{item.peran_label} · NIP {item.identifier}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <section className="rounded-xl border border-line bg-surface p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2"><GraduationCap className="size-5 text-primary-2" aria-hidden="true" /><h2 className="text-heading font-semibold text-primary">Review perlu ditindaklanjuti</h2></div>
            </div>
            {data.review_tindak_lanjut ? (
              <div className="mt-4 rounded-lg bg-warning-bg/60 p-4">
                <p className="text-label font-semibold text-warning">Perlu revisi · {data.review_tindak_lanjut.milestone}</p>
                <h3 className="mt-1 text-body font-semibold text-ink">{data.review_tindak_lanjut.nama_berkas}</h3>
                <p className="mt-1 text-body text-muted">Oleh {data.review_tindak_lanjut.pemberi}</p>
                {data.review_tindak_lanjut.komentar && <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-body text-ink">{data.review_tindak_lanjut.komentar}</p>}
                {data.review_tindak_lanjut.tenggat_revisi && <p className="mt-2 text-body text-muted">Tenggat revisi: {formatTanggal(data.review_tindak_lanjut.tenggat_revisi)}</p>}
                <Link to={data.review_tindak_lanjut.url} className={`${secondaryButtonClass} mt-3`}>Buka feedback <ArrowRight className="size-4" /></Link>
              </div>
            ) : (
              <EmptyState>Belum ada review terbit yang perlu ditindaklanjuti.</EmptyState>
            )}
          </section>

          <section className="rounded-xl border border-line bg-surface p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2"><CalendarDays className="size-5 text-primary-2" aria-hidden="true" /><h2 className="text-heading font-semibold text-primary">Bimbingan terdekat</h2></div>
              <Link to="/mahasiswa/jadwal" className="text-label font-semibold text-primary underline">Semua jadwal</Link>
            </div>
            {data.bimbingan_terdekat ? (
              <div className="mt-4 rounded-lg bg-page p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-body font-semibold text-ink">{data.bimbingan_terdekat.dosen.nama_lengkap}</p>
                  <StatusJadwalChip status={data.bimbingan_terdekat.status} />
                </div>
                <p className="mt-2 text-body text-ink">{formatWaktu(data.bimbingan_terdekat.mulai)} – {formatWaktu(data.bimbingan_terdekat.selesai)}</p>
                <p className="mt-1 text-body text-muted">
                  {data.bimbingan_terdekat.mode_label}{data.bimbingan_terdekat.lokasi_atau_tautan ? " · " : ""}
                  {data.bimbingan_terdekat.mode === "daring" && /^https?:\/\//i.test(data.bimbingan_terdekat.lokasi_atau_tautan) ? (
                    <a href={data.bimbingan_terdekat.lokasi_atau_tautan} target="_blank" rel="noopener noreferrer" className="font-semibold text-primary underline">Buka tautan rapat</a>
                  ) : data.bimbingan_terdekat.lokasi_atau_tautan}
                </p>
                {data.bimbingan_terdekat.agenda && <p className="mt-2 text-body text-muted">Agenda: {data.bimbingan_terdekat.agenda}</p>}
              </div>
            ) : (
              <div className="mt-4"><EmptyState>Belum ada jadwal bimbingan mendatang.</EmptyState></div>
            )}
          </section>

          <section className="rounded-xl border border-line bg-surface p-5 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2"><Wallet className="size-5 text-primary-2" aria-hidden="true" /><h2 className="text-heading font-semibold text-primary">Ringkasan denda keterlambatan</h2></div>
              <Link to="/mahasiswa/denda" className="text-label font-semibold text-primary underline">Lihat detail</Link>
            </div>
            {data.ringkasan_denda ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg bg-page p-4"><p className="text-body text-muted">Total nominal</p><p className="mt-2 text-title font-semibold text-primary">{new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(data.ringkasan_denda.total_nominal)}</p></div>
                <div className="rounded-lg bg-page p-4"><p className="text-body text-muted">Keterlambatan terbuka</p><p className="mt-2 text-title font-semibold text-primary">{data.ringkasan_denda.keterlambatan_terbuka}</p></div>
                <div className="rounded-lg bg-page p-4"><p className="text-body text-muted">Keberatan ditinjau</p><p className="mt-2 text-title font-semibold text-primary">{data.ringkasan_denda.keberatan_ditinjau}</p></div>
              </div>
            ) : (
              <div className="mt-4"><EmptyState>Belum ada konfigurasi denda untuk periode tugas akhir Anda.</EmptyState></div>
            )}
          </section>
        </div>
      </div>
    </PageFrame>
  );
}
