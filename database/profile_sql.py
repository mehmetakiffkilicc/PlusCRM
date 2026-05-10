import sqlite3
import time
import os
import datetime

db_path = r'c:\Users\Akif\Desktop\BackendFronend\database\sales_cache.db'

def profile_dashboard():
    print(f"Profiling Dashboard Data (Direct SQL Mode)")
    print("-" * 50)
    
    start_time = time.perf_counter()
    
    # 1. Connection
    t0 = time.perf_counter()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    t_conn = time.perf_counter() - t0
    print(f"1. Database Connection: {t_conn:.4f}s")

    # 2. KPIs & Trend (Fast Path)
    t1 = time.perf_counter()
    # Mocking filters (default home page)
    where_fast = "1=1"
    params_fast = []
    
    cursor.execute(f"""
        SELECT SUM(toplam_ciro) as rev, SUM(toplam_fis) as fis, COUNT(DISTINCT tarih) as days
        FROM GunlukCiroOzet WHERE {where_fast}
    """, params_fast)
    kpi_fast = cursor.fetchone()
    total_revenue = kpi_fast['rev'] or 0
    total_receipts = kpi_fast['fis'] or 0
    
    cursor.execute(f"SELECT COUNT(DISTINCT musteri_id) FROM Satislar WHERE {where_fast}", params_fast)
    total_customers = cursor.fetchone()[0] or 0
    
    cursor.execute(f"""
        SELECT strftime('%Y-%m', tarih) as month, SUM(toplam_ciro) as sales
        FROM GunlukCiroOzet WHERE {where_fast}
        GROUP BY month ORDER BY month
    """, params_fast)
    sales_by_month = [{'month': r['month'], 'sales': r['sales']} for r in cursor.fetchall()]
    
    t_kpis = time.perf_counter() - t1
    print(f"2. KPIs & Trend (Daily Summary + Satislar Unique): {t_kpis:.4f}s")

    # 3. Comparison Stats
    t2 = time.perf_counter()
    cursor.execute("""
        SELECT strftime('%Y', tarih) as year, strftime('%m', tarih) as month,
               SUM(toplam_ciro) as rev, SUM(toplam_fis) as fis, SUM(toplam_musteri) as cust
        FROM GunlukCiroOzet
        WHERE tarih >= '2024-01-01' AND tarih <= '2026-12-31'
        GROUP BY year, month
    """)
    rows = cursor.fetchall()
    t_comp = time.perf_counter() - t2
    print(f"3. Comparison Stats (3 Years Monthly): {t_comp:.4f}s")

    # 4. Churn
    t3 = time.perf_counter()
    cursor.execute("SELECT COUNT(*) FROM Musteriler")
    total_registered = cursor.fetchone()[0] or 0
    
    churn_thresh = '2025-10-14' # Mock churn date
    cursor.execute("""
        SELECT COUNT(DISTINCT musteri_id), COUNT(CASE WHEN max_date < ? THEN 1 END)
        FROM (SELECT musteri_id, MAX(tarih) as max_date FROM Satislar GROUP BY musteri_id)
    """, (churn_thresh,))
    churn_row = cursor.fetchone()
    t_churn = time.perf_counter() - t3
    print(f"4. Churn Calculation (Musteriler + Satislar Max Date Group): {t_churn:.4f}s")

    # 5. Segments (Optimized JOIN)
    t4 = time.perf_counter()
    cursor.execute("""
        SELECT m.rfm_segment, COUNT(DISTINCT m.id) as count, SUM(s_agg.rev) as revenue
        FROM Musteriler m
        JOIN (SELECT musteri_id, SUM(tutar) as rev FROM Satislar GROUP BY musteri_id) s_agg ON m.id = s_agg.musteri_id
        WHERE m.rfm_segment IS NOT NULL GROUP BY rfm_segment
    """)
    seg_rows = cursor.fetchall()
    t_segments = time.perf_counter() - t4
    print(f"5. Customer Segments (Optimized Join with Revenue): {t_segments:.4f}s")

    total_time = time.perf_counter() - start_time
    print("-" * 50)
    print(f"TOTAL DASHBOARD DATA LOAD TIME: {total_time:.4f}s")
    
    conn.close()

if __name__ == "__main__":
    profile_dashboard()
