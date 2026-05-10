import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def check_encoding():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT bolge FROM magazalar")
        rows = cursor.fetchall()
        for row in rows:
            bolge = row[0]
            if bolge:
                print(f"Bölge: {bolge} | Hex: {bolge.encode('utf-8').hex()}")

if __name__ == "__main__":
    check_encoding()
