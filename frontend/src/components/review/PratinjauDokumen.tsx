import { lazy, Suspense } from "react";

import { PdfPreview } from "./PdfPreview";

const DocxPreview = lazy(() =>
  import("./DocxPreview").then((modul) => ({ default: modul.DocxPreview })),
);

interface Props {
  src: string;
  nama: string;
  versiId: number;
}

export function PratinjauDokumen({ src, nama, versiId }: Props) {
  const ekstensi = nama.split(".").pop()?.toLowerCase();

  if (ekstensi === "pdf") {
    return <PdfPreview src={src} nama={nama} />;
  }

  if (ekstensi === "docx") {
    return (
      <Suspense
        fallback={(
          <section className="rounded-xl border border-line bg-surface p-5">
            <p role="status" className="text-body text-muted">Menyiapkan viewer DOCX…</p>
          </section>
        )}
      >
        <DocxPreview src={src} nama={nama} versiId={versiId} />
      </Suspense>
    );
  }

  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h3 className="text-heading font-semibold text-primary">Pratinjau dokumen</h3>
      <p className="mt-2 text-body text-muted">Jenis berkas ini belum didukung untuk pratinjau.</p>
    </section>
  );
}
