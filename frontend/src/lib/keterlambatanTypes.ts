import type { DashboardDosen, DashboardMahasiswa } from "./types";

export interface RingkasanDenda {
  total_nominal: number;
  keterlambatan_terbuka: number;
  keberatan_ditinjau: number;
  jumlah_catatan?: number;
  label_simulasi: boolean;
}

export type DashboardMahasiswaDenganDenda = Omit<DashboardMahasiswa, "ringkasan_denda"> & {
  ringkasan_denda: RingkasanDenda | null;
};

export type DashboardDosenDenganDenda = DashboardDosen & {
  ringkasan_denda: RingkasanDenda | null;
};

export interface AturanDenda {
  jenis: "telat_revisi" | "telat_berkas";
  jenis_label: string;
  tarif: number;
  toleransi_hari: number;
  batas_per_catatan: number;
  label_simulasi: boolean;
}

export interface KeberatanItem {
  id: number;
  alasan: string;
  nama_bukti: string;
  ukuran_bukti: number | null;
  bukti_url: string | null;
  status: "draf" | "diajukan" | "perlu_kelengkapan" | "diterima";
  status_label: string;
  catatan_peninjau: string;
  diajukan_pada: string | null;
  ditinjau_pada: string | null;
}

export interface CatatanKeterlambatanItem {
  id: number;
  tugas_akhir_id: number;
  mahasiswa: { id: number; identifier: string; nama_lengkap: string };
  jenis: "telat_revisi" | "telat_berkas";
  jenis_label: string;
  nama_dokumen: string;
  milestone: string;
  tenggat: string;
  realisasi: string | null;
  hari_terlambat: number;
  tarif: number;
  toleransi_hari: number;
  hari_dikenai: number;
  batas_per_catatan: number;
  subtotal: number;
  nominal: number;
  rumus: string;
  status_penilaian: "usulan" | "keberatan_ditinjau" | "ditetapkan" | "dibatalkan";
  status_label: string;
  label_simulasi: boolean;
  catatan_peninjau: string;
  ditinjau_oleh: string | null;
  ditinjau_pada: string | null;
  keberatan: KeberatanItem | null;
  tugas_akhir?: { id: number; judul: string; periode: string };
  review_id?: number | null;
  jenis_sanksi?: { id: number; nama: string; keterangan: string } | null;
  pratinjau?: {
    tanggal_hitung: string;
    hari_terlambat: number;
    hari_dikenai: number;
    tarif: number;
    toleransi_hari: number;
    batas_per_catatan: number;
    subtotal: number;
    nominal: number;
    rumus: string;
  };
}

export interface MahasiswaDendaPayload {
  ringkasan: RingkasanDenda | null;
  aturan: AturanDenda[];
  hasil: CatatanKeterlambatanItem[];
  kosong: boolean;
}

export interface DosenKeterlambatanPayload {
  jumlah: number;
  hasil: CatatanKeterlambatanItem[];
  ta_options: Array<{ id: number; mahasiswa: string; identifier: string; judul: string }>;
  label_simulasi: boolean;
}

export interface DosenKeterlambatanDetailPayload {
  catatan: CatatanKeterlambatanItem;
  jenis_sanksi: Array<{ id: number; nama: string }>;
}

export function formatRupiah(nilai: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(nilai);
}
