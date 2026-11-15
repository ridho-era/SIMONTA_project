import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowDownUp, Download, FileSpreadsheet, Loader2, Search, SlidersHorizontal } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { TargetDrawer } from "../components/milestone/TargetDrawer";
import { VerifikasiDrawer } from "../components/milestone/VerifikasiDrawer";
import { MilestoneStatusChip } from "../components/milestone/MilestoneStatusChip";
import { PageFrame } from "../components/PageFrame";
import { primaryButtonClass, secondaryButtonClass, inputClass } from "../components/ui";
import { useMahasiswaBimbingan, type FilterMahasiswaBimbingan } from "../hooks/useDashboard";
import { formatAngka } from "../lib/angka";
import { formatTanggal, formatWaktu } from "../lib/format";
import type { DashboardMilestone, MahasiswaBimbinganRow, StatusMahasiswa } from "../lib/types";

const TAB_LABEL: Record<FilterMahasiswaBimbingan["tab"], string> = {
  semua: "Semua",
  menunggu_review: "Menunggu Review",
  terlambat: "Terlambat",
};

function StatusMahasiswaChip({ status, label }: { status: StatusMahasiswa; label: string }) {
  const kelas: Record<StatusMahasiswa, string> = {
    menunggu_review: "bg-info-bg text-info",
    terlambat: "bg-danger-bg text-danger",
    berjalan: "bg-tint text-primary",
    selesai: "bg-surface-secondary text-muted",
    dibatalkan: "bg-danger-bg text-danger",
  };
  return <span className={`inline-flex rounded-full px-3 py-1 text-label font-semibold ${kelas[status]}`}>{label}</span>;
}

function AksiMahasiswa({
  item,
  bukaTarget,
  bukaVerifikasi,
}: {
  item: MahasiswaBimbinganRow;
  bukaTarget: (milestone: DashboardMilestone, mahasiswa: string) => void;
  bukaVerifikasi: (milestone: DashboardMilestone, mahasiswa: string) => void;
}) {
  const identitas = `${item.mahasiswa.nama_lengkap} (${item.mahasiswa.identifier})`;
  const tahap = item.tahap_aktif;

  return (
    <div className="flex flex-wrap gap-2">
      {item.versi_menunggu && (
        <Link to={`/dosen/review/${item.versi_menunggu.id}`} className={primaryButtonClass}>Review berkas</Link>
      )}
      <Link to={`/dosen/chat?mahasiswa=${item.mahasiswa.id}`} className={secondaryButtonClass}>Chat</Link>
      {item.status === "terlambat" && (
        <Link to={`/dosen/keterlambatan?mahasiswa=${item.mahasiswa.id}`} className={secondaryButtonClass}>Tinjau konsekuensi</Link>
      )}
      {item.can_manage_milestone && tahap && (
        <>
          <button type="button" onClick={() => bukaTarget(tahap, identitas)} className={secondaryButtonClass}>Tetapkan target</button>
          <button type="button" onClick={() => bukaVerifikasi(tahap, identitas)} className={secondaryButtonClass}>Verifikasi milestone</button>
        </>
      )}
      {!item.can_manage_milestone && item.can_review && (
        <span className="self-center text-label text-muted">Verifikasi dan target hanya untuk pembimbing utama.</span>
      )}
    </div>
  );
}

