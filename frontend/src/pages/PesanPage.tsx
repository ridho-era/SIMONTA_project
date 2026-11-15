import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, Check, CheckCheck, FileText, Loader2, MessageCircle, Paperclip, Search, Send, UserRound } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { EmptyState } from "../components/EmptyState";
import { PageFrame } from "../components/PageFrame";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../components/ui";
import { useDaftarPercakapan, useKirimPesan, useTandaiPesanDibaca, useThreadPesan } from "../hooks/usePesan";
import type { PesanItem, PercakapanItem } from "../lib/types";

const MAKS_LAMPIRAN = 15 * 1024 * 1024;
const EKSTENSI = [".pdf", ".docx", ".jpg", ".jpeg", ".png"];

function tanggalPemisah(iso: string) {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "full",
    timeZone: "Asia/Jakarta",
  }).format(new Date(iso));
}

function jamPesan(iso: string) {
  return new Intl.DateTimeFormat("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Asia/Jakarta",
  }).format(new Date(iso));
}

function ringkasan(item: PercakapanItem) {
  if (!item.pesan_terakhir) return "Mulai percakapan";
  if (item.pesan_terakhir.isi) return item.pesan_terakhir.isi;
  return item.pesan_terakhir.nama_lampiran || "Membagikan dokumen";
}

function PesanBubble({ item }: { item: PesanItem }) {
  return (
    <div className={`flex ${item.saya_pengirim ? "justify-end" : "justify-start"}`}>
      <article
        className={`max-w-[min(88%,42rem)] rounded-2xl px-4 py-3 shadow-sm ${
          item.saya_pengirim ? "rounded-br-sm bg-tint text-ink" : "rounded-bl-sm border border-line bg-surface text-ink"
        }`}
      >
        {!item.saya_pengirim && (
          <p className="mb-1 text-label font-semibold text-primary">{item.pengirim.nama_lengkap}</p>
        )}
        {item.dokumen_versi && (
          <div className="mb-2 rounded-lg border border-line bg-page p-3">
            <p className="flex items-center gap-2 text-body font-semibold text-primary">
              <FileText className="size-4" aria-hidden="true" /> Dokumen terkait
            </p>
            <p className="mt-1 text-body [overflow-wrap:anywhere]">{item.dokumen_versi.nama_asli}</p>
            <p className="text-label text-muted">{item.dokumen_versi.milestone} · Versi {item.dokumen_versi.nomor_versi}</p>
          </div>
        )}
        {item.isi && <p className="whitespace-pre-wrap break-words text-body">{item.isi}</p>}
        {item.lampiran_url && (
          <a
            href={item.lampiran_url}
            download
            className="mt-2 inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-body font-semibold text-primary hover:bg-page"
          >
            <Paperclip className="size-4" aria-hidden="true" />
            <span className="max-w-64 break-all">{item.nama_lampiran}</span>
          </a>
        )}
        <div className={`mt-2 flex items-center justify-end gap-1.5 text-label ${item.saya_pengirim ? "text-primary-2" : "text-muted"}`}>
          <time dateTime={item.dibuat_pada}>{jamPesan(item.dibuat_pada)}</time>
          {item.saya_pengirim && (
            <span className="inline-flex items-center gap-1" title={item.dibaca_pada ? "Dibaca" : "Terkirim"}>
              {item.dibaca_pada ? <CheckCheck className="size-3.5" aria-label="Dibaca" /> : <Check className="size-3.5" aria-label="Terkirim" />}
              {item.dibaca_pada ? "Dibaca" : "Terkirim"}
            </span>
          )}
        </div>
      </article>
    </div>
  );
}

