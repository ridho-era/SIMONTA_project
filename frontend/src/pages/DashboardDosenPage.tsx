import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, ArrowRight, ClipboardCheck, FileText, Users, Wallet } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { StatusVersiChip } from "../components/dokumen/StatusVersiChip";
import { PageFrame } from "../components/PageFrame";
import { secondaryButtonClass } from "../components/ui";
import { useDashboardDosen } from "../hooks/useDashboard";
import { usePermohonanMasukDosen } from "../hooks/useJadwal";
import { formatWaktu, formatTanggal } from "../lib/format";
import { formatUkuran } from "../lib/berkas";
import { JadwalKonfirmasiDrawer } from "../components/jadwal/JadwalKonfirmasiDrawer";
import type { BimbinganItem } from "../lib/types";
import { formatRupiah } from "../lib/keterlambatanTypes";

export default function DashboardDosenPage() {
  const { data, isLoading, isError, refetch, isFetching } = useDashboardDosen();
  const [jadwalDipilih, setJadwalDipilih] = useState<BimbinganItem | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const idPermohonan = Number(searchParams.get("jadwal"));
  const permohonanDeepLink = usePermohonanMasukDosen(Number.isFinite(idPermohonan) && idPermohonan > 0);

  useEffect(() => {
    if (!idPermohonan || !permohonanDeepLink.data) return;
    const item = permohonanDeepLink.data.hasil.find((row) => row.id === idPermohonan);
    if (item) setJadwalDipilih(item);
  }, [idPermohonan, permohonanDeepLink.data]);

  function tutupDrawerJadwal() {
    setJadwalDipilih(null);
    if (searchParams.has("jadwal")) {
      const next = new URLSearchParams(searchParams);
      next.delete("jadwal");
      setSearchParams(next, { replace: true });
    }
  }

  if (isLoading) {
    return <PageFrame title="Dashboard dosen"><p role="status" className="text-body text-muted">Memuat ringkasan bimbingan…</p></PageFrame>;
  }
  if (isError || !data) {
    return (
      <PageFrame title="Dashboard dosen">
        <EmptyState>
          <p>Dashboard dosen belum dapat dimuat.</p>
          <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
        </EmptyState>
      </PageFrame>
    );
  }

  const statistik = [
    { label: "Mahasiswa bimbingan", nilai: data.statistik.mahasiswa_bimbingan, icon: Users },
    { label: "Menunggu review", nilai: data.statistik.menunggu_review, icon: ClipboardCheck },
    { label: "Mahasiswa terlambat", nilai: data.statistik.terlambat, icon: AlertTriangle },
  ];

  return (
    <PageFrame title="Dashboard dosen" subtitle="Pantau mahasiswa bimbingan, antrean review, dan tenggat aktif.">
      <div className="space-y-6">
        <div>
          <h2 className="text-heading font-semibold text-ink">Selamat datang, {data.dosen.nama_lengkap}.</h2>
          <p className="mt-1 text-body text-muted">NIP {data.dosen.identifier}{data.dosen.email_akademik ? ` · ${data.dosen.email_akademik}` : ""}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {statistik.map(({ label, nilai, icon: Icon }) => (
            <section key={label} className="rounded-xl border border-line bg-surface p-4 sm:p-5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-body text-muted">{label}</p>
                <Icon className="size-5 text-primary-2" aria-hidden="true" />
              </div>
              <p className="mt-2 text-title font-semibold tabular-nums text-primary">{nilai}</p>
            </section>
          ))}
        </div>

        {data.label_simulasi && (
          <p className="rounded-lg bg-warning-bg px-4 py-2 text-body font-semibold text-warning">Simulasi — bukan kebijakan resmi kampus.</p>
        )}

        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2"><Wallet className="size-5 text-primary-2" aria-hidden="true" /><h2 className="text-heading font-semibold text-primary">Ringkasan keterlambatan & denda</h2></div>
            <Link to="/dosen/keterlambatan" className="text-label font-semibold text-primary underline">Tinjau catatan</Link>
          </div>
          {data.ringkasan_denda ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg bg-page p-4"><p className="text-body text-muted">Total nominal usulan/ditetapkan</p><p className="mt-2 text-title font-semibold text-primary">{formatRupiah(data.ringkasan_denda.total_nominal)}</p></div>
              <div className="rounded-lg bg-page p-4"><p className="text-body text-muted">Keterlambatan terbuka</p><p className="mt-2 text-title font-semibold text-primary">{data.ringkasan_denda.keterlambatan_terbuka}</p></div>
              <div className="rounded-lg bg-page p-4"><p className="text-body text-muted">Keberatan ditinjau</p><p className="mt-2 text-title font-semibold text-primary">{data.ringkasan_denda.keberatan_ditinjau}</p></div>
            </div>
          ) : (
            <div className="mt-4"><EmptyState>Belum ada konfigurasi denda atau catatan pada tugas akhir bimbingan utama.</EmptyState></div>
          )}
        </section>

        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-heading font-semibold text-primary">Antrean review</h2>
              <p className="mt-1 text-body text-muted">Berkas diurutkan dari unggahan tertua. Draf Anda dapat dilanjutkan.</p>
            </div>
            <Link to="/dosen/review" className={secondaryButtonClass}>Buka semua antrean <ArrowRight className="size-4" /></Link>
          </div>
          {data.antrean_review.hasil.length === 0 ? (
            <div className="mt-4"><EmptyState>Belum ada berkas yang menunggu review dari mahasiswa bimbingan Anda.</EmptyState></div>
          ) : (
            <ul className="mt-4 space-y-3">
              {data.antrean_review.hasil.map((item) => (
                <li key={item.versi.id} className="rounded-lg border border-line p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-body font-semibold text-ink wrap-anywhere">{item.versi.nama_asli}</h3>
                      <p className="mt-1 text-body text-muted">{item.mahasiswa.nama_lengkap} · {item.mahasiswa.identifier}</p>
                      <p className="mt-1 text-label text-muted">{item.versi.milestone.urutan}. {item.versi.milestone.nama} · Versi {item.versi.nomor_versi} · {formatWaktu(item.versi.diunggah_pada)}</p>
                      <p className="mt-1 text-label text-muted">{item.versi.halaman !== null ? `${item.versi.halaman} halaman · ` : ""}{formatUkuran(item.versi.ukuran)}</p>
                    </div>
                    <StatusVersiChip status={item.versi.status} />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-body text-muted">{item.draf ? `Draf disimpan ${formatWaktu(item.draf.diubah_pada)}` : "Belum ada draf feedback Anda."}</p>
                    <Link to={`/dosen/review/${item.versi.id}`} className={secondaryButtonClass}>{item.draf ? "Lanjutkan draf" : "Buka review"}<ArrowRight className="size-4" /></Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {data.antrean_review.jumlah > data.antrean_review.hasil.length && (
            <p className="mt-3 text-label text-muted">Menampilkan {data.antrean_review.hasil.length} dari {data.antrean_review.jumlah} berkas.</p>
          )}
        </section>

        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-heading font-semibold text-primary">Perlu perhatian</h2>
              <p className="mt-1 text-body text-muted">Milestone aktif yang telah melewati target.</p>
            </div>
            <Link to="/dosen/mahasiswa?tab=terlambat" className={secondaryButtonClass}>Lihat mahasiswa <ArrowRight className="size-4" /></Link>
          </div>
          {data.perlu_perhatian.length === 0 ? (
            <div className="mt-4"><EmptyState>Tidak ada mahasiswa bimbingan dengan milestone aktif yang terlambat.</EmptyState></div>
          ) : (
            <ul className="mt-4 divide-y divide-line">
              {data.perlu_perhatian.map((item) => (
                <li key={item.tugas_akhir.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-body font-semibold text-ink">{item.mahasiswa.nama_lengkap} · {item.mahasiswa.identifier}</p>
                    <p className="text-body text-muted">{item.milestone} · Tenggat {item.target ? formatTanggal(item.target) : "Belum ditetapkan"}</p>
                    <p className="text-label text-muted">{item.tugas_akhir.judul}</p>
                    <Link to={`/dosen/mahasiswa?q=${encodeURIComponent(item.mahasiswa.identifier)}&tab=terlambat`} className="mt-2 inline-flex text-label font-semibold text-primary underline">Tinjau mahasiswa</Link>
                  </div>
                  {item.sanksi_akademik && <span className="text-label text-danger">Sanksi: {item.sanksi_akademik}</span>}
                </li>
              ))}
            </ul>
          )}
          {data.jumlah_perlu_perhatian > data.perlu_perhatian.length && <p className="mt-3 text-label text-muted">Menampilkan {data.perlu_perhatian.length} dari {data.jumlah_perlu_perhatian} mahasiswa.</p>}

          <div className="mt-6 border-t border-line pt-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-body font-semibold text-primary">Permohonan jadwal bimbingan</h3>
                <p className="mt-1 text-label text-muted">Permohonan yang menunggu keputusan Anda.</p>
              </div>
              <span className="rounded-full bg-info-bg px-3 py-1 text-label font-semibold text-info">{data.permohonan_jadwal.jumlah} menunggu</span>
            </div>
            {data.permohonan_jadwal.hasil.length === 0 ? (
              <div className="mt-3"><EmptyState>Tidak ada permohonan jadwal yang menunggu konfirmasi.</EmptyState></div>
            ) : (
              <ul className="mt-3 divide-y divide-line">
                {data.permohonan_jadwal.hasil.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="text-body font-semibold text-ink">{item.mahasiswa.nama_lengkap} · {item.mahasiswa.identifier}</p>
                      <p className="mt-1 text-body text-muted">{formatWaktu(item.mulai)} – {formatWaktu(item.selesai)}</p>
                      <p className="text-label text-muted">{item.mode_label}{item.agenda ? ` · ${item.agenda}` : ""}</p>
                    </div>
                    <button type="button" onClick={() => setJadwalDipilih(item)} className={secondaryButtonClass}>Tinjau permohonan</button>
                  </li>
                ))}
              </ul>
            )}
            {data.permohonan_jadwal.jumlah > data.permohonan_jadwal.hasil.length && <p className="mt-2 text-label text-muted">Menampilkan {data.permohonan_jadwal.hasil.length} dari {data.permohonan_jadwal.jumlah} permohonan.</p>}
          </div>
        </section>

        <div className="flex justify-end">
          <Link to="/dosen/mahasiswa" className={secondaryButtonClass}><FileText className="size-4" />Daftar mahasiswa bimbingan</Link>
        </div>
      </div>
      <JadwalKonfirmasiDrawer open={Boolean(jadwalDipilih)} permohonan={jadwalDipilih} onClose={tutupDrawerJadwal} />
    </PageFrame>
  );
}
