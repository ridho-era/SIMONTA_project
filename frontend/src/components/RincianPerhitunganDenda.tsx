import { Calculator, Clock3, ShieldCheck, Wallet } from "lucide-react";

import { formatRupiah } from "../lib/keterlambatanTypes";
import type { CatatanKeterlambatanItem } from "../lib/keterlambatanTypes";

interface RincianPerhitunganDendaProps {
  item: CatatanKeterlambatanItem;
}

export function RincianPerhitunganDenda({ item }: RincianPerhitunganDendaProps) {
  const hariTerlambat = Math.max(0, item.hari_terlambat);
  const toleransi = Math.max(0, item.toleransi_hari);
  const hariDalamToleransi = Math.min(hariTerlambat, toleransi);
  const melewatiBatas = item.subtotal > item.batas_per_catatan;
  const dibatalkan = item.status_penilaian === "dibatalkan";

  const labelNominal = dibatalkan
    ? "Nominal pada catatan yang dibatalkan"
    : item.status_penilaian === "ditetapkan"
      ? "Nominal yang ditetapkan"
      : item.status_penilaian === "keberatan_ditinjau"
        ? "Nominal dalam peninjauan keberatan"
        : "Nominal yang diusulkan";

  return (
    <section
      aria-label="Rincian perhitungan denda"
      className="mt-4 rounded-xl border border-line bg-page p-4"
    >
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-tint p-2 text-primary" aria-hidden="true">
          <Calculator className="size-5" />
        </div>
        <div className="min-w-0">
          <h3 className="text-body font-semibold text-primary">Rincian perhitungan</h3>
          <p className="mt-1 text-label text-muted">
            Nominal dihitung dari jumlah hari yang melewati toleransi, tarif per hari, dan batas maksimal.
          </p>
        </div>
      </div>

      <ol className="mt-4 grid gap-3 md:grid-cols-2">
        <li className="rounded-lg border border-line bg-surface p-3">
          <div className="flex items-center gap-2 text-primary">
            <Clock3 className="size-4" aria-hidden="true" />
            <span className="text-label font-semibold">Langkah 1 · Hitung keterlambatan</span>
          </div>
          <p className="mt-2 text-heading font-semibold tabular-nums text-ink">
            {hariTerlambat} hari kalender
          </p>
          <p className="mt-1 text-label text-muted">
            Dihitung dari tenggat sampai tanggal realisasi, atau sampai hari ini jika belum dikumpulkan.
          </p>
        </li>

        <li className="rounded-lg border border-line bg-surface p-3">
          <div className="flex items-center gap-2 text-primary">
            <ShieldCheck className="size-4" aria-hidden="true" />
            <span className="text-label font-semibold">Langkah 2 · Terapkan toleransi</span>
          </div>
          <p className="mt-2 text-heading font-semibold tabular-nums text-ink">
            {item.hari_dikenai} hari dikenai denda
          </p>
          <p className="mt-1 text-label text-muted">
            {hariDalamToleransi} hari masuk masa toleransi ({toleransi} hari). Setelah toleransi, {item.hari_dikenai} hari menjadi dasar perhitungan.
          </p>
        </li>

        <li className="rounded-lg border border-line bg-surface p-3">
          <div className="flex items-center gap-2 text-primary">
            <Calculator className="size-4" aria-hidden="true" />
            <span className="text-label font-semibold">Langkah 3 · Kalikan dengan tarif</span>
          </div>
          <p className="mt-2 text-body font-semibold tabular-nums text-ink">
            {item.hari_dikenai} hari × {formatRupiah(item.tarif)} per hari
          </p>
          <p className="mt-1 text-label text-muted">Nominal sebelum batas: <strong className="text-ink">{formatRupiah(item.subtotal)}</strong></p>
        </li>

        <li className="rounded-lg border border-line bg-surface p-3">
          <div className="flex items-center gap-2 text-primary">
            <Wallet className="size-4" aria-hidden="true" />
            <span className="text-label font-semibold">Langkah 4 · Periksa batas maksimal</span>
          </div>
          <p className="mt-2 text-body font-semibold tabular-nums text-ink">
            Batas per catatan: {formatRupiah(item.batas_per_catatan)}
          </p>
          <p className="mt-1 text-label text-muted">
            {melewatiBatas
              ? "Nominal sebelum batas melebihi batas maksimal, sehingga nominal akhir dibatasi sesuai konfigurasi."
              : "Nominal sebelum batas tidak melebihi batas maksimal, sehingga nominal tidak perlu dikurangi."}
          </p>
        </li>
      </ol>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/20 bg-tint px-4 py-3">
        <div>
          <p className="text-label font-semibold text-primary">{labelNominal}</p>
          <p className="mt-1 text-label text-muted">Hasil perhitungan berdasarkan konfigurasi periode aktif.</p>
        </div>
        <p className="text-title font-bold tabular-nums text-primary">{formatRupiah(item.nominal)}</p>
      </div>

      <p className="mt-3 text-label text-muted">
        Informasi ini merupakan catatan perhitungan di SIMONTA, bukan tagihan atau bukti pembayaran.
        {dibatalkan ? " Catatan telah dibatalkan sehingga nominal ini hanya ditampilkan sebagai riwayat." : ""}
      </p>
    </section>
  );
}
