export type Role = "mahasiswa" | "dosen" | "admin";
export type PortalRole = Exclude<Role, "admin">;

export interface User {
  id: number;
  identifier: string;
  role: Role;
  nama_lengkap: string;
  email_akademik: string | null;
  telepon: string;
  punya_foto: boolean;
  must_change_password: boolean;
}

export interface PeriodeAktif {
  id: number;
  label: string;
  tanggal_mulai: string;
  tanggal_selesai: string;
}

export type MilestoneStatus = "disetujui" | "aktif" | "terlambat" | "terkunci" | "belum_terjadwal";

export interface MilestoneItem {
  id: number;
  urutan: number;
  nama: string;
  bobot: number;
  target: string | null;
  status: MilestoneStatus;
  tahap_aktif: boolean;
  terkunci: boolean;
  tingkat_penyelesaian: number;
  diverifikasi_pada: string | null;
}

/** Bagian milestone yang dibutuhkan drawer dosen (dipasang di F-12). */
export type MilestoneRingkas = Pick<MilestoneItem, "id" | "nama" | "bobot" | "target" | "status" | "tahap_aktif">;

export interface TimelineMahasiswa {
  tugas_akhir: { id: number; judul: string } | null;
  progres: number;
  jumlah_diverifikasi: number;
  tahap_aktif: { id: number; nama: string } | null;
  milestone: MilestoneItem[];
}

export interface AksiMilestoneResponse {
  milestone: MilestoneItem;
  progres: number;
}

export type StatusVersi = "menunggu_review" | "perlu_revisi" | "disetujui";

export interface MilestoneOpsi {
  id: number;
  urutan: number;
  nama: string;
  dapat_unggah: boolean;
  alasan: string;
}

export interface VersiDokumen {
  id: number;
  milestone: { id: number; urutan: number; nama: string };
  nomor_versi: number;
  nama_asli: string;
  halaman: number | null;
  ukuran: number;
  status: StatusVersi;
  catatan: string;
  diunggah_pada: string;
  unduh_url: string;
  pratinjau_url: string;
  review_id: number | null;
  nilai_review: number | null;
  ringkasan_feedback: string;
  review_url: string;
}

export interface RiwayatDokumen {
  jumlah: number;
  halaman: number;
  total_halaman: number;
  hasil: VersiDokumen[];
}

export interface DokumenSaya {
  tugas_akhir: { id: number; judul: string } | null;
  milestone: MilestoneOpsi[];
  riwayat: RiwayatDokumen;
  batas: { ukuran_maks_mb: number; ekstensi: string[] };
}
export type RekomendasiReview = "perlu_revisi" | "disetujui";

export interface ReviewRecord {
  id: number;
  pemberi: { nama_lengkap: string };
  bagian: string;
  komentar: string;
  nilai: number | null;
  rekomendasi: RekomendasiReview | null;
  rekomendasi_label: string | null;
  tenggat_revisi: string | null;
  diterbitkan_pada: string | null;
  versi?: {
    id: number;
    nama_asli: string;
    nomor_versi: number;
    milestone: { urutan: number; nama: string };
  };
}

export interface ReviewDraft extends Omit<ReviewRecord, "pemberi" | "rekomendasi_label" | "diterbitkan_pada"> {
  status: "draf";
  bagikan_catatan_awal: boolean;
  diubah_pada: string;
}

export interface ReviewDosenDetail {
  versi: {
    id: number;
    nama_asli: string;
    nomor_versi: number;
    halaman: number | null;
    ukuran: number;
    status: StatusVersi;
    catatan_mahasiswa: string;
    diunggah_pada: string;
    ekstensi: string;
    unduh_url: string;
    pratinjau_url: string;
    milestone: { id: number; urutan: number; nama: string };
  };
  mahasiswa: { identifier: string; nama_lengkap: string };
  tugas_akhir: { id: number; judul: string; jenis_penelitian: string };
  draf: ReviewDraft | null;
  catatan_sebelumnya: ReviewRecord[];
}

export interface ReviewMahasiswaListItem extends ReviewRecord {
  versi: {
    id: number;
    nama_asli: string;
    nomor_versi: number;
    status: StatusVersi;
    halaman: number | null;
    ukuran: number;
    unduh_url: string;
    milestone: { id: number; urutan: number; nama: string };
  };
}

export interface ReviewMenungguItem {
  versi: {
    id: number;
    nama_asli: string;
    nomor_versi: number;
    status: StatusVersi;
    halaman: number | null;
    ukuran: number;
    milestone: { id: number; urutan: number; nama: string };
  };
  catatan_awal: { bagian: string; komentar: string; label: string } | null;
}

