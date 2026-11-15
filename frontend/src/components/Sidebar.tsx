import { useState } from "react";
import { CircleHelp, LogOut, UserRound } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { NAV, SPACE_LABEL } from "../config/navigation";
import { usePeriodeAktif } from "../hooks/usePeriodeAktif";
import { formatRentang } from "../lib/format";

interface Props {
  open: boolean;
  onClose: () => void;
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-md px-3 py-2.5 text-body transition-colors ${
    isActive
      ? "bg-tint font-semibold text-primary shadow-[inset_3px_0_0_var(--color-gold)]"
      : "font-medium text-ink hover:bg-tint/60"
  }`;

export function Sidebar({ open, onClose }: Props) {
  const { user, logout } = useAuth();
  const periode = usePeriodeAktif();
  const [keluar, setKeluar] = useState(false);

  if (!user || user.role === "admin") return null;
  const role = user.role;

  async function onKeluar() {
    setKeluar(true);
    await logout(); // ProtectedRoute mengarahkan ke /masuk setelah sesi dibersihkan
  }

  return (
    <>
      {open && (
        <div
          aria-hidden="true"
          onClick={onClose}
          className="fixed inset-x-0 bottom-0 top-20 z-30 bg-ink/40 xl:hidden"
        />
      )}
      <aside
        id="sidebar"
        className={`fixed bottom-0 left-0 top-20 z-40 flex w-58 flex-col gap-4 overflow-y-auto border-r border-line bg-surface py-4 transition-transform duration-200 xl:sticky xl:bottom-auto xl:h-[calc(100vh-5rem)] xl:shrink-0 xl:translate-x-0 ${
          open ? "translate-x-0" : "invisible -translate-x-full xl:visible"
        }`}
      >
        <p className="px-5 text-label font-semibold tracking-wide text-muted">{SPACE_LABEL[role]}</p>

        <nav aria-label="Menu utama" className="flex flex-col gap-1 px-3">
          {NAV[role].map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={onClose} className={linkClass}>
              <Icon className="size-5 shrink-0" aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <section aria-label="Periode Tugas Akhir" className="mx-3 rounded-lg border border-line bg-page p-3">
          <p className="text-label font-semibold tracking-wide text-muted">PERIODE TUGAS AKHIR</p>
          {periode.data ? (
            <>
              <p className="mt-1 text-body font-semibold text-primary">{periode.data.label}</p>
              <p className="text-label text-muted">
                {formatRentang(periode.data.tanggal_mulai, periode.data.tanggal_selesai)}
              </p>
            </>
          ) : (
            <p className="mt-1 text-label text-muted">{periode.isLoading ? "Memuat…" : "Belum ada periode aktif"}</p>
          )}
        </section>

        <div className="mt-auto flex flex-col gap-1 border-t border-line px-3 pt-4">
          <NavLink to={`/${role}/profil`} onClick={onClose} className={linkClass}>
            <UserRound className="size-5 shrink-0" aria-hidden="true" />
            <span>Profil saya</span>
          </NavLink>
          <NavLink to={`/${role}/bantuan`} onClick={onClose} className={linkClass}>
            <CircleHelp className="size-5 shrink-0" aria-hidden="true" />
            <span>Pusat bantuan</span>
          </NavLink>
          <button
            type="button"
            onClick={onKeluar}
            disabled={keluar}
            className="flex items-center gap-3 rounded-md px-3 py-2.5 text-left text-body font-medium text-danger hover:bg-danger-bg disabled:opacity-60"
          >
            <LogOut className="size-5 shrink-0" aria-hidden="true" />
            <span>Keluar akun</span>
          </button>
          <p className="px-3 pt-2 text-label text-muted">© {new Date().getFullYear()} SIMONTA · UIN Raden Intan Lampung</p>
        </div>
      </aside>
    </>
  );
}