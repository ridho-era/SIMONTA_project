# SIMONTA: frontend

Vite + React + TypeScript + Tailwind v4.

```powershell
npm install
npm run dev        # http://localhost:5173 (backend harus jalan di 127.0.0.1:8000)
npm run typecheck
npm run build
```

- Permintaan `/api/*` diteruskan ke Django lewat proxy Vite (lihat `vite.config.ts`).
- Design tokens ada di `src/index.css` (blok `@theme`).
- Opsional: `VITE_ADMIN_URL` mengubah tautan Django admin pada halaman akun admin.