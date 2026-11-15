import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { MilestoneStatusChip } from "../components/milestone/MilestoneStatusChip";
import { PageFrame } from "../components/PageFrame";
import { secondaryButtonClass } from "../components/ui";
import { useTimelineSaya } from "../hooks/useMilestone";
import { formatAngka } from "../lib/angka";
import { formatTanggal } from "../lib/format";
import type { MilestoneItem, TimelineMahasiswa } from "../lib/types";

function KartuProgres({ data }: { data: TimelineMahasiswa }) {
  const persen = Math.min(Math.max(data.progres, 0), 100);
  const total = data.milestone.length;
  return (
    <section aria-labelledby="judul-progres" className="rounded-xl bg-primary p-6 text-white">
      <p id="judul-progres" className="text-label font-semibold tracking-wide text-gold-soft">
        PROGRES AKUMULASI
      </p>
      <p className="mt-1 text-title font-semibold">{formatAngka(persen)}%</p>
      <div
        role="progressbar"
        aria-label="Progres tugas akhir"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={persen}
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/20"
      >
        <div className="h-full rounded-full bg-gold" style={{ width: `${persen}%` }} />
      </div>
      <p className="mt-3 text-body">
        {data.jumlah_diverifikasi} dari {total} tahap diverifikasi ·{" "}
        {data.tahap_aktif ? `Tahap aktif: ${data.tahap_aktif.nama}` : "Seluruh tahap telah diverifikasi"}
      </p>
      {data.tugas_akhir && <p className="mt-1 text-body text-white/85">{data.tugas_akhir.judul}</p>}
      <p className="mt-3 text-label text-white/85">
        Progres hanya bertambah setelah pembimbing utama memverifikasi tahap. Riwayat unggahan tidak otomatis mengubah
        milestone.
      </p>
    </section>
  );
}

function Tahap({ m }: { m: MilestoneItem }) {
  const konteks = `?milestone=${m.id}`;
  return (
    <li
      aria-current={m.tahap_aktif ? "step" : undefined}
      className={`rounded-xl border border-line bg-surface p-4 sm:p-5 ${m.tahap_aktif ? "border-l-4 border-l-gold" : ""}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          {m.tahap_aktif && (
            <p className="mb-1 inline-flex items-center gap-1.5 text-label font-semibold text-primary">
              <span aria-hidden="true" className="size-2 rounded-full bg-gold" />
              FOKUS SAAT INI
            </p>
          )}
          <h3 className="text-heading font-semibold text-ink">
            <span className="text-muted">{m.urutan}. </span>
            {m.nama}
          </h3>
        </div>
        <MilestoneStatusChip status={m.status} />
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-body">
        <div>
          <dt className="text-label text-muted">Bobot</dt>
          <dd className="font-semibold text-ink">{formatAngka(m.bobot)}%</dd>
        </div>
        <div>
          <dt className="text-label text-muted">Tenggat</dt>
          <dd className="text-ink">{m.target ? formatTanggal(m.target) : "Belum ditetapkan"}</dd>
        </div>
        {m.diverifikasi_pada && (
          <div>
            <dt className="text-label text-muted">Diverifikasi</dt>
            <dd className="text-ink">{formatTanggal(m.diverifikasi_pada)}</dd>
          </div>
        )}
      </dl>

      {m.status === "disetujui" && (
        <Link to={`/mahasiswa/dokumen${konteks}`} className={`${secondaryButtonClass} mt-4`}>
          Lihat riwayat dokumen
        </Link>
      )}
      {m.tahap_aktif && (
        <Link to={`/mahasiswa/dokumen${konteks}`} className={`${secondaryButtonClass} mt-4`}>
          Unggah revisi
        </Link>
      )}
    </li>
  );
}

export default function MilestonePage() {
  const { data, isLoading, isError, refetch, isFetching } = useTimelineSaya();

  let isi;
  if (isLoading) {
    isi = (
      <div role="status" className="flex items-center gap-2 text-muted">
        <Loader2 className="size-5 animate-spin" aria-hidden="true" />
        Memuat milestone…
      </div>
    );
  } else if (isError || !data) {
    isi = (
      <EmptyState>
        <p>Data milestone tidak dapat dimuat.</p>
        <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>
          Coba lagi
        </button>
      </EmptyState>
    );
  } else if (!data.tugas_akhir) {
    isi = <EmptyState>Tugas akhir Anda belum didaftarkan. Hubungi admin Prodi.</EmptyState>;
  } else if (data.milestone.length === 0) {
    isi = <EmptyState>Belum ada tahapan milestone untuk tugas akhir Anda. Hubungi admin Prodi.</EmptyState>;
  } else {
    isi = (
      <div className="space-y-6">
        <KartuProgres data={data} />
        <ol className="space-y-3">
          {data.milestone.map((m) => (
            <Tahap key={m.id} m={m} />
          ))}
        </ol>
      </div>
    );
  }

  return (
    <PageFrame title="Timeline milestone" subtitle="Pantau tahapan tugas akhir dan status verifikasi dari pembimbing utama.">
      {isi}
    </PageFrame>
  );
}