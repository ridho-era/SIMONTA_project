import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { MahasiswaBimbinganList } from "../lib/types";
import type { DashboardDosenDenganDenda, DashboardMahasiswaDenganDenda } from "../lib/keterlambatanTypes";

export const DASHBOARD_KEY = ["dashboard"] as const;

export function useDashboardMahasiswa() {
  return useQuery({
    queryKey: [...DASHBOARD_KEY, "mahasiswa"],
    queryFn: () => api<DashboardMahasiswaDenganDenda>("/mahasiswa/dashboard/"),
  });
}

export function useDashboardDosen() {
  return useQuery({
    queryKey: [...DASHBOARD_KEY, "dosen"],
    queryFn: () => api<DashboardDosenDenganDenda>("/dosen/dashboard/"),
    refetchInterval: 60 * 1000,
  });
}

export interface FilterMahasiswaBimbingan {
  q: string;
  status: string;
  milestone: string;
  tab: "semua" | "menunggu_review" | "terlambat";
  urut: "nama" | "progres" | "target" | "terbaru";
  arah: "asc" | "desc";
  halaman: number;
}

export function useMahasiswaBimbingan(filters: FilterMahasiswaBimbingan) {
  return useQuery({
    queryKey: [...DASHBOARD_KEY, "dosen-mahasiswa", filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.q.trim()) params.set("q", filters.q.trim());
      if (filters.status) params.set("status", filters.status);
      if (filters.milestone) params.set("milestone", filters.milestone);
      params.set("tab", filters.tab);
      params.set("urut", filters.urut);
      params.set("arah", filters.arah);
      params.set("halaman", String(filters.halaman));
      return api<MahasiswaBimbinganList>(`/dosen/mahasiswa/?${params.toString()}`);
    },
    placeholderData: keepPreviousData,
  });
}
