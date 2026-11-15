import { useEffect, useState, type FormEvent } from "react";
import { AlertTriangle, FileText, Search } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { RincianPerhitunganDenda } from "../components/RincianPerhitunganDenda";
import { PageFrame } from "../components/PageFrame";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import {
  useBuatCatatanAdministrasi,
  useDetailKeterlambatan,
  useDosenKeterlambatan,
  useKeputusanCatatan,
  useKeputusanKeberatan,
} from "../hooks/useKeterlambatan";
import { formatTanggal } from "../lib/format";
import { formatRupiah } from "../lib/keterlambatanTypes";
import type { CatatanKeterlambatanItem } from "../lib/keterlambatanTypes";

const STATUS_CHOICES = [
  { value: "usulan", label: "Usulan" },
  { value: "keberatan_ditinjau", label: "Keberatan ditinjau" },
  { value: "ditetapkan", label: "Ditetapkan" },
  { value: "dibatalkan", label: "Dibatalkan" },
];

const JENIS_CHOICES = [
  { value: "telat_revisi", label: "Telat revisi" },
  { value: "telat_berkas", label: "Telat pengumpulan berkas administrasi" },
];

function RingkasanPratinjau({ item }: { item: CatatanKeterlambatanItem }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div><dt className="text-label text-muted">Tenggat awal</dt><dd className="text-body font-semibold text-ink">{formatTanggal(item.tenggat)}</dd></div>
      <div><dt className="text-label text-muted">Tanggal realisasi</dt><dd className="text-body font-semibold text-ink">{item.realisasi ? formatTanggal(item.realisasi) : "Belum dikumpulkan · dihitung sampai hari ini"}</dd></div>
      <div><dt className="text-label text-muted">Tarif per jenis</dt><dd className="text-body font-semibold text-ink">{formatRupiah(item.tarif)}</dd></div>
      <div><dt className="text-label text-muted">Hari terlambat</dt><dd className="text-body font-semibold text-ink">{item.hari_terlambat} hari</dd></div>
      <div><dt className="text-label text-muted">Toleransi</dt><dd className="text-body font-semibold text-ink">{item.toleransi_hari} hari</dd></div>
      <div><dt className="text-label text-muted">Hari dikenai</dt><dd className="text-body font-semibold text-ink">{item.hari_dikenai} hari</dd></div>
      <div><dt className="text-label text-muted">Batas per catatan</dt><dd className="text-body font-semibold text-ink">{formatRupiah(item.batas_per_catatan)}</dd></div>
      <div><dt className="text-label text-muted">Subtotal</dt><dd className="text-body font-semibold text-ink">{formatRupiah(item.subtotal)}</dd></div>
      <div><dt className="text-label text-muted">Total nominal</dt><dd className="text-body font-semibold text-primary">{formatRupiah(item.nominal)}</dd></div>
    </dl>
  );
}

