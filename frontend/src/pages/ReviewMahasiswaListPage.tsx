import { Link } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { StatusVersiChip } from "../components/dokumen/StatusVersiChip";
import { secondaryButtonClass } from "../components/ui";
import { useReviewMahasiswa } from "../hooks/useReview";
import { formatTanggal, formatWaktu } from "../lib/format";
import { formatUkuran } from "../lib/berkas";

export default function ReviewMahasiswaListPage() {
  const { data, isLoading, isError, refetch, isFetching } = useReviewMahasiswa();

  let isi;
  if (isLoading) {
    isi = <div role="status" className="flex items-center gap-2 text-muted"><Loader2 className="size-5 animate-spin" />Memuat review…</div>;
  } else if (isError || !data) {
    isi = (
      <EmptyState>
        <p>Data review belum dapat dimuat.</p>
        <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
      </EmptyState>
    );
  } else if (!data.tugas_akhir) {
    isi = <EmptyState>Tugas akhir Anda belum didaftarkan. Review akan muncul setelah berkas diunggah dan ditinjau pembimbing.</EmptyState>;
  } else {
    isi = (
      <div className="space-y-8">
        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <p className="text-label font-semibold uppercase tracking-wide text-muted">Tugas akhir</p>
          <h2 className="mt-1 text-heading font-semibold text-primary">{data.tugas_akhir.judul}</h2>
        </section>

        <section aria-labelledby="review-menunggu">
          <h2 id="review-menunggu" className="text-heading font-semibold text-primary">Berkas menunggu review</h2>
          {data.menunggu_review.length === 0 ? (
            <EmptyState>Belum ada berkas yang menunggu review.</EmptyState>
          ) : (
            <ul className="mt-3 space-y-3">
              {data.menunggu_review.map((item) => (
                <li key={item.versi.id} className="rounded-xl border border-line bg-surface p-4 sm:p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-body font-semibold text-ink wrap-anywhere">{item.versi.nama_asli}</h3>
                      <p className="mt-1 text-body text-muted">Versi {item.versi.nomor_versi} · {item.versi.milestone.urutan}. {item.versi.milestone.nama}</p>
                      <p className="mt-1 text-label text-muted">{item.versi.halaman !== null ? `${item.versi.halaman} halaman · ` : ""}{formatUkuran(item.versi.ukuran)}</p>
                    </div>
                    <StatusVersiChip status={item.versi.status} />
                  </div>
                  {item.catatan_awal && (
                    <div className="mt-4 rounded-lg border border-warning-bg bg-warning-bg/40 p-3">
                      <p className="text-body font-semibold text-warning">{item.catatan_awal.label}</p>
                      {item.catatan_awal.bagian && <p className="mt-1 text-body text-ink">{item.catatan_awal.bagian}</p>}
                      <p className="mt-1 whitespace-pre-wrap text-body text-ink">{item.catatan_awal.komentar}</p>
                    </div>
                  )}
                  {!item.catatan_awal && <p className="mt-3 text-body text-muted">Pembimbing belum membagikan catatan awal. Feedback final akan muncul setelah diterbitkan.</p>}
                  <Link to={`/mahasiswa/dokumen?milestone=${item.versi.milestone.id}`} className={`${secondaryButtonClass} mt-3`}>
                    Lihat berkas <ArrowRight className="size-4" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="review-terbit">
          <h2 id="review-terbit" className="text-heading font-semibold text-primary">Feedback diterbitkan</h2>
          {data.hasil.length === 0 ? (
            <EmptyState>Belum ada review yang diterbitkan oleh pembimbing.</EmptyState>
          ) : (
            <ul className="mt-3 space-y-3">
              {data.hasil.map((item) => (
                <li key={item.id} className="rounded-xl border border-line bg-surface p-4 sm:p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-body font-semibold text-ink wrap-anywhere">{item.versi.nama_asli}</h3>
                      <p className="mt-1 text-body text-muted">Versi {item.versi.nomor_versi} · {item.versi.milestone.urutan}. {item.versi.milestone.nama}</p>
                      <p className="mt-1 text-label text-muted">Oleh {item.pemberi.nama_lengkap}{item.diterbitkan_pada ? ` · ${formatWaktu(item.diterbitkan_pada)}` : ""}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-label font-semibold ${item.rekomendasi === "perlu_revisi" ? "bg-warning-bg text-warning" : "bg-tint text-primary"}`}>
                      {item.rekomendasi_label ?? "Review terbit"}
                    </span>
                  </div>
                  {item.nilai !== null && <p className="mt-2 text-body font-semibold text-ink">Nilai terbit: {item.nilai}/100</p>}
                  {item.bagian && <p className="mt-2 text-body text-muted">{item.bagian}</p>}
                  <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-body text-ink">{item.komentar || "Tidak ada komentar tambahan."}</p>
                  {item.tenggat_revisi && <p className="mt-2 text-body text-muted">Tenggat revisi: {formatTanggal(item.tenggat_revisi)}</p>}
                  <Link to={`/mahasiswa/review/${item.id}`} className={`${secondaryButtonClass} mt-3`}>
                    Buka detail review <ArrowRight className="size-4" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  }

  return <PageFrame title="Review dosen" subtitle="Baca feedback yang telah diterbitkan dan susun tindak lanjut revisi.">{isi}</PageFrame>;
}