import csv
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDosen, IsMahasiswa
from dokumen.services import ta_saya
from milestone.models import Milestone
from keterlambatan.services import (
    ringkasan_denda_dosen,
    ringkasan_denda_mahasiswa,
    sanksi_milestone,
)

from .services import (
    daftar_mahasiswa_bimbingan,
    dashboard_dosen,
    dashboard_mahasiswa,
    paginasi_mahasiswa_bimbingan,
)


def _aman_untuk_spreadsheet(nilai):
    if nilai is None:
        return ""
    if isinstance(nilai, str) and nilai.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + nilai
    return nilai


def _baris_ekspor(payload):
    for item in payload["hasil"]:
        tahap = item["tahap_aktif"] or {}
        versi = item["versi_menunggu"] or {}
        yield [
            item["mahasiswa"]["nama_lengkap"],
            item["mahasiswa"]["identifier"],
            item["tugas_akhir"]["judul"],
            item["tugas_akhir"]["periode"],
            item["status_label"],
            item["progres"],
            tahap.get("nama", ""),
            tahap.get("target", ""),
            versi.get("nama_asli", ""),
        ]


def _ekspor_csv(payload):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="mahasiswa-bimbingan.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "Nama mahasiswa", "NPM", "Judul tugas akhir", "Periode", "Status",
        "Progres (%)", "Tahap aktif", "Target", "Berkas menunggu review",
    ])
    for row in _baris_ekspor(payload):
        writer.writerow([_aman_untuk_spreadsheet(value) for value in row])
    return response


def _ekspor_xlsx(payload):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Mahasiswa Bimbingan")
    sheet.append([
        "Nama mahasiswa", "NPM", "Judul tugas akhir", "Periode", "Status",
        "Progres (%)", "Tahap aktif", "Target", "Berkas menunggu review",
    ])
    for row in _baris_ekspor(payload):
        sheet.append([_aman_untuk_spreadsheet(value) for value in row])
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="mahasiswa-bimbingan.xlsx"'
    return response


class DashboardMahasiswaView(APIView):
    permission_classes = [IsMahasiswa]

    def get(self, request):
        payload = dashboard_mahasiswa(request.user)
        tugas_akhir = ta_saya(request.user)
        payload["ringkasan_denda"] = ringkasan_denda_mahasiswa(tugas_akhir)
        banner = payload.get("banner_keterlambatan")
        if tugas_akhir and banner:
            banner["sanksi_akademik"] = sanksi_milestone(
                tugas_akhir.pk, banner["milestone"]["id"]
            )
        return Response(payload)


class DashboardDosenView(APIView):
    permission_classes = [IsDosen]

    def get(self, request):
        payload = dashboard_dosen(request.user)
        payload["ringkasan_denda"] = ringkasan_denda_dosen(request.user)
        for item in payload["perlu_perhatian"]:
            milestone = Milestone.objects.filter(
                tugas_akhir_id=item["tugas_akhir"]["id"],
                nama=item["milestone"],
            ).first()
            if milestone:
                item["sanksi_akademik"] = sanksi_milestone(
                    item["tugas_akhir"]["id"], milestone.pk
                )
        return Response(payload)


class DaftarMahasiswaBimbinganView(APIView):
    permission_classes = [IsDosen]

    def get(self, request):
        try:
            payload = daftar_mahasiswa_bimbingan(request.user, request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        jenis_ekspor = request.query_params.get("ekspor", "").lower()
        if jenis_ekspor == "csv":
            return _ekspor_csv(payload)
        if jenis_ekspor == "xlsx":
            return _ekspor_xlsx(payload)
        if jenis_ekspor:
            return Response(
                {"detail": "Format ekspor harus csv atau xlsx."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return Response(paginasi_mahasiswa_bimbingan(payload, request.query_params.get("halaman", 1)))
        except (TypeError, ValueError):
            return Response({"detail": "Nomor halaman tidak valid."}, status=status.HTTP_400_BAD_REQUEST)