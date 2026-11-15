import io
import os
import re
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

MAKS_BUKTI = 5 * 1024 * 1024
EKSTENSI_BUKTI = {".pdf", ".jpg", ".jpeg"}


class BuktiKeberatanError(Exception):
    """Bukti tidak memenuhi syarat dan aman ditampilkan kepada pengguna."""


@dataclass
class HasilValidasiBukti:
    nama_asli: str
    ukuran: int
    ekstensi: str


def bersihkan_nama_bukti(nama):
    nama = (nama or "").replace("\\", "/").split("/")[-1]
    nama = re.sub(r"[\x00-\x1f\x7f]", "", nama).strip()
    stem, ekstensi = os.path.splitext(nama)
    return (stem[: 255 - len(ekstensi)] + ekstensi)[:255]


def validasi_bukti(berkas):
    nama = bersihkan_nama_bukti(getattr(berkas, "name", ""))
    ekstensi = os.path.splitext(nama)[1].lower()
    if ekstensi not in EKSTENSI_BUKTI:
        raise BuktiKeberatanError("Bukti keberatan harus berupa PDF atau JPG/JPEG.")

    ukuran = getattr(berkas, "size", 0) or 0
    if ukuran <= 0:
        raise BuktiKeberatanError("Berkas bukti kosong.")
    if ukuran > MAKS_BUKTI:
        raise BuktiKeberatanError("Ukuran bukti maksimal 5 MB.")

    berkas.seek(0)
    try:
        data = berkas.read(MAKS_BUKTI + 1)
    finally:
        berkas.seek(0)
    if len(data) != ukuran or len(data) > MAKS_BUKTI:
        raise BuktiKeberatanError("Ukuran bukti tidak valid.")

    if ekstensi == ".pdf":
        if b"%PDF-" not in data[:1024]:
            raise BuktiKeberatanError("Isi berkas bukan PDF yang valid.")
        try:
            pdf = PdfReader(io.BytesIO(data))
            if pdf.is_encrypted or len(pdf.pages) < 1:
                raise BuktiKeberatanError("PDF terkunci atau tidak memiliki halaman.")
        except BuktiKeberatanError:
            raise
        except Exception:
            raise BuktiKeberatanError("PDF rusak atau tidak dapat dibaca.") from None
    else:
        try:
            with Image.open(io.BytesIO(data)) as gambar:
                if gambar.format != "JPEG":
                    raise BuktiKeberatanError("Isi gambar tidak sesuai dengan ekstensi JPG.")
                gambar.verify()
        except BuktiKeberatanError:
            raise
        except (UnidentifiedImageError, OSError, ValueError):
            raise BuktiKeberatanError("Gambar JPG rusak atau tidak dapat dibaca.") from None

    return HasilValidasiBukti(nama_asli=nama, ukuran=ukuran, ekstensi=ekstensi)
