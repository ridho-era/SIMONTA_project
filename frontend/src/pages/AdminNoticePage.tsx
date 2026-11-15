import { useEffect } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { FullPageLoader } from "../components/Loader";
import { secondaryButtonClass } from "../components/ui";
import { homePath } from "../config/navigation";

const ADMIN_URL = (import.meta.env.VITE_ADMIN_URL as string | undefined) ?? "http://127.0.0.1:8000/admin/";

export default function AdminNoticePage() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    document.title = "Akun admin · SIMONTA";
  }, []);

  if (isLoading) return <FullPageLoader />;
  if (!user) return <Navigate to="/masuk" replace />;
  if (user.role !== "admin") return <Navigate to={homePath(user.role)} replace />;

  async function onKeluar() {
    await logout();
    navigate("/masuk", { replace: true });
  }

  return (
    <div className="grid min-h-screen place-items-center bg-page px-4 py-8">
      <div className="w-full max-w-md rounded-xl border border-line bg-surface p-6 sm:p-8">
        <h1 className="text-subtitle font-semibold text-primary">Akun Admin Prodi</h1>
        <p className="mt-2 text-body text-muted">
          Data akademik, akun, dan penugasan dikelola lewat Django admin. Portal SIMONTA ditujukan untuk mahasiswa dan
          dosen.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <a href={ADMIN_URL} className={secondaryButtonClass}>
            Buka Django admin
          </a>
          <button type="button" onClick={onKeluar} className={secondaryButtonClass}>
            Keluar akun
          </button>
        </div>
      </div>
    </div>
  );
}