import csv
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Role, User, identifier_validator
from accounts.passwords import buat_password_sementara
from audit.models import AuditLog
from audit.services import catat_audit, snapshot

KOLOM_WAJIB = ("identifier", "nama_lengkap", "role")
ROLE_DIIZINKAN = {Role.MAHASISWA.value, Role.DOSEN.value}  # admin dibuat lewat createsuperuser/admin


class Command(BaseCommand):
    help = (
        "Mengimpor akun mahasiswa/dosen dari CSV (kolom: identifier, nama_lengkap, role, "
        "email_akademik, telepon). Setiap akun mendapat password sementara dan wajib "
        "menggantinya saat masuk pertama. Password sementara ditulis ke berkas keluaran."
    )

    def add_arguments(self, parser):
        parser.add_argument("berkas_csv", help="Path berkas CSV (UTF-8, pemisah koma atau titik koma).")
        parser.add_argument(
            "--keluaran",
            help="Path CSV hasil (identifier, nama, role, password sementara). "
            "Bawaan: media/impor/hasil_impor_<waktu>.csv",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Hanya memeriksa dan melaporkan; tidak menulis apa pun.",
        )

    def handle(self, *args, **options):
        path = Path(options["berkas_csv"])
        dry_run = options["dry_run"]
        if not path.is_file():
            raise CommandError(f"Berkas tidak ditemukan: {path}")

        rows = self._baca_csv(path)

        keluaran_path = None
        keluaran_file = None
        penulis = None
        if not dry_run:
            keluaran_path = self._tentukan_keluaran(options["keluaran"])
            try:
                keluaran_path.parent.mkdir(parents=True, exist_ok=True)
                keluaran_file = keluaran_path.open("w", newline="", encoding="utf-8-sig")
            except OSError as exc:
                raise CommandError(f"Tidak dapat menulis berkas keluaran: {exc}") from exc
            penulis = csv.writer(keluaran_file)
            penulis.writerow(["identifier", "nama_lengkap", "role", "password_sementara"])

        berhasil = 0
        gagal = []  # (nomor_baris, identifier, alasan)
        id_terlihat, email_terlihat = set(), set()
        total = 0

        try:
            for nomor, data in rows:
                if not any(data.values()):
                    continue  # baris kosong
                total += 1
                alasan = self._validasi(data, id_terlihat, email_terlihat)
                if alasan:
                    gagal.append((nomor, data.get("identifier", ""), alasan))
                    continue

                identifier = data["identifier"]
                id_terlihat.add(identifier.lower())
                email = User.objects.normalize_email(data.get("email_akademik", ""))
                if email:
                    email_terlihat.add(email.lower())

                if dry_run:
                    berhasil += 1
                    continue

                password = buat_password_sementara()
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            identifier,
                            password,
                            role=data["role"].lower(),
                            nama_lengkap=data["nama_lengkap"],
                            email_akademik=email or None,
                            telepon=data.get("telepon", ""),
                            must_change_password=True,
                        )
                        catat_audit(
                            None,
                            AuditLog.Aksi.TAMBAH,
                            user,
                            sesudah=snapshot(user),
                            keterangan=f"Impor CSV {path.name}, baris {nomor}",
                        )
                except IntegrityError:
                    gagal.append((nomor, identifier, "gagal disimpan: identifier atau email sudah dipakai"))
                    continue

                penulis.writerow([identifier, user.nama_lengkap, user.role, password])
                keluaran_file.flush()
                berhasil += 1
        finally:
            if keluaran_file:
                keluaran_file.close()

        self._laporan(total, berhasil, gagal, dry_run, keluaran_path)

    def _baca_csv(self, path):
        try:
            with path.open(newline="", encoding="utf-8-sig") as f:
                baris_pertama = f.readline()
                f.seek(0)
                delimiter = ";" if baris_pertama.count(";") > baris_pertama.count(",") else ","
                reader = csv.DictReader(f, delimiter=delimiter)
                kolom = [(k or "").strip().lower() for k in (reader.fieldnames or [])]
                kurang = [k for k in KOLOM_WAJIB if k not in kolom]
                if kurang:
                    raise CommandError(
                        "Kolom wajib tidak ada di CSV: " + ", ".join(kurang)
                        + ". Kolom yang dikenali: identifier, nama_lengkap, role, "
                        "email_akademik, telepon."
                    )
                reader.fieldnames = kolom
                hasil = []
                for nomor, row in enumerate(reader, start=2):  # baris 1 = header
                    data = {k: (v or "").strip() for k, v in row.items() if k}
                    hasil.append((nomor, data))
                return hasil
        except UnicodeDecodeError as exc:
            raise CommandError("Berkas bukan UTF-8. Simpan ulang CSV sebagai UTF-8.") from exc

    def _tentukan_keluaran(self, nilai):
        if nilai:
            return Path(nilai)
        stempel = timezone.localtime().strftime("%Y%m%d-%H%M%S")
        return Path(settings.MEDIA_ROOT) / "impor" / f"hasil_impor_{stempel}.csv"

    def _validasi(self, data, id_terlihat, email_terlihat):
        """Mengembalikan teks alasan bila baris tidak valid, atau None bila valid."""
        identifier = data.get("identifier", "")
        if not identifier:
            return "identifier kosong"
        if len(identifier) > 30:
            return "identifier lebih dari 30 karakter"
        try:
            identifier_validator(identifier)
        except ValidationError:
            return "identifier hanya boleh huruf, angka, titik, garis bawah, dan minus"
        if identifier.lower() in id_terlihat:
            return "identifier duplikat di dalam berkas"
        if User.objects.filter(identifier__iexact=identifier).exists():
            return "identifier sudah terdaftar"

        nama = data.get("nama_lengkap", "")
        if not nama:
            return "nama_lengkap kosong"
        if len(nama) > 150:
            return "nama_lengkap lebih dari 150 karakter"

        if data.get("role", "").lower() not in ROLE_DIIZINKAN:
            return "role harus 'mahasiswa' atau 'dosen'"

        email = User.objects.normalize_email(data.get("email_akademik", ""))
        if email:
            try:
                validate_email(email)
            except ValidationError:
                return "email_akademik tidak valid"
            if email.lower() in email_terlihat:
                return "email_akademik duplikat di dalam berkas"
            if User.objects.filter(email_akademik__iexact=email).exists():
                return "email_akademik sudah terdaftar"

        if len(data.get("telepon", "")) > 20:
            return "telepon lebih dari 20 karakter"
        return None

    def _laporan(self, total, berhasil, gagal, dry_run, keluaran_path):
        self.stdout.write("")
        if dry_run:
            self.stdout.write("Mode uji coba: tidak ada data yang ditulis.")
        self.stdout.write(f"Total baris data: {total}")
        self.stdout.write(self.style.SUCCESS(f"{'Valid' if dry_run else 'Berhasil'}: {berhasil}"))
        self.stdout.write(self.style.ERROR(f"Gagal: {len(gagal)}") if gagal else "Gagal: 0")
        for nomor, identifier, alasan in gagal:
            self.stdout.write(f"  Baris {nomor} [{identifier or '-'}]: {alasan}")
        if not dry_run and berhasil:
            self.stdout.write("")
            self.stdout.write(
                f"Password sementara disimpan di: {keluaran_path}\n"
                "Serahkan ke masing-masing pengguna lewat jalur aman, lalu hapus berkas itu."
            )