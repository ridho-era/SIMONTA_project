import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type {
  DosenKeterlambatanDetailPayload,
  DosenKeterlambatanPayload,
  MahasiswaDendaPayload,
} from "../lib/keterlambatanTypes";

export const KETERLAMBATAN_KEY = ["keterlambatan"] as const;

export function useMahasiswaDenda() {
  return useQuery({
    queryKey: [...KETERLAMBATAN_KEY, "mahasiswa"],
    queryFn: () => api<MahasiswaDendaPayload>("/mahasiswa/denda/"),
  });
}

export interface FilterKeterlambatanDosen {
  q: string;
  jenis: string;
  status: string;
}

export function useDosenKeterlambatan(filters: FilterKeterlambatanDosen) {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  if (filters.jenis) params.set("jenis", filters.jenis);
  if (filters.status) params.set("status", filters.status);
  const suffix = params.toString();
  return useQuery({
    queryKey: [...KETERLAMBATAN_KEY, "dosen", filters],
    queryFn: () => api<DosenKeterlambatanPayload>(`/dosen/keterlambatan/${suffix ? `?${suffix}` : ""}`),
  });
}

export function useDetailKeterlambatan(catatanId: number | null) {
  return useQuery({
    queryKey: [...KETERLAMBATAN_KEY, "detail", catatanId],
    queryFn: () => api<DosenKeterlambatanDetailPayload>(`/dosen/keterlambatan/${catatanId}/`),
    enabled: catatanId !== null,
  });
}

export function useSimpanKeberatan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ catatanId, body }: { catatanId: number; body: FormData }) =>
      api(`/mahasiswa/denda/${catatanId}/keberatan/`, { method: "POST", body }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: [...KETERLAMBATAN_KEY, "mahasiswa"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "mahasiswa"] }),
      ]);
    },
  });
}

export function useKeputusanCatatan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ catatanId, body }: { catatanId: number; body: Record<string, unknown> }) =>
      api(`/dosen/keterlambatan/${catatanId}/keputusan/`, { method: "POST", body }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: KETERLAMBATAN_KEY }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "dosen"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "mahasiswa"] }),
      ]);
    },
  });
}

export function useKeputusanKeberatan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ keberatanId, body }: { keberatanId: number; body: Record<string, unknown> }) =>
      api(`/dosen/keberatan/${keberatanId}/keputusan/`, { method: "POST", body }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: KETERLAMBATAN_KEY }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "dosen"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "mahasiswa"] }),
      ]);
    },
  });
}

export function useBuatCatatanAdministrasi() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api("/dosen/keterlambatan/administrasi/", { method: "POST", body }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: KETERLAMBATAN_KEY }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "dosen"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard", "mahasiswa"] }),
      ]);
    },
  });
}
