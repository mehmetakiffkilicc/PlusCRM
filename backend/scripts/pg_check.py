import os
import psycopg2
from psycopg2.extras import RealDictCursor
from decouple import Config, RepositoryEnv

# .env yükle
BASE_DIR = 'c:\\Users\\Akif\\Desktop\\BackendFronend'
env_path = os.path.join(BASE_DIR, '.env')
config = Config(RepositoryEnv(env_path))

DATABASE_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"PostgreSQL bağlantısı kuruluyor...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("\n--- Genel Tarih Durumu ---")
    cursor.execute("SELECT MAX(tarih) as max_satis, (SELECT MAX(tarih) FROM product_daily_summary) as max_pds FROM satislar")
    row = cursor.fetchone()
    print(f"Satislar En Son: {row['max_satis']}")
    print(f"PDS En Son: {row['max_pds']}")
    print(f"Sistem Tarihi (SQL):")
    cursor.execute("SELECT CURRENT_DATE as bugun")
    print(f"Bugün: {cursor.fetchone()['bugun']}")

    print("\n--- Ürün Arama: DANA TRANC ---")
    cursor.execute("SELECT id, ad FROM urunler WHERE ad ILIKE '%DANA TRANC%' LIMIT 5")
    products = cursor.fetchall()
    
    for p in products:
        p_id = p['id']
        p_ad = p['ad']
        print(f"\nID: {p_id}, Ad: {p_ad}")

        # Son 7/30/90 gün hesabı için SQL üzerinden kontrol
        cursor.execute(f"""
            SELECT 
                COUNT(*) filter (where tarih >= CURRENT_DATE - INTERVAL '7 days') as s7_cnt,
                SUM(tutar) filter (where tarih >= CURRENT_DATE - INTERVAL '7 days') as s7_rev,
                COUNT(*) filter (where tarih >= CURRENT_DATE - INTERVAL '30 days') as s30_cnt,
                SUM(tutar) filter (where tarih >= CURRENT_DATE - INTERVAL '30 days') as s30_rev,
                COUNT(*) filter (where tarih >= CURRENT_DATE - INTERVAL '90 days') as s90_cnt,
                SUM(tutar) filter (where tarih >= CURRENT_DATE - INTERVAL '90 days') as s90_rev
            FROM satislar 
            WHERE urun_id = %s
        """, (p_id,))
        stats = cursor.fetchone()
        print(f"  Satislar Tablosu (Son X Gün):")
        print(f"    Son 7:  {stats['s7_cnt']} adet, {stats['s7_rev']} TL")
        print(f"    Son 30: {stats['s30_cnt']} adet, {stats['s30_rev']} TL")
        print(f"    Son 90: {stats['s90_cnt']} adet, {stats['s90_rev']} TL")

        # PDS kontrolü
        cursor.execute("SELECT SUM(unit_count) as units, SUM(revenue) as rev FROM product_daily_summary WHERE urun_id = %s AND tarih >= CURRENT_DATE - INTERVAL '90 days'", (p_id,))
        pds_stats = cursor.fetchone()
        print(f"  PDS Tablosu (Son 90 Gün):")
        print(f"    Toplam: {pds_stats['units']} adet, {pds_stats['rev']} TL")

        # Ham verideki en son 3 tarih
        cursor.execute("SELECT tarih, miktar, tutar FROM satislar WHERE urun_id = %s ORDER BY tarih DESC LIMIT 3", (p_id,))
        raw = cursor.fetchall()
        print(f"  En Son 3 Gerçek Satış:")
        for r in raw:
            print(f"    {r['tarih']}: {r['miktar']} adet, {r['tutar']} TL")

    conn.close()
except Exception as e:
    print(f"Hata: {e}")
