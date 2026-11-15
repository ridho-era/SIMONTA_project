"""Validasi lampiran pesan: ekstensi dan isi aktual, maksimal 15 MB."""
import io
import os
import re
import zipfile
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

MAKS_UKURAN = 15 * 1024 * 1024
EKSTENSI = (".pdf", ".docx", ".jpg", ".jpeg", ".png")


class LampiranPesanError(Exception):
    """Lampiran tidak memenuhi ketentuan dan aman ditampilkan ke pengguna."""


@dataclass
class HasilLampiran:
    nama_asli: str
    ekstensi: str
    ukuran: int


def bersihkan_nama(nama: str) -> str:
    nama = (nama or "").replace("\\", "/").split("/")[-1]
    nama = re.sub(r"[\x00-\x1f\x7f]", "", nama).strip()
    stem, ext = os.path.splitext(nama)
    return (stem[: 255 - len(ext)] + ext)[:255]


def _validasi_pdf(data: bytes) -> None:
    if b"%PDF-" not in data[:1024]:
        raise LampiranPesanError("Isi lampiran bukan PDF yang valid.")
    try:
        pembaca = PdfReader(io.BytesIO(data))
        if pembaca.is_encrypted or len(pembaca.pages) < 1:
            raise LampiranPesanError("PDF terkunci atau tidak memiliki halaman.")
    except LampiranPesanError:
        raise
    except Exception:
        raise LampiranPesanError("PDF rusak atau tidak dapat dibaca.") from None


def _validasi_docx(data: bytes) -> None:
    buffer = io.BytesIO(data)
    if not zipfile.is_zipfile(buffer):
        raise LampiranPesanError("Isi lampiran bukan DOCX yang valid.")
    try:
        with zipfile.ZipFile(buffer) as arsip:
            nama = set(arsip.namelist())
            total = sum(item.file_size for item in arsip.infolist())
            if "[Content_Types].xml" not in nama or "word/document.xml" not in nama:
                raise LampiranPesanError("Struktur DOCX tidak valid.")
            if total > 200 * 1024 * 1024:
                raise LampiranPesanError("Isi DOCX terlalu besar setelah diekstrak.")
            if any(n.lower().endswith("vbaproject.bin") for n in nama):
                raise LampiranPesanError("DOCX bermakro tidak dapat dilampirkan.")
    except LampiranPesanError:
        raise
    except (zipfile.BadZipFile, OSError):
        raise LampiranPesanError("DOCX rusak atau tidak dapat dibaca.") from None


def _validasi_gambar(data: bytes, ekstensi: str) -> None:
    try:
        with Image.open(io.BytesIO(data)) as gambar:
            format_aktual = (gambar.format or "").upper()
            if (ekstensi in {".jpg", ".jpeg"} and format_aktual != "JPEG") or (
                ekstensi == ".png" and format_aktual != "PNG"
            ):
                raise LampiranPesanError("Isi gambar tidak sesuai dengan ekstensi berkas.")
            gambar.verify()
    except LampiranPesanError:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise LampiranPesanError("Gambar rusak atau tidak dapat dibaca.") from None


def validasi_lampiran(berkas) -> HasilLampiran:
    nama = bersihkan_nama(getattr(berkas, "name", ""))
    ekstensi = os.path.splitext(nama)[1].lower()
    if ekstensi not in EKSTENSI:
        raise LampiranPesanError("Lampiran harus PDF, DOCX, JPG, JPEG, atau PNG.")
    ukuran = getattr(berkas, "size", 0) or 0
    if ukuran <= 0:
        raise LampiranPesanError("Lampiran kosong.")
    if ukuran > MAKS_UKURAN:
        raise LampiranPesanError("Ukuran lampiran maksimal 15 MB.")
    berkas.seek(0)
    try:
        data = berkas.read(MAKS_UKURAN + 1)
    finally:
        berkas.seek(0)
    if len(data) != ukuran or len(data) > MAKS_UKURAN:
        raise LampiranPesanError("Ukuran lampiran tidak valid.")

    if ekstensi == ".pdf":
        _validasi_pdf(data)
    elif ekstensi == ".docx":
        _validasi_docx(data)
    else:
        _validasi_gambar(data, ekstensi)
    return HasilLampiran(nama_asli=nama, ekstensi=ekstensi, ukuran=ukuran)
