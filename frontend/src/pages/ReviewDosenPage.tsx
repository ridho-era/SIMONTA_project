import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, Loader2, Save, Send } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { PratinjauDokumen } from "../components/review/PratinjauDokumen";
import { StatusVersiChip } from "../components/dokumen/StatusVersiChip";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import {
  useReviewDosen,
  useSimpanDrafReview,
  useTerbitkanReview,
  type ReviewDraftPayload,
} from "../hooks/useReview";
import { formatTanggal, formatWaktu } from "../lib/format";
import { pesanDariError } from "../lib/galat";
import type { ReviewDraft } from "../lib/types";
import { formatUkuran } from "../lib/berkas";

interface FormReview {
  bagian: string;
  komentar: string;
  nilai: string;
  rekomendasi: "perlu_revisi" | "disetujui" | "";
  tenggat_revisi: string;
  bagikan_catatan_awal: boolean;
}

const FORM_KOSONG: FormReview = {
  bagian: "",
  komentar: "",
  nilai: "",
  rekomendasi: "",
  tenggat_revisi: "",
  bagikan_catatan_awal: false,
};

function muatForm(draf: ReviewDraft | null): FormReview {
  if (!draf) return FORM_KOSONG;
  return {
    bagian: draf.bagian,
    komentar: draf.komentar,
    nilai: draf.nilai === null ? "" : String(draf.nilai),
    rekomendasi: draf.rekomendasi ?? "",
    tenggat_revisi: draf.tenggat_revisi ?? "",
    bagikan_catatan_awal: draf.bagikan_catatan_awal,
  };
}

