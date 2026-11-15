import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "../lib/api";
import type { PortalRole, User } from "../lib/types";

export interface LoginPayload {
  identifier: string;
  password: string;
  tipe: PortalRole;
  ingat_saya: boolean;
}

interface AuthValue {
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);
const ME_KEY = ["me"] as const;

async function ambilMe(): Promise<User | null> {
  try {
    return await api<User>("/auth/me/");
  } catch (error) {
    // Belum masuk: Django (SessionAuthentication) menjawab 403 (atau 401).
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
    throw error;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ME_KEY, queryFn: ambilMe, retry: false, staleTime: 5 * 60_000 });

  const login = useCallback(
    async (payload: LoginPayload) => {
      const user = await api<User>("/auth/login/", { method: "POST", body: payload });
      queryClient.setQueryData(ME_KEY, user);
      return user;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout/", { method: "POST" });
    } catch {
      // Sesi mungkin sudah berakhir di server; tetap bersihkan keadaan di browser.
    }
    queryClient.clear();
    queryClient.setQueryData(ME_KEY, null);
  }, [queryClient]);

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ME_KEY });
  }, [queryClient]);

  const value = useMemo<AuthValue>(
    () => ({ user: me.data ?? null, isLoading: me.isLoading, login, logout, refresh }),
    [me.data, me.isLoading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth harus dipakai di dalam AuthProvider.");
  return ctx;
}