export interface ReviewMahasiswaList {
  tugas_akhir: { id: number; judul: string } | null;
  hasil: ReviewMahasiswaListItem[];
  menunggu_review: ReviewMenungguItem[];
}

export interface ChecklistRevisiItem {
  id: number;
  catatan: string;
  selesai: boolean;
  dibuat_pada: string;
  diubah_pada: string;
}

export interface ReviewMahasiswaDetail {
  review: ReviewRecord;
  versi: {
    id: number;
    nama_asli: string;
    nomor_versi: number;
    status: StatusVersi;
    halaman: number | null;
    ukuran: number;
    ekstensi: string;
    unduh_url: string;
    pratinjau_url: string;
    milestone: { id: number; urutan: number; nama: string };
  };
  tugas_akhir: { id: number; judul: string };
  riwayat_feedback: ReviewRecord[];
  checklist: ChecklistRevisiItem[];
}

export interface ReviewDosenQueueItem {
  versi: {
    id: number;
    nama_asli: string;
    nomor_versi: number;
    halaman: number | null;
    ukuran: number;
    status: StatusVersi;
    diunggah_pada: string;
    milestone: { id: number; urutan: number; nama: string };
  };
  mahasiswa: { identifier: string; nama_lengkap: string };
  tugas_akhir: { id: number; judul: string; jenis_penelitian: string };
  draf: { id: number; diubah_pada: string } | null;
}

export interface ReviewDosenQueue {
  jumlah: number;
  jumlah_menunggu: number;
  jumlah_draf: number;
  hasil: ReviewDosenQueueItem[];
}


export type StatusMahasiswa = "menunggu_review" | "terlambat" | "berjalan" | "selesai" | "dibatalkan";

export type ModeBimbingan = "luring" | "daring";
export type StatusBimbingan = "menunggu_konfirmasi" | "disetujui" | "ditolak" | "dibatalkan" | "selesai";

export interface BimbinganItem {
  id: number;
  tugas_akhir: { id: number; judul: string };
  mahasiswa: { id: number; identifier: string; nama_lengkap: string };
  dosen: { id: number; identifier: string; nama_lengkap: string; peran: string; peran_label: string };
  mulai: string;
  selesai: string;
  mode: ModeBimbingan;
  mode_label: string;
  lokasi_atau_tautan: string;
  agenda: string;
  status: StatusBimbingan;
  status_label: string;
  menggantikan: number | null;
  alasan_penolakan: string;
  dibuat_pada: string;
}

export interface JadwalMahasiswaData {
  tugas_akhir: { id: number; judul: string; periode: string } | null;
  dosen_tujuan: Array<{ id: number; identifier: string; nama_lengkap: string; peran: string; peran_label: string }>;
  mendatang: BimbinganItem[];
  riwayat: BimbinganItem[];
}

export interface PermohonanJadwalDosen {
  jumlah: number;
  hasil: BimbinganItem[];
}

export interface DashboardMilestone extends MilestoneItem {}

export interface DashboardMahasiswa {
  mahasiswa: { id: number; identifier: string; nama_lengkap: string };
  tugas_akhir: {
    id: number;
    judul: string;
    jenis_penelitian: string;
    status: "aktif" | "selesai" | "dibatalkan";
    periode: string;
  } | null;
  progres: number;
  jumlah_diverifikasi: number;
  total_milestone: number;
  tahap_aktif: DashboardMilestone | null;
  milestone: DashboardMilestone[];
  tim_pembimbing: Array<{
    id: number;
    identifier: string;
    nama_lengkap: string;
    peran: "utama" | "pendamping";
    peran_label: string;
  }>;
  review_tindak_lanjut: {
    id: number;
    pemberi: string;
    komentar: string;
    bagian: string;
    nilai: number | null;
    tenggat_revisi: string | null;
    milestone: string;
    nama_berkas: string;
    url: string;
  } | null;
  banner_keterlambatan: {
    milestone: { id: number; nama: string };
    target: string;
    sanksi_akademik: string | null;
  } | null;
  bimbingan_terdekat: BimbinganItem | null;
  ringkasan_denda: null;
}

