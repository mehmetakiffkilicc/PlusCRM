import os
import sys
import django
from django.db import connection

# Add the project directory to sys.path
sys.path.append('c:\\Users\\Akif\\Desktop\\BackendFronend\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_metrics():
    with connection.cursor() as cursor:
        print("Checking daily_metrics_summary...")
        cursor.execute("SELECT COUNT(*) FROM daily_metrics_summary")
        count = cursor.fetchone()[0]
        print(f"Total rows in daily_metrics_summary: {count}")
        
        if count > 0:
            cursor.execute("SELECT MIN(tarih), MAX(tarih) FROM daily_metrics_summary")
            min_date, max_date = cursor.fetchone()
            print(f"Date range: {min_date} to {max_date}")
            
            cursor.execute("SELECT SUM(revenue) FROM daily_metrics_summary")
            total_revenue = cursor.fetchone()[0]
            print(f"Total revenue in summary: {total_revenue}")
            
            # Check for current year
            from datetime import datetime
            curr_year = datetime.now().year
            cursor.execute("SELECT COUNT(*) FROM daily_metrics_summary WHERE EXTRACT(YEAR FROM tarih) = %s", [curr_year])
            curr_year_count = cursor.fetchone()[0]
            print(f"Rows for year {curr_year}: {curr_year_count}")
        
        print("\nChecking satislar...")
        cursor.execute("SELECT COUNT(*) FROM satislar")
        satislar_count = cursor.fetchone()[0]
        print(f"Total rows in satislar: {satislar_count}")
        
        print("\nChecking musteriler...")
        cursor.execute("SELECT COUNT(*) FROM musteriler")
        cust_count = cursor.fetchone()[0]
        print(f"Total rows in musteriler: {cust_count}")

if __name__ == "__main__":
    check_metrics()
