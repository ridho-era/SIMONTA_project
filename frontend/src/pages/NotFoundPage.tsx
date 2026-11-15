import { useEffect } from "react";
import { Link } from "react-router-dom";

import { secondaryButtonClass } from "../components/ui";

export default function NotFoundPage() {
  useEffect(() => {
    document.title = "Halaman tidak ditemukan · SIMONTA";
  }, []);

  return (
    <div className="grid min-h-screen place-items-center bg-page px-4">
      <div className="text-center">
        <h1 className="text-title font-semibold text-primary">Halaman tidak ditemukan</h1>
        <p className="mt-2 text-body text-muted">Alamat yang Anda buka tidak tersedia di SIMONTA.</p>
        <Link to="/" className={`${secondaryButtonClass} mt-6`}>
          Kembali
        </Link>
      </div>
    </div>
  );
}