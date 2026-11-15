import json

from django.core.serializers.json import DjangoJSONEncoder

from .models import AuditLog

# Tidak pernah ditulis ke log, apa pun admin yang meminta.
FIELD_SENSITIF = frozenset({"password"})


class _Encoder(DjangoJSONEncoder):
    """Seperti DjangoJSONEncoder, tetapi tipe lain (mis. berkas foto) dijadikan string."""

    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            return str(o)


def snapshot(objek, exclude=()):
    """Salinan nilai field konkret sebuah objek sebagai dict yang aman untuk JSON."""
    if objek is None:
        return None
    lewati = FIELD_SENSITIF | set(exclude)
    data = {}
    for field in objek._meta.concrete_fields:
        if field.name in lewati:
            continue
        data[field.attname] = field.value_from_object(objek)
    return json.loads(json.dumps(data, cls=_Encoder))


def diff(sebelum, sesudah):
    """Mengembalikan (sebelum, sesudah) yang hanya berisi field yang berubah."""
    kunci = set(sebelum) | set(sesudah)
    berubah = sorted(k for k in kunci if sebelum.get(k) != sesudah.get(k))
    return (
        {k: sebelum.get(k) for k in berubah},
        {k: sesudah.get(k) for k in berubah},
    )


def catat_audit(
    aktor,
    aksi,
    objek,
    *,
    sebelum=None,
    sesudah=None,
    keterangan="",
    objek_id=None,
    objek_repr=None,
):
    """Menulis satu baris AuditLog.

    objek_id dan objek_repr dapat diberikan eksplisit untuk objek yang sudah dihapus
    (pk instance menjadi None setelah delete).
    """
    aktor_valid = aktor if (aktor is not None and getattr(aktor, "pk", None)) else None
    return AuditLog.objects.create(
        aktor=aktor_valid,
        aktor_identifier=aktor_valid.identifier if aktor_valid else "",
        aksi=aksi,
        objek_tipe=objek._meta.label,
        objek_id=str(objek.pk if objek_id is None else objek_id),
        objek_repr=(str(objek) if objek_repr is None else objek_repr)[:255],
        sebelum=sebelum,
        sesudah=sesudah,
        keterangan=keterangan[:255],
    )