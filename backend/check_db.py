import os
import psycopg2
from decouple import config

def check():
    url = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
    if not url:
        print("DATABASE_URL not set")
        return
    
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
        
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM satislar")
        count = cur.fetchone()[0]
        print(f"COUNT: {count}")
        
        cur.execute("SELECT tarih, SUM(tutar) FROM satislar GROUP BY tarih ORDER BY tarih DESC LIMIT 5")
        rows = cur.fetchall()
        print(f"LAST 5 DAYS: {rows}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check()
