import { useMemo, useState } from "react";
import { AlertTriangle, FileText, Wallet } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { RincianPerhitunganDenda } from "../components/RincianPerhitunganDenda";
import { PageFrame } from "../components/PageFrame";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import { useMahasiswaDenda, useSimpanKeberatan } from "../hooks/useKeterlambatan";
import { formatTanggal } from "../lib/format";
import { formatRupiah } from "../lib/keterlambatanTypes";
import type { CatatanKeterlambatanItem } from "../lib/keterlambatanTypes";

function bolehMengajukan(item: CatatanKeterlambatanItem): boolean {
  if (item.status_penilaian === "dibatalkan") return false;
  if (!item.keberatan) return true;
  return item.keberatan.status === "draf" || item.keberatan.status === "perlu_kelengkapan";
}

export default function MahasiswaDendaPage() {
  const { data, isLoading, isError, refetch, isFetching } = useMahasiswaDenda();
  const mutation = useSimpanKeberatan();
  const [catatanDipilih, setCatatanDipilih] = useState<number | null>(null);
  const [alasan, setAlasan] = useState("");
  const [bukti, setBukti] = useState<File | null>(null);
  const [pesan, setPesan] = useState("");
  const [galatBerkas, setGalatBerkas] = useState("");

  const itemDipilih = useMemo(
    () => data?.hasil.find((item) => item.id === catatanDipilih) ?? null,
    [data, catatanDipilih],
  );

  function pilihCatatan(item: CatatanKeterlambatanItem) {
    setCatatanDipilih(item.id);
    setAlasan(item.keberatan?.alasan ?? "");
    setBukti(null);
    setPesan("");
    setGalatBerkas("");
  }

  function pilihBukti(file: File | null) {
    setGalatBerkas("");
    if (file && file.size > 5 * 1024 * 1024) {
      setBukti(null);
      setGalatBerkas("Ukuran bukti maksimal 5 MB.");
      return;
    }
    if (file && !/\.(pdf|jpg|jpeg)$/i.test(file.name)) {
      setBukti(null);
      setGalatBerkas("Bukti harus berupa PDF atau JPG/JPEG.");
      return;
    }
    setBukti(file);
  }

  function kirimKeberatan(aksi: "simpan_draf" | "ajukan") {
    if (!itemDipilih) return;
    if (!alasan.trim()) {
      setPesan("Alasan keberatan wajib diisi.");
      return;
    }
    if (galatBerkas) return;
    const body = new FormData();
    body.append("alasan", alasan.trim());
    body.append("aksi", aksi);
    if (bukti) body.append("bukti", bukti);
    setPesan("");
    mutation.mutate(
      { catatanId: itemDipilih.id, body },
      {
        onSuccess: () => {
          setPesan(aksi === "ajukan" ? "Keberatan berhasil diajukan untuk ditinjau." : "Draf keberatan berhasil disimpan.");
          setBukti(null);
          void refetch();
        },
        onError: (error) => setPesan(error instanceof Error ? error.message : "Keberatan tidak dapat disimpan."),
      },
    );
  }

  if (isLoading) {
    return <PageFrame title="Denda & keterlambatan"><p role="status" className="text-body text-muted">Memuat catatan keterlambatan…</p></PageFrame>;
  }
  if (isError || !data) {
    return (
      <PageFrame title="Denda & keterlambatan">
        <EmptyState>
          <p>Informasi keterlambatan belum dapat dimuat.</p>
          <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>Coba lagi</button>
        </EmptyState>
      </PageFrame>
    );
  }

  const ringkasan = data.ringkasan;
  const labelSimulasi = data.aturan.some((aturan) => aturan.label_simulasi) || data.hasil.some((item) => item.label_simulasi);

  return (
    <PageFrame title="Denda & keterlambatan" subtitle="Lihat perhitungan keterlambatan dan ajukan keberatan bila diperlukan.">
      <div className="space-y-6">
        {labelSimulasi && (
          <p className="rounded-lg bg-warning-bg px-4 py-3 text-body font-semibold text-warning">
            Simulasi — bukan kebijakan resmi kampus.
          </p>
        )}

        <section className="grid gap-3 sm:grid-cols-3" aria-label="Ringkasan denda">
          <div className="rounded-xl border border-line bg-surface p-4">
            <p className="text-body text-muted">Total nominal</p>
            <p className="mt-2 text-title font-semibold tabular-nums text-primary">{formatRupiah(ringkasan?.total_nominal ?? 0)}</p>
          </div>
          <div className="rounded-xl border border-line bg-surface p-4">
            <p className="text-body text-muted">Keterlambatan terbuka</p>
            <p className="mt-2 text-title font-semibold tabular-nums text-primary">{ringkasan?.keterlambatan_terbuka ?? 0}</p>
          </div>
          <div className="rounded-xl border border-line bg-surface p-4">
            <p className="text-body text-muted">Keberatan ditinjau</p>
            <p className="mt-2 text-title font-semibold tabular-nums text-primary">{ringkasan?.keberatan_ditinjau ?? 0}</p>
          </div>
        </section>

        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex items-center gap-2">
            <Wallet className="size-5 text-primary-2" aria-hidden="true" />
            <h2 className="text-heading font-semibold text-primary">Catatan keterlambatan</h2>
          </div>
          {data.hasil.length === 0 ? (
            <div className="mt-4">
              <EmptyState>
                <p>Tidak ada catatan keterlambatan.</p>
                <p className="mt-1 font-semibold text-primary">Total {formatRupiah(0)}</p>
              </EmptyState>
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {data.hasil.map((item) => (
                <article key={item.id} className="rounded-lg border border-line p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-body font-semibold text-ink">{item.jenis_label}</h3>
                      <p className="mt-1 text-body text-muted">{item.milestone || item.nama_dokumen || "Berkas administrasi"}</p>
                    </div>
                    <span className="rounded-full bg-tint px-3 py-1 text-label font-semibold text-primary">{item.status_label}</span>
                  </div>
                  <dl className="mt-4 grid gap-x-5 gap-y-3 text-body sm:grid-cols-2 lg:grid-cols-3">
                    <div><dt className="text-muted">Tenggat awal</dt><dd className="font-semibold text-ink">{formatTanggal(item.tenggat)}</dd></div>
                    <div><dt className="text-muted">Tanggal realisasi</dt><dd className="font-semibold text-ink">{item.realisasi ? formatTanggal(item.realisasi) : "Belum dikumpulkan · dihitung sampai hari ini"}</dd></div>
                    <div><dt className="text-muted">Hari terlambat</dt><dd className="font-semibold text-ink">{item.hari_terlambat} hari</dd></div>
                    <div><dt className="text-muted">Tarif per hari</dt><dd className="font-semibold text-ink">{formatRupiah(item.tarif)}</dd></div>
                    <div><dt className="text-muted">Hari dikenai</dt><dd className="font-semibold text-ink">{item.hari_dikenai} hari · toleransi {item.toleransi_hari} hari</dd></div>
                    <div><dt className="text-muted">Batas per catatan</dt><dd className="font-semibold text-ink">{formatRupiah(item.batas_per_catatan)}</dd></div>
                  </dl>
                  <RincianPerhitunganDenda item={item} />
                  {item.keberatan && (
                    <div className="mt-3 rounded-md bg-warning-bg/60 p-3 text-body">
                      <p className="font-semibold text-warning">Keberatan: {item.keberatan.status_label}</p>
                      <p className="mt-1 whitespace-pre-wrap text-ink">{item.keberatan.alasan}</p>
                      {item.keberatan.bukti_url && (
                        <a href={item.keberatan.bukti_url} className="mt-2 inline-flex items-center gap-2 font-semibold text-primary underline">
                          <FileText className="size-4" aria-hidden="true" /> Unduh {item.keberatan.nama_bukti || "bukti"}
                        </a>
                      )}
                      {item.keberatan.catatan_peninjau && <p className="mt-2 text-muted">Catatan peninjau: {item.keberatan.catatan_peninjau}</p>}
                    </div>
                  )}
                  {bolehMengajukan(item) && (
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-label text-muted">Anda dapat menyimpan draf atau mengajukan satu keberatan untuk catatan ini.</p>
                      <button type="button" onClick={() => pilihCatatan(item)} className={secondaryButtonClass}>
                        {item.keberatan ? "Lengkapi keberatan" : "Ajukan keberatan"}
                      </button>
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-heading font-semibold text-primary">Aturan perhitungan</h2>
          {data.aturan.length === 0 ? (
            <div className="mt-4"><EmptyState>Konfigurasi denda untuk periode tugas akhir belum tersedia.</EmptyState></div>
          ) : (
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {data.aturan.map((aturan) => (
                <div key={aturan.jenis} className="rounded-lg bg-page p-4">
                  <h3 className="text-body font-semibold text-ink">{aturan.jenis_label}</h3>
                  <p className="mt-2 text-body text-muted">Tarif: <strong className="text-ink">{formatRupiah(aturan.tarif)}</strong> per hari.</p>
                  <p className="text-body text-muted">Toleransi: <strong className="text-ink">{aturan.toleransi_hari} hari</strong>.</p>
                  <p className="text-body text-muted">Batas per catatan: <strong className="text-ink">{formatRupiah(aturan.batas_per_catatan)}</strong>.</p>
                </div>
              ))}
            </div>
          )}
          <p className="mt-4 text-body text-muted">Hari terlambat = hari kalender antara tenggat dan realisasi, atau hari ini bila belum dikumpulkan. Hari dikenai = maksimum (hari terlambat − toleransi, 0). Nominal = minimum (hari dikenai × tarif, batas per catatan).</p>
          <p className="mt-2 text-label text-muted">SIMONTA tidak memproses pembayaran atau penagihan denda.</p>
        </section>

        {itemDipilih && (
          <section className="rounded-xl border border-primary/30 bg-surface p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
              <div>
                <h2 className="text-heading font-semibold text-primary">Pengajuan keberatan</h2>
                <p className="mt-1 text-body text-muted">Catatan #{itemDipilih.id} · {itemDipilih.jenis_label}. Mengajukan keberatan tidak berarti keberatan disetujui.</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <label className="block text-body font-semibold text-ink" htmlFor="alasan-keberatan">Alasan keberatan</label>
              <textarea
                id="alasan-keberatan"
                value={alasan}
                onChange={(event) => setAlasan(event.target.value)}
                rows={4}
                maxLength={10000}
                className="w-full rounded-md border border-line bg-surface p-3 text-body text-ink focus:border-primary-2"
                placeholder="Jelaskan alasan keberatan Anda."
              />
              <label className="block text-body font-semibold text-ink" htmlFor="bukti-keberatan">Bukti pendukung (PDF/JPG, maksimal 5 MB)</label>
              <input
                id="bukti-keberatan"
                type="file"
                accept=".pdf,.jpg,.jpeg,application/pdf,image/jpeg"
                onChange={(event) => pilihBukti(event.target.files?.[0] ?? null)}
                className={`${inputClass} h-auto py-2`}
              />
              {bukti && <p className="text-label text-muted">Berkas dipilih: {bukti.name}</p>}
              {galatBerkas && <p role="alert" className="text-body text-danger">{galatBerkas}</p>}
              {pesan && <p role="status" className="text-body text-primary">{pesan}</p>}
              {mutation.isError && <p role="alert" className="text-body text-danger">{mutation.error.message}</p>}
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => kirimKeberatan("simpan_draf")} disabled={mutation.isPending || Boolean(galatBerkas)} className={secondaryButtonClass}>Simpan draf</button>
                <button type="button" onClick={() => kirimKeberatan("ajukan")} disabled={mutation.isPending || Boolean(galatBerkas)} className={`${primaryButtonClass} sm:w-auto`}>Ajukan keberatan</button>
                <button type="button" onClick={() => setCatatanDipilih(null)} className={secondaryButtonClass}>Tutup</button>
              </div>
            </div>
          </section>
        )}
      </div>
    </PageFrame>
  );
}
