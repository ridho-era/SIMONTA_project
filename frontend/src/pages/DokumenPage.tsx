import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Info, Loader2 } from "lucide-react";

import { EmptyState } from "../components/EmptyState";
import { RiwayatBerkas } from "../components/dokumen/RiwayatBerkas";
import { UnggahForm } from "../components/dokumen/UnggahForm";
import { PageFrame } from "../components/PageFrame";
import { secondaryButtonClass } from "../components/ui";
import { useDokumenSaya } from "../hooks/useDokumen";

function KartuInfo() {
  return (
    <aside className="rounded-xl border border-line bg-info-bg p-5 text-info">
      <p className="flex items-center gap-2 text-heading font-semibold">
        <Info className="size-5 shrink-0" aria-hidden="true" />
        Riwayat dokumen ≠ penyelesaian milestone
      </p>
      <p className="mt-2 text-body">
        Mengunggah atau disetujuinya sebuah dokumen tidak mengubah progres. Milestone dinyatakan selesai hanya setelah
        pembimbing utama memverifikasinya di halaman Timeline milestone.
      </p>
    </aside>
  );
}

export default function DokumenPage() {
  const [params, setParams] = useSearchParams();
  const milestoneParam = Number(params.get("milestone")) || null;
  const [halaman, setHalaman] = useState(1);
  const { data, isLoading, isError, refetch, isFetching } = useDokumenSaya(milestoneParam, halaman);

  function saring(id: number | null) {
    setParams(id ? { milestone: String(id) } : {}, { replace: true });
    setHalaman(1);
  }

  let isi;
  if (isLoading) {
    isi = (
      <div role="status" className="flex items-center gap-2 text-muted">
        <Loader2 className="size-5 animate-spin" aria-hidden="true" />
        Memuat dokumen…
      </div>
    );
  } else if (isError || !data) {
    isi = (
      <EmptyState>
        <p>Data dokumen tidak dapat dimuat.</p>
        <button type="button" onClick={() => void refetch()} disabled={isFetching} className={`${secondaryButtonClass} mt-4`}>
          Coba lagi
        </button>
      </EmptyState>
    );
  } else if (!data.tugas_akhir) {
    isi = <EmptyState>Tugas akhir Anda belum didaftarkan. Hubungi admin Prodi.</EmptyState>;
  } else if (data.milestone.length === 0) {
    isi = <EmptyState>Belum ada tahapan milestone untuk tugas akhir Anda. Hubungi admin Prodi.</EmptyState>;
  } else {
    isi = (
      <div className="space-y-8">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <UnggahForm data={data} praPilih={milestoneParam} />
          <KartuInfo />
        </div>
        <RiwayatBerkas
          riwayat={data.riwayat}
          milestone={data.milestone}
          filter={milestoneParam}
          onFilter={saring}
          onHalaman={setHalaman}
          onUnggah={() => document.getElementById("unggah-milestone")?.focus()}
        />
      </div>
    );
  }

  return (
    <PageFrame title="Dokumen & unggahan" subtitle="Unggah draf per milestone dan pantau riwayat berkas Anda.">
      {isi}
    </PageFrame>
  );
}