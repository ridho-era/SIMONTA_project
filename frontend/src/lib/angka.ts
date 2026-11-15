/** Angka berformat Indonesia, maksimal 2 desimal (mis. 12,5). */
export function formatAngka(nilai: number): string {
  return nilai.toLocaleString("id-ID", { maximumFractionDigits: 2 });
}