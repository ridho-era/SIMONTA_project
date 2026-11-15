from rest_framework.authentication import SessionAuthentication


class CsrfEnforcedAuthentication(SessionAuthentication):
    """Selalu memeriksa token CSRF, termasuk untuk pengguna yang belum masuk.

    Dipakai pada endpoint login agar terlindung dari login CSRF. Kelas ini tidak
    pernah mengautentikasi siapa pun (selalu mengembalikan None).
    """

    def authenticate(self, request):
        self.enforce_csrf(request)
        return None