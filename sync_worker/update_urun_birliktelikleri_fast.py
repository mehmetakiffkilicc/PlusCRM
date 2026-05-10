import os
import sys

# Ensure shared models are accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_path():
    try:
        from models import DB_PATH
        return DB_PATH
    except ImportError:
        return 'database/sales_cache.db'

def update_urun_birliktelikleri_table():
    print("Starting cross-category product association analysis...")
    from models import get_connection, DB_BACKEND
    conn = get_connection()
    cursor = conn.cursor()

    
    cursor.execute("DELETE FROM urunbirliktelikleri")
    
    float_type = "FLOAT" if DB_BACKEND == "sqlite" else "DOUBLE PRECISION"
    now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
    
    cursor.execute(f"""
        INSERT INTO urunbirliktelikleri 
        (urun_id_1, urun_id_2, confidence, lift, ortak_fis_sayisi, tip, analiz_tarihi)
        WITH 
        filtered_products AS (
            SELECT u.id
            FROM urunler u
            JOIN kategoriler k ON u.kategori_id = k.id
            WHERE k.ana NOT IN ('Meyve & Sebze - Yeşillik', 'Unlu Mamuller & Ekmek', 'Sarf & Gider', 'Sigara & Gazete', 'Horeca', 'İşletici kategorileri')
              AND u.ad NOT LIKE '%POŞET%' AND u.ad NOT LIKE 'POSET %' AND u.ad NOT LIKE '%EKMEK%'
        ),
        filtered_sales AS (
            SELECT s.fis_no, s.urun_id, COALESCE(NULLIF(k.alt2, ''), NULLIF(k.alt1, ''), k.ana) as kategori_ana
            FROM satislar s
            JOIN filtered_products fp ON s.urun_id = fp.id
            JOIN kategoriler k ON s.kategori_id = k.id
            WHERE s.tutar > 0
        ),
        valid_baskets AS (
            SELECT fis_no FROM filtered_sales GROUP BY fis_no HAVING COUNT(DISTINCT urun_id) BETWEEN 2 AND 30
        ),
        qualified_sales AS (
            SELECT f.fis_no, f.urun_id, f.kategori_ana FROM filtered_sales f JOIN valid_baskets v ON f.fis_no = v.fis_no
        ),
        total_receipts_calc AS (
            SELECT COUNT(DISTINCT fis_no) as total FROM qualified_sales
        ),
        product_frequencies AS (
            SELECT urun_id, COUNT(DISTINCT fis_no) as fis_count FROM qualified_sales GROUP BY urun_id HAVING COUNT(DISTINCT fis_no) >= 25
        ),
        cross_category_pairs AS (
            SELECT 
                s1.urun_id as urun_id_1, s2.urun_id as urun_id_2,
                COUNT(DISTINCT s1.fis_no) as ortak_fis_sayisi
            FROM qualified_sales s1
            JOIN qualified_sales s2 ON s1.fis_no = s2.fis_no AND s1.urun_id < s2.urun_id
            JOIN product_frequencies pf1 ON s1.urun_id = pf1.urun_id
            JOIN product_frequencies pf2 ON s2.urun_id = pf2.urun_id
            WHERE s1.kategori_ana != s2.kategori_ana
            GROUP BY s1.urun_id, s2.urun_id
            HAVING COUNT(DISTINCT s1.fis_no) >= 25
        ),
        metrics AS (
            SELECT 
                p.urun_id_1, p.urun_id_2, 
                (CAST(p.ortak_fis_sayisi AS {float_type})/CAST(f1.fis_count AS {float_type})) as conf,
                (CAST(p.ortak_fis_sayisi AS {float_type}) * CAST(tr.total AS {float_type})) / (CAST(f1.fis_count AS {float_type}) * CAST(f2.fis_count AS {float_type})) as lft,
                p.ortak_fis_sayisi
            FROM cross_category_pairs p
            JOIN product_frequencies f1 ON p.urun_id_1 = f1.urun_id
            JOIN product_frequencies f2 ON p.urun_id_2 = f2.urun_id
            CROSS JOIN total_receipts_calc tr
            WHERE (CAST(p.ortak_fis_sayisi AS {float_type}) * CAST(tr.total AS {float_type})) / (CAST(f1.fis_count AS {float_type}) * CAST(f2.fis_count AS {float_type})) >= 1.2
        )
        SELECT 
            urun_id_1, urun_id_2,
            conf, lft, ortak_fis_sayisi, 'CROSS_CATEGORY_SQL_DEEP', {now_func}
        FROM metrics
        ORDER BY lft DESC, ortak_fis_sayisi DESC
        LIMIT 5000
    """)
    conn.commit()
    conn.close()
    print("✅ Successfully updated urunbirliktelikleri!")

