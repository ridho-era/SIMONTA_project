import { Link } from "react-router-dom";
import { ArrowRight, FileText, Loader2 } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { StatusVersiChip } from "../components/dokumen/StatusVersiChip";
import { secondaryButtonClass } from "../components/ui";
import { useReviewDosenList } from "../hooks/useReview";
import { formatWaktu } from "../lib/format";
import { formatUkuran } from "../lib/berkas";

export default function ReviewDosenListPage() {
  const { data, isLoading, isError, refetch, isFetching } = useReviewDosenList();

  let isi;
  if (isLoading) {
    isi = (
      <div role="status" className="flex items-center gap-2 text-muted">
        <Loader2 className="size-5 animate-spin" aria-hidden="true" />
        Memuat antrean review…
      </div>
    );
  } else if (isError || !data) {
    isi = (
      <EmptyState>
        <p>Antrean review tidak dapat dimuat.</p>
        <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>
          Coba lagi
        </button>
      </EmptyState>
    );
  } else if (data.jumlah === 0) {
    isi = (
      <EmptyState>
        Belum ada berkas yang menunggu review dari mahasiswa bimbingan Anda.
      </EmptyState>
    );
  } else {
    isi = (
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <section className="rounded-xl border border-line bg-surface p-4">
            <p className="text-body text-muted">Menunggu review</p>
            <p className="mt-1 text-title font-semibold text-primary">{data.jumlah_menunggu}</p>
          </section>
          <section className="rounded-xl border border-line bg-surface p-4">
            <p className="text-body text-muted">Draf tersimpan</p>
            <p className="mt-1 text-title font-semibold text-primary">{data.jumlah_draf}</p>
          </section>
        </div>

        <section aria-labelledby="judul-antrean">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 id="judul-antrean" className="text-heading font-semibold text-primary">Antrean berkas mahasiswa</h2>
              <p className="mt-1 text-body text-muted">Diurutkan dari unggahan paling lama.</p>
            </div>
            <p className="text-body text-muted">{data.jumlah} berkas</p>
          </div>

          <ul className="mt-4 space-y-3">
            {data.hasil.map((item) => (
              <li key={item.versi.id} className="rounded-xl border border-line bg-surface p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-start gap-2">
                      <FileText className="mt-0.5 size-5 shrink-0 text-primary-2" aria-hidden="true" />
                      <div className="min-w-0">
                        <h3 className="text-body font-semibold text-ink wrap-anywhere">{item.versi.nama_asli}</h3>
                        <p className="mt-1 text-body text-muted">Versi {item.versi.nomor_versi} · {item.versi.milestone.urutan}. {item.versi.milestone.nama}</p>
                      </div>
                    </div>
                  </div>
                  <StatusVersiChip status={item.versi.status} />
                </div>

                <div className="mt-3 grid gap-1 text-body text-muted sm:grid-cols-2">
                  <p>Mahasiswa: <span className="font-semibold text-ink">{item.mahasiswa.nama_lengkap}</span> · {item.mahasiswa.identifier}</p>
                  <p>Diunggah: {formatWaktu(item.versi.diunggah_pada)}</p>
                  <p>Tugas akhir: {item.tugas_akhir.judul}</p>
                  <p>{item.versi.halaman !== null ? `${item.versi.halaman} halaman · ` : ""}{formatUkuran(item.versi.ukuran)}</p>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  {item.draf ? (
                    <p className="text-body text-muted">Draf Anda terakhir disimpan {formatWaktu(item.draf.diubah_pada)}.</p>
                  ) : (
                    <p className="text-body text-muted">Belum ada draf feedback Anda untuk berkas ini.</p>
                  )}
                  <Link to={`/dosen/review/${item.versi.id}`} className={secondaryButtonClass}>
                    {item.draf ? "Lanjutkan draf" : "Buka review"}
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    );
  }

  return (
    <PageFrame title="Review dokumen" subtitle="Periksa berkas mahasiswa bimbingan dan berikan feedback.">
      {isi}
    </PageFrame>
  );
}
