import sqlite3
import os
import sys

# DB yolunu tespit et (backend/api/db_engine.py'deki mantığa yakın)
db_path = 'c:\\Users\\Akif\\Desktop\\BackendFronend\\backend\\sales_cache.db'

print(f"Veritabanı kontrol ediliyor: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n--- Genel Durum ---")
    cursor.execute("SELECT MAX(tarih) as max_date FROM satislar")
    row = cursor.fetchone()
    print(f"Satislar En Son Tarih: {row['max_date']}")

    print("\n--- Ürün Kontrol: DANA TRANC ---")
    cursor.execute("SELECT id, ad FROM urunperadetay WHERE urunadi LIKE '%DANA TRANC%' LIMIT 5")
    rows = cursor.fetchall()
    if not rows:
        cursor.execute("SELECT id, ad FROM urunler WHERE ad LIKE '%DANA TRANC%' LIMIT 5")
        rows = cursor.fetchall()
    
    for r in rows:
        p_id = r['id']
        p_ad = r['ad']
        print(f"ID: {p_id}, Ad: {p_ad}")

        # Son satışları getir
        cursor.execute("SELECT tarih, miktar, tutar FROM satislar WHERE urun_id = ? ORDER BY tarih DESC LIMIT 5", (p_id,))
        sales = cursor.fetchall()
        print(f"  Son Satışlar (Ham):")
        for s in sales:
            print(f"    Tarih: {s['tarih']}, Miktar: {s['miktar']}, Tutar: {s['tutar']}")

        # PDS Özeti
        cursor.execute("SELECT tarih, unit_count, revenue FROM product_daily_summary WHERE urun_id = ? ORDER BY tarih DESC LIMIT 5", (p_id,))
        pds = cursor.fetchall()
        print(f"  PDS Özeti (Son 5 Gün):")
        for p in pds:
            print(f"    Tarih: {p['tarih']}, Miktar: {p['unit_count']}, Ciro: {p['revenue']}")

    conn.close()
except Exception as e:
    print(f"Hata: {e}")
