import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, Download, Loader2, Plus, Trash2 } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { PratinjauDokumen } from "../components/review/PratinjauDokumen";
import { secondaryButtonClass, inputClass, primaryButtonClass } from "../components/ui";
import {
  useHapusChecklist,
  useReviewMahasiswaDetail,
  useTambahChecklist,
  useUbahChecklist,
} from "../hooks/useReview";
import { formatTanggal, formatWaktu, isoHariIni } from "../lib/format";
import { pesanDariError } from "../lib/galat";
import { formatUkuran } from "../lib/berkas";

export default function ReviewMahasiswaDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const parsedId = Number(id);
  const reviewId = Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null;
  const { data, isLoading, isError, refetch, isFetching } = useReviewMahasiswaDetail(reviewId);
  const tambah = useTambahChecklist(reviewId ?? 0);
  const ubah = useUbahChecklist(reviewId ?? 0);
  const hapus = useHapusChecklist(reviewId ?? 0);
  const [catatan, setCatatan] = useState("");
  const [galat, setGalat] = useState("");

  async function tambahCatatan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const teks = catatan.trim();
    if (!teks) return;
    setGalat("");
    try {
      await tambah.mutateAsync(teks);
      setCatatan("");
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  async function ubahStatus(itemId: number, selesai: boolean) {
    setGalat("");
    try {
      await ubah.mutateAsync({ id: itemId, selesai });
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  async function hapusCatatan(itemId: number) {
    setGalat("");
    try {
      await hapus.mutateAsync(itemId);
    } catch (error) {
      setGalat(pesanDariError(error));
    }
  }

  let isi;
  if (!reviewId) {
    isi = <EmptyState>ID review pada alamat halaman tidak valid.</EmptyState>;
  } else if (isLoading) {
    isi = <div role="status" className="flex items-center gap-2 text-muted"><Loader2 className="size-5 animate-spin" />Memuat detail review…</div>;
  } else if (isError || !data) {
    isi = (
      <EmptyState>
        <p>Review tidak ditemukan, belum diterbitkan, atau bukan milik tugas akhir Anda.</p>
        <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
      </EmptyState>
    );
  } else {
    const { review, versi } = data;
    const terlambat = Boolean(review.tenggat_revisi && review.tenggat_revisi < isoHariIni());
    const dokumenPdf = versi.ekstensi === "pdf";

    isi = (
      <div className="space-y-6">
        <div className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <label htmlFor="pilih-review" className="mb-1.5 block text-body font-semibold text-ink">Pilih berkas/review</label>
          <select
            id="pilih-review"
            value={String(review.id)}
            onChange={(event) => navigate(`/mahasiswa/review/${event.target.value}`)}
            className={inputClass}
          >
            <option value={review.id}>{versi.nama_asli} · versi {versi.nomor_versi} (terpilih)</option>
            {data.riwayat_feedback.map((item) => (
              <option key={item.id} value={item.id}>
                {item.versi ? `${item.versi.nama_asli} · versi ${item.versi.nomor_versi}` : `Review ${item.id}`} · {item.pemberi.nama_lengkap}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="min-w-0">
            <p className="text-label font-semibold uppercase tracking-wide text-muted">Tugas akhir</p>
            <h2 className="mt-1 text-heading font-semibold text-primary">{data.tugas_akhir.judul}</h2>
            <p className="mt-1 text-body text-muted">{versi.milestone.urutan}. {versi.milestone.nama} · Versi {versi.nomor_versi}</p>
          </div>
          <Link to="/mahasiswa/review" className={secondaryButtonClass}>Kembali ke review</Link>
        </div>

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-label font-semibold uppercase tracking-wide text-muted">Berkas</p>
              <h3 className="mt-1 text-heading font-semibold text-ink wrap-anywhere">{versi.nama_asli}</h3>
              <p className="mt-1 text-body text-muted">{versi.halaman !== null ? `${versi.halaman} halaman · ` : ""}{formatUkuran(versi.ukuran)}</p>
            </div>
            <span className="rounded-full bg-tint px-3 py-1 text-label font-semibold text-primary">Review terbit</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <a href={versi.unduh_url} download className={secondaryButtonClass}>
              <Download className="size-4" aria-hidden="true" />Unduh {dokumenPdf ? "PDF" : "DOCX"}
            </a>
            <Link to={`/mahasiswa/dokumen?milestone=${versi.milestone.id}`} className={primaryButtonClass}>
              Unggah revisi
            </Link>
          </div>
        </section>

        <PratinjauDokumen
          src={versi.pratinjau_url}
          nama={versi.nama_asli}
          versiId={versi.id}
        />

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5" aria-labelledby="judul-feedback-terbit">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 id="judul-feedback-terbit" className="text-heading font-semibold text-primary">Feedback pembimbing</h3>
              <p className="mt-1 text-body text-muted">Diterbitkan {review.diterbitkan_pada ? formatWaktu(review.diterbitkan_pada) : "—"} oleh {review.pemberi.nama_lengkap}</p>
            </div>
            <span className={`rounded-full px-3 py-1 text-label font-semibold ${review.rekomendasi === "perlu_revisi" ? "bg-warning-bg text-warning" : "bg-tint text-primary"}`}>
              {review.rekomendasi_label ?? "Review terbit"}
            </span>
          </div>
          {review.nilai !== null && <p className="mt-4 text-subtitle font-semibold text-primary">Nilai terbit: {review.nilai}/100</p>}
          {review.bagian && <div className="mt-4"><p className="text-body font-semibold text-ink">Subbab/halaman</p><p className="mt-1 text-body text-muted">{review.bagian}</p></div>}
          <div className="mt-4">
            <p className="text-body font-semibold text-ink">Arahan pembimbing</p>
            <p className="mt-1 whitespace-pre-wrap text-body text-ink">{review.komentar || "Tidak ada komentar tambahan."}</p>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-page p-3">
              <p className="text-label font-semibold text-muted">Tenggat revisi</p>
              <p className="mt-1 text-body font-semibold text-ink">{review.tenggat_revisi ? formatTanggal(review.tenggat_revisi) : "Tidak ditetapkan"}</p>
              {review.tenggat_revisi && (
                <p className={`mt-1 text-body font-semibold ${terlambat ? "text-danger" : "text-primary"}`}>
                  {terlambat ? "Terlambat" : "Belum jatuh tempo"}
                </p>
              )}
            </div>
            <div className="rounded-lg bg-page p-3">
              <p className="text-label font-semibold text-muted">Status penilaian keterlambatan</p>
              <p className="mt-1 text-body text-ink">Belum tersedia pada tahap review dokumen.</p>
              <Link to="/mahasiswa/denda" className="mt-1 inline-block text-body font-semibold text-primary underline">Lihat detail keterlambatan</Link>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5" aria-labelledby="judul-checklist">
          <div>
            <h3 id="judul-checklist" className="text-heading font-semibold text-primary">Checklist revisi pribadi</h3>
            <p className="mt-1 text-body text-muted">Catatan ini hanya milik Anda dan tidak dikirim kepada pembimbing.</p>
          </div>
          <form onSubmit={tambahCatatan} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              className={inputClass}
              value={catatan}
              onChange={(event) => setCatatan(event.target.value)}
              maxLength={1000}
              placeholder="Tambahkan hal yang perlu dikerjakan…"
              aria-label="Catatan checklist baru"
            />
            <button type="submit" disabled={!catatan.trim() || tambah.isPending} className={`${primaryButtonClass} sm:w-auto`}>
              {tambah.isPending ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}Tambah
            </button>
          </form>
          {galat && <p role="alert" className="mt-3 text-body text-danger">{galat}</p>}
          {data.checklist.length === 0 ? (
            <EmptyState>Belum ada catatan revisi pribadi.</EmptyState>
          ) : (
            <ul className="mt-4 space-y-2">
              {data.checklist.map((item) => (
                <li key={item.id} className="flex items-start gap-3 rounded-lg border border-line p-3">
                  <button
                    type="button"
                    onClick={() => void ubahStatus(item.id, !item.selesai)}
                    disabled={ubah.isPending}
                    aria-label={item.selesai ? "Tandai belum selesai" : "Tandai selesai"}
                    className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-md border ${item.selesai ? "border-primary bg-primary text-white" : "border-line bg-surface text-muted"}`}
                  >
                    {item.selesai && <Check className="size-4" aria-hidden="true" />}
                  </button>
                  <p className={`flex-1 text-body ${item.selesai ? "text-muted line-through" : "text-ink"}`}>{item.catatan}</p>
                  <button type="button" onClick={() => void hapusCatatan(item.id)} disabled={hapus.isPending} aria-label="Hapus catatan" className="grid size-8 shrink-0 place-items-center rounded-md text-muted hover:bg-danger-bg hover:text-danger">
                    <Trash2 className="size-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5" aria-labelledby="judul-riwayat-feedback">
          <h3 id="judul-riwayat-feedback" className="text-heading font-semibold text-primary">Riwayat feedback lain</h3>
          {data.riwayat_feedback.length === 0 ? (
            <p className="mt-2 text-body text-muted">Belum ada feedback terbit lainnya.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {data.riwayat_feedback.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 first:border-0 first:pt-0">
                  <div className="min-w-0">
                    <p className="text-body font-semibold text-ink">{item.rekomendasi_label ?? "Feedback"} · {item.pemberi.nama_lengkap}</p>
                    <p className="text-label text-muted">{item.diterbitkan_pada ? formatWaktu(item.diterbitkan_pada) : "—"} · {item.bagian || "Bagian tidak dicantumkan"}</p>
                  </div>
                  <Link to={`/mahasiswa/review/${item.id}`} className={secondaryButtonClass}>Buka</Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  }

  return <PageFrame title="Detail review" parent="Review dosen" subtitle="Feedback yang telah diterbitkan oleh pembimbing.">{isi}</PageFrame>;
}