function KartuMahasiswa({
  item,
  bukaTarget,
  bukaVerifikasi,
}: {
  item: MahasiswaBimbinganRow;
  bukaTarget: (milestone: DashboardMilestone, mahasiswa: string) => void;
  bukaVerifikasi: (milestone: DashboardMilestone, mahasiswa: string) => void;
}) {
  const tahap = item.tahap_aktif;
  return (
    <article className="rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-heading font-semibold text-ink">{item.mahasiswa.nama_lengkap}</h3>
          <p className="text-body text-muted">NPM {item.mahasiswa.identifier}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusMahasiswaChip status={item.status} label={item.status_label} />
          <span className="text-label text-muted">Informasi sanksi belum tersedia.</span>
        </div>
      </div>

      <div className="mt-3">
        <p className="text-label font-semibold text-muted">JUDUL TUGAS AKHIR</p>
        <p className="text-body font-medium text-ink">{item.tugas_akhir.judul}</p>
        <p className="text-label text-muted">{item.tugas_akhir.periode}</p>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <div className="flex justify-between gap-2 text-body">
            <span className="text-muted">Progres</span>
            <span className="font-semibold text-ink tabular-nums">{formatAngka(item.progres)}%</span>
          </div>
          <div role="progressbar" aria-label={`Progres ${item.mahasiswa.nama_lengkap}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={item.progres} className="mt-2 h-2 overflow-hidden rounded-full bg-tint">
            <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, Math.max(0, item.progres))}%` }} />
          </div>
          <p className="mt-1 text-label text-muted">{item.jumlah_diverifikasi} dari {item.total_milestone} milestone diverifikasi</p>
        </div>
        <div>
          <p className="text-body text-muted">Tahap aktif</p>
          {tahap ? (
            <>
              <p className="text-body font-semibold text-ink">{tahap.urutan}. {tahap.nama}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2"><MilestoneStatusChip status={tahap.status} /> <span className="text-label text-muted">Target: {tahap.target ? formatTanggal(tahap.target) : "Belum ditetapkan"}</span></div>
            </>
          ) : <p className="text-body text-muted">{item.total_milestone > 0 ? "Semua milestone diverifikasi." : "Milestone belum dibuat."}</p>}
        </div>
      </div>

      {item.versi_menunggu && (
        <div className="mt-4 rounded-lg bg-info-bg/70 p-3">
          <p className="text-label font-semibold text-info">Berkas menunggu review</p>
          <p className="mt-1 text-body text-ink">{item.versi_menunggu.nama_asli}</p>
          <p className="text-label text-muted">Diunggah {formatWaktu(item.versi_menunggu.diunggah_pada)}</p>
        </div>
      )}

      <div className="mt-4">
        <AksiMahasiswa item={item} bukaTarget={bukaTarget} bukaVerifikasi={bukaVerifikasi} />
      </div>
    </article>
  );
}

