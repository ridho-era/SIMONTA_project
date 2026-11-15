import { useRef, useState } from "react";
import { FileUp, X } from "lucide-react";

import { formatUkuran } from "../../lib/berkas";
import { secondaryButtonClass } from "../ui";

interface Props {
  berkas: File | null;
  onPilih: (berkas: File | null) => void;
  ekstensi: string[];
  maksMb: number;
  disabled?: boolean;
}

export function DropZone({ berkas, onPilih, ekstensi, maksMb, disabled = false }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [seret, setSeret] = useState(false);
  const jenis = ekstensi.map((e) => e.replace(".", "").toUpperCase()).join(" atau ");

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setSeret(true);
      }}
      onDragLeave={() => setSeret(false)}
      onDrop={(e) => {
        e.preventDefault();
        setSeret(false);
        const file = e.dataTransfer.files[0];
        if (!disabled && file) onPilih(file);
      }}
      className={`rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
        seret ? "border-primary-2 bg-tint" : "border-line bg-page"
      }`}
    >
      <input
        ref={input}
        type="file"
        hidden
        accept={ekstensi.join(",")}
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onPilih(file);
          e.target.value = "";
        }}
      />
      <FileUp className="mx-auto size-8 text-primary-2" aria-hidden="true" />

      {berkas ? (
        <div className="mt-2 flex items-center justify-center gap-2">
          <p className="min-w-0 text-body font-semibold text-ink wrap-anywhere">
            {berkas.name} <span className="font-normal text-muted">({formatUkuran(berkas.size)})</span>
          </p>
          <button
            type="button"
            onClick={() => onPilih(null)}
            disabled={disabled}
            aria-label="Hapus pilihan berkas"
            className="grid size-8 shrink-0 place-items-center rounded-md text-muted hover:bg-tint"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <p className="mt-2 text-body text-ink">Tarik berkas ke sini, atau pilih dari komputer Anda.</p>
      )}

      <p className="mt-1 text-label text-muted">
        {jenis}, maksimal {maksMb} MB
      </p>
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={disabled}
        className={`${secondaryButtonClass} mt-4`}
      >
        {berkas ? "Ganti berkas" : "Pilih berkas"}
      </button>
    </div>
  );
}