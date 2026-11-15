import { useEffect, useRef, useState } from "react";
import {
  GlobalWorkerOptions,
  getDocument,
  type PDFDocumentProxy,
} from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";
import { Maximize, Minus, Plus } from "lucide-react";

import { secondaryButtonClass } from "../ui";

GlobalWorkerOptions.workerSrc = workerUrl;

interface Props {
  src: string;
  nama: string;
}

export function PdfPreview({ src, nama }: Props) {
  const areaRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [dokumen, setDokumen] = useState<PDFDocumentProxy | null>(null);
  const [halaman, setHalaman] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [memuat, setMemuat] = useState(true);
  const [merender, setMerender] = useState(false);
  const [galat, setGalat] = useState("");
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    let aktif = true;
    const loadingTask = getDocument({ url: src, withCredentials: true });
    setMemuat(true);
    setGalat("");
    setDokumen(null);
    setHalaman(1);

    loadingTask.promise
  .then((hasil: PDFDocumentProxy) => {
    if (aktif) setDokumen(hasil);
  })
      .catch(() => {
        if (aktif) setGalat("Pratinjau PDF tidak dapat dimuat. Gunakan tombol Unduh untuk membuka berkas.");
      })
      .finally(() => {
        if (aktif) setMemuat(false);
      });

    return () => {
      aktif = false;
      void loadingTask.destroy();
    };
  }, [src]);

  useEffect(() => {
    if (!dokumen || !canvasRef.current) return;
    let aktif = true;
    let tugas: { promise: Promise<void>; cancel: () => void } | null = null;
    setMerender(true);
    setGalat("");

    dokumen
      .getPage(halaman)
      .then((page) => {
        if (!aktif || !canvasRef.current) return;
        const viewport = page.getViewport({ scale: zoom });
        const canvas = canvasRef.current;
        const context = canvas.getContext("2d");
        if (!context) throw new Error("Canvas context unavailable");

        const ratio = window.devicePixelRatio || 1;
        canvas.width = Math.floor(viewport.width * ratio);
        canvas.height = Math.floor(viewport.height * ratio);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        context.setTransform(ratio, 0, 0, ratio, 0, 0);

        const renderTask = page.render({
  canvas,
  canvasContext: context,
  viewport,
});
        tugas = renderTask;
        return renderTask.promise;
      })
      .catch((error: unknown) => {
        if (aktif && !(error instanceof Error && error.name === "RenderingCancelledException")) {
          setGalat("Halaman PDF tidak dapat dirender.");
        }
      })
      .finally(() => {
        if (aktif) setMerender(false);
      });

    return () => {
      aktif = false;
      tugas?.cancel();
    };
  }, [dokumen, halaman, zoom]);

  useEffect(() => {
    const onFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onFullscreen);
    return () => document.removeEventListener("fullscreenchange", onFullscreen);
  }, []);

  async function toggleFullscreen() {
    if (!areaRef.current) return;
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await areaRef.current.requestFullscreen();
    } catch {
      setGalat("Mode layar penuh tidak dapat dibuka pada browser ini.");
    }
  }

  return (
    <section ref={areaRef} className="rounded-xl border border-line bg-surface p-3 sm:p-4" aria-label={`Pratinjau ${nama}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <p className="min-w-0 text-body font-semibold text-ink wrap-anywhere">Pratinjau PDF</p>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setZoom((nilai) => Math.max(0.5, Math.round((nilai - 0.1) * 10) / 10))}
            disabled={zoom <= 0.5}
            className={secondaryButtonClass}
            aria-label="Perkecil pratinjau"
          >
            <Minus className="size-4" aria-hidden="true" />
          </button>
          <span className="min-w-12 text-center text-body tabular-nums text-muted">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            onClick={() => setZoom((nilai) => Math.min(2, Math.round((nilai + 0.1) * 10) / 10))}
            disabled={zoom >= 2}
            className={secondaryButtonClass}
            aria-label="Perbesar pratinjau"
          >
            <Plus className="size-4" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => void toggleFullscreen()} className={secondaryButtonClass}>
            <Maximize className="size-4" aria-hidden="true" />
            {fullscreen ? "Keluar layar penuh" : "Layar penuh"}
          </button>
        </div>
      </div>

      {memuat ? (
        <p role="status" className="py-10 text-center text-body text-muted">Memuat dokumen PDF…</p>
      ) : galat ? (
        <p role="alert" className="py-10 text-center text-body text-danger">{galat}</p>
      ) : dokumen ? (
        <>
          <div className="flex items-center justify-between gap-3 border-b border-line py-3">
            <button
              type="button"
              onClick={() => setHalaman((nilai) => Math.max(1, nilai - 1))}
              disabled={halaman <= 1}
              className={`${secondaryButtonClass} disabled:opacity-50`}
            >
              Sebelumnya
            </button>
            <p className="text-body text-muted" aria-live="polite">
              Halaman <span className="font-semibold text-ink">{halaman}</span> dari {dokumen.numPages}
              {merender ? " · Merender…" : ""}
            </p>
            <button
              type="button"
              onClick={() => setHalaman((nilai) => Math.min(dokumen.numPages, nilai + 1))}
              disabled={halaman >= dokumen.numPages}
              className={`${secondaryButtonClass} disabled:opacity-50`}
            >
              Berikutnya
            </button>
          </div>
          <div className="max-h-[75vh] overflow-auto bg-page p-3 text-center">
            <canvas ref={canvasRef} className="mx-auto max-w-full shadow-md" />
          </div>
        </>
      ) : null}
    </section>
  );
}
