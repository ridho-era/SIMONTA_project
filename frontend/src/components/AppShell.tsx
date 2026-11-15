import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const [terbuka, setTerbuka] = useState(false);
  const lokasi = useLocation();

  useEffect(() => {
    setTerbuka(false);
  }, [lokasi.pathname]);

  useEffect(() => {
    if (!terbuka) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTerbuka(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [terbuka]);

  return (
    <div className="min-h-screen bg-page">
      <a
        href="#konten"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-60 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-white"
      >
        Lewati ke konten
      </a>
      <Header onMenu={() => setTerbuka((v) => !v)} menuOpen={terbuka} />
      <div className="flex">
        <Sidebar open={terbuka} onClose={() => setTerbuka(false)} />
        <div className="flex min-h-[calc(100vh-5rem)] min-w-0 flex-1 flex-col">
          <main id="konten" tabIndex={-1} className="flex-1 px-4 py-6 outline-none md:px-8">
            <Outlet />
          </main>
          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-surface px-4 py-4 text-label text-muted md:px-8">
            <span>SIMONTA / Sistem Monitoring Tugas Akhir</span>
            <span>UIN Raden Intan Lampung</span>
          </footer>
        </div>
      </div>
    </div>
  );
}