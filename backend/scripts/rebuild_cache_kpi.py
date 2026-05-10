import sys
import os
import time
from datetime import datetime, timedelta

# Add current directory to path so we can import api
sys.path.append(os.getcwd())

from api import db_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rebuild_cache():
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()
        
        print(f"--- REBUILDING KPI CACHE (Backend: {db_engine.DB_BACKEND}) ---")
        t_start = time.perf_counter()
        
        def upsert(key, val):
            if db_engine.DB_BACKEND == "postgresql":
                cursor.execute(f"""
                    INSERT INTO cache_kpi (key, value, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
                """, (key, str(val)))
            else:
                cursor.execute(
                    f"INSERT OR REPLACE INTO cache_kpi (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (key, str(val))
                )

        # 1. Onay sayıları
        print("Calculating Approval counts...")
        cursor.execute("SELECT onay_durumu, COUNT(*) as cnt FROM musteriler GROUP BY onay_durumu")
        rows = cursor.fetchall()
        approved = 0
        unapproved = 0
        total_registered = 0
        for r in rows:
            status = str(r['onay_durumu'] or '').upper()
            cnt = r['cnt']
            total_registered += cnt
            if status == 'ONAYLI':
                approved += cnt
            else:
                unapproved += cnt
        
        upsert('approved_count', approved)
        upsert('unapproved_count', unapproved)
        upsert('total_registered_count', total_registered)
        print(f"  Approved: {approved}, Unapproved: {unapproved}, Total: {total_registered}")

        # 2. Aktif müşteri sayısı
        print("Calculating Active Customer count...")
        cursor.execute("SELECT COUNT(*) as cnt FROM musteridetayozet WHERE aktivite_durumu = 'AKTİF'")
        active_cnt = cursor.fetchone()['cnt'] or 0
        upsert('active_customer_count', active_cnt)
        print(f"  Active Customers (AKTİF): {active_cnt}")

        # 3. Churn Rate
        print("Calculating Churn Rate...")
        churn_thresh = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        cursor.execute(f"SELECT COUNT(*) as cnt FROM musteridetayozet WHERE son_alisveris_tarihi < {ph}", [churn_thresh])
        churned_count = cursor.fetchone()['cnt'] or 0
        churn_rate = round((churned_count / total_registered * 100), 1) if total_registered > 0 else 0
        upsert('churn_rate', churn_rate)
        print(f"  Churn Rate: {churn_rate}%")

        # 4. Loyalty Revenue Share
        print("Calculating Loyalty Share...")
        cursor.execute("SELECT SUM(toplam_ciro) as tr FROM gunlukciroozet")
        total_rev = cursor.fetchone()['tr'] or 0
        if total_rev > 0:
            loyal_segments = ('01-) Şampiyonlar', '02-) Potansiyel Şampiyonlar', '03-) Sadık Müşteriler', '11-) Yüksek Harcama Yapanlar')
            cursor.execute(f"SELECT SUM(toplam_harcama) as loyal_rev FROM musteridetayozet WHERE rfm_segment IN ({','.join([ph]*len(loyal_segments))})", list(loyal_segments))
            loyal_rev = cursor.fetchone()['loyal_rev'] or 0
            loyalty_share = round((loyal_rev / total_rev * 100), 1)
            upsert('loyalty_revenue_share', loyalty_share)
            print(f"  Loyalty Share: {loyalty_share}%")
        else:
            upsert('loyalty_revenue_share', 0)

        # 5. Brand & Product counts
        print("Calculating Brand/Product counts...")
        cursor.execute("SELECT COUNT(DISTINCT marka_id) as cnt FROM urunler WHERE marka_id IS NOT NULL")
        brand_cnt = cursor.fetchone()['cnt'] or 0
        upsert('total_brands_count', brand_cnt)
        cursor.execute("SELECT COUNT(DISTINCT ad) as cnt FROM urunler WHERE ad IS NOT NULL AND ad != ''")
        prod_cnt = cursor.fetchone()['cnt'] or 0
        upsert('total_products_count', prod_cnt)
        print(f"  Brands: {brand_cnt}, Products: {prod_cnt}")

        # 6. Dates
        print("Updating Date Markers...")
        cursor.execute("SELECT MAX(tarih) as md FROM gunlukciroozet")
        ozet_max = cursor.fetchone()['md']
        cursor.execute("SELECT MAX(tarih) as md FROM satislar")
        satis_max = cursor.fetchone()['md']
        
        from datetime import date as _date
        ref_date = _date(2020, 1, 1)
        
        def to_date(val):
            if val is None: return None
            if isinstance(val, str): return datetime.strptime(val[:10], "%Y-%m-%d").date()
            if hasattr(val, 'date'): return val.date() # if it's datetime
            return val # already date
            
        d_ozet = to_date(ozet_max)
        if d_ozet:
            upsert('ozet_max_tarih_ts', (d_ozet - ref_date).days)
            
        d_satis = to_date(satis_max)
        if d_satis:
            upsert('satislar_max_tarih_ts', (d_satis - ref_date).days)

        conn.commit()
        print(f"\n✅ Cache successfully rebuilt in {time.perf_counter() - t_start:.2f}s")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            db_engine.release_connection(conn)

if __name__ == "__main__":
    rebuild_cache()