export default function MahasiswaBimbinganPage() {
  const [searchParams] = useSearchParams();
  const tabAwal = searchParams.get("tab");
  const [filters, setFilters] = useState<FilterMahasiswaBimbingan>(() => ({
    q: searchParams.get("q") ?? "", status: "", milestone: "",
    tab: tabAwal === "terlambat" || tabAwal === "menunggu_review" ? tabAwal : "semua",
    urut: "nama", arah: "asc", halaman: 1,
  }));
  const { data, isLoading, isError, refetch, isFetching } = useMahasiswaBimbingan(filters);
  const [drawer, setDrawer] = useState<{ jenis: "target" | "verifikasi"; milestone: DashboardMilestone; mahasiswa: string } | null>(null);
  const [ekspor, setEkspor] = useState<"csv" | "xlsx" | null>(null);
  const [galatEkspor, setGalatEkspor] = useState<string | null>(null);

  function ubahFilter<K extends keyof FilterMahasiswaBimbingan>(field: K, value: FilterMahasiswaBimbingan[K]) {
    setFilters((lama) => ({ ...lama, [field]: value, halaman: 1 }));
  }

  async function unduh(format: "csv" | "xlsx") {
    setEkspor(format);
    setGalatEkspor(null);
    try {
      const params = new URLSearchParams();
      if (filters.q.trim()) params.set("q", filters.q.trim());
      if (filters.status) params.set("status", filters.status);
      if (filters.milestone) params.set("milestone", filters.milestone);
      params.set("tab", filters.tab);
      params.set("urut", filters.urut);
      params.set("arah", filters.arah);
      params.set("ekspor", format);
      const response = await fetch(`/api/v1/dosen/mahasiswa/?${params.toString()}`, {
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        let pesan = "Ekspor tidak dapat dibuat.";
        try {
          const body = (await response.json()) as { detail?: string };
          if (body.detail) pesan = body.detail;
        } catch { /* respons bukan JSON */ }
        throw new Error(pesan);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `mahasiswa-bimbingan.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setGalatEkspor(error instanceof Error ? error.message : "Ekspor tidak dapat dibuat.");
    } finally {
      setEkspor(null);
    }
  }

  const semua = data?.jumlah_semua ?? 0;
  const menunggu = data?.jumlah_menunggu_review ?? 0;
  const terlambat = data?.jumlah_terlambat ?? 0;

  let isi;
  if (isLoading) {
    isi = <div role="status" className="flex items-center gap-2 text-body text-muted"><Loader2 className="size-5 animate-spin" />Memuat mahasiswa bimbingan…</div>;
  } else if (isError || !data) {
    isi = <EmptyState><p>Daftar mahasiswa bimbingan belum dapat dimuat.</p><button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button></EmptyState>;
  } else if (data.jumlah === 0) {
    isi = <EmptyState>{data.jumlah_semua === 0 ? "Belum ada mahasiswa bimbingan." : "Tidak ada mahasiswa yang sesuai dengan filter saat ini."}</EmptyState>;
  } else {
    const bukaTarget = (milestone: DashboardMilestone, mahasiswa: string) => setDrawer({ jenis: "target", milestone, mahasiswa });
    const bukaVerifikasi = (milestone: DashboardMilestone, mahasiswa: string) => setDrawer({ jenis: "verifikasi", milestone, mahasiswa });

    isi = (
      <div className="space-y-4">
        <div className="hidden overflow-x-auto rounded-xl border border-line bg-surface md:block">
          <table className="w-full min-w-262.5 border-collapse text-left">
            <thead className="bg-page">
              <tr className="border-b border-line text-label font-semibold text-muted">
                <th scope="col" className="px-4 py-3">Mahasiswa / NPM</th>
                <th scope="col" className="px-4 py-3">Milestone / Target</th>
                <th scope="col" className="px-4 py-3">Progres</th>
                <th scope="col" className="px-4 py-3">Status / Sanksi</th>
                <th scope="col" className="px-4 py-3">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {data.hasil.map((item) => (
                <tr key={item.id} className="border-b border-line align-top last:border-0">
                  <td className="px-4 py-4">
                    <p className="text-body font-semibold text-ink">{item.mahasiswa.nama_lengkap}</p>
                    <p className="text-label text-muted">{item.mahasiswa.identifier}</p>
                    <p className="mt-1 max-w-xs text-label text-muted">{item.tugas_akhir.judul}</p>
                  </td>
                  <td className="px-4 py-4">
                    {item.tahap_aktif ? (
                      <>
                        <p className="text-body font-semibold text-ink">{item.tahap_aktif.urutan}. {item.tahap_aktif.nama}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2"><MilestoneStatusChip status={item.tahap_aktif.status} /><span className="text-label text-muted">{item.tahap_aktif.target ? formatTanggal(item.tahap_aktif.target) : "Belum ditetapkan"}</span></div>
                      </>
                    ) : <p className="text-body text-muted">{item.total_milestone > 0 ? "Semua milestone diverifikasi" : "Milestone belum dibuat"}</p>}
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-body font-semibold tabular-nums text-ink">{formatAngka(item.progres)}%</p>
                    <div role="progressbar" aria-label={`Progres ${item.mahasiswa.nama_lengkap}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={item.progres} className="mt-2 h-2 w-32 overflow-hidden rounded-full bg-tint">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, Math.max(0, item.progres))}%` }} />
                    </div>
                    <p className="mt-1 text-label text-muted">{item.jumlah_diverifikasi}/{item.total_milestone} milestone</p>
                  </td>
                  <td className="px-4 py-4">
                    <StatusMahasiswaChip status={item.status} label={item.status_label} />
                    <p className="mt-2 text-label text-muted">Informasi sanksi akademik belum tersedia.</p>
                  </td>
                  <td className="min-w-70 px-4 py-4">
                    <AksiMahasiswa item={item} bukaTarget={bukaTarget} bukaVerifikasi={bukaVerifikasi} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid gap-4 md:hidden">
          {data.hasil.map((item) => (
            <KartuMahasiswa key={item.id} item={item} bukaTarget={bukaTarget} bukaVerifikasi={bukaVerifikasi} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <PageFrame title="Mahasiswa bimbingan" subtitle="Cari, saring, dan pantau progres mahasiswa yang ditugaskan kepada Anda.">
      <div className="space-y-5">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Kelompok mahasiswa">
          {(["semua", "menunggu_review", "terlambat"] as const).map((tab) => {
            const total = tab === "semua" ? semua : tab === "menunggu_review" ? menunggu : terlambat;
            return (
              <button key={tab} type="button" role="tab" aria-selected={filters.tab === tab} onClick={() => ubahFilter("tab", tab)} className={`inline-flex h-10 items-center gap-2 rounded-full px-4 text-body font-semibold ${filters.tab === tab ? "bg-primary text-white" : "border border-line bg-surface text-primary hover:bg-tint"}`}>
                {TAB_LABEL[tab]} <span className="rounded-full bg-black/10 px-2 py-0.5 text-label tabular-nums">{total}</span>
              </button>
            );
          })}
        </div>

        <section className="rounded-xl border border-line bg-surface p-4 sm:p-5">
          <div className="grid gap-3 lg:grid-cols-[minmax(220px,1.4fr)_repeat(3,minmax(150px,1fr))]">
            <div>
              <label htmlFor="cari-mahasiswa" className="mb-1.5 block text-label font-semibold text-muted">Cari nama atau NPM</label>
              <div className="relative"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" /><input id="cari-mahasiswa" value={filters.q} onChange={(event) => ubahFilter("q", event.target.value)} placeholder="Nama / NPM" className={`${inputClass} pl-9`} /></div>
            </div>
            <div>
              <label htmlFor="filter-status" className="mb-1.5 block text-label font-semibold text-muted">Status</label>
              <select id="filter-status" value={filters.status} onChange={(event) => ubahFilter("status", event.target.value)} className={inputClass}>
                <option value="">Semua status</option>
                {data?.status_choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="filter-milestone" className="mb-1.5 block text-label font-semibold text-muted">Milestone</label>
              <select id="filter-milestone" value={filters.milestone} onChange={(event) => ubahFilter("milestone", event.target.value)} className={inputClass}>
                <option value="">Semua milestone</option>
                {data?.milestone_choices.map((item) => <option key={item.id} value={item.id}>{item.urutan}. {item.nama}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="urutkan" className="mb-1.5 block text-label font-semibold text-muted">Urutkan</label>
              <select id="urutkan" value={filters.urut} onChange={(event) => ubahFilter("urut", event.target.value as FilterMahasiswaBimbingan["urut"])} className={inputClass}>
                <option value="nama">Nama mahasiswa</option><option value="progres">Progres</option><option value="target">Target terdekat</option><option value="terbaru">Unggahan terbaru</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <button type="button" onClick={() => ubahFilter("arah", filters.arah === "asc" ? "desc" : "asc")} className={secondaryButtonClass}><ArrowDownUp className="size-4" />Urutan {filters.arah === "asc" ? "naik" : "turun"}</button>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => void unduh("csv")} disabled={ekspor !== null} className={secondaryButtonClass}><Download className="size-4" />{ekspor === "csv" ? "Menyiapkan CSV…" : "Ekspor CSV"}</button>
              <button type="button" onClick={() => void unduh("xlsx")} disabled={ekspor !== null} className={secondaryButtonClass}><FileSpreadsheet className="size-4" />{ekspor === "xlsx" ? "Menyiapkan XLSX…" : "Ekspor XLSX"}</button>
            </div>
          </div>
          {galatEkspor && <p role="alert" className="mt-2 text-body text-danger">{galatEkspor}</p>}
          {isFetching && !isLoading && <p role="status" className="mt-2 text-label text-muted">Memperbarui hasil…</p>}
        </section>

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2"><SlidersHorizontal className="size-4 text-muted" aria-hidden="true" /><p className="text-body text-muted">Menampilkan {data?.hasil.length ?? 0} dari {data?.jumlah ?? 0} mahasiswa</p></div>
          <p className="text-label text-muted">20 baris per halaman</p>
        </div>
        {isi}

        {data && data.total_halaman > 1 && (
          <nav aria-label="Paginasi mahasiswa bimbingan" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface p-3">
            <button type="button" onClick={() => ubahFilter("halaman", Math.max(1, filters.halaman - 1))} disabled={data.halaman <= 1 || isFetching} className={`${secondaryButtonClass} disabled:opacity-50`}>Sebelumnya</button>
            <p className="text-body text-muted">Halaman {data.halaman} dari {data.total_halaman}</p>
            <button type="button" onClick={() => ubahFilter("halaman", Math.min(data.total_halaman, filters.halaman + 1))} disabled={data.halaman >= data.total_halaman || isFetching} className={`${secondaryButtonClass} disabled:opacity-50`}>Berikutnya</button>
          </nav>
        )}
      </div>

      {drawer?.jenis === "target" && (
        <TargetDrawer open onClose={() => setDrawer(null)} milestone={drawer.milestone} mahasiswa={drawer.mahasiswa} />
      )}
      {drawer?.jenis === "verifikasi" && (
        <VerifikasiDrawer open onClose={() => setDrawer(null)} milestone={drawer.milestone} mahasiswa={drawer.mahasiswa} />
      )}
    </PageFrame>
  );
}