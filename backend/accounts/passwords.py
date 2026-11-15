from django.utils.crypto import get_random_string

# Tanpa karakter yang mudah tertukar (0/O, 1/l/I).
TEMP_PASSWORD_CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"


def buat_password_sementara(panjang=12):
    return get_random_string(panjang, allowed_chars=TEMP_PASSWORD_CHARS)