export default function ReviewDosenPage() {
  const { id = "" } = useParams();
  const parsedId = Number(id);
  const versiId = Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null;
  const { data, isLoading, isError, refetch, isFetching } = useReviewDosen(versiId);
  const simpan = useSimpanDrafReview(versiId ?? 0);
  const terbitkan = useTerbitkanReview();

  const [form, setForm] = useState<FormReview>(FORM_KOSONG);
  const [kotor, setKotor] = useState(false);
  const [menyimpan, setMenyimpan] = useState(false);
  const [mengirim, setMengirim] = useState(false);
  const [pesan, setPesan] = useState("");
  const [galat, setGalat] = useState("");

  const formRef = useRef(form);
  const kotorRef = useRef(kotor);
  const sedangSimpanRef = useRef(false);
  const versiAwalRef = useRef<number | null>(null);
  formRef.current = form;
  kotorRef.current = kotor;

  useEffect(() => {
    if (!data || versiAwalRef.current === data.versi.id) return;
    versiAwalRef.current = data.versi.id;
    const awal = muatForm(data.draf);
    setForm(awal);
    formRef.current = awal;
    setKotor(false);
    kotorRef.current = false;
    setPesan(data.draf ? `Draf terakhir disimpan ${formatWaktu(data.draf.diubah_pada)}.` : "Belum ada draf feedback untuk versi ini.");
    setGalat("");
  }, [data]);

  const simpanDraf = useCallback(async (paksa: boolean): Promise<ReviewDraft | null> => {
    if (!versiId || (!paksa && !kotorRef.current) || sedangSimpanRef.current) return null;
    sedangSimpanRef.current = true;
    setMenyimpan(true);
    setGalat("");
    const snapshot = formRef.current;
    const payload: ReviewDraftPayload = {
      bagian: snapshot.bagian,
      komentar: snapshot.komentar,
      nilai: snapshot.nilai === "" ? null : Number(snapshot.nilai),
      rekomendasi: snapshot.rekomendasi || null,
      tenggat_revisi: snapshot.tenggat_revisi || null,
      bagikan_catatan_awal: snapshot.bagikan_catatan_awal,
    };
    try {
      const hasil = await simpan.mutateAsync(payload);
      if (formRef.current === snapshot) {
        setKotor(false);
        kotorRef.current = false;
      }
      setPesan(`Draf tersimpan ${formatWaktu(hasil.diubah_pada)}.`);
      return hasil;
    } catch (error) {
      setGalat(pesanDariError(error));
      return null;
    } finally {
      sedangSimpanRef.current = false;
      setMenyimpan(false);
    }
  }, [versiId, simpan]);

  const simpanRef = useRef(simpanDraf);
  simpanRef.current = simpanDraf;

  useEffect(() => {
    const timer = window.setInterval(() => {
      void simpanRef.current(false);
    }, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  function ubah<K extends keyof FormReview>(kunci: K, nilai: FormReview[K]) {
    setForm((sebelumnya) => ({ ...sebelumnya, [kunci]: nilai }));
    setKotor(true);
    kotorRef.current = true;
    setPesan("Ada perubahan yang belum disimpan.");
    setGalat("");
  }

  async function kirimFeedback() {
    if (mengirim) return;
    setMengirim(true);
    setPesan("");
    const tersimpan = await simpanDraf(true);
    if (!tersimpan) {
      setMengirim(false);
      return;
    }
    try {
      const hasil = await terbitkan.mutateAsync(tersimpan.id);
      setForm(FORM_KOSONG);
      formRef.current = FORM_KOSONG;
      setKotor(false);
      kotorRef.current = false;
      setPesan(hasil.sudah_terbit ? "Review ini sudah pernah diterbitkan." : "Feedback berhasil diterbitkan kepada mahasiswa.");
      await refetch();
    } catch (error) {
      setGalat(pesanDariError(error));
    } finally {
      setMengirim(false);
    }
  }

  let isi;
  if (!versiId) {
    isi = <EmptyState>ID versi dokumen pada alamat halaman tidak valid.</EmptyState>;
  } else if (isLoading) {
    isi = <div role="status" className="flex items-center gap-2 text-muted"><Loader2 className="size-5 animate-spin" />Memuat berkas dan review…</div>;
  } else if (isError || !data) {
    isi = (
      <EmptyState>
        <p>Berkas tidak dapat dimuat atau Anda bukan pembimbing utama maupun pendamping untuk tugas akhir ini.</p>
        <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
      </EmptyState>
    );
  } else {
    const versi = data.versi;
    const pdf = versi.ekstensi === "pdf";
    isi = (
      <div className="space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="min-w-0">
            <p className="text-body text-muted">Mahasiswa · {data.mahasiswa.identifier}</p>
            <h2 className="mt-1 text-heading font-semibold text-primary">{data.mahasiswa.nama_lengkap}</h2>
            <p className="mt-1 text-body text-muted">{data.tugas_akhir.judul}</p>
            {data.tugas_akhir.jenis_penelitian && <p className="text-body text-muted">Jenis penelitian: {data.tugas_akhir.jenis_penelitian}</p>}
          </div>
          <Link to="/dosen/mahasiswa" className={secondaryButtonClass}>Kembali ke mahasiswa</Link>
        </div>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(360px,1fr)]">
          <div className="space-y-4">
            <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-label font-semibold uppercase tracking-wide text-muted">Berkas yang direview</p>
                  <h3 className="mt-1 text-heading font-semibold text-ink wrap-anywhere">{versi.nama_asli}</h3>
                  <p className="mt-1 text-body text-muted">Versi {versi.nomor_versi} · {versi.milestone.urutan}. {versi.milestone.nama}</p>
                </div>
                <StatusVersiChip status={versi.status} />
              </div>
              <p className="mt-2 text-body text-muted">
                {[versi.halaman !== null ? `${versi.halaman} halaman` : null, formatUkuran(versi.ukuran), formatWaktu(versi.diunggah_pada)]
                  .filter(Boolean).join(" · ")}
              </p>
              {versi.catatan_mahasiswa && <p className="mt-3 rounded-lg bg-page p-3 text-body text-ink">Catatan mahasiswa: {versi.catatan_mahasiswa}</p>}
              <a href={versi.unduh_url} download className={`${secondaryButtonClass} mt-3`}>
                <Download className="size-4" aria-hidden="true" />Unduh {pdf ? "PDF" : "DOCX"}
              </a>
            </section>
            <PratinjauDokumen
              src={versi.pratinjau_url}
              nama={versi.nama_asli}
              versiId={versi.id}
            />
          </div>

          <div className="space-y-4">
            <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-heading font-semibold text-primary">Feedback pembimbing</h3>
                <span className="rounded-full bg-info-bg px-3 py-1 text-label font-semibold text-info">Nilai draf, bukan nilai terbit</span>
              </div>
              <div className="mt-4 space-y-4">
                <div>
                  <label htmlFor="review-bagian" className="mb-1.5 block text-body font-semibold text-ink">Bagian/halaman yang direview</label>
                  <input id="review-bagian" className={inputClass} value={form.bagian} maxLength={5000} onChange={(e) => ubah("bagian", e.target.value)} placeholder="Contoh: Bab 1, halaman 3–5" />
                </div>
                <div>
                  <label htmlFor="review-komentar" className="mb-1.5 block text-body font-semibold text-ink">Komentar dan arahan</label>
                  <textarea id="review-komentar" className={`${inputClass} h-36 resize-y py-3`} value={form.komentar} maxLength={10000} onChange={(e) => ubah("komentar", e.target.value)} placeholder="Tuliskan masukan dan arahan perbaikan…" />
                  <p className="mt-1 text-label text-muted">Wajib diisi bila rekomendasi Perlu revisi.</p>
                </div>
                <div>
                  <label htmlFor="review-nilai" className="mb-1.5 block text-body font-semibold text-ink">Nilai milestone (opsional)</label>
                  <input id="review-nilai" type="number" min="0" max="100" step="1" className={inputClass} value={form.nilai} onChange={(e) => ubah("nilai", e.target.value)} placeholder="0–100" />
                </div>
                <div>
                  <label htmlFor="review-rekomendasi" className="mb-1.5 block text-body font-semibold text-ink">Rekomendasi</label>
                  <select id="review-rekomendasi" className={inputClass} value={form.rekomendasi} onChange={(e) => ubah("rekomendasi", e.target.value as FormReview["rekomendasi"])}>
                    <option value="">Pilih rekomendasi</option>
                    <option value="perlu_revisi">Perlu revisi</option>
                    <option value="disetujui">Disetujui</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="review-tenggat" className="mb-1.5 block text-body font-semibold text-ink">Tenggat revisi yang diusulkan</label>
                  <input id="review-tenggat" type="date" className={inputClass} value={form.tenggat_revisi} onChange={(e) => ubah("tenggat_revisi", e.target.value)} />
                </div>
                <label className="flex items-start gap-3 text-body text-ink">
                  <input type="checkbox" checked={form.bagikan_catatan_awal} onChange={(e) => ubah("bagikan_catatan_awal", e.target.checked)} className="mt-1 size-4 accent-primary" />
                  <span>Bagikan catatan awal kepada mahasiswa sebelum review diterbitkan. Yang dibagikan hanya bagian dan komentar, bukan nilai atau rekomendasi.</span>
                </label>
              </div>

              {galat && <p role="alert" className="mt-4 rounded-lg bg-danger-bg p-3 text-body text-danger">{galat}</p>}
              {pesan && <p role="status" className="mt-4 text-body text-muted">{pesan}</p>}

              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                <button type="button" onClick={() => void simpanDraf(true)} disabled={menyimpan || mengirim} className={secondaryButtonClass}>
                  {menyimpan ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}Simpan draf
                </button>
                <button type="button" onClick={() => void kirimFeedback()} disabled={mengirim || menyimpan} className={primaryButtonClass}>
                  {mengirim ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}Kirim feedback
                </button>
              </div>
              <p className="mt-3 text-label text-muted">Autosave berjalan setiap 30 detik saat ada perubahan. Review yang sudah terbit tidak dapat diubah; buat draf baru untuk koreksi.</p>
            </section>

            <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
              <h3 className="text-heading font-semibold text-primary">Catatan sebelumnya</h3>
              {data.catatan_sebelumnya.length === 0 ? (
                <p className="mt-3 text-body text-muted">Belum ada review yang diterbitkan untuk versi ini.</p>
              ) : (
                <ul className="mt-3 space-y-3">
                  {data.catatan_sebelumnya.map((item) => (
                    <li key={item.id} className="border-t border-line pt-3 first:border-0 first:pt-0">
                      <div className="flex flex-wrap justify-between gap-2">
                        <p className="text-body font-semibold text-ink">{item.pemberi.nama_lengkap}</p>
                        <p className="text-label text-muted">{item.diterbitkan_pada ? formatTanggal(item.diterbitkan_pada) : "—"}</p>
                      </div>
                      <p className="mt-1 text-body text-ink">{item.rekomendasi_label ?? "Feedback"}{item.nilai !== null ? ` · Nilai ${item.nilai}` : ""}</p>
                      {item.bagian && <p className="mt-1 text-body text-muted">{item.bagian}</p>}
                      <p className="mt-1 whitespace-pre-wrap text-body text-muted">{item.komentar || "Tidak ada komentar."}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      </div>
    );
  }

  return <PageFrame title="Review dokumen" subtitle="Periksa berkas mahasiswa dan terbitkan arahan pembimbing.">{isi}</PageFrame>;
}
