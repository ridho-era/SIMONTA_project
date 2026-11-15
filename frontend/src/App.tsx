import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute, RootRedirect } from "./auth/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { PageFrame } from "./components/PageFrame";
import { PORTAL } from "./config/navigation";
import AdminNoticePage from "./pages/AdminNoticePage";
import DokumenPage from "./pages/DokumenPage";
import DashboardMahasiswaPage from "./pages/DashboardMahasiswaPage";
import DashboardDosenPage from "./pages/DashboardDosenPage";
import MahasiswaBimbinganPage from "./pages/MahasiswaBimbinganPage";
import ForcedPasswordPage from "./pages/ForcedPasswordPage";
import LoginPage from "./pages/LoginPage";
import MilestonePage from "./pages/MilestonePage";
import JadwalMahasiswaPage from "./pages/JadwalMahasiswaPage";
import ReviewDosenPage from "./pages/ReviewDosenPage";
import ReviewDosenListPage from "./pages/ReviewDosenListPage";
import ReviewMahasiswaDetailPage from "./pages/ReviewMahasiswaDetailPage";
import ReviewMahasiswaListPage from "./pages/ReviewMahasiswaListPage";
import NotFoundPage from "./pages/NotFoundPage";
import PesanPage from "./pages/PesanPage";
import NotifikasiPage from "./pages/NotifikasiPage";
import MahasiswaDendaPage from "./pages/MahasiswaDendaPage";
import DosenKeterlambatanPage from "./pages/DosenKeterlambatanPage";
import ProfilePage, { BantuanPage } from "./pages/ProfilePage";

// Halaman yang sudah dibangun. Rute lain di navigation.ts masih berupa judul saja.
const HALAMAN: Partial<Record<string, ReactElement>> = {
  "mahasiswa/dashboard": <DashboardMahasiswaPage />,
  "dosen/dashboard": <DashboardDosenPage />,
  "dosen/mahasiswa": <MahasiswaBimbinganPage />,
  "mahasiswa/milestone": <MilestonePage />,
  "mahasiswa/jadwal": <JadwalMahasiswaPage />,
  "mahasiswa/dokumen": <DokumenPage />,
  "mahasiswa/review": <ReviewMahasiswaListPage />,
  "mahasiswa/review/:id": <ReviewMahasiswaDetailPage />,
  "dosen/review": <ReviewDosenListPage />,
  "dosen/review/:id": <ReviewDosenPage />,
  "mahasiswa/pesan": <PesanPage />,
  "dosen/chat": <PesanPage />,
  "mahasiswa/denda": <MahasiswaDendaPage />,
  "dosen/keterlambatan": <DosenKeterlambatanPage />,
  "mahasiswa/profil": <ProfilePage />,
  "dosen/profil": <ProfilePage />,
  "mahasiswa/bantuan": <BantuanPage />,
  "dosen/bantuan": <BantuanPage />,
  "mahasiswa/notifikasi": <NotifikasiPage />,
  "dosen/notifikasi": <NotifikasiPage />,
};

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/masuk" element={<LoginPage />} />
      <Route path="/ganti-password" element={<ForcedPasswordPage />} />
      <Route path="/akses-admin" element={<AdminNoticePage />} />

      {PORTAL.map(({ role, pages }) => (
        <Route
          key={role}
          path={`/${role}`}
          element={
            <ProtectedRoute roles={[role]}>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          {pages.map((p) => (
            <Route
              key={p.path}
              path={p.path}
              element={HALAMAN[`${role}/${p.path}`] ?? <PageFrame title={p.title} parent={p.parent} />}
            />
          ))}
        </Route>
      ))}

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}