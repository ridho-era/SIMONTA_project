import { ApiError, kumpulkanGalat } from "./api";

/** Teks galat yang ramah pengguna dari error permintaan API. */
export function pesanDariError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 400) {
      const daftar = kumpulkanGalat(error.data);
      if (daftar.length) return daftar.join(" ");
    }
    return error.message;
  }
  return "Tidak dapat terhubung ke server. Periksa koneksi Anda.";
}