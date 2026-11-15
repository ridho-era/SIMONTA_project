import { Bell, GraduationCap, Menu } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { homePath, ROLE_LABEL } from "../config/navigation";
import { usePeriodeAktif } from "../hooks/usePeriodeAktif";
import { useJumlahNotifikasiBelumDibaca } from "../hooks/useNotifikasi";
import { inisial } from "../lib/format";

interface Props {
  onMenu: () => void;
  menuOpen: boolean;
}

export function Header({ onMenu, menuOpen }: Props) {
  const { user } = useAuth();
  const periode = usePeriodeAktif();
  const unread = useJumlahNotifikasiBelumDibaca();

  if (!user || user.role === "admin") return null;
  const role = user.role;
  const teksPeriode = periode.data ? periode.data.label : periode.isLoading ? "Memuat periode…" : "Periode belum diatur";

  return (
    <header className="sticky top-0 z-50 flex h-20 items-center gap-3 border-b border-line bg-surface px-4 md:px-6">
      <button
        type="button"
        onClick={onMenu}
        aria-label="Menu navigasi"
        aria-expanded={menuOpen}
        aria-controls="sidebar"
        className="grid size-10 shrink-0 place-items-center rounded-md border border-line text-primary xl:hidden"
      >
        <Menu className="size-5" aria-hidden="true" />
      </button>

      <Link to={homePath(role)} className="flex min-w-0 items-center gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-lg bg-primary text-white">
          <GraduationCap className="size-6" aria-hidden="true" />
        </span>
        <span className="min-w-0 leading-tight">
          <span className="block text-heading font-semibold text-primary">SIMONTA</span>
          <span className="hidden truncate text-label font-medium tracking-wide text-muted sm:block">
            UIN RADEN INTAN LAMPUNG • SISTEM INFORMASI
          </span>
        </span>
      </Link>

      <div className="ml-auto flex items-center gap-3">
        <span
          title="Periode akademik aktif"
          className="hidden max-w-56 truncate rounded-full bg-tint px-3 py-1.5 text-label font-semibold text-primary md:inline-block"
        >
          {teksPeriode}
        </span>

        <Link
          to={`/${role}/notifikasi`}
          aria-label={unread.data?.jumlah_belum_dibaca ? `Notifikasi, ${unread.data.jumlah_belum_dibaca} belum dibaca` : "Notifikasi"}
          className="relative grid size-10 place-items-center rounded-full border border-line text-ink hover:bg-tint"
        >
          <Bell className="size-5" aria-hidden="true" />
          {!!unread.data?.jumlah_belum_dibaca && (
            <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-danger px-1 text-center text-[10px] font-bold leading-5 text-white" aria-hidden="true">
              {unread.data.jumlah_belum_dibaca > 99 ? "99+" : unread.data.jumlah_belum_dibaca}
            </span>
          )}
        </Link>

        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-full bg-tint text-body font-semibold text-primary"
          >
            {user.punya_foto ? (
              <img src="/api/v1/profil/foto/" alt="" className="size-full object-cover" />
            ) : (
              inisial(user.nama_lengkap)
            )}
          </span>
          <span className="hidden text-left leading-tight sm:block">
            <span className="block max-w-44 truncate text-body font-semibold text-ink">{user.nama_lengkap}</span>
            <span className="block max-w-44 truncate text-label text-muted">
              {ROLE_LABEL[role]} · {user.identifier}
            </span>
          </span>
        </div>
      </div>
    </header>
  );
}