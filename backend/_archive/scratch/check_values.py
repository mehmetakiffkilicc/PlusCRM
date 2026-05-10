import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def check_values():
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT customer_type FROM daily_metrics_summary")
        print(f"Customer Types: {cursor.fetchall()}")
        cursor.execute("SELECT DISTINCT onay_durumu FROM daily_metrics_summary")
        print(f"Onay Durumu: {cursor.fetchall()}")

if __name__ == "__main__":
    check_values()