export interface DashboardDosen {
  dosen: { id: number; identifier: string; nama_lengkap: string; email_akademik: string | null };
  statistik: { mahasiswa_bimbingan: number; menunggu_review: number; terlambat: number };
  antrean_review: ReviewDosenQueue;
  perlu_perhatian: Array<{
    mahasiswa: { id: number; identifier: string; nama_lengkap: string };
    tugas_akhir: { id: number; judul: string; jenis_penelitian: string; status: string; periode: string };
    milestone: string;
    target: string | null;
    sanksi_akademik: string | null;
  }>;
  jumlah_perlu_perhatian: number;
  permohonan_jadwal: PermohonanJadwalDosen;
  label_simulasi: boolean;
}

export interface MahasiswaBimbinganRow {
  id: number;
  mahasiswa: { id: number; identifier: string; nama_lengkap: string };
  tugas_akhir: { id: number; judul: string; jenis_penelitian: string; status: string; periode: string };
  status: StatusMahasiswa;
  status_label: string;
  progres: number;
  jumlah_diverifikasi: number;
  total_milestone: number;
  tahap_aktif: DashboardMilestone | null;
  milestone: DashboardMilestone[];
  menunggu_review: boolean;
  versi_menunggu: { id: number; nama_asli: string; diunggah_pada: string } | null;
  pembimbing: Array<{ id: number; identifier: string; nama_lengkap: string; peran: string; peran_label: string }>;
  can_manage_milestone: boolean;
  can_review: boolean;
}

export interface MahasiswaBimbinganList {
  jumlah: number;
  jumlah_semua: number;
  jumlah_menunggu_review: number;
  jumlah_terlambat: number;
  halaman: number;
  total_halaman: number;
  per_halaman: number;
  tab: "semua" | "menunggu_review" | "terlambat";
  status_choices: Array<{ value: StatusMahasiswa; label: string }>;
  milestone_choices: Array<{ id: number; urutan: number; nama: string }>;
  hasil: MahasiswaBimbinganRow[];
}

export interface PesanLawanBicara {
  id: number;
  identifier: string;
  nama_lengkap: string;
  role: Role;
  peran: string;
  peran_label: string;
}

export interface PesanPreview {
  id: number;
  isi: string;
  nama_lampiran: string;
  pengirim_id: number;
  dibuat_pada: string;
}

export interface PercakapanItem {
  id: number;
  tugas_akhir: { id: number; judul: string };
  lawan_bicara: PesanLawanBicara;
  pesan_terakhir: PesanPreview | null;
  jumlah_belum_dibaca: number;
  diubah_pada: string;
}

export interface PesanDokumenTerkait {
  id: number;
  nama_asli: string;
  nomor_versi: number;
  milestone: string;
}

export interface PesanItem {
  id: number;
  pengirim: { id: number; nama_lengkap: string; identifier: string; role: Role };
  saya_pengirim: boolean;
  isi: string;
  nama_lampiran: string;
  lampiran_url: string;
  dokumen_versi: PesanDokumenTerkait | null;
  dibuat_pada: string;
  dibaca_pada: string | null;
}

export interface ThreadPesanData {
  percakapan: {
    id: number;
    tugas_akhir: { id: number; judul: string };
    lawan_bicara: PesanLawanBicara;
  };
  dokumen_tersedia: PesanDokumenTerkait[];
  pesan: PesanItem[];
  pesan_dibaca: Array<{ id: number; dibaca_pada: string }>;
}

export interface NotifikasiItem {
  id: number;
  jenis: string;
  jenis_label: string;
  judul: string;
  isi: string;
  tautan: string;
  dibaca_pada: string | null;
  dibuat_pada: string;
}

export interface DaftarNotifikasi {
  jumlah: number;
  jumlah_belum_dibaca: number;
  hasil: NotifikasiItem[];
}

export interface JumlahNotifikasiBelumDibaca {
  jumlah_belum_dibaca: number;
}

export interface PengaturanNotifikasiData {
  pengingat_aktif: boolean;
  h_minus_7: boolean;
  h_minus_3: boolean;
  h_minus_1: boolean;
  kanal_aplikasi: boolean;
  kanal_email: boolean;
  ringkasan_mingguan: boolean;
  dokumen_feedback_aktif: boolean;
  jadwal_bimbingan_aktif: boolean;
  jam_kirim: string;
  zona_waktu: "Asia/Jakarta";
  zona_waktu_label: string;
}

export interface PratinjauPengingatItem {
  milestone_id: number;
  milestone: string;
  mahasiswa: string;
  identifier: string;
  target: string;
  offset_hari: 7 | 3 | 1;
  jadwal_kirim: string;
  zona_waktu: string;
}

export interface PratinjauPengingatData {
  aktif: boolean;
  zona_waktu: string;
  jam_kirim: string;
  jumlah: number;
  hasil: PratinjauPengingatItem[];
}
