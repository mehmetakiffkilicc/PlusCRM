import os, sys, django, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api import db_engine

def measure_queries():
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    is_pg = db_engine.DB_BACKEND == 'postgresql'
    
    with open("perf_test.txt", "w", encoding="utf-8") as f:
        f.write(f"Testing direct SQL queries on DB Backend: {db_engine.DB_BACKEND}\n")
        
        # Check what columns exist in musteriler
        cursor.execute("SELECT * FROM musteriler LIMIT 1")
        col_names = list(cursor.fetchone().keys())
        
        # 1. COUNT query
        start_time = time.time()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM musteriler m
            LEFT JOIN musteridetayozet o ON m.id = o.musteri_id
        """)
        cnt1 = cursor.fetchone()
        t1 = time.time() - start_time
        f.write(f"COUNT WITH JOIN: {t1:.4f} seconds (Total: {cnt1.get('cnt') if cnt1 else 'None'})\n")

        start_time = time.time()
        cursor.execute("SELECT COUNT(*) as cnt FROM musteriler")
        cnt2 = cursor.fetchone()
        t2 = time.time() - start_time
        f.write(f"COUNT WITHOUT JOIN (Optimized): {t2:.4f} seconds (Total: {cnt2.get('cnt') if cnt2 else 'None'})\n")

        # 2. Main List Query (Pagination load)
        order = "m.rfm_segment ASC NULLS LAST, m.id DESC" if is_pg else "m.rfm_segment ASC, m.id DESC"
        m_type_col = 'tip' if 'tip' in col_names else 'kurumsal_bireysel' if 'kurumsal_bireysel' in col_names else 'id'
        
        start_time = time.time()
        cursor.execute(f"""
            SELECT 
                m.id, m.ad, m.{m_type_col}, m.rfm_segment,
                o.son_alisveris_tarihi, o.toplam_harcama, o.toplam_alisveris
            FROM musteriler m
            LEFT JOIN musteridetayozet o ON m.id = o.musteri_id
            ORDER BY {order}
            LIMIT 10 OFFSET 0
        """)
        rows = cursor.fetchall()
        t3 = time.time() - start_time
        f.write(f"MAIN FULL JOIN QUERY (Default Sort): {t3:.4f} seconds (Fetched {len(rows)} rows)\n")

    db_engine.release_connection(conn)

if __name__ == "__main__":
    measure_queries()
