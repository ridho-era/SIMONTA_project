import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { PeriodeAktif } from "../lib/types";

export function usePeriodeAktif() {
  return useQuery({
    queryKey: ["periode-aktif"],
    queryFn: async () => (await api<{ periode: PeriodeAktif | null }>("/periode/aktif/")).periode,
  });
}