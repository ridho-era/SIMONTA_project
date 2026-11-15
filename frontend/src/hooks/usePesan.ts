import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { PesanItem, PercakapanItem, ThreadPesanData } from "../lib/types";

export const PESAN_KEY = ["pesan"] as const;

export function useDaftarPercakapan() {
  return useQuery({
    queryKey: [...PESAN_KEY, "daftar"],
    queryFn: () => api<PercakapanItem[]>("/pesan/"),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
}

export function useThreadPesan(percakapanId: number | null) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: [...PESAN_KEY, "thread", percakapanId],
    enabled: Boolean(percakapanId),
    queryFn: async () => {
      if (!percakapanId) throw new Error("Percakapan belum dipilih.");
      const key = [...PESAN_KEY, "thread", percakapanId] as const;
      const lama = queryClient.getQueryData<ThreadPesanData>(key);
      const after = lama?.pesan.length ? lama.pesan[lama.pesan.length - 1].id : null;
      const suffix = after ? `?after=${after}` : "";
      const baru = await api<ThreadPesanData>(`/pesan/${percakapanId}/${suffix}`);
      if (!lama) return baru;
      const gabung = new Map<number, PesanItem>();
      for (const item of lama.pesan) gabung.set(item.id, item);
      for (const item of baru.pesan) gabung.set(item.id, item);
      for (const status of baru.pesan_dibaca ?? []) {
        const sebelumnya = gabung.get(status.id);
        if (sebelumnya) gabung.set(status.id, { ...sebelumnya, dibaca_pada: status.dibaca_pada });
      }
      return { ...baru, pesan: [...gabung.values()].sort((a, b) => a.id - b.id) };
    },
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
}

export function useKirimPesan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ percakapanId, form }: { percakapanId: number; form: FormData }) =>
      api<PesanItem>(`/pesan/${percakapanId}/kirim/`, { method: "POST", body: form }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: [...PESAN_KEY, "daftar"] });
      void queryClient.invalidateQueries({ queryKey: [...PESAN_KEY, "thread", variables.percakapanId] });
    },
  });
}

export function useTandaiPesanDibaca() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (percakapanId: number) =>
      api<{ ditandai: number; dibaca_pada: string }>(`/pesan/${percakapanId}/dibaca/`, { method: "POST" }),
    onSuccess: (hasil, percakapanId) => {
      const key = [...PESAN_KEY, "thread", percakapanId] as const;
      queryClient.setQueryData<ThreadPesanData>(key, (lama) => {
        if (!lama) return lama;
        return {
          ...lama,
          pesan: lama.pesan.map((item) =>
            !item.saya_pengirim && !item.dibaca_pada
              ? { ...item, dibaca_pada: hasil.dibaca_pada }
              : item,
          ),
        };
      });
      void queryClient.invalidateQueries({ queryKey: [...PESAN_KEY, "daftar"] });
    },
  });
}
