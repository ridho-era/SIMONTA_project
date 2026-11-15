const ZONA = "Asia/Jakarta";

const pemformat = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: ZONA,
});

const pemformatWaktu = new Intl.DateTimeFormat("id-ID", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: ZONA,
});

/** Format "13 Nov 2026" (PRD bagian 8). Menerima tanggal ISO atau objek Date. */
export function formatTanggal(nilai: string | Date): string {
  return pemformat.format(typeof nilai === "string" ? new Date(nilai) : nilai);
}

/** Format tanggal dan jam 24 jam WIB, mis. "13 Nov 2026 19.31 WIB". */
export function formatWaktu(iso: string): string {
  return `${pemformatWaktu.format(new Date(iso))} WIB`;
}

export function formatRentang(mulai: string, selesai: string): string {
  return `${formatTanggal(mulai)} – ${formatTanggal(selesai)}`;
}

/** Tanggal hari ini (WIB) sebagai YYYY-MM-DD untuk atribut <time>. */
export function isoHariIni(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: ZONA });
}

export function inisial(nama: string): string {
  const bagian = nama.trim().split(/\s+/).filter(Boolean);
  return (bagian.slice(0, 2).map((b) => b[0]).join("") || "?").toUpperCase();
}