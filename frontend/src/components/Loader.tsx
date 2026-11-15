import { Loader2 } from "lucide-react";

export function FullPageLoader() {
  return (
    <div role="status" className="grid min-h-screen place-items-center bg-page text-muted">
      <Loader2 className="size-6 animate-spin" aria-hidden="true" />
      <span className="sr-only">Memuat…</span>
    </div>
  );
}