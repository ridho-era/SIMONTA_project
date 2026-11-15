import {
  Bell,
  CalendarDays,
  ClipboardCheck,
  FileText,
  Flag,
  LayoutDashboard,
  MessageSquare,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import type { PortalRole, Role } from "../lib/types";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export interface PageDef {
  path: string;
  title: string;
  parent?: string;
}

export const ROLE_LABEL: Record<PortalRole, string> = {
  mahasiswa: "Mahasiswa",
  dosen: "Dosen",
};

export const ID_LABEL: Record<PortalRole, string> = {
  mahasiswa: "NPM",
  dosen: "NIP",
};

export const SPACE_LABEL: Record<PortalRole, string> = {
  mahasiswa: "RUANG MAHASISWA",
  dosen: "RUANG DOSEN PEMBIMBING",
};

export function homePath(role: Role): string {
  if (role === "mahasiswa") return "/mahasiswa/dashboard";
  if (role === "dosen") return "/dosen/dashboard";
  return "/akses-admin";
}

export const NAV: Record<PortalRole, NavItem[]> = {
  mahasiswa: [
    { to: "/mahasiswa/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/mahasiswa/milestone", label: "Timeline milestone", icon: Flag },
    { to: "/mahasiswa/dokumen", label: "Dokumen & unggahan", icon: FileText },
    { to: "/mahasiswa/review", label: "Review dosen", icon: ClipboardCheck },
    { to: "/mahasiswa/denda", label: "Denda & keterlambatan", icon: Wallet },
    { to: "/mahasiswa/jadwal", label: "Jadwal bimbingan", icon: CalendarDays },
    { to: "/mahasiswa/pesan", label: "Pesan pembimbing", icon: MessageSquare },
    { to: "/mahasiswa/notifikasi", label: "Notifikasi & pengaturan", icon: Bell },
  ],
  dosen: [
    { to: "/dosen/dashboard", label: "Dashboard dosen", icon: LayoutDashboard },
    { to: "/dosen/mahasiswa", label: "Mahasiswa bimbingan", icon: Users },
    { to: "/dosen/review", label: "Review dokumen", icon: ClipboardCheck },
    { to: "/dosen/keterlambatan", label: "Keterlambatan & denda", icon: Wallet },
    { to: "/dosen/chat", label: "Chat mahasiswa", icon: MessageSquare },
    { to: "/dosen/notifikasi", label: "Notifikasi & pengaturan", icon: Bell },
  ],
};

// Rute F-02 s.d. F-17 (+ Pusat bantuan). Isi tiap halaman dibangun pada task berikutnya.
const mahasiswaPages: PageDef[] = [
  { path: "dashboard", title: "Dashboard" },
  { path: "milestone", title: "Timeline milestone" },
  { path: "dokumen", title: "Dokumen & unggahan" },
  { path: "review", title: "Review dosen" },
  { path: "review/:id", title: "Detail review", parent: "Review dosen" },
  { path: "denda", title: "Denda & keterlambatan" },
  { path: "jadwal", title: "Jadwal bimbingan" },
  { path: "pesan", title: "Pesan pembimbing" },
  { path: "notifikasi", title: "Notifikasi & pengaturan" },
  { path: "profil", title: "Profil saya" },
  { path: "bantuan", title: "Pusat bantuan" },
];

const dosenPages: PageDef[] = [
  { path: "dashboard", title: "Dashboard dosen" },
  { path: "mahasiswa", title: "Mahasiswa bimbingan" },
  { path: "review", title: "Review dokumen" },
  { path: "review/:id", title: "Detail review", parent: "Review dokumen" },
  { path: "keterlambatan", title: "Keterlambatan & denda" },
  { path: "chat", title: "Chat mahasiswa" },
  { path: "notifikasi", title: "Notifikasi & pengaturan" },
  { path: "profil", title: "Profil saya" },
  { path: "bantuan", title: "Pusat bantuan" },
];

export const PORTAL: { role: PortalRole; pages: PageDef[] }[] = [
  { role: "mahasiswa", pages: mahasiswaPages },
  { role: "dosen", pages: dosenPages },
];