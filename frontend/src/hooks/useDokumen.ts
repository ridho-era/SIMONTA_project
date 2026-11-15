import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { DokumenSaya, VersiDokumen } from "../lib/types";

export const DOKUMEN_KEY = ["dokumen"] as const;

// Tautan unduh berlaku 15 menit; muat ulang berkala agar tautan di layar selalu segar.
const SEGARKAN_MS = 10 * 60 * 1000;

export function useDokumenSaya(milestoneId: number | null, halaman: number) {
  return useQuery({
    queryKey: [...DOKUMEN_KEY, "saya", milestoneId, halaman],
    queryFn: () => {
      const query = new URLSearchParams();
      if (milestoneId) query.set("milestone", String(milestoneId));
      if (halaman > 1) query.set("halaman", String(halaman));
      const teks = query.toString();
      return api<DokumenSaya>(`/mahasiswa/dokumen/${teks ? `?${teks}` : ""}`);
    },
    placeholderData: keepPreviousData,
    refetchInterval: SEGARKAN_MS,
  });
}

export function useUnggahDokumen() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api<VersiDokumen>("/mahasiswa/dokumen/", { method: "POST", body: form }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: DOKUMEN_KEY }),
  });
}