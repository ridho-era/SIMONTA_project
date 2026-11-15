# SIMONTA: Sistem Monitoring Tugas Akhir

Prodi Sistem Informasi, UIN Raden Intan Lampung. Rujukan utama: `docs/` (PRD).

## Struktur

- `backend/`: Django 5 + Django REST Framework + MySQL 8
- `frontend/`: Vite + React + TypeScript + Tailwind (dibuat pada task berikutnya)
- `docs/`: PRD dan catatan progres

## Menjalankan backend (Windows, PowerShell)

1. Jalankan Laragon (Start All) dan buat database dengan charset `utf8mb4`
   dan collation `utf8mb4_unicode_ci` (nama sesuai `DB_NAME` di `.env`).
2. Di folder `backend/`:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   # isi SECRET_KEY dan kredensial database di .env
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

3. Cek `http://127.0.0.1:8000/api/v1/health/`, `http://127.0.0.1:8000/api/docs/`,
   dan masuk ke `http://127.0.0.1:8000/admin/` dengan akun superuser.

## Akun

- Model User kustom ada di `backend/accounts/`. Identifier (NPM/NIP) menjadi username.
- Mahasiswa dan dosen masuk lewat portal (`POST /api/v1/auth/login/`).
  Admin Prodi masuk lewat Django admin (`/admin/`).
- Tidak ada data contoh di repo. Akun dibuat lewat `createsuperuser`, Django admin,
  atau impor CSV.
- Reset password: Django admin > Pengguna > pilih akun > aksi "Reset password".

## Master data akademik (Django admin)

Urutan pengisian pada instalasi baru: Program studi, Periode akademik (satu aktif),
Template milestone (total bobot aktif tepat 100), Konfigurasi denda, Jenis sanksi,
lalu pengguna, Tugas akhir, dan penugasan dosen (inline di Tugas akhir).
Semua perubahan data akademik dan akun dicatat di **Audit > Audit log** (hanya baca).

## Impor pengguna dari CSV

Kolom: `identifier, nama_lengkap, role, email_akademik, telepon` (role: `mahasiswa` atau `dosen`).

```powershell
python manage.py import_pengguna C:\path\pengguna.csv --dry-run
python manage.py import_pengguna C:\path\pengguna.csv
```

Password sementara ditulis ke `backend/media/impor/hasil_impor_<waktu>.csv`
(atau path dari `--keluaran`). Serahkan ke pengguna lewat jalur aman, lalu hapus berkasnya.
Setiap akun wajib mengganti password saat masuk pertama.

## Tes

```powershell
python manage.py test --noinput
```