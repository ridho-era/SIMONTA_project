import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type {
  DaftarNotifikasi,
  JumlahNotifikasiBelumDibaca,
  PengaturanNotifikasiData,
  PratinjauPengingatData,
} from "../lib/types";

export const NOTIFIKASI_KEY = ["notifikasi"] as const;
export const PENGATURAN_NOTIFIKASI_KEY = ["notifikasi", "pengaturan"] as const;

export function useJumlahNotifikasiBelumDibaca() {
  return useQuery({
    queryKey: [...NOTIFIKASI_KEY, "jumlah-belum-dibaca"],
    queryFn: () => api<JumlahNotifikasiBelumDibaca>("/notifikasi/jumlah-belum-dibaca/"),
    refetchInterval: 30_000,
  });
}

export function useDaftarNotifikasi(filter: "semua" | "belum_dibaca") {
  return useQuery({
    queryKey: [...NOTIFIKASI_KEY, filter],
    queryFn: () => api<DaftarNotifikasi>(`/notifikasi/?status=${filter}`),
    refetchInterval: 30_000,
  });
}

function gunakanInvalidasiNotifikasi() {
  const client = useQueryClient();
  return () => {
    void client.invalidateQueries({ queryKey: NOTIFIKASI_KEY });
  };
}

export function useTandaiNotifikasiDibaca() {
  const invalidasi = gunakanInvalidasiNotifikasi();
  return useMutation({
    mutationFn: (id: number) => api(`/notifikasi/${id}/dibaca/`, { method: "POST" }),
    onSuccess: invalidasi,
  });
}

export function useTandaiSemuaNotifikasiDibaca() {
  const invalidasi = gunakanInvalidasiNotifikasi();
  return useMutation({
    mutationFn: () => api("/notifikasi/dibaca-semua/", { method: "POST" }),
    onSuccess: invalidasi,
  });
}

export function usePengaturanNotifikasi() {
  return useQuery({
    queryKey: PENGATURAN_NOTIFIKASI_KEY,
    queryFn: () => api<PengaturanNotifikasiData>("/notifikasi/pengaturan/"),
  });
}

export function useSimpanPengaturanNotifikasi() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<PengaturanNotifikasiData>) =>
      api<PengaturanNotifikasiData>("/notifikasi/pengaturan/", { method: "PATCH", body: payload }),
    onSuccess: (data) => {
      client.setQueryData(PENGATURAN_NOTIFIKASI_KEY, data);
      void client.invalidateQueries({ queryKey: [...NOTIFIKASI_KEY, "pratinjau"] });
    },
  });
}

export function usePulihkanDefaultNotifikasi() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<PengaturanNotifikasiData>("/notifikasi/pengaturan/pulihkan-default/", { method: "POST" }),
    onSuccess: (data) => {
      client.setQueryData(PENGATURAN_NOTIFIKASI_KEY, data);
      void client.invalidateQueries({ queryKey: [...NOTIFIKASI_KEY, "pratinjau"] });
    },
  });
}

export function usePratinjauPengingat() {
  return useMutation({
    mutationFn: () => api<PratinjauPengingatData>("/notifikasi/pratinjau-pengingat/"),
  });
}
