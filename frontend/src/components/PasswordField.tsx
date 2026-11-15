import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { inputClass } from "./ui";

interface Props {
  id: string;
  label: string;
  value: string;
  onChange: (nilai: string) => void;
  autoComplete: string;
}

export function PasswordField({ id, label, value, onChange, autoComplete }: Props) {
  const [terlihat, setTerlihat] = useState(false);

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-body font-medium text-ink">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={terlihat ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          required
          className={`${inputClass} pr-11`}
        />
        <button
          type="button"
          onClick={() => setTerlihat((v) => !v)}
          aria-label={terlihat ? "Sembunyikan password" : "Tampilkan password"}
          aria-pressed={terlihat}
          className="absolute inset-y-0 right-0 grid w-11 place-items-center text-muted hover:text-ink"
        >
          {terlihat ? <EyeOff className="size-5" aria-hidden="true" /> : <Eye className="size-5" aria-hidden="true" />}
        </button>
      </div>
    </div>
  );
}