def update_group_associations():
    print("\n--- Starting Optimized Group-Level Association Analysis ---")
    from models import create_schema
    create_schema()
    
    from models import get_connection, DB_BACKEND
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM grupbirliktelikleri")
        conn.commit()
    except Exception:
        conn.rollback()

    print("Step 1: Filtering and capturing basic group sales...")
    cursor.execute("DROP TABLE IF EXISTS tmp_f_sales")
    cursor.execute("""
        CREATE TEMPORARY TABLE tmp_f_sales AS
        SELECT s.fis_no, s.musteri_id, s.marka_id, s.kategori_id, COALESCE(NULLIF(k.alt2, ''), NULLIF(k.alt1, ''), k.ana) as kategori_ana
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        JOIN kategoriler k ON s.kategori_id = k.id
        WHERE s.tutar > 0 
          AND k.ana NOT IN ('Meyve & Sebze - Yeşillik', 'Unlu Mamuller & Ekmek', 'Sarf & Gider', 'Sigara & Gazete', 'Horeca', 'İşletici kategorileri')
          AND u.ad NOT LIKE '%POŞET%' AND u.ad NOT LIKE 'POSET %' AND u.ad NOT LIKE '%EKMEK%'
          AND s.marka_id IS NOT NULL AND s.kategori_id IS NOT NULL
    """)
    
    print("Step 2: Calculating group frequencies (Brand + Category)...")
    cursor.execute("DROP TABLE IF EXISTS tmp_g_freqs")
    cursor.execute("""
        CREATE TEMPORARY TABLE tmp_g_freqs AS
        SELECT marka_id, kategori_id, COUNT(DISTINCT fis_no) as fis_count 
        FROM tmp_f_sales 
        GROUP BY marka_id, kategori_id 
        HAVING COUNT(DISTINCT fis_no) >= 50
    """)
    cursor.execute("CREATE INDEX idx_tgf_mk ON tmp_g_freqs(marka_id, kategori_id)")

    print("Step 3: Creating frequent group sales subset...")
    cursor.execute("DROP TABLE IF EXISTS tmp_freq_sales")
    cursor.execute("""
        CREATE TEMPORARY TABLE tmp_freq_sales AS
        SELECT DISTINCT tfs.fis_no, tfs.musteri_id, tfs.marka_id, tfs.kategori_id, tfs.kategori_ana
        FROM tmp_f_sales tfs
        JOIN tmp_g_freqs tgf ON tfs.marka_id = tgf.marka_id AND tfs.kategori_id = tgf.kategori_id
    """)
    cursor.execute("CREATE INDEX idx_tfs_fis ON tmp_freq_sales(fis_no)")
    cursor.execute("CREATE INDEX idx_tfs_grp ON tmp_freq_sales(marka_id, kategori_id)")
    
    cursor.execute("SELECT COUNT(DISTINCT fis_no) FROM tmp_freq_sales")
    total_receipts = cursor.fetchone()[0] or 1
    print(f"Total frequent baskets: {total_receipts}")

    float_type = "FLOAT" if DB_BACKEND == "sqlite" else "DOUBLE PRECISION"
    now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"

    # BRAND + CAT
    print("Calculating Brand + Category associations (Symmetric)...")
    cursor.execute(f"""
        INSERT INTO grupbirliktelikleri 
        (marka_id_1, kategori_id_1, marka_id_2, kategori_id_2, confidence, lift, ortak_fis_sayisi, ortak_musteri_sayisi, tip, analiz_tarihi)
        WITH pairs AS (
            SELECT 
                s1.marka_id as m1, s1.kategori_id as k1,
                s2.marka_id as m2, s2.kategori_id as k2,
                COUNT(DISTINCT s1.fis_no) as o_fis,
                COUNT(DISTINCT s1.musteri_id) as o_cust
            FROM tmp_freq_sales s1
            JOIN tmp_freq_sales s2 ON s1.fis_no = s2.fis_no 
                 AND (s1.marka_id < s2.marka_id OR (s1.marka_id = s2.marka_id AND s1.kategori_id < s2.kategori_id))
            WHERE s1.kategori_id != s2.kategori_id
            GROUP BY s1.marka_id, s1.kategori_id, s2.marka_id, s2.kategori_id
            HAVING COUNT(DISTINCT s1.fis_no) >= 50
        ),
        metrics AS (
            SELECT 
                m1, k1, m2, k2,
                (CAST(o_fis AS {float_type})/CAST(f1.fis_count AS {float_type})) as conf1, -- Confidence k1 -> k2
                (CAST(o_fis AS {float_type})/CAST(f2.fis_count AS {float_type})) as conf2, -- Confidence k2 -> k1
                (CAST(o_fis AS {float_type}) * CAST({total_receipts} AS {float_type})) / (CAST(f1.fis_count AS {float_type}) * CAST(f2.fis_count AS {float_type})) as lft,
                o_fis, o_cust
            FROM pairs p
            JOIN tmp_g_freqs f1 ON p.m1 = f1.marka_id AND p.k1 = f1.kategori_id
            JOIN tmp_g_freqs f2 ON p.m2 = f2.marka_id AND p.k2 = f2.kategori_id
            WHERE (CAST(o_fis AS {float_type}) * CAST({total_receipts} AS {float_type})) / (CAST(f1.fis_count AS {float_type}) * CAST(f2.fis_count AS {float_type})) >= 1.2
        )
        SELECT m1, k1, m2, k2, conf1, lft, o_fis, o_cust, 'BRAND_CAT_SQL', {now_func} FROM metrics
    """)
    
    # CAT ONLY (Decoupled from brand-level filtering)
    print("Calculating Pure Category associations (Symmetric, using all qualified sales)...")
    cursor.execute(f"""
        INSERT INTO grupbirliktelikleri 
        (marka_id_1, kategori_id_1, marka_id_2, kategori_id_2, confidence, lift, ortak_fis_sayisi, ortak_musteri_sayisi, tip, analiz_tarihi)
        WITH 
        cat_freqs AS (
            SELECT kategori_id, COUNT(DISTINCT fis_no) as fis_count 
            FROM tmp_f_sales 
            GROUP BY kategori_id 
            HAVING COUNT(DISTINCT fis_no) >= 50
        ),
        cat_sales AS (
            SELECT DISTINCT fis_no, musteri_id, kategori_id, kategori_ana FROM tmp_f_sales
            WHERE kategori_id IN (SELECT kategori_id FROM cat_freqs)
        ),
        pairs AS (
            SELECT 
                s1.kategori_id as k1, s2.kategori_id as k2,
                COUNT(DISTINCT s1.fis_no) as o_fis,
                COUNT(DISTINCT s1.musteri_id) as o_cust
            FROM cat_sales s1
            JOIN cat_sales s2 ON s1.fis_no = s2.fis_no AND s1.kategori_id < s2.kategori_id
            WHERE s1.kategori_id != s2.kategori_id
            GROUP BY s1.kategori_id, s2.kategori_id
            HAVING COUNT(DISTINCT s1.fis_no) >= 50
        ),
        metrics AS (
            SELECT 
                CAST(NULL AS INTEGER) as m1, k1, CAST(NULL AS INTEGER) as m2, k2,
                (CAST(o_fis AS {float_type})/CAST(f1.fis_count AS {float_type})) as conf1, -- Confidence k1 -> k2
                (CAST(o_fis AS {float_type})/CAST(f2.fis_count AS {float_type})) as conf2, -- Confidence k2 -> k1
                (CAST(o_fis AS {float_type}) * CAST({total_receipts} AS {float_type})) / (CAST(f1.fis_count AS {float_type}) * CAST(f2.fis_count AS {float_type})) as lft,
                o_fis, o_cust
            FROM pairs p
            JOIN cat_freqs f1 ON p.k1 = f1.kategori_id
            JOIN cat_freqs f2 ON p.k2 = f2.kategori_id
            WHERE (CAST(o_fis AS {float_type}) * CAST({total_receipts} AS {float_type})) / (CAST(f1.fis_count AS {float_type}) * CAST(f2.fis_count AS {float_type})) >= 1.2
        )
        SELECT m1, k1, m2, k2, conf1, lft, o_fis, o_cust, 'CAT_ONLY_SQL', {now_func} FROM metrics
    """)

    conn.commit()
    conn.close()
    print("✅ Successfully updated grupbirliktelikleri!")

if __name__ == "__main__":
    import sys
    update_urun_birliktelikleri_table()
    update_group_associations()
    sys.stdout.flush()