import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { CircleAlert, Loader2 } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { FullPageLoader } from "../components/Loader";
import { PasswordField } from "../components/PasswordField";
import { primaryButtonClass } from "../components/ui";
import { homePath } from "../config/navigation";
import { api, ApiError, kumpulkanGalat } from "../lib/api";

export default function ForcedPasswordPage() {
  const { user, isLoading, logout, refresh } = useAuth();
  const navigate = useNavigate();
  const [lama, setLama] = useState("");
  const [baru, setBaru] = useState("");
  const [konfirmasi, setKonfirmasi] = useState("");
  const [galat, setGalat] = useState<string[]>([]);
  const [mengirim, setMengirim] = useState(false);

  useEffect(() => {
    document.title = "Ganti password · SIMONTA";
  }, []);

  if (isLoading) return <FullPageLoader />;
  if (!user) return <Navigate to="/masuk" replace />;
  if (!user.must_change_password) return <Navigate to={homePath(user.role)} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (mengirim) return;
    setGalat([]);
    setMengirim(true);
    try {
      await api("/auth/change-password/", {
        method: "POST",
        body: { password_lama: lama, password_baru: baru, konfirmasi_password: konfirmasi },
      });
      await refresh(); // must_change_password menjadi false, halaman ini mengarahkan ke dashboard
    } catch (error) {
      if (error instanceof ApiError) {
        const daftar = kumpulkanGalat(error.data);
        setGalat(daftar.length ? daftar : [error.message]);
      } else {
        setGalat(["Tidak dapat terhubung ke server. Periksa koneksi Anda."]);
      }
    } finally {
      setMengirim(false);
    }
  }

  async function onKeluar() {
    await logout();
    navigate("/masuk", { replace: true });
  }

  return (
    <div className="grid min-h-screen place-items-center bg-page px-4 py-8">
      <div className="w-full max-w-md rounded-xl border border-line bg-surface p-6 sm:p-8">
        <h1 className="text-subtitle font-semibold text-primary">Ganti password</h1>
        <p className="mt-1 text-body text-muted">
          Anda masuk dengan password sementara. Buat password baru sebelum melanjutkan.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {galat.length > 0 && (
            <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger">
              <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <ul className="space-y-1">
                {galat.map((pesan) => (
                  <li key={pesan}>{pesan}</li>
                ))}
              </ul>
            </div>
          )}
          <PasswordField id="password-lama" label="Password sementara" value={lama} onChange={setLama} autoComplete="current-password" />
          <PasswordField id="password-baru" label="Password baru" value={baru} onChange={setBaru} autoComplete="new-password" />
          <PasswordField id="password-konfirmasi" label="Ulangi password baru" value={konfirmasi} onChange={setKonfirmasi} autoComplete="new-password" />
          <button type="submit" disabled={mengirim} className={primaryButtonClass}>
            {mengirim && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            Simpan password baru
          </button>
        </form>

        <button type="button" onClick={onKeluar} className="mt-4 w-full text-center text-body font-medium text-primary-2 hover:underline">
          Keluar akun
        </button>
      </div>
    </div>
  );
}