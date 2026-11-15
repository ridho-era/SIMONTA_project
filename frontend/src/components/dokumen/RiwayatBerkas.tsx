import { Download, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { formatUkuran } from "../../lib/berkas";
import { formatWaktu } from "../../lib/format";
import type { MilestoneOpsi, RiwayatDokumen } from "../../lib/types";
import { EmptyState } from "../EmptyState";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../ui";
import { StatusVersiChip } from "./StatusVersiChip";
import { PratinjauDokumen } from "../review/PratinjauDokumen";

interface Props {
  riwayat: RiwayatDokumen;
  milestone: MilestoneOpsi[];
  filter: number | null;
  onFilter: (id: number | null) => void;
  onHalaman: (halaman: number) => void;
  onUnggah: () => void;
}

export function RiwayatBerkas({ riwayat, milestone, filter, onFilter, onHalaman, onUnggah }: Props) {
  const [pratinjauId, setPratinjauId] = useState<number | null>(null);

  return (
    <section aria-labelledby="judul-riwayat">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id="judul-riwayat" className="text-heading font-semibold text-primary">
          Riwayat berkas diunggah
        </h2>
        <div className="w-full sm:w-72">
          <label htmlFor="filter-milestone" className="mb-1.5 block text-label font-semibold text-muted">
            Saring milestone
          </label>
          <select
            id="filter-milestone"
            value={filter ?? ""}
            onChange={(e) => onFilter(e.target.value ? Number(e.target.value) : null)}
            className={inputClass}
          >
            <option value="">Semua milestone</option>
            {milestone.map((m) => (
              <option key={m.id} value={m.id}>
                {m.urutan}. {m.nama}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4">
        {riwayat.jumlah === 0 ? (
          filter ? (
            <EmptyState>Belum ada berkas untuk milestone ini.</EmptyState>
          ) : (
            <EmptyState>
              <p>Belum ada berkas diunggah.</p>
              <button type="button" onClick={onUnggah} className={`${primaryButtonClass} mx-auto mt-4 sm:w-auto`}>
                Unggah berkas
              </button>
            </EmptyState>
          )
        ) : (
          <ul className="space-y-3">
            {riwayat.hasil.map((v) => (
              <li key={v.id} className="rounded-xl border border-line bg-surface p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-heading font-semibold text-ink wrap-anywhere">{v.nama_asli}</p>
                    <p className="text-body text-muted">
                      Versi {v.nomor_versi} · {v.milestone.urutan}. {v.milestone.nama}
                    </p>
                  </div>
                  <StatusVersiChip status={v.status} />
                </div>
                <p className="mt-2 text-body text-muted">
                  {[v.halaman !== null ? `${v.halaman} halaman` : null, formatUkuran(v.ukuran), formatWaktu(v.diunggah_pada)]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                {v.catatan && (
                  <p className="mt-2 text-body text-ink wrap:anywhere">
                    <span className="text-muted">Catatan Anda: </span>
                    {v.catatan}
                  </p>
                )}
                {v.review_id !== null && (
                  <div className="mt-3 rounded-lg bg-page p-3">
                    <p className="text-body font-semibold text-ink">
                      {v.nilai_review !== null ? `Nilai review: ${v.nilai_review}/100` : "Feedback pembimbing telah diterbitkan"}
                    </p>
                    {v.ringkasan_feedback && <p className="mt-1 line-clamp-2 text-body text-muted">{v.ringkasan_feedback}</p>}
                    <Link to={`/mahasiswa/review/${v.review_id}`} className="mt-2 inline-block text-body font-semibold text-primary underline">
                      Lihat review/catatan
                    </Link>
                  </div>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <a href={v.unduh_url} download className={secondaryButtonClass}>
                    <Download className="size-4" aria-hidden="true" />
                    Unduh
                  </a>
                  <button
                    type="button"
                    onClick={() => setPratinjauId((sebelumnya) => sebelumnya === v.id ? null : v.id)}
                    className={secondaryButtonClass}
                    aria-expanded={pratinjauId === v.id}
                  >
                    {pratinjauId === v.id ? (
                      <><EyeOff className="size-4" aria-hidden="true" />Tutup pratinjau</>
                    ) : (
                      <><Eye className="size-4" aria-hidden="true" />Lihat isi</>
                    )}
                  </button>
                </div>
                {pratinjauId === v.id && (
                  <div className="mt-4">
                    <PratinjauDokumen src={v.pratinjau_url} nama={v.nama_asli} versiId={v.id} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {riwayat.total_halaman > 1 && (
        <nav aria-label="Halaman riwayat" className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => onHalaman(riwayat.halaman - 1)}
            disabled={riwayat.halaman <= 1}
            className={`${secondaryButtonClass} disabled:cursor-not-allowed disabled:opacity-60`}
          >
            Sebelumnya
          </button>
          <p className="text-body text-muted">
            Halaman {riwayat.halaman} dari {riwayat.total_halaman} · {riwayat.jumlah} berkas
          </p>
          <button
            type="button"
            onClick={() => onHalaman(riwayat.halaman + 1)}
            disabled={riwayat.halaman >= riwayat.total_halaman}
            className={`${secondaryButtonClass} disabled:cursor-not-allowed disabled:opacity-60`}
          >
            Berikutnya
          </button>
        </nav>
      )}
    </section>
  );
}