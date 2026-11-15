import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { CircleAlert, GraduationCap, Info, Loader2 } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { FullPageLoader } from "../components/Loader";
import { PasswordField } from "../components/PasswordField";
import { inputClass, primaryButtonClass } from "../components/ui";
import { homePath, ID_LABEL, ROLE_LABEL } from "../config/navigation";
import { ApiError } from "../lib/api";
import type { PortalRole } from "../lib/types";

const TIPE: PortalRole[] = ["mahasiswa", "dosen"];
const TAHAPAN = ["Pengajuan", "Proposal", "Penelitian", "Kelulusan"] as const;

export default function LoginPage() {
  const { user, isLoading, login } = useAuth();
  const [tipe, setTipe] = useState<PortalRole>("mahasiswa");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [ingat, setIngat] = useState(false);
  const [bantuanReset, setBantuanReset] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);
  const [mengirim, setMengirim] = useState(false);

  useEffect(() => {
    document.title = "Masuk · SIMONTA";
  }, []);

  if (isLoading) return <FullPageLoader />;
  if (user) {
    return <Navigate to={user.must_change_password ? "/ganti-password" : homePath(user.role)} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (mengirim) return;
    setGalat(null);

    if (!identifier.trim() || !password) {
      setGalat(`Lengkapi ${ID_LABEL[tipe]} dan password.`);
      return;
    }

    setMengirim(true);
    try {
      await login({ identifier: identifier.trim(), password, tipe, ingat_saya: ingat });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 400) setGalat(`Lengkapi ${ID_LABEL[tipe]} dan password.`);
        else if (error.status === 403) setGalat("Sesi keamanan tidak valid. Muat ulang halaman lalu coba lagi.");
        else setGalat(error.message);
      } else {
        setGalat("Tidak dapat terhubung ke server. Periksa koneksi Anda.");
      }
      setPassword("");
    } finally {
      setMengirim(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-page px-4 py-8">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-xl border border-line bg-surface lg:grid-cols-2">
        <section className="p-6 sm:p-10">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-lg bg-primary text-white">
              <GraduationCap className="size-6" aria-hidden="true" />
            </span>
            <div className="leading-tight">
              <p className="text-heading font-semibold text-primary">SIMONTA</p>
              <p className="text-label font-medium tracking-wide text-muted">UIN RADEN INTAN LAMPUNG • SISTEM INFORMASI</p>
            </div>
          </div>

          <h1 className="mt-8 text-title font-semibold text-primary">Akses SIMONTA</h1>
          <p className="mt-1 text-body text-muted">Masuk dengan {ID_LABEL[tipe]} dan password Anda.</p>

          <div role="tablist" aria-label="Jenis akun" className="mt-6 grid grid-cols-2 rounded-lg bg-page p-1">
            {TIPE.map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                id={`tab-${t}`}
                aria-selected={tipe === t}
                aria-controls="form-masuk"
                onClick={() => {
                  setTipe(t);
                  setGalat(null);
                }}
                className={`rounded-md px-3 py-2 text-body font-semibold transition-colors ${
                  tipe === t ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-ink"
                }`}
              >
                {ROLE_LABEL[t]}
              </button>
            ))}
          </div>

          <form
            id="form-masuk"
            role="tabpanel"
            aria-labelledby={`tab-${tipe}`}
            onSubmit={onSubmit}
            noValidate
            className="mt-5 space-y-4"
          >
            {galat && (
              <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger">
                <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <span>{galat}</span>
              </div>
            )}

            <div>
              <label htmlFor="identifier" className="mb-1.5 block text-body font-medium text-ink">
                {ID_LABEL[tipe]}
              </label>
              <input
                id="identifier"
                type="text"
                inputMode="text"
                autoComplete="username"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                className={inputClass}
              />
            </div>

            <PasswordField id="password" label="Password" value={password} onChange={setPassword} autoComplete="current-password" />

            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-body text-ink">
                <input
                  type="checkbox"
                  checked={ingat}
                  onChange={(e) => setIngat(e.target.checked)}
                  className="size-4 accent-primary"
                />
                Ingat saya
              </label>
              <button
                type="button"
                onClick={() => setBantuanReset((v) => !v)}
                aria-expanded={bantuanReset}
                aria-controls="bantuan-reset"
                className="text-body font-medium text-primary-2 underline-offset-2 hover:underline"
              >
                Lupa password?
              </button>
            </div>

            {bantuanReset && (
              <p id="bantuan-reset" className="rounded-md bg-info-bg p-3 text-label text-info">
                Reset password dilakukan oleh admin Prodi. Hubungi admin Prodi untuk mendapatkan password sementara,
                lalu ganti saat masuk pertama.
              </p>
            )}

            <button type="submit" disabled={mengirim} className={primaryButtonClass}>
              {mengirim && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
              Masuk ke SIMONTA
            </button>
          </form>

          <p className="mt-5 flex items-start gap-2 rounded-md bg-info-bg p-3 text-label text-info">
            <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>
              Akun SIMONTA dibuat oleh admin Prodi. Jika Anda belum memiliki akun atau akun Anda nonaktif, hubungi admin
              Prodi.
            </span>
          </p>
        </section>

        <aside className="bg-primary p-6 text-white sm:p-10">
          <h2 className="text-subtitle font-semibold">Perjalanan tugas akhir Anda</h2>
          <ol className="mt-8">
            {TAHAPAN.map((nama, i) => (
              <li key={nama} className="relative flex items-center gap-4 pb-6 last:pb-0">
                {i < TAHAPAN.length - 1 && (
                  <span aria-hidden="true" className="absolute left-3.75 top-8 h-6 w-px bg-gold/70" />
                )}
                <span className="relative grid size-8 shrink-0 place-items-center rounded-full border-2 border-gold bg-primary text-body font-semibold">
                  {i + 1}
                </span>
                <span className="text-heading font-semibold">{nama}</span>
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </div>
  );
}