import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { BimbinganItem, JadwalMahasiswaData, ModeBimbingan, PermohonanJadwalDosen } from "../lib/types";

export const JADWAL_KEY = ["jadwal"] as const;

export interface FormJadwalPayload {
  mulai: string;
  selesai: string;
  mode: ModeBimbingan;
  lokasi_atau_tautan: string;
  agenda: string;
}

function useInvalidasiJadwal() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: JADWAL_KEY });
    void client.invalidateQueries({ queryKey: ["dashboard"] });
  };
}

export function useJadwalMahasiswa() {
  return useQuery({
    queryKey: [...JADWAL_KEY, "mahasiswa"],
    queryFn: () => api<JadwalMahasiswaData>("/mahasiswa/jadwal/"),
    refetchInterval: 60_000,
  });
}


export function usePermohonanMasukDosen(aktif = true) {
  return useQuery({
    queryKey: [...JADWAL_KEY, "permohonan-dosen"],
    queryFn: () => api<PermohonanJadwalDosen>("/dosen/jadwal/permohonan/"),
    enabled: aktif,
    staleTime: 0,
  });
}

export function useAjukanJadwal() {
  const invalidasi = useInvalidasiJadwal();
  return useMutation({
    mutationFn: (payload: FormJadwalPayload & { dosen_id: number }) =>
      api<BimbinganItem>("/mahasiswa/jadwal/", { method: "POST", body: payload }),
    onSuccess: invalidasi,
  });
}

export function useRescheduleJadwal() {
  const invalidasi = useInvalidasiJadwal();
  return useMutation({
    mutationFn: ({ id, ...payload }: FormJadwalPayload & { id: number }) =>
      api<BimbinganItem>(`/mahasiswa/jadwal/${id}/reschedule/`, { method: "POST", body: payload }),
    onSuccess: invalidasi,
  });
}

export function useSetujuiJadwal() {
  const invalidasi = useInvalidasiJadwal();
  return useMutation({
    mutationFn: ({ id, lokasi_atau_tautan }: { id: number; lokasi_atau_tautan: string }) =>
      api<BimbinganItem>(`/dosen/jadwal/${id}/setujui/`, {
        method: "POST",
        body: { lokasi_atau_tautan },
      }),
    onSuccess: invalidasi,
  });
}

export function useTolakJadwal() {
  const invalidasi = useInvalidasiJadwal();
  return useMutation({
    mutationFn: ({ id, alasan }: { id: number; alasan: string }) =>
      api<BimbinganItem>(`/dosen/jadwal/${id}/tolak/`, { method: "POST", body: { alasan } }),
    onSuccess: invalidasi,
  });
}

export function useUsulkanWaktuJadwal() {
  const invalidasi = useInvalidasiJadwal();
  return useMutation({
    mutationFn: ({ id, mulai, selesai, lokasi_atau_tautan }: {
      id: number;
      mulai: string;
      selesai: string;
      lokasi_atau_tautan?: string;
    }) => api<BimbinganItem>(`/dosen/jadwal/${id}/usulkan/`, {
      method: "POST",
      body: { mulai, selesai, ...(lokasi_atau_tautan === undefined ? {} : { lokasi_atau_tautan }) },
    }),
    onSuccess: invalidasi,
  });
}
