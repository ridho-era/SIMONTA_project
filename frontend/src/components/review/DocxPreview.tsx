import { useEffect, useState } from "react";
import mammoth from "mammoth";
import DOMPurify from "dompurify";
import { Loader2 } from "lucide-react";

import "./DocxPreview.css";

interface Props {
  src: string;
  nama: string;
  versiId: number;
}

export function DocxPreview({ src, nama, versiId }: Props) {
  const [html, setHtml] = useState("");
  const [memuat, setMemuat] = useState(true);
  const [galat, setGalat] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let aktif = true;

    async function muat() {
      setMemuat(true);
      setGalat("");
      setHtml("");
      try {
        const response = await fetch(src, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) {
          if (response.status === 410) {
            throw new Error("Tautan pratinjau kedaluwarsa. Muat ulang halaman untuk memperbaruinya.");
          }
          if (response.status === 403 || response.status === 404) {
            throw new Error("Anda tidak memiliki akses untuk melihat berkas ini.");
          }
          throw new Error("Berkas DOCX tidak dapat diambil dari server.");
        }

        const arrayBuffer = await response.arrayBuffer();
        const hasil = await mammoth.convertToHtml(
          { arrayBuffer },
          {
            includeDefaultStyleMap: true,
            includeEmbeddedStyleMap: false,
            externalFileAccess: false,
            ignoreEmptyParagraphs: false,
            idPrefix: `simonta-versi-${versiId}-`,
          },
        );

        // DOCX berasal dari unggahan pengguna. Sanitasi hasil konversi sebelum memasukkannya ke DOM.
        const aman = DOMPurify.sanitize(hasil.value, {
          USE_PROFILES: { html: true },
          SANITIZE_NAMED_PROPS: true,
          FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "form", "input", "button"],
          FORBID_ATTR: ["style", "srcset"],
        });

        if (aktif) {
          setHtml(aman);
          if (!aman.trim()) setGalat("Dokumen tidak memiliki teks yang dapat ditampilkan.");
        }
      } catch (error) {
        if (!aktif || (error instanceof Error && error.name === "AbortError")) return;
        setGalat(error instanceof Error ? error.message : "Pratinjau DOCX tidak dapat dimuat.");
      } finally {
        if (aktif) setMemuat(false);
      }
    }

    void muat();
    return () => {
      aktif = false;
      controller.abort();
    };
  }, [src, versiId]);

  return (
    <section className="rounded-xl border border-line bg-surface p-3 sm:p-4" aria-label={`Pratinjau ${nama}`}>
      <div className="border-b border-line pb-3">
        <h3 className="text-heading font-semibold text-primary">Pratinjau DOCX</h3>
        <p className="mt-1 text-label text-muted">
          Tampilan isi dokumen. Tata letak dan pemformatan kompleks mungkin berbeda dari Microsoft Word.
        </p>
      </div>

      {memuat ? (
        <div role="status" className="flex items-center justify-center gap-2 py-10 text-body text-muted">
          <Loader2 className="size-5 animate-spin" aria-hidden="true" />
          Memuat dan menyiapkan pratinjau DOCX…
        </div>
      ) : galat ? (
        <p role="alert" className="py-8 text-center text-body text-danger">{galat}</p>
      ) : (
        <div className="simonta-docx-scroll mt-3">
          <article className="simonta-docx-content" dangerouslySetInnerHTML={{ __html: html }} />
        </div>
      )}
    </section>
  );
}
