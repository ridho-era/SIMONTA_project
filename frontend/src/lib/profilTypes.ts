export interface ProgramStudiProfil {
  id: number;
  nama: string;
}

export interface DosenProfilRingkas {
  identifier: string;
  nama_lengkap: string;
  gelar: string;
  peran: string;
}

export interface ProfilData {
  id: number;
  identifier: string;
  role: "mahasiswa" | "dosen";
  nama_lengkap: string;
  gelar: string;
  email_akademik: string | null;
  telepon: string;
  program_studi: ProgramStudiProfil | null;
  punya_foto: boolean;
  foto_url: string | null;
  konteks_akademik: {
    tugas_akhir?: { id: number; judul: string; status: string } | null;
    periode?: {
      id: number;
      label: string;
      tanggal_mulai: string;
      tanggal_selesai: string;
    } | null;
    pembimbing?: DosenProfilRingkas[];
    penguji?: DosenProfilRingkas[];
    jumlah_mahasiswa_bimbingan?: number;
  };
}

export interface HalamanBantuanItem {
  id: number;
  judul: string;
  slug: string;
  ringkasan: string;
  konten: string;
  diperbarui_pada: string;
}
