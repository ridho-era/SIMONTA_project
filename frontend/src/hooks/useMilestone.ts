import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { AksiMilestoneResponse, TimelineMahasiswa } from "../lib/types";

export const MILESTONE_KEY = ["milestone"] as const;

export function useTimelineSaya() {
  return useQuery({
    queryKey: [...MILESTONE_KEY, "saya"],
    queryFn: () => api<TimelineMahasiswa>("/mahasiswa/milestone/"),
  });
}

export function useTetapkanTarget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, target }: { id: number; target: string | null }) =>
      api<AksiMilestoneResponse>(`/dosen/milestone/${id}/target/`, { method: "PATCH", body: { target } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MILESTONE_KEY });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useVerifikasiMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, tingkat }: { id: number; tingkat: number }) =>
      api<AksiMilestoneResponse>(`/dosen/milestone/${id}/verifikasi/`, {
        method: "POST",
        body: { tingkat_penyelesaian: tingkat },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MILESTONE_KEY });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}