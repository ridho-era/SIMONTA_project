import { useEffect, type ReactNode } from "react";

import { useAuth } from "../auth/AuthContext";
import { ROLE_LABEL } from "../config/navigation";
import { formatTanggal, isoHariIni } from "../lib/format";

interface Props {
  title: string;
  parent?: string;
  subtitle?: string;
  children?: ReactNode;
}

export function PageFrame({ title, parent, subtitle, children }: Props) {
  const { user } = useAuth();

  useEffect(() => {
    document.title = `${title} · SIMONTA`;
  }, [title]);

  const peran = user && user.role !== "admin" ? ROLE_LABEL[user.role] : undefined;
  const remah = [peran, parent, title].filter((x): x is string => Boolean(x));

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-label text-muted">
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-1.5">
            {remah.map((teks, i) => {
              const terakhir = i === remah.length - 1;
              return (
                <li key={`${teks}-${i}`} className="flex items-center gap-1.5">
                  {i > 0 && <span aria-hidden="true">/</span>}
                  <span aria-current={terakhir ? "page" : undefined} className={terakhir ? "font-semibold text-ink" : ""}>
                    {teks}
                  </span>
                </li>
              );
            })}
          </ol>
        </nav>
        <time dateTime={isoHariIni()}>{formatTanggal(new Date())}</time>
      </div>

      <h1 className="mt-3 text-title font-semibold text-primary">{title}</h1>
      {subtitle && <p className="mt-1 text-body text-muted">{subtitle}</p>}
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}