function KontakItem({
  item,
  aktif,
  onClick,
}: {
  item: PercakapanItem;
  aktif: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={aktif}
      className={`w-full rounded-xl border p-3 text-left transition-colors ${
        aktif ? "border-primary-2 bg-tint" : "border-transparent bg-surface hover:border-line hover:bg-page"
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-full bg-tint text-primary">
          <UserRound className="size-5" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center justify-between gap-2">
            <span className="truncate text-body font-semibold text-ink">{item.lawan_bicara.nama_lengkap}</span>
            {item.jumlah_belum_dibaca > 0 && (
              <span className="grid min-h-5 min-w-5 place-items-center rounded-full bg-primary px-1.5 text-label font-bold text-white">
                {item.jumlah_belum_dibaca > 99 ? "99+" : item.jumlah_belum_dibaca}
              </span>
            )}
          </span>
          <span className="block truncate text-label text-muted">
            {item.lawan_bicara.peran_label || item.lawan_bicara.identifier}
          </span>
          <span className="mt-1 block truncate text-body text-muted">{ringkasan(item)}</span>
        </span>
      </div>
    </button>
  );
}

function Composer({
  percakapanId,
  dokumen,
}: {
  percakapanId: number;
  dokumen: Array<{ id: number; nama_asli: string; nomor_versi: number; milestone: string }>;
}) {
  const [isi, setIsi] = useState("");
  const [lampiran, setLampiran] = useState<File | null>(null);
  const [dokumenId, setDokumenId] = useState("");
  const [galat, setGalat] = useState("");
  const kirim = useKirimPesan();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGalat("");
    const teks = isi.trim();
    if (!teks && !lampiran && !dokumenId) {
      setGalat("Tulis pesan, pilih lampiran, atau pilih dokumen terkait.");
      return;
    }
    const form = new FormData();
    if (teks) form.append("isi", teks);
    if (lampiran) form.append("lampiran", lampiran);
    if (dokumenId) form.append("dokumen_versi", dokumenId);
    try {
      await kirim.mutateAsync({ percakapanId, form });
      setIsi("");
      setLampiran(null);
      setDokumenId("");
      const input = document.getElementById("pesan-lampiran") as HTMLInputElement | null;
      if (input) input.value = "";
    } catch {
      setGalat("Pesan belum berhasil dikirim. Periksa koneksi dan coba kembali.");
    }
  }

  function pilihLampiran(file: File | null) {
    setGalat("");
    if (!file) {
      setLampiran(null);
      return;
    }
    const ext = `.${file.name.split(".").pop()?.toLowerCase() || ""}`;
    if (!EKSTENSI.includes(ext)) {
      setGalat("Format lampiran harus PDF, DOCX, JPG, JPEG, atau PNG.");
      return;
    }
    if (file.size <= 0 || file.size > MAKS_LAMPIRAN) {
      setGalat("Ukuran lampiran harus lebih dari 0 dan maksimal 15 MB.");
      return;
    }
    setLampiran(file);
  }

  return (
    <form onSubmit={submit} className="border-t border-line bg-surface p-4">
      {dokumen.length > 0 && (
        <div className="mb-3">
          <label htmlFor="pesan-dokumen" className="mb-1 block text-label font-semibold text-muted">
            Kaitkan dokumen (opsional)
          </label>
          <select id="pesan-dokumen" value={dokumenId} onChange={(event) => setDokumenId(event.target.value)} className={inputClass}>
            <option value="">Tidak mengaitkan dokumen</option>
            {dokumen.map((item) => (
              <option key={item.id} value={item.id}>
                {item.milestone} · v{item.nomor_versi} · {item.nama_asli}
              </option>
            ))}
          </select>
        </div>
      )}
      <label htmlFor="pesan-isi" className="sr-only">Tulis pesan</label>
      <textarea
        id="pesan-isi"
        rows={3}
        value={isi}
        onChange={(event) => setIsi(event.target.value)}
        maxLength={10000}
        placeholder="Tulis pesan untuk pembimbing…"
        className={`${inputClass} h-auto min-h-20 resize-y py-3`}
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <label className={`${secondaryButtonClass} cursor-pointer`} htmlFor="pesan-lampiran">
            <Paperclip className="size-4" aria-hidden="true" /> Lampiran
          </label>
          <input
            id="pesan-lampiran"
            type="file"
            accept=".pdf,.docx,.jpg,.jpeg,.png"
            className="sr-only"
            onChange={(event) => pilihLampiran(event.target.files?.[0] ?? null)}
          />
          {lampiran && (
            <span className="max-w-60 truncate text-label text-muted" title={lampiran.name}>{lampiran.name}</span>
          )}
          <span className="text-label text-muted">PDF/DOCX/JPG/PNG · maks. 15 MB</span>
        </div>
        <button type="submit" disabled={kirim.isPending} className={`${primaryButtonClass} w-auto min-w-32`}>
          {kirim.isPending ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <Send className="size-4" aria-hidden="true" />}
          Kirim
        </button>
      </div>
      {galat && <p role="alert" className="mt-2 flex items-center gap-2 text-body text-danger"><AlertCircle className="size-4"/> {galat}</p>}
    </form>
  );
}

export default function PesanPage() {
  const { user } = useAuth();
  const dosenMode = user?.role === "dosen";
  const judul = dosenMode ? "Chat mahasiswa" : "Pesan pembimbing";
  const daftar = useDaftarPercakapan();
  const [pilihanId, setPilihanId] = useState<number | null>(null);
  const [cari, setCari] = useState("");
  const thread = useThreadPesan(pilihanId);
  const tandaiDibaca = useTandaiPesanDibaca();
  const kontak = useMemo(() => {
    const kata = cari.trim().toLowerCase();
    if (!kata) return daftar.data ?? [];
    return (daftar.data ?? []).filter((item) =>
      [item.lawan_bicara.nama_lengkap, item.lawan_bicara.identifier, item.tugas_akhir.judul]
        .some((nilai) => nilai.toLowerCase().includes(kata)),
    );
  }, [daftar.data, cari]);

  useEffect(() => {
    if (!daftar.data?.length) {
      setPilihanId(null);
      return;
    }
    if (!pilihanId || !daftar.data.some((item) => item.id === pilihanId)) {
      setPilihanId(daftar.data[0].id);
    }
  }, [daftar.data, pilihanId]);

  useEffect(() => {
    if (!pilihanId || !thread.data) return;
    const adaPesanMasukBelumDibaca = thread.data.pesan.some(
      (item) => !item.saya_pengirim && !item.dibaca_pada,
    );
    if (adaPesanMasukBelumDibaca && !tandaiDibaca.isPending) {
      tandaiDibaca.mutate(pilihanId);
    }
  }, [pilihanId, thread.data?.pesan, tandaiDibaca.isPending]);

  const aktif = (daftar.data ?? []).find((item) => item.id === pilihanId) ?? null;
  const pesan = thread.data?.pesan ?? [];
  let tanggalSebelumnya = "";

  return (
    <PageFrame
      title={judul}
      subtitle={dosenMode ? "Komunikasi dengan mahasiswa yang ditugaskan kepada Anda." : "Komunikasi dengan dosen yang ditugaskan pada tugas akhir Anda."}
    >
      <div className="grid min-h-[620px] overflow-hidden rounded-xl border border-line bg-surface lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="border-b border-line bg-page p-3 lg:border-b-0 lg:border-r">
          <label htmlFor="cari-kontak" className="mb-2 block text-label font-semibold text-muted">Cari nama atau NPM/NIP</label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input id="cari-kontak" value={cari} onChange={(event) => setCari(event.target.value)} placeholder="Cari kontak…" className={`${inputClass} pl-9`} />
          </div>
          <div className="mt-3 space-y-1.5">
            {daftar.isLoading && <p className="p-3 text-body text-muted">Memuat kontak…</p>}
            {daftar.isError && <EmptyState>Daftar kontak tidak dapat dimuat. Muat ulang halaman.</EmptyState>}
            {!daftar.isLoading && !daftar.isError && kontak.length === 0 && (
              <EmptyState>{cari ? "Kontak tidak ditemukan." : "Belum ada dosen/mahasiswa yang ditugaskan untuk percakapan."}</EmptyState>
            )}
            {kontak.map((item) => (
              <KontakItem key={item.id} item={item} aktif={item.id === pilihanId} onClick={() => setPilihanId(item.id)} />
            ))}
          </div>
        </aside>

        <section className="flex min-h-[620px] min-w-0 flex-col">
          {!aktif ? (
            <div className="flex flex-1 items-center justify-center p-6">
              <EmptyState>
                <MessageCircle className="mx-auto mb-2 size-8 text-muted" aria-hidden="true" />
                Pilih kontak untuk memulai percakapan.
              </EmptyState>
            </div>
          ) : (
            <>
              <header className="border-b border-line px-5 py-4">
                <p className="text-heading font-semibold text-primary">{aktif.lawan_bicara.nama_lengkap}</p>
                <p className="text-label text-muted">{aktif.lawan_bicara.identifier} · {aktif.tugas_akhir.judul}</p>
              </header>
              <div className="flex-1 space-y-4 overflow-y-auto bg-page p-4 sm:p-6" aria-live="polite">
                {thread.isLoading && <p className="text-body text-muted">Memuat pesan…</p>}
                {thread.isError && <EmptyState>Pesan tidak dapat dimuat. Coba muat ulang halaman.</EmptyState>}
                {!thread.isLoading && !thread.isError && pesan.length === 0 && (
                  <EmptyState>Belum ada pesan. Mulai percakapan dengan menulis pesan di bawah.</EmptyState>
                )}
                {pesan.map((item) => {
                  const tanggal = tanggalPemisah(item.dibuat_pada);
                  const tampilTanggal = tanggal !== tanggalSebelumnya;
                  tanggalSebelumnya = tanggal;
                  return (
                    <div key={item.id} className="space-y-3">
                      {tampilTanggal && (
                        <div className="flex justify-center">
                          <span className="rounded-full border border-line bg-surface px-3 py-1 text-label text-muted">{tanggal}</span>
                        </div>
                      )}
                      <PesanBubble item={item} />
                    </div>
                  );
                })}
              </div>
              <Composer
                key={pilihanId}
                percakapanId={pilihanId!}
                dokumen={thread.data?.dokumen_tersedia ?? []}
              />
            </>
          )}
        </section>
      </div>
      <p className="mt-3 text-label text-muted">Pesan diperbarui otomatis setiap 5 detik. Penilaian resmi tugas akhir tetap melalui fitur Review dosen.</p>
    </PageFrame>
  );
}
