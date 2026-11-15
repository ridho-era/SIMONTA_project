import { useEffect, useState, type FormEvent, type ChangeEvent } from "react";
import { Camera, CheckCircle2, ChevronDown, CircleAlert, GraduationCap, KeyRound, Loader2, MonitorSmartphone, Save, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthContext";
import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import { api, ApiError, kumpulkanGalat } from "../lib/api";
import { formatTanggal } from "../lib/format";
import type { HalamanBantuanItem, ProfilData } from "../lib/profilTypes";

const PROFIL_KEY = ["profil-saya"] as const;

function FieldReadOnly({ label, value }: { label: string; value: string }) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-label font-medium text-muted">{label}</span>
      <input className={`${inputClass} bg-page text-muted`} value={value || "Belum diatur oleh admin Prodi"} readOnly disabled />
    </label>
  );
}

function LabelField({
  id,
  label,
  value,
  onChange,
  maxLength,
  type = "text",
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  type?: string;
}) {
  return (
    <label htmlFor={id} className="block space-y-1.5">
      <span className="block text-label font-medium text-muted">{label}</span>
      <input id={id} type={type} maxLength={maxLength} className={inputClass} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function PersonList({ title, people }: { title: string; people: { identifier: string; nama_lengkap: string; gelar: string; peran: string }[] }) {
  return (
    <section className="space-y-2">
      <h3 className="text-body font-semibold text-ink">{title}</h3>
      {people.length ? (
        <div className="space-y-2">
          {people.map((person) => (
            <div key={`${person.identifier}-${person.peran}`} className="rounded-lg border border-line bg-surface p-3">
              <p className="text-body font-semibold text-ink">{person.nama_lengkap}{person.gelar ? `, ${person.gelar}` : ""}</p>
              <p className="text-label text-muted">{person.identifier} · {person.peran}</p>
            </div>
          ))}
        </div>
      ) : <EmptyState>Data {title.toLowerCase()} belum tersedia.</EmptyState>}
    </section>
  );
}

export default function ProfilePage() {
  const { user, refresh } = useAuth();
  const queryClient = useQueryClient();
  const profil = useQuery({
    queryKey: PROFIL_KEY,
    queryFn: () => api<ProfilData>("/profil/"),
  });
  const [tab, setTab] = useState<"pribadi" | "akademik">("pribadi");
  const [nama, setNama] = useState("");
  const [gelar, setGelar] = useState("");
  const [telepon, setTelepon] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [fotoPreview, setFotoPreview] = useState<string | null>(null);
  const [fotoVersion, setFotoVersion] = useState(0);
  const [galatProfil, setGalatProfil] = useState<string[]>([]);
  const [pesanProfil, setPesanProfil] = useState<string | null>(null);
  const [passwordLama, setPasswordLama] = useState("");
  const [passwordBaru, setPasswordBaru] = useState("");
  const [konfirmasiPassword, setKonfirmasiPassword] = useState("");
  const [galatPassword, setGalatPassword] = useState<string[]>([]);
  const [pesanPassword, setPesanPassword] = useState<string | null>(null);
  const [pesanSesi, setPesanSesi] = useState<string | null>(null);
  const [galatSesi, setGalatSesi] = useState<string | null>(null);

  useEffect(() => {
    if (!profil.data) return;
    setNama(profil.data.nama_lengkap);
    setGelar(profil.data.gelar ?? "");
    setTelepon(profil.data.telepon ?? "");
  }, [profil.data]);

  useEffect(() => {
    if (!foto) {
      setFotoPreview(null);
      return;
    }
    const url = URL.createObjectURL(foto);
    setFotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [foto]);

  const simpanProfil = useMutation({
    mutationFn: (payload: FormData) => api<ProfilData>("/profil/", { method: "PATCH", body: payload }),
    onSuccess: (data) => {
      queryClient.setQueryData(PROFIL_KEY, data);
      setFoto(null);
      setFotoVersion((value) => value + 1);
      setGalatProfil([]);
      setPesanProfil("Perubahan profil berhasil disimpan.");
      void refresh();
    },
    onError: (error) => {
      const daftar = error instanceof ApiError ? kumpulkanGalat(error.data) : [];
      setGalatProfil(daftar.length ? daftar : [error instanceof Error ? error.message : "Profil tidak dapat disimpan."]);
    },
  });

  const gantiPassword = useMutation({
    mutationFn: () => api<{ detail: string }>("/auth/change-password/", {
      method: "POST",
      body: { password_lama: passwordLama, password_baru: passwordBaru, konfirmasi_password: konfirmasiPassword },
    }),
    onSuccess: async (data) => {
      setPasswordLama("");
      setPasswordBaru("");
      setKonfirmasiPassword("");
      setGalatPassword([]);
      setPesanPassword(data.detail);
      await refresh();
    },
    onError: (error) => {
      const daftar = error instanceof ApiError ? kumpulkanGalat(error.data) : [];
      setGalatPassword(daftar.length ? daftar : [error instanceof Error ? error.message : "Password tidak dapat diubah."]);
    },
  });

  const keluarPerangkatLain = useMutation({
    mutationFn: () => api<{ detail: string; jumlah_sesi_dikeluarkan: number }>("/profil/sesi/keluar-perangkat-lain/", { method: "POST" }),
    onSuccess: (data) => {
      setGalatSesi(null);
      setPesanSesi(`${data.detail} Jumlah sesi yang dikeluarkan: ${data.jumlah_sesi_dikeluarkan}.`);
    },
    onError: (error) => {
      setPesanSesi(null);
      setGalatSesi(error instanceof Error ? error.message : "Sesi perangkat lain tidak dapat dikeluarkan.");
    },
  });

  const preview = fotoPreview;

  if (!user || user.role === "admin") {
    return <PageFrame title="Profil saya"><EmptyState>Menu profil hanya tersedia untuk mahasiswa dan dosen.</EmptyState></PageFrame>;
  }

  function pilihFoto(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setGalatProfil([]);
    setPesanProfil(null);
    if (!file) {
      setFoto(null);
      return;
    }
    if (! ["image/jpeg", "image/png"].includes(file.type)) {
      setGalatProfil(["Foto harus berformat JPG atau PNG."]);
      event.target.value = "";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setGalatProfil(["Ukuran foto maksimal 2 MB."]);
      event.target.value = "";
      return;
    }
    setFoto(file);
  }

  function submitProfil(event: FormEvent) {
    event.preventDefault();
    setPesanProfil(null);
    setGalatProfil([]);
    const payload = new FormData();
    payload.append("nama_lengkap", nama.trim());
    payload.append("telepon", telepon.trim());
    if (profil.data?.role === "dosen") payload.append("gelar", gelar.trim());
    if (foto) payload.append("foto", foto);
    simpanProfil.mutate(payload);
  }

  function batalProfil() {
    if (!profil.data) return;
    setNama(profil.data.nama_lengkap);
    setGelar(profil.data.gelar ?? "");
    setTelepon(profil.data.telepon ?? "");
    setFoto(null);
    setGalatProfil([]);
    setPesanProfil(null);
  }

  function submitPassword(event: FormEvent) {
    event.preventDefault();
    setGalatPassword([]);
    setPesanPassword(null);
    gantiPassword.mutate();
  }

  if (profil.isLoading) return <PageFrame title="Profil saya"><p className="text-body text-muted">Memuat profil…</p></PageFrame>;
  if (profil.isError || !profil.data) return <PageFrame title="Profil saya"><EmptyState>Data profil tidak dapat dimuat. Muat ulang halaman atau coba kembali.</EmptyState></PageFrame>;

  const data = profil.data;
  const fotoSrc = preview ?? (data.foto_url ? `${data.foto_url}?v=${fotoVersion}` : null);

  return (
    <PageFrame title="Profil saya" subtitle="Kelola informasi pribadi dan lihat konteks akademik akun Anda.">
      <div className="space-y-6">
        <section className="rounded-xl border border-line bg-surface p-5">
          <div className="flex flex-wrap items-center gap-4">
            <div className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-full border border-line bg-tint text-primary">
              {fotoSrc ? <img src={fotoSrc} alt="Foto profil" className="size-full object-cover" /> : <span className="text-title font-semibold">{data.nama_lengkap.trim().slice(0, 1).toUpperCase()}</span>}
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-subtitle font-semibold text-primary">{data.nama_lengkap}{data.role === "dosen" && data.gelar ? `, ${data.gelar}` : ""}</h2>
              <p className="text-body text-muted">{data.role === "mahasiswa" ? "Mahasiswa" : "Dosen"} · {data.identifier}</p>
              <p className="text-label text-muted">{data.program_studi?.nama ?? "Program studi belum diatur admin Prodi"}</p>
            </div>
            <label className={`${secondaryButtonClass} cursor-pointer`}>
              <Camera className="size-4" aria-hidden="true" />
              Ganti foto
              <input type="file" accept="image/jpeg,image/png" className="sr-only" onChange={pilihFoto} />
            </label>
          </div>
          <p className="mt-3 text-label text-muted">Format JPG atau PNG, ukuran maksimal 2 MB. Setelah memilih foto, tekan Simpan perubahan pada tab Informasi pribadi.</p>
        </section>

        <section className="overflow-hidden rounded-xl border border-line bg-surface">
          <div className="flex border-b border-line p-2" role="tablist" aria-label="Bagian profil">
            <button type="button" role="tab" aria-selected={tab === "pribadi"} onClick={() => setTab("pribadi")} className={`rounded-md px-4 py-2 text-body font-semibold ${tab === "pribadi" ? "bg-tint text-primary" : "text-muted hover:bg-page"}`}>Informasi pribadi</button>
            <button type="button" role="tab" aria-selected={tab === "akademik"} onClick={() => setTab("akademik")} className={`rounded-md px-4 py-2 text-body font-semibold ${tab === "akademik" ? "bg-tint text-primary" : "text-muted hover:bg-page"}`}>Konteks akademik</button>
          </div>

          {tab === "pribadi" ? (
            <form onSubmit={submitProfil} className="space-y-4 p-5">
              <div className="grid gap-4 md:grid-cols-2">
                <FieldReadOnly label={data.role === "mahasiswa" ? "NPM" : "NIP"} value={data.identifier} />
                <FieldReadOnly label="Email akademik" value={data.email_akademik ?? ""} />
                <LabelField id="profil-nama" label="Nama lengkap" value={nama} onChange={setNama} maxLength={150} />
                {data.role === "dosen" && <LabelField id="profil-gelar" label="Gelar" value={gelar} onChange={setGelar} maxLength={100} />}
                <LabelField id="profil-telepon" label="Nomor telepon / WhatsApp" value={telepon} onChange={setTelepon} maxLength={20} />
              </div>
              {galatProfil.length > 0 && <AlertError messages={galatProfil} />}
              {pesanProfil && <AlertSuccess message={pesanProfil} />}
              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={batalProfil} className={secondaryButtonClass}>Batal</button>
                <button type="submit" disabled={simpanProfil.isPending} className={primaryButtonClass}>
                  {simpanProfil.isPending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                  Simpan perubahan
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-5 p-5">
              <div className="grid gap-4 md:grid-cols-2">
                <FieldReadOnly label="Program studi" value={data.program_studi?.nama ?? ""} />
                <FieldReadOnly label="Email akademik" value={data.email_akademik ?? ""} />
              </div>
              {data.role === "mahasiswa" ? (
                <>
                  <section className="space-y-2">
                    <h3 className="text-body font-semibold text-ink">Tugas akhir dan periode</h3>
                    {data.konteks_akademik.tugas_akhir ? (
                      <div className="rounded-lg border border-line bg-page p-4">
                        <p className="text-body font-semibold text-ink">{data.konteks_akademik.tugas_akhir.judul}</p>
                        <p className="mt-1 text-label text-muted">Status: {data.konteks_akademik.tugas_akhir.status}</p>
                        <p className="text-label text-muted">Periode: {data.konteks_akademik.periode?.label ?? "Belum tersedia"}</p>
                      </div>
                    ) : <EmptyState>Tugas akhir Anda belum didaftarkan. Hubungi admin Prodi.</EmptyState>}
                  </section>
                  <div className="grid gap-5 md:grid-cols-2">
                    <PersonList title="Tim pembimbing" people={data.konteks_akademik.pembimbing ?? []} />
                    <PersonList title="Penguji" people={data.konteks_akademik.penguji ?? []} />
                  </div>
                </>
              ) : (
                <div className="rounded-lg border border-line bg-page p-4">
                  <div className="flex items-center gap-3">
                    <Users className="size-6 text-primary" aria-hidden="true" />
                    <div>
                      <p className="text-label text-muted">Jumlah mahasiswa bimbingan aktif</p>
                      <p className="text-title font-semibold text-primary">{data.konteks_akademik.jumlah_mahasiswa_bimbingan ?? 0}</p>
                    </div>
                  </div>
                  <Link to="/dosen/mahasiswa" className="mt-3 inline-flex text-body font-semibold text-primary-2 hover:underline">Lihat mahasiswa bimbingan</Link>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="space-y-4 rounded-xl border border-line bg-surface p-5">
          <div className="flex items-center gap-3">
            <KeyRound className="size-5 text-primary" aria-hidden="true" />
            <div>
              <h2 className="text-subtitle font-semibold text-primary">Keamanan akun</h2>
              <p className="text-label text-muted">Ganti password secara berkala dan jangan bagikan kepada orang lain.</p>
            </div>
          </div>
          <form onSubmit={submitPassword} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <PasswordInput id="password-lama-profil" label="Password lama" value={passwordLama} onChange={setPasswordLama} autoComplete="current-password" />
              <PasswordInput id="password-baru-profil" label="Password baru" value={passwordBaru} onChange={setPasswordBaru} autoComplete="new-password" />
              <PasswordInput id="password-konfirmasi-profil" label="Konfirmasi password baru" value={konfirmasiPassword} onChange={setKonfirmasiPassword} autoComplete="new-password" />
            </div>
            {galatPassword.length > 0 && <AlertError messages={galatPassword} />}
            {pesanPassword && <AlertSuccess message={pesanPassword} />}
            <button type="submit" disabled={gantiPassword.isPending} className={primaryButtonClass}>
              {gantiPassword.isPending ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
              Ubah password
            </button>
          </form>
          {data.role === "dosen" && (
            <div className="border-t border-line pt-4">
              <div className="flex items-start gap-3">
                <MonitorSmartphone className="mt-1 size-5 text-primary" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <h3 className="text-body font-semibold text-ink">Kelola sesi masuk</h3>
                  <p className="mt-1 text-label text-muted">Keluar dari semua perangkat lain. Sesi pada perangkat yang sedang digunakan ini tetap aktif.</p>
                  {pesanSesi && <p role="status" className="mt-2 text-label text-success">{pesanSesi}</p>}
                  {galatSesi && <p role="alert" className="mt-2 text-label text-danger">{galatSesi}</p>}
                  <button type="button" onClick={() => {
                    if (window.confirm("Keluarkan semua sesi akun ini dari perangkat lain? Sesi pada perangkat ini tetap aktif.")) keluarPerangkatLain.mutate();
                  }} disabled={keluarPerangkatLain.isPending} className={`${secondaryButtonClass} mt-3`}>
                    {keluarPerangkatLain.isPending && <Loader2 className="size-4 animate-spin" />}
                    Keluar dari perangkat lain
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </PageFrame>
  );
}

function PasswordInput({ id, label, value, onChange, autoComplete }: { id: string; label: string; value: string; onChange: (value: string) => void; autoComplete: string }) {
  return <label htmlFor={id} className="block space-y-1.5"><span className="block text-label font-medium text-muted">{label}</span><input id={id} type="password" autoComplete={autoComplete} required className={inputClass} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function AlertError({ messages }: { messages: string[] }) {
  return <div role="alert" className="flex items-start gap-2 rounded-md bg-danger-bg p-3 text-body text-danger"><CircleAlert className="mt-0.5 size-4 shrink-0" /><ul className="list-disc space-y-1 pl-4">{messages.map((message, index) => <li key={`${index}-${message}`}>{message}</li>)}</ul></div>;
}

function AlertSuccess({ message }: { message: string }) {
  return <div role="status" className="flex items-center gap-2 rounded-md bg-tint p-3 text-body text-primary"><CheckCircle2 className="size-4 shrink-0" />{message}</div>;
}

export function BantuanPage() {
  const bantuan = useQuery({
    queryKey: ["halaman-bantuan"],
    queryFn: () => api<HalamanBantuanItem[]>("/bantuan/"),
  });

  return (
    <PageFrame title="Pusat bantuan" subtitle="Informasi dan panduan penggunaan SIMONTA.">
      {bantuan.isLoading ? <p className="text-body text-muted">Memuat pusat bantuan…</p> : bantuan.isError ? (
        <EmptyState>Pusat bantuan tidak dapat dimuat. Silakan coba kembali.</EmptyState>
      ) : !bantuan.data?.length ? (
        <EmptyState>Halaman bantuan belum tersedia. Admin Prodi akan menambahkan panduan di sini.</EmptyState>
      ) : (
        <div className="space-y-3">
          {bantuan.data.map((item) => (
            <details key={item.id} className="group overflow-hidden rounded-xl border border-line bg-surface">
              <summary className="flex cursor-pointer list-none items-center gap-3 p-5 transition-colors hover:bg-page [&::-webkit-details-marker]:hidden">
                <GraduationCap className="size-5 shrink-0 text-primary" aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-semibold text-primary">{item.judul}</span>
                  {item.ringkasan && <span className="mt-1 block text-label text-muted">{item.ringkasan}</span>}
                </span>
                <ChevronDown className="size-5 shrink-0 text-muted transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
              </summary>
              <div className="border-t border-line px-5 pb-5 pt-4">
                <div className="whitespace-pre-wrap text-body leading-7 text-ink">{item.konten}</div>
                <p className="mt-4 text-label text-muted">Diperbarui {formatTanggal(new Date(item.diperbarui_pada))}</p>
              </div>
            </details>
          ))}
        </div>
      )}
    </PageFrame>
  );
}
