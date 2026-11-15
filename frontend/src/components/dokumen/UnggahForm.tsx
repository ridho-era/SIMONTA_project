import { useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";

import { useUnggahDokumen } from "../../hooks/useDokumen";
import { pesanDariError } from "../../lib/galat";
import type { DokumenSaya } from "../../lib/types";
import { inputClass, primaryButtonClass, secondaryButtonClass } from "../ui";
import { DropZone } from "./DropZone";

const textareaClass =
  "min-h-24 w-full rounded-md border border-line bg-surface px-3 py-2 text-body text-ink placeholder:text-muted focus:border-primary-2";

interface Props {
  data: DokumenSaya;
  /** Milestone yang dibawa dari halaman Timeline (?milestone=id). */
  praPilih: number | null;
}

export function UnggahForm({ data, praPilih }: Props) {
  const unggah = useUnggahDokumen();
  const bisa = data.milestone.filter((m) => m.dapat_unggah);
  const [dipilih, setDipilih] = useState<string | null>(null);
  const [berkas, setBerkas] = useState<File | null>(null);
  const [catatan, setCatatan] = useState("");
  const [galat, setGalat] = useState<string | null>(null);
  const [sukses, setSukses] = useState<string | null>(null);

  const bawaan = bisa.find((m) => m.id === praPilih) ?? bisa[0];
  const efektif = bisa.some((m) => String(m.id) === dipilih) ? (dipilih ?? "") : bawaan ? String(bawaan.id) : "";
  const { ukuran_maks_mb: maksMb, ekstensi } = data.batas;

  function pilihBerkas(file: File | null) {
    setSukses(null);
    if (!file) {
      setBerkas(null);
      setGalat(null);
      return;
    }
    const nama = file.name.toLowerCase();
    if (!ekstensi.some((e) => nama.endsWith(e))) {
      setBerkas(null);
      setGalat("Hanya berkas PDF atau DOCX yang dapat diunggah.");
    } else if (file.size > maksMb * 1024 * 1024) {
      setBerkas(null);
      setGalat(`Ukuran berkas melebihi ${maksMb} MB.`);
    } else {
      setBerkas(file);
      setGalat(null);
    }
  }

  function batal() {
    setDipilih(null);
    setBerkas(null);
    setCatatan("");
    setGalat(null);
    setSukses(null);
  }

  function kirim(e: FormEvent) {
    e.preventDefault();
    if (!berkas || !efektif) {
      setGalat("Pilih milestone dan berkas terlebih dahulu.");
      return;
    }
    setGalat(null);
    setSukses(null);
    const form = new FormData();
    form.append("milestone", efektif);
    form.append("berkas", berkas);
    form.append("catatan", catatan.trim());
    unggah.mutate(form, {
      onSuccess: (versi) => {
        setBerkas(null);
        setCatatan("");
        setSukses(`Berkas versi ${versi.nomor_versi} untuk ${versi.milestone.nama} berhasil diunggah.`);
      },
      onError: (error) => setGalat(pesanDariError(error)),
    });
  }

  return (
    <section aria-labelledby="judul-unggah" className="rounded-xl border border-line bg-surface p-5">
      <h2 id="judul-unggah" className="text-heading font-semibold text-primary">
        Unggah draf milestone
      </h2>

      {bisa.length === 0 ? (
        <p className="mt-3 text-body text-muted">Tidak ada milestone yang dapat menerima unggahan saat ini.</p>
      ) : (
        <form onSubmit={kirim} className="mt-4 space-y-4">
          <div>
            <label htmlFor="unggah-milestone" className="mb-1.5 block text-body font-semibold text-ink">
              Milestone
            </label>
            <select
              id="unggah-milestone"
              value={efektif}
              onChange={(e) => setDipilih(e.target.value)}
              disabled={unggah.isPending}
              className={inputClass}
            >
              {data.milestone.map((m) => (
                <option key={m.id} value={m.id} disabled={!m.dapat_unggah}>
                  {m.urutan}. {m.nama}
                  {m.alasan ? ` (${m.alasan})` : ""}
                </option>
              ))}
            </select>
          </div>

          <DropZone berkas={berkas} onPilih={pilihBerkas} ekstensi={ekstensi} maksMb={maksMb} disabled={unggah.isPending} />

          <div>
            <label htmlFor="unggah-catatan" className="mb-1.5 block text-body font-semibold text-ink">
              Catatan untuk pembimbing <span className="font-normal text-muted">(opsional)</span>
            </label>
            <textarea
              id="unggah-catatan"
              value={catatan}
              onChange={(e) => setCatatan(e.target.value)}
              maxLength={2000}
              disabled={unggah.isPending}
              className={textareaClass}
            />
          </div>

          {galat && (
            <p role="alert" className="rounded-md bg-danger-bg px-3 py-2 text-body text-danger">
              {galat}
            </p>
          )}
          {sukses && (
            <p role="status" className="rounded-md bg-tint px-3 py-2 text-body text-primary">
              {sukses}
            </p>
          )}

          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" onClick={batal} disabled={unggah.isPending} className={secondaryButtonClass}>
              Batal
            </button>
            <button type="submit" disabled={unggah.isPending || !berkas} className={`${primaryButtonClass} sm:w-auto`}>
              {unggah.isPending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
              {unggah.isPending ? "Mengunggah…" : "Unggah berkas"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}