import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def check_hex():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT onay_durumu FROM daily_metrics_summary")
        rows = cursor.fetchall()
        for row in rows:
            val = row[0]
            if val:
                print(f"Value: {val} | Hex: {val.encode('utf-8').hex()}")

if __name__ == "__main__":
    check_hex()
