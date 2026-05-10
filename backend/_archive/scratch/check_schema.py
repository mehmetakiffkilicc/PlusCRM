import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def check_schema():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM daily_metrics_summary LIMIT 0")
        columns = [desc[0] for desc in cursor.description]
        print(f"Columns: {columns}")

if __name__ == "__main__":
    check_schema()
