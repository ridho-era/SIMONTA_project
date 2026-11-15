"""Validasi berkas unggahan (F-04). Tanpa ketergantungan Django agar mudah diuji."""
import io
import os
import re
import zipfile
from dataclasses import dataclass

from pypdf import PdfReader

MAKS_UKURAN = 15 * 1024 * 1024  # 15 MB
EKSTENSI = (".pdf", ".docx")
MAKS_ISI_DOCX = 200 * 1024 * 1024  # batas ukuran setelah dikembangkan (anti zip bomb)
MAKS_PANJANG_NAMA = 255


class BerkasError(Exception):
    """Berkas tidak memenuhi syarat; pesannya aman ditampilkan ke pengguna."""


@dataclass
class HasilValidasi:
    nama_asli: str
    ekstensi: str
    ukuran: int
    halaman: int | None


def bersihkan_nama(nama: str) -> str:
    """Hanya nama berkas (tanpa folder), tanpa karakter kontrol, maksimal 255 karakter."""
    nama = (nama or "").replace("\\", "/").split("/")[-1]
    nama = re.sub(r"[\x00-\x1f\x7f]", "", nama).strip()
    stem, ekstensi = os.path.splitext(nama)
    return stem[: MAKS_PANJANG_NAMA - len(ekstensi)] + ekstensi


def _periksa_pdf(data: bytes) -> int:
    if b"%PDF-" not in data[:1024]:
        raise BerkasError("Isi berkas bukan PDF yang valid.")
    try:
        pembaca = PdfReader(io.BytesIO(data))
        if pembaca.is_encrypted:
            raise BerkasError("PDF yang dikunci dengan password tidak dapat diterima.")
        halaman = len(pembaca.pages)
    except BerkasError:
        raise
    except Exception:
        raise BerkasError("PDF rusak atau tidak dapat dibaca.") from None
    if halaman < 1:
        raise BerkasError("PDF tidak memiliki halaman.")
    return halaman


def _periksa_docx(data: bytes) -> None:
    buf = io.BytesIO(data)
    if not zipfile.is_zipfile(buf):
        raise BerkasError("Isi berkas bukan DOCX yang valid.")
    try:
        with zipfile.ZipFile(buf) as arsip:
            nama = set(arsip.namelist())
            total = sum(info.file_size for info in arsip.infolist())
    except zipfile.BadZipFile:
        raise BerkasError("DOCX rusak atau tidak dapat dibaca.") from None
    if "[Content_Types].xml" not in nama or "word/document.xml" not in nama:
        raise BerkasError("Isi berkas bukan DOCX yang valid.")
    if "word/vbaProject.bin" in nama:
        raise BerkasError("DOCX yang memuat makro tidak dapat diterima.")
    if total > MAKS_ISI_DOCX:
        raise BerkasError("Isi DOCX terlalu besar.")


def validasi_berkas(berkas) -> HasilValidasi:
    """Memeriksa ekstensi, ukuran, dan isi sebenarnya (bukan header Content-Type klien)."""
    nama = bersihkan_nama(getattr(berkas, "name", "") or "")
    ekstensi = os.path.splitext(nama)[1].lower()
    if ekstensi not in EKSTENSI:
        raise BerkasError("Hanya berkas PDF atau DOCX yang dapat diunggah.")
    ukuran = berkas.size
    if ukuran == 0:
        raise BerkasError("Berkas kosong.")
    if ukuran > MAKS_UKURAN:
        raise BerkasError(f"Ukuran berkas melebihi {MAKS_UKURAN // (1024 * 1024)} MB.")
    berkas.seek(0)
    try:
        data = berkas.read()
    finally:
        berkas.seek(0)
    if ekstensi == ".pdf":
        halaman = _periksa_pdf(data)
    else:
        _periksa_docx(data)
        halaman = None
    return HasilValidasi(nama_asli=nama, ekstensi=ekstensi, ukuran=ukuran, halaman=halaman)