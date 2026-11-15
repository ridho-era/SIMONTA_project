import type { ReactNode } from "react";

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface p-8 text-center text-body text-muted">
      {children}
    </div>
  );
}