export default function DosenKeterlambatanPage() {
  const [q, setQ] = useState("");
  const [jenis, setJenis] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [catatanId, setCatatanId] = useState<number | null>(null);
  const [catatanPeninjau, setCatatanPeninjau] = useState("");
  const [jenisSanksiId, setJenisSanksiId] = useState("");
  const [pesan, setPesan] = useState("");

  const [taId, setTaId] = useState("");
  const [namaDokumen, setNamaDokumen] = useState("");
  const [tenggat, setTenggat] = useState("");
  const [realisasi, setRealisasi] = useState("");

  const daftar = useDosenKeterlambatan({ q, jenis, status: statusFilter });
  const detail = useDetailKeterlambatan(catatanId);
  const keputusanCatatan = useKeputusanCatatan();
  const keputusanKeberatan = useKeputusanKeberatan();
  const buatCatatan = useBuatCatatanAdministrasi();

  useEffect(() => {
    if (!detail.data?.catatan) return;
    setCatatanPeninjau(detail.data.catatan.catatan_peninjau ?? "");
    setJenisSanksiId(detail.data.catatan.jenis_sanksi?.id ? String(detail.data.catatan.jenis_sanksi.id) : "");
    setPesan("");
  }, [detail.data]);

  function pilihCatatan(item: CatatanKeterlambatanItem) {
    setCatatanId(item.id);
    setPesan("");
  }

  function putuskanCatatan(aksi: "konfirmasi" | "batalkan") {
    if (catatanId === null) return;
    keputusanCatatan.mutate(
      {
        catatanId,
        body: {
          aksi,
          catatan_peninjau: catatanPeninjau,
          jenis_sanksi_id: jenisSanksiId ? Number(jenisSanksiId) : null,
        },
      },
      {
        onSuccess: () => setPesan(aksi === "konfirmasi" ? "Usulan keterlambatan berhasil ditetapkan." : "Catatan keterlambatan berhasil dibatalkan."),
        onError: (error) => setPesan(error instanceof Error ? error.message : "Keputusan tidak dapat disimpan."),
      },
    );
  }

  function putuskanKeberatan(keberatanId: number, aksi: "terima" | "minta_kelengkapan") {
    keputusanKeberatan.mutate(
      { keberatanId, body: { aksi, catatan_peninjau: catatanPeninjau } },
      {
        onSuccess: () => setPesan(aksi === "terima" ? "Keberatan diterima dan catatan dibatalkan." : "Permintaan kelengkapan dikirim kepada mahasiswa."),
        onError: (error) => setPesan(error instanceof Error ? error.message : "Keputusan keberatan tidak dapat disimpan."),
      },
    );
  }

  function simpanCatatanAdministrasi(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPesan("");
    buatCatatan.mutate(
      {
        tugas_akhir_id: Number(taId),
        nama_dokumen: namaDokumen,
        tenggat,
        realisasi: realisasi || null,
      },
      {
        onSuccess: () => {
          setNamaDokumen("");
          setTenggat("");
          setRealisasi("");
          setPesan("Catatan keterlambatan berkas administrasi berhasil dibuat.");
        },
        onError: (error) => setPesan(error instanceof Error ? error.message : "Catatan manual tidak dapat dibuat."),
      },
    );
  }

  if (daftar.isLoading) {
    return <PageFrame title="Keterlambatan & denda"><p role="status" className="text-body text-muted">Memuat daftar keterlambatan…</p></PageFrame>;
  }
  if (daftar.isError || !daftar.data) {
    return (
      <PageFrame title="Keterlambatan & denda">
        <EmptyState>
          <p>Daftar keterlambatan belum dapat dimuat.</p>
          <button type="button" onClick={() => void daftar.refetch()} disabled={daftar.isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
        </EmptyState>
      </PageFrame>
    );
  }

  const labelSimulasi = daftar.data.label_simulasi || daftar.data.hasil.some((item) => item.label_simulasi);
  const itemDetail = detail.data?.catatan ?? null;
  const keberatan = itemDetail?.keberatan;

  return (
    <PageFrame title="Keterlambatan & denda" subtitle="Tinjau usulan, periksa keberatan, dan catat sanksi akademik secara terpisah.">
      <div className="space-y-6">
        {labelSimulasi && (
          <p className="rounded-lg bg-warning-bg px-4 py-3 text-body font-semibold text-warning">
            Simulasi — bukan kebijakan resmi kampus.
          </p>
        )}

        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-heading font-semibold text-primary">Filter keterlambatan</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <label className="block text-body text-muted">
              Mahasiswa / NPM
              <div className="relative mt-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
                <input value={q} onChange={(event) => setQ(event.target.value)} className={`${inputClass} pl-9`} placeholder="Cari nama atau NPM" />
              </div>
            </label>
            <label className="block text-body text-muted">
              Jenis
              <select value={jenis} onChange={(event) => setJenis(event.target.value)} className={`${inputClass} mt-1`}>
                <option value="">Semua jenis</option>
                {JENIS_CHOICES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label className="block text-body text-muted">
              Status penilaian
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className={`${inputClass} mt-1`}>
                <option value="">Semua status</option>
                {STATUS_CHOICES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
          </div>
          <p className="mt-3 text-label text-muted">Menampilkan {daftar.data.jumlah} catatan sesuai filter.</p>
        </section>

        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-heading font-semibold text-primary">Daftar catatan keterlambatan</h2>
          {daftar.data.hasil.length === 0 ? (
            <div className="mt-4"><EmptyState>Tidak ada catatan keterlambatan yang sesuai dengan filter.</EmptyState></div>
          ) : (
            <div className="mt-4 space-y-3">
              {daftar.data.hasil.map((item) => (
                <article key={item.id} className={`rounded-lg border p-4 ${catatanId === item.id ? "border-primary bg-tint/40" : "border-line"}`}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="text-body font-semibold text-ink">{item.mahasiswa.nama_lengkap} · {item.mahasiswa.identifier}</h3>
                      <p className="mt-1 text-body text-muted">{item.jenis_label} · {item.milestone || item.nama_dokumen}</p>
                      <p className="mt-1 text-label text-muted">Tenggat {formatTanggal(item.tenggat)} · Realisasi {item.realisasi ? formatTanggal(item.realisasi) : "Belum dikumpulkan"}</p>
                    </div>
                    <span className="rounded-full bg-page px-3 py-1 text-label font-semibold text-primary">{item.status_label}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-body text-muted">{item.hari_terlambat} hari terlambat · {formatRupiah(item.nominal)}</p>
                    <button type="button" onClick={() => pilihCatatan(item)} className={secondaryButtonClass}>Tinjau detail</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {catatanId !== null && (
          <section className="rounded-xl border border-line bg-surface p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-heading font-semibold text-primary">Tinjau usulan #{catatanId}</h2>
              <button type="button" onClick={() => setCatatanId(null)} className={secondaryButtonClass}>Tutup detail</button>
            </div>
            {detail.isLoading ? (
              <p role="status" className="mt-4 text-body text-muted">Memuat pratinjau perhitungan…</p>
            ) : detail.isError || !itemDetail ? (
              <p role="alert" className="mt-4 text-body text-danger">Detail catatan tidak dapat dimuat.</p>
            ) : (
              <div className="mt-4 space-y-5">
                <div>
                  <p className="text-body font-semibold text-ink">{itemDetail.mahasiswa.nama_lengkap} · {itemDetail.mahasiswa.identifier}</p>
                  <p className="mt-1 text-body text-muted">{itemDetail.tugas_akhir?.judul}</p>
                </div>
                <div>
                  <h3 className="text-body font-semibold text-primary">Pratinjau aturan</h3>
                  <div className="mt-3 rounded-lg bg-page p-4">
                    <RingkasanPratinjau item={itemDetail} />
                    <RincianPerhitunganDenda item={itemDetail} />
                  </div>
                </div>

                <div className="space-y-3">
                  <label htmlFor="catatan-peninjau" className="block text-body font-semibold text-ink">Catatan peninjau</label>
                  <textarea id="catatan-peninjau" value={catatanPeninjau} onChange={(event) => setCatatanPeninjau(event.target.value)} rows={3} className="w-full rounded-md border border-line bg-surface p-3 text-body text-ink focus:border-primary-2" />
                  <div>
                    <h3 className="text-body font-semibold text-ink">Opsi sanksi akademik (terpisah dari denda)</h3>
                    <p className="mt-1 text-label text-muted">Sanksi hanya dicatat. Sistem tidak otomatis mengubah nilai atau progres.</p>
                    <div className="mt-2 space-y-2">
                      <label className="flex items-center gap-2 text-body text-ink">
                        <input type="radio" name="jenis-sanksi" value="" checked={jenisSanksiId === ""} onChange={() => setJenisSanksiId("")} />
                        Tidak mencatat sanksi akademik
                      </label>
                      {detail.data?.jenis_sanksi.map((item) => (
                        <label key={item.id} className="flex items-center gap-2 text-body text-ink">
                          <input type="radio" name="jenis-sanksi" value={item.id} checked={jenisSanksiId === String(item.id)} onChange={() => setJenisSanksiId(String(item.id))} />
                          {item.nama}
                        </label>
                      ))}
                      {detail.data?.jenis_sanksi.length === 0 && <p className="text-label text-muted">Belum ada master jenis sanksi aktif.</p>}
                    </div>
                  </div>
                  {pesan && <p role="status" className="text-body text-primary">{pesan}</p>}
                  {keputusanCatatan.isError && <p role="alert" className="text-body text-danger">{keputusanCatatan.error.message}</p>}
                  {itemDetail.status_penilaian === "usulan" && (
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => putuskanCatatan("konfirmasi")} disabled={keputusanCatatan.isPending} className={`${primaryButtonClass} sm:w-auto`}>Konfirmasi usulan</button>
                      <button type="button" onClick={() => putuskanCatatan("batalkan")} disabled={keputusanCatatan.isPending} className={secondaryButtonClass}>Batalkan catatan</button>
                    </div>
                  )}
                  {itemDetail.status_penilaian === "ditetapkan" && <p className="text-body text-muted">Catatan sudah ditetapkan pada {itemDetail.ditinjau_pada ? formatTanggal(itemDetail.ditinjau_pada) : "waktu yang tercatat"}.</p>}
                </div>

                {keberatan && (
                  <div className="rounded-lg border border-warning/30 bg-warning-bg/40 p-4">
                    <h3 className="text-body font-semibold text-warning">Keberatan masuk · {keberatan.status_label}</h3>
                    <p className="mt-2 whitespace-pre-wrap text-body text-ink">{keberatan.alasan}</p>
                    {keberatan.bukti_url && (
                      <a href={keberatan.bukti_url} className="mt-2 inline-flex items-center gap-2 text-body font-semibold text-primary underline">
                        <FileText className="size-4" aria-hidden="true" /> Unduh bukti: {keberatan.nama_bukti}
                      </a>
                    )}
                    {keberatan.catatan_peninjau && <p className="mt-2 text-body text-muted">Catatan sebelumnya: {keberatan.catatan_peninjau}</p>}
                    {keberatan.status === "diajukan" && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button type="button" onClick={() => putuskanKeberatan(keberatan.id, "terima")} disabled={keputusanKeberatan.isPending} className={`${primaryButtonClass} sm:w-auto`}>Terima keberatan</button>
                        <button type="button" onClick={() => putuskanKeberatan(keberatan.id, "minta_kelengkapan")} disabled={keputusanKeberatan.isPending} className={secondaryButtonClass}>Minta kelengkapan</button>
                      </div>
                    )}
                    {keputusanKeberatan.isError && <p role="alert" className="mt-2 text-body text-danger">{keputusanKeberatan.error.message}</p>}
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-primary-2" aria-hidden="true" />
            <h2 className="text-heading font-semibold text-primary">Catat keterlambatan berkas administrasi</h2>
          </div>
          <p className="mt-1 text-body text-muted">Catatan manual hanya dapat dibuat untuk tugas akhir yang berada dalam penugasan utama Anda. Periode tugas akhir menentukan konfigurasi tarif.</p>
          {daftar.data.ta_options.length === 0 ? (
            <div className="mt-4"><EmptyState>Belum ada tugas akhir aktif yang dapat dikelola.</EmptyState></div>
          ) : (
            <form onSubmit={simpanCatatanAdministrasi} className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="block text-body text-muted md:col-span-2">
                Mahasiswa / tugas akhir
                <select value={taId} onChange={(event) => setTaId(event.target.value)} required className={`${inputClass} mt-1`}>
                  <option value="">Pilih tugas akhir</option>
                  {daftar.data.ta_options.map((item) => <option key={item.id} value={item.id}>{item.mahasiswa} · {item.identifier} — {item.judul}</option>)}
                </select>
              </label>
              <label className="block text-body text-muted md:col-span-2">
                Nama berkas administrasi
                <input value={namaDokumen} onChange={(event) => setNamaDokumen(event.target.value)} required maxLength={255} className={`${inputClass} mt-1`} />
              </label>
              <label className="block text-body text-muted">
                Tenggat awal
                <input type="date" value={tenggat} onChange={(event) => setTenggat(event.target.value)} required className={`${inputClass} mt-1`} />
              </label>
              <label className="block text-body text-muted">
                Tanggal realisasi (kosong bila belum dikumpulkan)
                <input type="date" value={realisasi} onChange={(event) => setRealisasi(event.target.value)} className={`${inputClass} mt-1`} />
              </label>
              <div className="md:col-span-2">
                <button type="submit" disabled={buatCatatan.isPending || !taId || !namaDokumen.trim() || !tenggat} className={`${primaryButtonClass} sm:w-auto`}>Simpan catatan manual</button>
              </div>
            </form>
          )}
          {buatCatatan.isError && <p role="alert" className="mt-3 text-body text-danger">{buatCatatan.error.message}</p>}
          {pesan && <p role="status" className="mt-3 text-body text-primary">{pesan}</p>}
        </section>
      </div>
    </PageFrame>
  );
}
