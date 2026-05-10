import sqlite3
import logging
try:
    import models
    from models import DB_BACKEND
except ImportError:
    try:
        from . import models
        from .models import DB_BACKEND
    except (ImportError, ValueError):
        from sync_worker import models
        from sync_worker.models import DB_BACKEND



logger = logging.getLogger(__name__)

def calculate_stats_for_period(cursor, donem_tipi, donem_degeri, where_clause, params):
    """
    Belirli bir dönem için GENEL, KATEGORİ ve MARKA bazlı en çok satanları hesaplar.
    """
    ph = "%s" if DB_BACKEND == "postgresql" else "?"

    try:
        # 1. GENEL (Tüm ürünler arasında Top 1)
        cursor.execute(f"""
            SELECT
                u.ad,
                SUM(s.tutar) as total_revenue,
                SUM(s.miktar) as total_qty
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            {where_clause}
            GROUP BY u.ad
            ORDER BY total_revenue DESC
            LIMIT 1
        """, params)

        row = cursor.fetchone()
        if row:
            cursor.execute(f"""
                INSERT INTO encoksatanlar (donem_tipi, donem_degeri, grup_tipi, grup_degeri, urun_ad, toplam_ciro, toplam_adet, updated_at)
                VALUES ({ph}, {ph}, 'GENEL', 'ALL', {ph}, {ph}, {ph}, CURRENT_TIMESTAMP)
                ON CONFLICT(donem_tipi, donem_degeri, grup_tipi, grup_degeri) DO UPDATE SET
                    urun_ad = EXCLUDED.urun_ad,
                    toplam_ciro = EXCLUDED.toplam_ciro,
                    toplam_adet = EXCLUDED.toplam_adet,
                    updated_at = CURRENT_TIMESTAMP
            """, (donem_tipi, donem_degeri, row[0], row[1], row[2]))

        # 2. KATEGORİ BAZLI (Her ana kategori için Top 1)
        query_cat = f"""
            WITH Ranked AS (
                SELECT
                    k.ana as grup_adi,
                    u.ad as urun_adi,
                    SUM(s.tutar) as cirosu,
                    SUM(s.miktar) as adedi,
                    ROW_NUMBER() OVER (PARTITION BY k.ana ORDER BY SUM(s.tutar) DESC) as rn
                FROM satislar s
                JOIN urunler u ON s.urun_id = u.id
                JOIN kategoriler k ON u.kategori_id = k.id
                {where_clause}
                GROUP BY k.ana, u.ad
            )
            SELECT grup_adi, urun_adi, cirosu, adedi
            FROM Ranked
            WHERE rn = 1
        """
        cursor.execute(query_cat, params)
        rows_cat = cursor.fetchall()

        for r in rows_cat:
            cursor.execute(f"""
                INSERT INTO encoksatanlar (donem_tipi, donem_degeri, grup_tipi, grup_degeri, urun_ad, toplam_ciro, toplam_adet, updated_at)
                VALUES ({ph}, {ph}, 'KATEGORI', {ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP)
                ON CONFLICT(donem_tipi, donem_degeri, grup_tipi, grup_degeri) DO UPDATE SET
                    urun_ad = EXCLUDED.urun_ad,
                    toplam_ciro = EXCLUDED.toplam_ciro,
                    toplam_adet = EXCLUDED.toplam_adet,
                    updated_at = CURRENT_TIMESTAMP
            """, (donem_tipi, donem_degeri, r[0], r[1], r[2], r[3]))

        # 3. MARKA BAZLI (Her marka için Top 1)
        query_brand = f"""
            WITH Ranked AS (
                SELECT
                    m.ad as grup_adi,
                    u.ad as urun_adi,
                    SUM(s.tutar) as cirosu,
                    SUM(s.miktar) as adedi,
                    ROW_NUMBER() OVER (PARTITION BY m.ad ORDER BY SUM(s.tutar) DESC) as rn
                FROM satislar s
                JOIN urunler u ON s.urun_id = u.id
                JOIN markalar m ON u.marka_id = m.id
                {where_clause}
                GROUP BY m.ad, u.ad
            )
            SELECT grup_adi, urun_adi, cirosu, adedi
            FROM Ranked
            WHERE rn = 1
        """
        cursor.execute(query_brand, params)
        rows_brand = cursor.fetchall()

        for r in rows_brand:
            cursor.execute(f"""
                INSERT INTO encoksatanlar (donem_tipi, donem_degeri, grup_tipi, grup_degeri, urun_ad, toplam_ciro, toplam_adet, updated_at)
                VALUES ({ph}, {ph}, 'MARKA', {ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP)
                ON CONFLICT(donem_tipi, donem_degeri, grup_tipi, grup_degeri) DO UPDATE SET
                    urun_ad = EXCLUDED.urun_ad,
                    toplam_ciro = EXCLUDED.toplam_ciro,
                    toplam_adet = EXCLUDED.toplam_adet,
                    updated_at = CURRENT_TIMESTAMP
            """, (donem_tipi, donem_degeri, r[0], r[1], r[2], r[3]))

    except Exception as e:
        logger.error(f"❌ İstatistik detayı hesaplanırken hata ({donem_tipi} - {donem_degeri}): {e}")


def update_best_sellers(cursor, year=None, month=None):
    """
    En çok satan ürünleri günceller.
    year/month verilirse o dönemi, verilmezse GLOBAL dönemi günceller.
    """
    if year and month:
        # 1. AY
        month_str = f"{year}-{month:02d}"
        logger.info(f"   🏆 İstatistikler güncelleniyor (Detaylı): {month_str}...")
        from models import DB_BACKEND
        if DB_BACKEND == "postgresql":
            calculate_stats_for_period(cursor, 'AY', month_str, "WHERE TO_CHAR(s.tarih, 'YYYY-MM') = %s", (month_str,))
        else:
            calculate_stats_for_period(cursor, 'AY', month_str, "WHERE strftime('%Y-%m', s.tarih) = ?", (month_str,))

        # 2. YIL
        year_str = str(year)
        logger.info(f"   🏆 Yıllık İstatistik güncelleniyor (Detaylı): {year_str}...")
        if DB_BACKEND == "postgresql":
            calculate_stats_for_period(cursor, 'YIL', year_str, "WHERE TO_CHAR(s.tarih, 'YYYY') = %s", (year_str,))
        else:
            calculate_stats_for_period(cursor, 'YIL', year_str, "WHERE strftime('%Y', s.tarih) = ?", (year_str,))

    else:
        # GLOBAL
        logger.info(f"   🏆 GLOBAL İstatistik güncelleniyor (Detaylı)...")
        calculate_stats_for_period(cursor, 'GLOBAL', 'ALL', "", ())
