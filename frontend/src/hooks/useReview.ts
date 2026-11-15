import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type {
  ChecklistRevisiItem,
  ReviewDosenDetail,
  ReviewDosenQueue,
  ReviewDraft,
  ReviewMahasiswaDetail,
  ReviewMahasiswaList,
} from "../lib/types";

export const REVIEW_KEY = ["review"] as const;

export interface ReviewDraftPayload {
  bagian: string;
  komentar: string;
  nilai: number | null;
  rekomendasi: "perlu_revisi" | "disetujui" | null;
  tenggat_revisi: string | null;
  bagikan_catatan_awal: boolean;
}

export function useReviewDosen(versiId: number | null) {
  return useQuery({
    queryKey: [...REVIEW_KEY, "dosen", versiId],
    queryFn: () => api<ReviewDosenDetail>(`/dosen/review/${versiId}/`),
    enabled: Boolean(versiId),
    // URL unduhan bertanda waktu berlaku 15 menit; segarkan sebelum kedaluwarsa.
    refetchInterval: 10 * 60 * 1000,
  });
}

export function useSimpanDrafReview(versiId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReviewDraftPayload) =>
      api<ReviewDraft>(`/dosen/review/${versiId}/draf/`, { method: "PUT", body: payload }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...REVIEW_KEY, "dosen", versiId] });
      queryClient.invalidateQueries({ queryKey: [...REVIEW_KEY, "dosen", "list"] });
    },
  });
}

export function useTerbitkanReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reviewId: number) =>
      api<{ review: ReviewDraft; sudah_terbit: boolean }>(`/dosen/review/${reviewId}/terbitkan/`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REVIEW_KEY });
      queryClient.invalidateQueries({ queryKey: ["dokumen"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useReviewDosenList() {
  return useQuery({
    queryKey: [...REVIEW_KEY, "dosen", "list"],
    queryFn: () => api<ReviewDosenQueue>("/dosen/review/"),
    refetchInterval: 60 * 1000,
  });
}

export function useReviewMahasiswa() {
  return useQuery({
    queryKey: [...REVIEW_KEY, "mahasiswa", "list"],
    queryFn: () => api<ReviewMahasiswaList>("/mahasiswa/review/"),
    refetchInterval: 10 * 60 * 1000,
  });
}

export function useReviewMahasiswaDetail(reviewId: number | null) {
  return useQuery({
    queryKey: [...REVIEW_KEY, "mahasiswa", reviewId],
    queryFn: () => api<ReviewMahasiswaDetail>(`/mahasiswa/review/${reviewId}/`),
    enabled: Boolean(reviewId),
    refetchInterval: 10 * 60 * 1000,
  });
}

export function useTambahChecklist(reviewId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (catatan: string) =>
      api<ChecklistRevisiItem>(`/mahasiswa/review/${reviewId}/checklist/`, {
        method: "POST",
        body: { catatan },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...REVIEW_KEY, "mahasiswa", reviewId] }),
  });
}

export function useUbahChecklist(reviewId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, selesai, catatan }: { id: number; selesai?: boolean; catatan?: string }) =>
      api<ChecklistRevisiItem>(`/mahasiswa/checklist/${id}/`, {
        method: "PATCH",
        body: { selesai, catatan },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...REVIEW_KEY, "mahasiswa", reviewId] }),
  });
}

export function useHapusChecklist(reviewId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/mahasiswa/checklist/${id}/`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...REVIEW_KEY, "mahasiswa", reviewId] }),
  });
}
