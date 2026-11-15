#!/usr/bin/env python
"""Utilitas baris perintah Django untuk SIMONTA."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django tidak ditemukan. Aktifkan virtualenv dan jalankan "
            "'pip install -r requirements.txt'."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()