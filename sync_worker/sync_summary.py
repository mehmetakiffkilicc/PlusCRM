"""
Özet Tabloları Hesaplama ve Güncelleme
PowerBI KPI'larını SQLite'ta tutan özet tablolarını günceller

Bu script:
1. gunlukciroozet - Günlük toplam KPI'lar
2. magazagunlukozet - Mağaza bazlı günlük KPI'lar
"""

import sys
import os

# Base directory for imports
# Hem yerel hem de Docker ortamında (sync_worker'ın /app'e kopyalandığı durum) çalışacak şekilde
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(os.path.join(BASE_DIR, "backend")):
    # Eğer backend klasörü yoksa, muhtemelen Docker içindeyiz ve dosyalar kök dizindedir
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sqlite3
import logging
import time
from datetime import datetime, timedelta
from collections import defaultdict
from models import get_connection, DB_PATH, DB_BACKEND
from sync_stats import update_best_sellers
from db_logger import setup_db_logging
import subprocess

logger = logging.getLogger(__name__)
setup_db_logging(service_name='summary-worker')


def update_gunluk_ciro_ozet_daily(conn, target_date: str):
    """gunlukciroozet tablosunu güncelle"""
    cursor = conn.cursor()
    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    
    t_clause = "tarih" if DB_BACKEND == "postgresql" else "date(tarih)"
    # 1. Hesapla
    cursor.execute(f"""
        SELECT
            COALESCE(SUM(tutar), 0) as toplam_ciro,
            COUNT(DISTINCT fis_no) as toplam_fis,
            COUNT(DISTINCT musteri_id) as toplam_musteri,
            COALESCE(SUM(miktar), 0) as toplam_miktar,
            COUNT(DISTINCT urun_id) as sku_sayisi
        FROM satislar
        WHERE {t_clause} = {ph}
    """, (target_date,))
    row = cursor.fetchone()
    
    t_ciro = row["toplam_ciro"] or 0
    t_fis = row["toplam_fis"] or 0
    t_must = row["toplam_musteri"] or 0
    t_mikt = row["toplam_miktar"] or 0
    sku_s = row["sku_sayisi"] or 0
    s_ort = t_ciro / t_fis if t_fis > 0 else 0
    m_ciro = t_ciro / t_must if t_must > 0 else 0
    m_fis = t_fis / t_must if t_must > 0 else 0

    # 2. Kaydet
    if DB_BACKEND == "postgresql":
        cursor.execute(f"""
            INSERT INTO gunlukciroozet
            (tarih, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar,
             sepet_ortalamasi, musteri_basina_ciro, musteri_basina_fis, sku_sayisi, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, CURRENT_TIMESTAMP)
            ON CONFLICT (tarih) DO UPDATE SET
                toplam_ciro=EXCLUDED.toplam_ciro, toplam_fis=EXCLUDED.toplam_fis,
                toplam_musteri=EXCLUDED.toplam_musteri, toplam_miktar=EXCLUDED.toplam_miktar,
                sepet_ortalamasi=EXCLUDED.sepet_ortalamasi, musteri_basina_ciro=EXCLUDED.musteri_basina_ciro,
                musteri_basina_fis=EXCLUDED.musteri_basina_fis, sku_sayisi=EXCLUDED.sku_sayisi,
                updated_at=CURRENT_TIMESTAMP
        """, (target_date, t_ciro, t_fis, t_must, t_mikt, s_ort, m_ciro, m_fis, sku_s))
    else:
        cursor.execute(f"""
            INSERT OR REPLACE INTO gunlukciroozet
            (tarih, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar,
             sepet_ortalamasi, musteri_basina_ciro, musteri_basina_fis, sku_sayisi, updated_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, datetime('now'))
        """, (target_date, t_ciro, t_fis, t_must, t_mikt, s_ort, m_ciro, m_fis, sku_s))


def update_magaza_gunluk_ozet_daily(conn, target_date: str):
    """magazagunlukozet tablosunu güncelle"""
    cursor = conn.cursor()
    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    
    t_clause = "tarih" if DB_BACKEND == "postgresql" else "date(tarih)"
    # 1. Hesapla
    cursor.execute(f"""
        SELECT
            magaza_id,
            COALESCE(SUM(tutar), 0) as toplam_ciro,
            COUNT(DISTINCT fis_no) as toplam_fis,
            COUNT(DISTINCT musteri_id) as toplam_musteri,
            COALESCE(SUM(miktar), 0) as toplam_miktar,
            COUNT(DISTINCT urun_id) as sku_sayisi
        FROM satislar
        WHERE {t_clause} = {ph} AND magaza_id IS NOT NULL
        GROUP BY magaza_id
    """, (target_date,))
    
    rows = cursor.fetchall()
    
    # 2. Kaydet
    final_rows = []
    for row in rows:
        m_id = row[0]
        t_ciro = row[1] or 0
        t_fis = row[2] or 0
        t_must = row[3] or 0
        t_mikt = row[4] or 0
        sku_s = row[5] or 0
        s_ort = t_ciro / t_fis if t_fis > 0 else 0
        final_rows.append((target_date, m_id, t_ciro, t_fis, t_must, t_mikt, s_ort, sku_s))

    if not final_rows:
        return

    if DB_BACKEND == "postgresql":
        from psycopg2.extras import execute_values
        query = """
            INSERT INTO magazagunlukozet
            (tarih, magaza_id, toplam_ciro, toplam_fis, toplam_musteri,
             toplam_miktar, sepet_ortalamasi, sku_sayisi)
            VALUES %s
            ON CONFLICT (tarih, magaza_id) DO UPDATE SET
                toplam_ciro=EXCLUDED.toplam_ciro, toplam_fis=EXCLUDED.toplam_fis,
                toplam_musteri=EXCLUDED.toplam_musteri, toplam_miktar=EXCLUDED.toplam_miktar,
                sepet_ortalamasi=EXCLUDED.sepet_ortalamasi, sku_sayisi=EXCLUDED.sku_sayisi
        """
        execute_values(cursor, query, final_rows)
    else:
        cursor.executemany(f"""
            INSERT OR REPLACE INTO magazagunlukozet
            (tarih, magaza_id, toplam_ciro, toplam_fis, toplam_musteri,
             toplam_miktar, sepet_ortalamasi, sku_sayisi)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, final_rows)



def update_crm_ozet_daily(conn, target_date: str):
    """crmozet tablosunu (Günlük, Magaza, Kategori, Marka) güncelle"""
    cursor = conn.cursor()
    
    # Hesapla ve Ekle (Upsert mantığı ile)
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO crmozet (tarih, ay, magaza_id, kategori_id, marka_id, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar, sepet_ort)
            SELECT 
                tarih,
                TO_CHAR(tarih, 'YYYY-MM') as ay,
                COALESCE(magaza_id, 0),
                COALESCE(kategori_id, 0),
                COALESCE(marka_id, 0),
                SUM(tutar) as toplam_ciro,
                COUNT(DISTINCT fis_no) as toplam_fis,
                COUNT(DISTINCT musteri_id) as toplam_musteri,
                SUM(miktar) as toplam_miktar,
                CASE WHEN COUNT(DISTINCT fis_no) > 0 THEN SUM(tutar) / COUNT(DISTINCT fis_no) ELSE 0 END
            FROM satislar
            WHERE CAST(tarih AS DATE) = %s
            GROUP BY tarih, TO_CHAR(tarih, 'YYYY-MM'), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0)
            ON CONFLICT (tarih, magaza_id, kategori_id, marka_id) DO UPDATE SET
                toplam_ciro = EXCLUDED.toplam_ciro,
                toplam_fis = EXCLUDED.toplam_fis,
                toplam_musteri = EXCLUDED.toplam_musteri,
                toplam_miktar = EXCLUDED.toplam_miktar,
                sepet_ort = EXCLUDED.sepet_ort
        """, (target_date,))
    else:
        # SQLite için OR REPLACE zaten PK çakışmasını çözer
        cursor.execute("""
            INSERT OR REPLACE INTO crmozet (tarih, ay, magaza_id, kategori_id, marka_id, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar, sepet_ort)
            SELECT 
                tarih,
                strftime('%Y-%m', tarih) as ay,
                COALESCE(magaza_id, 0),
                COALESCE(kategori_id, 0),
                COALESCE(marka_id, 0),
                SUM(tutar) as toplam_ciro,
                COUNT(DISTINCT fis_no) as toplam_fis,
                COUNT(DISTINCT musteri_id) as toplam_musteri,
                SUM(miktar) as toplam_miktar,
                CASE WHEN COUNT(DISTINCT fis_no) > 0 THEN SUM(tutar) / COUNT(DISTINCT fis_no) ELSE 0 END
            FROM satislar
            WHERE date(tarih) = ?
            GROUP BY tarih, strftime('%Y-%m', tarih), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0)
        """, (target_date,))
    
    logger.info(f"   + crmozet güncellendi: {target_date}")


def update_daily_metrics_summary(conn, target_date: str):
    """daily_metrics_summary tablosunu (Tüm Filtreleri Kapsayan Özet) güncelle"""
    cursor = conn.cursor()
    
    tarih_clause = "s.tarih" if DB_BACKEND == "postgresql" else "date(s.tarih)"
    
    query = f"""
        SELECT 
            s.tarih,
            COALESCE(s.magaza_id, 0),
            COALESCE(s.kategori_id, 0),
            COALESCE(s.marka_id, 0),
            COALESCE(m.tip, 'Bilinmiyor'),
            COALESCE(mdo.rfm_segment, 'Diğer'),
            COALESCE(s.onay_durumu, 'Bilinmiyor'),
            SUM(s.tutar),
            COUNT(DISTINCT s.fis_no),
            COUNT(DISTINCT s.musteri_id),
            SUM(s.miktar)
        FROM satislar s
        LEFT JOIN musteriler m ON s.musteri_id = m.id
        LEFT JOIN musteridetayozet mdo ON s.musteri_id = mdo.musteri_id
        WHERE {tarih_clause} = %s
        GROUP BY 
            s.tarih, COALESCE(s.magaza_id, 0), COALESCE(s.kategori_id, 0), 
            COALESCE(s.marka_id, 0), COALESCE(m.tip, 'Bilinmiyor'), 
            COALESCE(mdo.rfm_segment, 'Diğer'), COALESCE(s.onay_durumu, 'Bilinmiyor')
    """
    cursor.execute(query, (target_date,))
    rows = cursor.fetchall()

    if not rows:
        return

    if DB_BACKEND == "postgresql":
        from psycopg2.extras import execute_values
        insert_query = """
            INSERT INTO daily_metrics_summary (
                tarih, magaza_id, kategori_id, marka_id, customer_type, 
                rfm_segment, onay_durumu, revenue, receipt_count, 
                customer_count, unit_count
            ) VALUES %s
            ON CONFLICT (tarih, magaza_id, kategori_id, marka_id, customer_type, rfm_segment, onay_durumu) 
            DO UPDATE SET
                revenue = EXCLUDED.revenue,
                receipt_count = EXCLUDED.receipt_count,
                customer_count = EXCLUDED.customer_count,
                unit_count = EXCLUDED.unit_count
        """
        execute_values(cursor, insert_query, rows)
    else:
        cursor.executemany("""
            INSERT OR REPLACE INTO daily_metrics_summary (
                tarih, magaza_id, kategori_id, marka_id, customer_type, 
                rfm_segment, onay_durumu, revenue, receipt_count, 
                customer_count, unit_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
    
    logger.info(f"   + daily_metrics_summary güncellendi: {target_date}")


def update_cache_kpi_approval(conn):
    """cache_kpi tablosuna dashboard KPI cache'lerini kaydet (hız optimizasyonu)"""
    cursor = conn.cursor()
    ph = "%s" if DB_BACKEND == "postgresql" else "?"

    def upsert(key, val):
        if DB_BACKEND == "postgresql":
            cursor.execute(f"""
                INSERT INTO cache_kpi (key, value, updated_at) VALUES ({ph}, {ph}, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (key, val))
        else:
            cursor.execute(
                f"INSERT OR REPLACE INTO cache_kpi (key, value, updated_at) VALUES ({ph}, {ph}, CURRENT_TIMESTAMP)",
                (key, val)
            )

    # 1. Onay sayıları
    cursor.execute("SELECT onay_durumu, COUNT(*) as cnt FROM musteriler GROUP BY onay_durumu")
    rows = cursor.fetchall()
    approved = 0
    unapproved = 0
    total_registered = 0
    for r in rows:
        status = str(r[0] if not isinstance(r, dict) else r['onay_durumu'] or '').upper()
        cnt = r[1] if not isinstance(r, dict) else r['cnt']
        total_registered += cnt
        if status == 'ONAYLI':
            approved += cnt
        else:
            unapproved += cnt
    upsert('approved_count', approved)
    upsert('unapproved_count', unapproved)
    upsert('total_registered_count', total_registered)

    # 2. Aktif müşteri sayısı (musteridetayozet üzerinden — satislar COUNT DISTINCT çok yavaş)
    cursor.execute("SELECT COUNT(*) as cnt FROM musteridetayozet WHERE aktivite_durumu = 'AKTİF'")
    active_row = cursor.fetchone()
    active_cnt = (active_row[0] if not isinstance(active_row, dict) else active_row['cnt']) or 0
    upsert('active_customer_count', active_cnt)

    # 3. Churn Rate (Son 120 gün alışveriş yapmayanlar / Toplam)
    try:
        from datetime import datetime, timedelta
        churn_thresh = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        cursor.execute(f"SELECT COUNT(*) as cnt FROM musteridetayozet WHERE son_alisveris_tarihi < {ph}", [churn_thresh])
        churn_row = cursor.fetchone()
        churned_count = (churn_row[0] if not isinstance(churn_row, dict) else churn_row['cnt']) or 0
        churn_rate = round((churned_count / total_registered * 100), 1) if total_registered > 0 else 0
        upsert('churn_rate', churn_rate)
    except Exception as e:
        logger.error(f"   ! Churn rate cache hatası: {e}")

    # 4. Loyalty Revenue Share (Sadık Segmentler Cirosu / Toplam Ciro)
    try:
        cursor.execute("SELECT SUM(toplam_ciro) as tr FROM gunlukciroozet")
        rev_row = cursor.fetchone()
        total_rev = (rev_row[0] if not isinstance(rev_row, dict) else rev_row['tr']) or 0
        
        if total_rev > 0:
            loyal_segments = ('01-) Şampiyonlar', '02-) Potansiyel Şampiyonlar', '03-) Sadık Müşteriler', '05-) Yüksek Harcama Yapanlar')
            cursor.execute(f"SELECT SUM(toplam_harcama) as loyal_rev FROM musteridetayozet WHERE rfm_segment IN ({','.join([ph]*len(loyal_segments))})", list(loyal_segments))
            loyal_row = cursor.fetchone()
            loyal_rev = (loyal_row[0] if not isinstance(loyal_row, dict) else loyal_row['loyal_rev']) or 0
            loyalty_share = round((loyal_rev / total_rev * 100), 1)
            upsert('loyalty_revenue_share', loyalty_share)
        else:
            upsert('loyalty_revenue_share', 0)
    except Exception as e:
        logger.error(f"   ! Loyalty share cache hatası: {e}")

    # 5. Özet tablo max tarih timestamp'leri (fallback karar için)
    cursor.execute("SELECT MAX(tarih) as md FROM gunlukciroozet")
    ozet_row = cursor.fetchone()
    ozet_max = ozet_row[0] if not isinstance(ozet_row, dict) else ozet_row['md']
    cursor.execute("SELECT MAX(tarih) as md FROM satislar")
    satis_row = cursor.fetchone()
    satis_max = satis_row[0] if not isinstance(satis_row, dict) else satis_row['md']
    if ozet_max:
        try:
            from datetime import datetime as _dt
            ozet_ts = (_dt.strptime(str(ozet_max)[:10], "%Y-%m-%d") - _dt(2020, 1, 1)).days
            upsert('ozet_max_tarih_ts', ozet_ts)
        except: pass
    if satis_max:
        try:
            from datetime import datetime as _dt
            satis_ts = (_dt.strptime(str(satis_max)[:10], "%Y-%m-%d") - _dt(2020, 1, 1)).days
            upsert('satislar_max_tarih_ts', satis_ts)
        except: pass

    conn.commit()
    logger.info(f"   + cache_kpi güncellendi (onaylı={approved}, onaysız={unapproved}, aktif_musteri={active_cnt}, churn={churn_rate if 'churn_rate' in locals() else '?'})")


# ================== YENİ ÖZET FONKSİYONLARI ==================

def update_gunluk_ozet(conn, target_date: str):
    """gunlukozet tablosunu (Detaylı - Mağaza/Kategori/Marka) güncelle"""
    cursor = conn.cursor()
    
    # Hesapla ve Ekle
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO gunlukozet 
            (tarih, magaza_id, kategori_id, marka_id, toplam_ciro, fis_sayisi, musteri_sayisi, urun_adedi)
            SELECT 
                CAST(tarih AS DATE),
                COALESCE(magaza_id, 0),
                COALESCE(kategori_id, 0),
                COALESCE(marka_id, 0),
                SUM(tutar),
                COUNT(DISTINCT fis_no),
                COUNT(DISTINCT musteri_id),
                SUM(miktar)
            FROM satislar
            WHERE CAST(tarih AS DATE) = %s
            GROUP BY CAST(tarih AS DATE), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0)
            ON CONFLICT (tarih, magaza_id, kategori_id, marka_id) DO UPDATE SET
                toplam_ciro = EXCLUDED.toplam_ciro,
                fis_sayisi = EXCLUDED.fis_sayisi,
                musteri_sayisi = EXCLUDED.musteri_sayisi,
                urun_adedi = EXCLUDED.urun_adedi
        """, (target_date,))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO gunlukozet 
            (tarih, magaza_id, kategori_id, marka_id, toplam_ciro, fis_sayisi, musteri_sayisi, urun_adedi)
            SELECT 
                date(tarih),
                COALESCE(magaza_id, 0),
                COALESCE(kategori_id, 0),
                COALESCE(marka_id, 0),
                SUM(tutar),
                COUNT(DISTINCT fis_no),
                COUNT(DISTINCT musteri_id),
                SUM(miktar)
            FROM satislar
            WHERE date(tarih) = ?
            GROUP BY date(tarih), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0)
        """, (target_date,))
    logger.info(f"   + gunlukozet güncellendi: {target_date}")


def update_kategori_karsilastirma(conn, target_date: str):
    """Kategori Karşılaştırma tablosunu güncelle (Ay bazlı birikir)"""
    # Bu tablo aylık olduğu için target_date'in ait olduğu ayı güncelleriz
    month_str = target_date[:7] # YYYY-MM
    cursor = conn.cursor()
    
    # O ay için temizle
    cursor.execute("DELETE FROM kategorikarsilastirma WHERE ay = %s" if DB_BACKEND == "postgresql" else "DELETE FROM kategorikarsilastirma WHERE ay = ?", (month_str,))
    
    # O ayın ilk ve son gününü bul
    import calendar
    year, month = map(int, month_str.split('-'))
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{month_str}-01"
    end_date = f"{month_str}-{last_day}"

    # Hesapla ve Ekle
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO kategorikarsilastirma 
            (ay, kategori, toplam_ciro, crm_ciro, anonim_ciro, crm_fis, anonim_fis, crm_sepet_ort, anonim_sepet_ort)
            SELECT 
                %s as ay,
                k.ana as kategori,
                SUM(s.tutar) as toplam_ciro,
                SUM(CASE WHEN s.musteri_id IS NOT NULL THEN s.tutar ELSE 0 END) as crm_ciro,
                SUM(CASE WHEN s.musteri_id IS NULL THEN s.tutar ELSE 0 END) as anonim_ciro,
                COUNT(DISTINCT CASE WHEN s.musteri_id IS NOT NULL THEN s.fis_no END) as crm_fis,
                COUNT(DISTINCT CASE WHEN s.musteri_id IS NULL THEN s.fis_no END) as anonim_fis,
                0, 0
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            JOIN kategoriler k ON u.kategori_id = k.id
            WHERE s.tarih >= %s AND s.tarih <= %s
            GROUP BY k.ana
        """, (month_str, start_date, end_date))
    else:
        cursor.execute("""
            INSERT INTO kategorikarsilastirma 
            (ay, kategori, toplam_ciro, crm_ciro, anonim_ciro, crm_fis, anonim_fis, crm_sepet_ort, anonim_sepet_ort)
            SELECT 
                ? as ay,
                k.ana as kategori,
                SUM(s.tutar) as toplam_ciro,
                SUM(CASE WHEN s.musteri_id IS NOT NULL THEN s.tutar ELSE 0 END) as crm_ciro,
                SUM(CASE WHEN s.musteri_id IS NULL THEN s.tutar ELSE 0 END) as anonim_ciro,
                COUNT(DISTINCT CASE WHEN s.musteri_id IS NOT NULL THEN s.fis_no END) as crm_fis,
                COUNT(DISTINCT CASE WHEN s.musteri_id IS NULL THEN s.fis_no END) as anonim_fis,
                0, 0
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            JOIN kategoriler k ON u.kategori_id = k.id
            WHERE date(s.tarih) >= ? AND date(s.tarih) <= ?
            GROUP BY k.ana
        """, (month_str, start_date, end_date))
    
    # Ortalamaları güncelle
    cursor.execute("""
        UPDATE kategorikarsilastirma SET
            crm_sepet_ort = CASE WHEN crm_fis > 0 THEN crm_ciro / crm_fis ELSE 0 END,
            anonim_sepet_ort = CASE WHEN anonim_fis > 0 THEN anonim_ciro / anonim_fis ELSE 0 END
        WHERE ay = %s
    """ if DB_BACKEND == "postgresql" else """
        UPDATE kategorikarsilastirma SET
            crm_sepet_ort = CASE WHEN crm_fis > 0 THEN crm_ciro / crm_fis ELSE 0 END,
            anonim_sepet_ort = CASE WHEN anonim_fis > 0 THEN anonim_ciro / anonim_fis ELSE 0 END
        WHERE ay = ?
    """, (month_str,))


def update_marka_karsilastirma(conn, target_date: str):
    """Marka Karşılaştırma tablosunu güncelle"""
    month_str = target_date[:7]
    cursor = conn.cursor()
    cursor.execute("DELETE FROM markakarsilastirma WHERE ay = %s" if DB_BACKEND == "postgresql" else "DELETE FROM markakarsilastirma WHERE ay = ?", (month_str,))
    
    # O ayın ilk ve son gününü bul
    import calendar
    year, month = map(int, month_str.split('-'))
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{month_str}-01"
    end_date = f"{month_str}-{last_day}"

    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO markakarsilastirma
            (ay, marka, toplam_ciro, crm_ciro, crm_musteri)
            SELECT
                %s as ay,
                m.ad as marka,
                SUM(s.tutar),
                SUM(CASE WHEN s.musteri_id IS NOT NULL THEN s.tutar ELSE 0 END),
                COUNT(DISTINCT s.musteri_id)
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            JOIN markalar m ON u.marka_id = m.id
            WHERE s.tarih >= %s AND s.tarih <= %s
            GROUP BY m.ad
        """, (month_str, start_date, end_date))
    else:
        cursor.execute("""
            INSERT INTO markakarsilastirma
            (ay, marka, toplam_ciro, crm_ciro, crm_musteri)
            SELECT
                ? as ay,
                m.ad as marka,
                SUM(s.tutar),
                SUM(CASE WHEN s.musteri_id IS NOT NULL THEN s.tutar ELSE 0 END),
                COUNT(DISTINCT s.musteri_id)
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            JOIN markalar m ON u.marka_id = m.id
            WHERE date(s.tarih) >= ? AND date(s.tarih) <= ?
            GROUP BY m.ad
        """, (month_str, start_date, end_date))


def update_kampanya_ozet(conn, target_date: str):
    """Kampanya Özet tablosunu güncelle"""
    month_str = target_date[:7]
    cursor = conn.cursor()
    cursor.execute("DELETE FROM kampanyaozet WHERE ay = %s" if DB_BACKEND == "postgresql" else "DELETE FROM kampanyaozet WHERE ay = ?", (month_str,))
    
    # O ayın ilk ve son gününü bul
    import calendar
    year, month = map(int, month_str.split('-'))
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{month_str}-01"
    end_date = f"{month_str}-{last_day}"

    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO kampanyaozet
            (ay, kampanya_id, kampanya_ad, katilim_sayisi, toplam_ciro, benzersiz_musteri)
            SELECT
                %s,
                s.kampanya_id,
                k.ad,
                COUNT(*),
                SUM(s.tutar),
                COUNT(DISTINCT s.musteri_id)
            FROM satislar s
            JOIN kampanyalar k ON s.kampanya_id = k.id
            WHERE s.tarih >= %s AND s.tarih <= %s AND s.kampanya_id IS NOT NULL
            GROUP BY s.kampanya_id, k.ad
        """, (month_str, start_date, end_date))
    else:
        cursor.execute("""
            INSERT INTO kampanyaozet
            (ay, kampanya_id, kampanya_ad, katilim_sayisi, toplam_ciro, benzersiz_musteri)
            SELECT
                ?,
                s.kampanya_id,
                k.ad,
                COUNT(*),
                SUM(s.tutar),
                COUNT(DISTINCT s.musteri_id)
            FROM satislar s
            JOIN kampanyalar k ON s.kampanya_id = k.id
            WHERE date(s.tarih) >= ? AND date(s.tarih) <= ? AND s.kampanya_id IS NOT NULL
            GROUP BY s.kampanya_id, k.ad
        """, (month_str, start_date, end_date))


def update_musteri_sadakat(conn, target_date: str):
    """Müşteri Sadakat Analizi (Basit Versiyon)"""
    month_str = target_date[:7]
    cursor = conn.cursor()
    cursor.execute("DELETE FROM musterisadakat WHERE ay = %s" if DB_BACKEND == "postgresql" else "DELETE FROM musterisadakat WHERE ay = ?", (month_str,))
    
    # Yeni Müşteri: Kayıt tarihi bu ay olanlar
    # Tekrar Müşteri: Kayıt tarihi eski olup bu ay alışveriş yapanlar
    
    # Şimdilik basitçe satislar ve musteriler tablosundan hesaplayalım
    # NOT: Bu sorgu büyük datada yavaş olabilir, optimize edilebilir
    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO musterisadakat (ay, yeni_musteri, tekrar_musteri, kayip_musteri, yeni_musteri_sepet, tekrar_musteri_sepet)
            SELECT
                %s as ay,
                (SELECT COUNT(*) FROM musteriler WHERE TO_CHAR(kayit_tarihi, 'YYYY-MM') = %s) as yeni,
                (SELECT COUNT(DISTINCT s.musteri_id) 
                 FROM satislar s 
                 JOIN musteriler m ON s.musteri_id = m.id 
                 WHERE TO_CHAR(s.tarih, 'YYYY-MM') = %s AND TO_CHAR(m.kayit_tarihi, 'YYYY-MM') < %s) as tekrar,
                 0, 0, 0
        """, (month_str, month_str, month_str, month_str))
    else:
        cursor.execute("""
            INSERT INTO musterisadakat (ay, yeni_musteri, tekrar_musteri, kayip_musteri, yeni_musteri_sepet, tekrar_musteri_sepet)
            SELECT
                ? as ay,
                (SELECT COUNT(*) FROM musteriler WHERE strftime('%Y-%m', kayit_tarihi) = ?) as yeni,
                (SELECT COUNT(DISTINCT s.musteri_id) 
                 FROM satislar s 
                 JOIN musteriler m ON s.musteri_id = m.id 
                 WHERE strftime('%Y-%m', s.tarih) = ? AND strftime('%Y-%m', m.kayit_tarihi) < ?) as tekrar,
                 0, 0, 0
        """, (month_str, month_str, month_str, month_str))


def update_genel_ozet(conn, target_date: str):
    """Genel Özet (Aylık Mağaza Bazlı)"""
    month_str = target_date[:7]
    cursor = conn.cursor()
    
    # O ayın ilk ve son gününü bul
    import calendar
    year, month = map(int, month_str.split('-'))
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{month_str}-01"
    end_date = f"{month_str}-{last_day}"

    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO genelozet
            (ay, magaza_id, toplam_ciro, toplam_fis, toplam_miktar, 
             crm_ciro, crm_fis, crm_musteri, crm_miktar,
             anonim_ciro, anonim_fis,
             crm_sepet_ort, anonim_sepet_ort, crm_oran_ciro, crm_oran_fis)
            SELECT
                %s as ay,
                COALESCE(magaza_id, 0),
                SUM(tutar),
                COUNT(DISTINCT fis_no),
                SUM(miktar),
                SUM(CASE WHEN musteri_id IS NOT NULL THEN tutar ELSE 0 END),
                COUNT(DISTINCT CASE WHEN musteri_id IS NOT NULL THEN fis_no END),
                COUNT(DISTINCT musteri_id),
                SUM(CASE WHEN musteri_id IS NOT NULL THEN miktar ELSE 0 END),
                SUM(CASE WHEN musteri_id IS NULL THEN tutar ELSE 0 END),
                COUNT(DISTINCT CASE WHEN musteri_id IS NULL THEN fis_no END),
                0, 0, 0, 0
            FROM satislar
            WHERE tarih >= %s AND tarih <= %s
            GROUP BY COALESCE(magaza_id, 0)
            ON CONFLICT (ay, magaza_id) DO UPDATE SET
                toplam_ciro = EXCLUDED.toplam_ciro,
                toplam_fis = EXCLUDED.toplam_fis,
                toplam_miktar = EXCLUDED.toplam_miktar,
                crm_ciro = EXCLUDED.crm_ciro,
                crm_fis = EXCLUDED.crm_fis,
                crm_musteri = EXCLUDED.crm_musteri,
                crm_miktar = EXCLUDED.crm_miktar,
                anonim_ciro = EXCLUDED.anonim_ciro,
                anonim_fis = EXCLUDED.anonim_fis
        """, (month_str, start_date, end_date))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO genelozet
            (ay, magaza_id, toplam_ciro, toplam_fis, toplam_miktar, 
             crm_ciro, crm_fis, crm_musteri, crm_miktar,
             anonim_ciro, anonim_fis,
             crm_sepet_ort, anonim_sepet_ort, crm_oran_ciro, crm_oran_fis)
            SELECT
                ? as ay,
                COALESCE(magaza_id, 0),
                SUM(tutar),
                COUNT(DISTINCT fis_no),
                SUM(miktar),
                SUM(CASE WHEN musteri_id IS NOT NULL THEN tutar ELSE 0 END),
                COUNT(DISTINCT CASE WHEN musteri_id IS NOT NULL THEN fis_no END),
                COUNT(DISTINCT musteri_id),
                SUM(CASE WHEN musteri_id IS NOT NULL THEN miktar ELSE 0 END),
                SUM(CASE WHEN musteri_id IS NULL THEN tutar ELSE 0 END),
                COUNT(DISTINCT CASE WHEN musteri_id IS NULL THEN fis_no END),
                0, 0, 0, 0
            FROM satislar
            WHERE date(tarih) >= ? AND date(tarih) <= ?
            GROUP BY COALESCE(magaza_id, 0)
        """, (month_str, start_date, end_date))
    
    # Oranları güncelle
    cursor.execute("""
        UPDATE genelozet SET
            crm_sepet_ort = CASE WHEN crm_fis > 0 THEN crm_ciro / crm_fis ELSE 0 END,
            anonim_sepet_ort = CASE WHEN anonim_fis > 0 THEN anonim_ciro / anonim_fis ELSE 0 END,
            crm_oran_ciro = CASE WHEN toplam_ciro > 0 THEN (crm_ciro / toplam_ciro) * 100 ELSE 0 END,
            crm_oran_fis = CASE WHEN toplam_fis > 0 THEN (crm_fis * 1.0 / toplam_fis) * 100 ELSE 0 END
        WHERE ay = %s
    """ if DB_BACKEND == "postgresql" else """
        UPDATE genelozet SET
            crm_sepet_ort = CASE WHEN crm_fis > 0 THEN crm_ciro / crm_fis ELSE 0 END,
            anonim_sepet_ort = CASE WHEN anonim_fis > 0 THEN anonim_ciro / anonim_fis ELSE 0 END,
            crm_oran_ciro = CASE WHEN toplam_ciro > 0 THEN (crm_ciro / toplam_ciro) * 100 ELSE 0 END,
            crm_oran_fis = CASE WHEN toplam_fis > 0 THEN (crm_fis * 1.0 / toplam_fis) * 100 ELSE 0 END
        WHERE ay = ?
    """, (month_str,))

def update_product_daily_summary(conn, target_date: str):
    """
    Ürün bazlı günlük özet tablosunu güncelle.
    Ürün Analizi sayfasındaki Top Products verisini hızlandırmak için kullanılır.
    """
    cursor = conn.cursor()
    # Önce o güne ait veriyi sil (clean sync)
    cursor.execute("DELETE FROM product_daily_summary WHERE tarih = %s" if DB_BACKEND == "postgresql" else "DELETE FROM product_daily_summary WHERE tarih = ?", (target_date,))
    
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            INSERT INTO product_daily_summary
            (tarih, urun_id, revenue, unit_count, customer_count, receipt_count)
            SELECT 
                tarih, urun_id, 
                SUM(tutar), SUM(miktar), COUNT(DISTINCT musteri_id), COUNT(DISTINCT fis_no)
            FROM satislar
            WHERE tarih = %s AND urun_id IS NOT NULL
            GROUP BY tarih, urun_id
        """, (target_date,))
    else:
        cursor.execute("""
            INSERT INTO product_daily_summary
            (tarih, urun_id, revenue, unit_count, customer_count, receipt_count)
            SELECT 
                tarih, urun_id, 
                SUM(tutar), SUM(miktar), COUNT(DISTINCT musteri_id), COUNT(DISTINCT fis_no)
            FROM satislar
            WHERE tarih = ? AND urun_id IS NOT NULL
            GROUP BY tarih, urun_id
        """, (target_date,))
    conn.commit()

def update_brand_summary(conn):
    """
    brandsummary tablosunu tümüyle yeniden oluşturur.
    Bu tablo Marka Raporu sayfası için lightning-fast filtreleme sağlar.
    """
    cursor = conn.cursor()
    logger.info("brandsummary tablosu güncelleniyor...")
    start_time = time.time()
    import time as time_mod
    
    # 1. Tabloyu temizle veya oluştur
    real_t = "DOUBLE PRECISION" if DB_BACKEND == "postgresql" else "REAL"
    cursor.execute("DROP TABLE IF EXISTS brandsummary")
    cursor.execute(f"""
        CREATE TABLE brandsummary (
            brand_id INTEGER,
            brand_name TEXT,
            year INTEGER,
            month INTEGER,
            region TEXT,
            customer_type TEXT,
            segment TEXT,
            approval_status TEXT,
            category_id INTEGER,
            category_main TEXT,
            category_sub1 TEXT,
            category_sub2 TEXT,
            total_sales {real_t},
            total_units {real_t},
            customer_count INTEGER,
            brand_name_norm TEXT,
            region_norm TEXT,
            customer_type_norm TEXT,
            approval_status_norm TEXT,
            segment_norm TEXT,
            category_norm TEXT,
            category_sub1_norm TEXT,
            category_sub2_norm TEXT
        )
    """)
    
    # 2. Turkish Lower Helper (ASCII Folding ile)
    def tr_lower(s):
        if s is None: return ""
        if not isinstance(s, str): s = str(s)
        s = s.strip().replace('\xa0', ' ')
        s = s.replace('İ', 'i').replace('I', 'ı')
        s = s.lower()
        replacements = {'ç': 'c', 'ğ': 'g', 'ö': 'o', 'ş': 's', 'ü': 'u', 'ı': 'i'}
        for search, replace in replacements.items():
            s = s.replace(search, replace)
        return s

    year_part = "TO_CHAR(s.tarih, 'YYYY')" if DB_BACKEND == "postgresql" else "strftime('%Y', s.tarih)"
    month_part = "TO_CHAR(s.tarih, 'MM')" if DB_BACKEND == "postgresql" else "strftime('%m', s.tarih)"
    
    select_query = f"""
        SELECT 
            u.marka_id, m.ad,
            {year_part} as year,
            {month_part} as month,
            COALESCE(mg.bolge, 'Diğer') as region,
            COALESCE(mu.tip, 'Bilinmiyor') as customer_type,
            COALESCE(mdo.rfm_segment, 'Diğer') as segment,
            COALESCE(s.onay_durumu, 'Bilinmiyor') as approval_status,
            u.kategori_id,
            COALESCE(k.ana, 'Diğer') as category_main,
            COALESCE(k.alt1, '') as category_sub1,
            COALESCE(k.alt2, '') as category_sub2,
            SUM(s.tutar) as total_sales,
            SUM(s.miktar) as total_units,
            COUNT(DISTINCT s.musteri_id) as customer_count
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        LEFT JOIN markalar m ON u.marka_id = m.id
        LEFT JOIN musteriler mu ON s.musteri_id = mu.id
        LEFT JOIN musteridetayozet mdo ON s.musteri_id = mdo.musteri_id
        LEFT JOIN magazalar mg ON s.magaza_id = mg.id
        LEFT JOIN kategoriler k ON u.kategori_id = k.id
        GROUP BY
            u.marka_id, m.ad, {year_part}, {month_part}, 
            COALESCE(mg.bolge, 'Diğer'), COALESCE(mu.tip, 'Bilinmiyor'), 
            COALESCE(mdo.rfm_segment, 'Diğer'), COALESCE(s.onay_durumu, 'Bilinmiyor'),
            u.kategori_id, COALESCE(k.ana, 'Diğer'), COALESCE(k.alt1, ''), COALESCE(k.alt2, '')
    """
    
    if DB_BACKEND == "postgresql":
        # PostgreSQL için server-side cursor kullanarak RAM tasarrufu sağla
        cursor_name = f"brand_summary_{int(time_mod.time())}"
        cursor = conn.cursor(name=cursor_name)
    else:
        cursor = conn.cursor()

    cursor.execute(select_query)
    
    _ph = "%s" if DB_BACKEND == "postgresql" else "?"
    _placeholders = ",".join([_ph] * 23)
    insert_sql = f"""
        INSERT INTO brandsummary (
            brand_id, brand_name, year, month, region, customer_type, segment, approval_status,
            category_id, category_main, category_sub1, category_sub2,
            total_sales, total_units, customer_count,
            brand_name_norm, region_norm, customer_type_norm, approval_status_norm, segment_norm, category_norm, category_sub1_norm, category_sub2_norm
        ) VALUES ({_placeholders})
    """
    
    # Yazma işlemi için ayrı bir cursor (PostgreSQL'de named cursor varken veri yazılamaz)
    write_cursor = conn.cursor()
    
    batch = []
    batch_size = 5000
    total_count = 0
    
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
            
        final_rows = []
        for r in rows:
            # PostgreSQL'de named cursor dict döndürmez, index ile erişelim
            bname = r[1]
            bname_n = tr_lower(bname)
            reg_n = tr_lower(r[4])
            ctype_n = tr_lower(r[5])
            seg_n = tr_lower(r[6])
            appr_n = tr_lower(r[7])
            cat_main_n = tr_lower(r[9])
            cat_sub1_n = tr_lower(r[10])
            cat_sub2_n = tr_lower(r[11])
            
            final_rows.append((
                r[0], r[1], int(r[2]) if r[2] else None, int(r[3]) if r[3] else None, r[4], r[5], r[6], r[7], 
                r[8], r[9], r[10], r[11], 
                r[12], r[13], r[14],
                bname_n, reg_n, ctype_n, appr_n, seg_n, cat_main_n, cat_sub1_n, cat_sub2_n
            ))
            
        write_cursor.executemany(insert_sql, final_rows)
        total_count += len(final_rows)
        # RAM boşaltmaya yardımcı ol (isteğe bağlı)
        del final_rows
        
    if DB_BACKEND == "postgresql":
        cursor.close() # Named cursor'ı kapat
        
    # Indexler
    write_cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_main ON brandsummary(year, month)")
    write_cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_dims ON brandsummary(region_norm, customer_type_norm, category_norm, brand_name_norm)")
    
    duration = time_mod.time() - start_time
    logger.info(f"✅ brandsummary güncellendi ({total_count} satır, {duration:.1f}s)")

def rebuild_musteri_detay_ozet(conn):
    """
    musteridetayozet tablosunu tümüyle yeniden oluşturur.
    Tüm metrikleri tek bir optimize edilmiş SQL sorgusuyla hesaplar.
    """
    logger.info("Müşteri Detay Özet tablosu güncelleniyor (Optimize edilmiş tek sorgu)...")
    start_time = time.time()
    cursor = conn.cursor()
    
    is_pg = (DB_BACKEND == "postgresql")
    now_date = "CURRENT_DATE" if is_pg else "date('now')"
    int_30 = "INTERVAL '30 days'" if is_pg else "'-30 days'"
    int_90 = "INTERVAL '90 days'" if is_pg else "'-90 days'"
    
    # SQLite/PostgreSQL uyumlu date diff logic
    if is_pg:
        date_diff = "ABS(%s::DATE - %s::DATE)"
    else:
        date_diff = "ABS(strftime('%%s', %s)/86400 - strftime('%%s', %s)/86400)"

    cursor.execute("DELETE FROM musteridetayozet")
    
    # Tek bir dev sorgu ile her şeyi hesapla
    main_query = f"""
        WITH BaseMetrics AS (
            SELECT 
                s.musteri_id, 
                MAX(m.ad) as ad_soyad, MAX(m.telefon) as telefon, MAX(m.kayit_tarihi) as kayit_tarihi,
                MAX(m.rfm_segment) as rfm_segment, MAX(m.rfm_r_score) as rfm_r_score, MAX(m.rfm_f_score) as rfm_f_score, MAX(m.rfm_m_score) as rfm_m_score,
                MIN(s.tarih) as ilk_tarih, MAX(s.tarih) as son_tarih,
                COUNT(DISTINCT s.fis_no) as total_visits, 
                SUM(s.tutar) as total_spend,
                SUM(s.miktar) as total_units,
                COUNT(DISTINCT CASE WHEN s.tarih >= ({now_date}::DATE - {int_30}) THEN s.fis_no END) as visits_30,
                SUM(CASE WHEN s.tarih >= ({now_date}::DATE - {int_30}) THEN s.tutar ELSE 0 END) as spend_30,
                COUNT(DISTINCT CASE WHEN s.tarih >= ({now_date}::DATE - {int_90}) THEN s.fis_no END) as visits_90,
                SUM(CASE WHEN s.tarih >= ({now_date}::DATE - {int_90}) THEN s.tutar ELSE 0 END) as spend_90,
                SUM(CASE WHEN s.saat BETWEEN 6 AND 11 THEN 1 ELSE 0 END) as s_sabah,
                SUM(CASE WHEN s.saat BETWEEN 12 AND 17 THEN 1 ELSE 0 END) as s_ogle,
                SUM(CASE WHEN s.saat BETWEEN 18 AND 23 THEN 1 ELSE 0 END) as s_aksam,
                SUM(CASE WHEN s.saat BETWEEN 0 AND 5 THEN 1 ELSE 0 END) as s_gece
            FROM satislar s
            LEFT JOIN musteriler m ON s.musteri_id = m.id
            WHERE s.musteri_id IS NOT NULL
            GROUP BY s.musteri_id
        ),
        -- Favori Kategori (Hızlı Yöntem)
        CatSpend AS (
            SELECT s.musteri_id, k.ana, SUM(s.tutar) as t FROM satislar s JOIN urunler u ON s.urun_id=u.id JOIN kategoriler k ON u.kategori_id=k.id GROUP BY 1, 2
        ),
        CatMax AS (
            SELECT musteri_id, MAX(t) as mt FROM CatSpend GROUP BY 1
        ),
        FavCat AS (
            SELECT cs.musteri_id, MIN(cs.ana) as f_kat FROM CatSpend cs JOIN CatMax cm ON cs.musteri_id=cm.musteri_id AND cs.t=cm.mt GROUP BY 1
        ),
        -- Favori Marka
        BrandSpend AS (
            SELECT s.musteri_id, ma.ad, SUM(s.tutar) as t FROM satislar s JOIN urunler u ON s.urun_id=u.id JOIN markalar ma ON u.marka_id=ma.id GROUP BY 1, 2
        ),
        BrandMax AS (
            SELECT musteri_id, MAX(t) as mt FROM BrandSpend GROUP BY 1
        ),
        FavBrand AS (
            SELECT bs.musteri_id, MIN(bs.ad) as f_marka FROM BrandSpend bs JOIN BrandMax bm ON bs.musteri_id=bm.musteri_id AND bs.t=bm.mt GROUP BY 1
        ),
        -- Favori Mağaza
        StoreVisits AS (
            SELECT s.musteri_id, mag.ad, COUNT(DISTINCT s.fis_no) as v FROM satislar s JOIN magazalar mag ON s.magaza_id=mag.id GROUP BY 1, 2
        ),
        StoreMax AS (
            SELECT musteri_id, MAX(v) as mv FROM StoreVisits GROUP BY 1
        ),
        FavStore AS (
            SELECT sv.musteri_id, MIN(sv.ad) as f_mag FROM StoreVisits sv JOIN StoreMax sm ON sv.musteri_id=sm.musteri_id AND sv.v=sm.mv GROUP BY 1
        )
        INSERT INTO musteridetayozet (
            musteri_id, ad_soyad, telefon, kayit_tarihi,
            rfm_segment, r_score, f_score, m_score,
            ilk_alisveris_tarihi, son_alisveris_tarihi,
            toplam_alisveris, toplam_harcama, ortalama_sepet_tutari,
            ortalama_siparis_buyuklugu,
            son_30_gun_alisveris, son_30_gun_harcama,
            son_90_gun_alisveris, son_90_gun_harcama,
            saat_sabah, saat_ogle, saat_aksam, saat_gece,
            favori_kategori, favori_marka, favori_magaza,
            musteri_yasi_gun, churn_risk_skoru, aktivite_durumu, lifetime_value_tahmini, toplam_miktar_calculated, trend
        )
        SELECT 
            b.musteri_id, b.ad_soyad, b.telefon, b.kayit_tarihi,
            b.rfm_segment, b.rfm_r_score, b.rfm_f_score, b.rfm_m_score,
            b.ilk_tarih, b.son_tarih,
            b.total_visits, b.total_spend, b.total_spend / b.total_visits,
            b.total_units / CAST(b.total_visits AS FLOAT),
            b.visits_30, b.spend_30, b.visits_90, b.spend_90,
            b.s_sabah, b.s_ogle, b.s_aksam, b.s_gece,
            fcat.f_kat, fbr.f_marka, fst.f_mag,
            {date_diff % (now_date, "b.kayit_tarihi")},
            CASE 
                WHEN b.son_tarih >= ({now_date}::DATE - {int_30}) THEN 10
                WHEN b.son_tarih >= ({now_date}::DATE - {int_90}) THEN 50
                ELSE 90
            END,
            CASE 
                WHEN b.son_tarih >= ({now_date}::DATE - {int_30}) THEN 'AKTİF'
                WHEN b.son_tarih >= ({now_date}::DATE - {int_90}) THEN 'PASİF'
                ELSE 'KAYIP'
            END,
            b.total_spend * 1.5,
            b.total_units,
            CASE 
                WHEN b.spend_30 > (b.total_spend / (NULLIF({date_diff % (now_date, "b.ilk_tarih")}, 0) / 30.0 + 1)) * 1.2 THEN 'YÜKSELİŞ'
                WHEN b.spend_30 < (b.total_spend / (NULLIF({date_diff % (now_date, "b.ilk_tarih")}, 0) / 30.0 + 1)) * 0.8 THEN 'DÜŞÜŞ'
                ELSE 'STABİL'
            END
        FROM BaseMetrics b
        LEFT JOIN FavCat fcat ON b.musteri_id = fcat.musteri_id
        LEFT JOIN FavBrand fbr ON b.musteri_id = fbr.musteri_id
        LEFT JOIN FavStore fst ON b.musteri_id = fst.musteri_id
    """
    
    # SQLite için ::DATE cast'lerini kaldır
    if not is_pg:
        main_query = main_query.replace("::DATE", "")
        main_query = main_query.replace("::TEXT", "")

    cursor.execute(main_query)

    # Satışsız müşterileri de musteridetayozet'e ekle (rfm_segment ve temel bilgilerle)
    no_sales_query = f"""
        INSERT INTO musteridetayozet (
            musteri_id, ad_soyad, telefon, kayit_tarihi,
            rfm_segment, r_score, f_score, m_score,
            toplam_alisveris, toplam_harcama, ortalama_sepet_tutari,
            ortalama_siparis_buyuklugu,
            son_30_gun_alisveris, son_30_gun_harcama,
            son_90_gun_alisveris, son_90_gun_harcama,
            saat_sabah, saat_ogle, saat_aksam, saat_gece,
            musteri_yasi_gun, churn_risk_skoru, aktivite_durumu,
            lifetime_value_tahmini, toplam_miktar_calculated, trend
        )
        SELECT
            m.id, m.ad, m.telefon, m.kayit_tarihi,
            m.rfm_segment, m.rfm_r_score, m.rfm_f_score, m.rfm_m_score,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            {date_diff % (now_date, 'm.kayit_tarihi')},
            90, 'KAYIP', 0, 0, 'STABİL'
        FROM musteriler m
        WHERE m.id NOT IN (SELECT DISTINCT musteri_id FROM satislar WHERE musteri_id IS NOT NULL)
        ON CONFLICT (musteri_id) DO NOTHING
    """ if is_pg else f"""
        INSERT OR IGNORE INTO musteridetayozet (
            musteri_id, ad_soyad, telefon, kayit_tarihi,
            rfm_segment, r_score, f_score, m_score,
            toplam_alisveris, toplam_harcama, ortalama_sepet_tutari,
            ortalama_siparis_buyuklugu,
            son_30_gun_alisveris, son_30_gun_harcama,
            son_90_gun_alisveris, son_90_gun_harcama,
            saat_sabah, saat_ogle, saat_aksam, saat_gece,
            musteri_yasi_gun, churn_risk_skoru, aktivite_durumu,
            lifetime_value_tahmini, toplam_miktar_calculated, trend
        )
        SELECT
            m.id, m.ad, m.telefon, m.kayit_tarihi,
            m.rfm_segment, m.rfm_r_score, m.rfm_f_score, m.rfm_m_score,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            ABS(julianday(date('now')) - julianday(m.kayit_tarihi)),
            90, 'KAYIP', 0, 0, 'STABİL'
        FROM musteriler m
        WHERE m.id NOT IN (SELECT DISTINCT musteri_id FROM satislar WHERE musteri_id IS NOT NULL)
    """
    try:
        cursor.execute(no_sales_query)
        logger.info(f"  → Satışsız müşteriler musteridetayozet'e eklendi")
    except Exception as e:
        logger.warning(f"  ⚠️ Satışsız müşteri ekleme hatası (kritik değil): {e}")

    duration = time.time() - start_time
    logger.info(f"✅ musteridetayozet güncellendi ({duration:.1f}s)")

def update_rfm_analysis(conn=None):
    """Müşteri RFM skorlarını ve segmentlerini güncelle (Subprocess ile)"""
    logger.info("RFM Analizi güncelleniyor (rfm_daily_update.py üzerinden)...")
    try:
        backend_dir = os.path.join(BASE_DIR, "backend")
        script_path = os.path.join(backend_dir, "rfm_daily_update.py")

        if not os.path.exists(script_path):
            logger.error(f"❌ rfm_daily_update.py bulunamadı: {script_path}")
            return

        # venv Python'unu önce dene, bulamazsa sys.executable kullan
        venv_python = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable
        logger.info(f"   Python: {python_exe}")

        # capture_output=False: stdout/stderr RAM'de birikmesin, doğrudan log'a aktsın
        result = subprocess.run(
            [python_exe, script_path],
            cwd=backend_dir,
            capture_output=False,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            logger.info("✅ RFM Analizi tamamlandı.")
        else:
            logger.warning(f"⚠️ RFM Analizi başarısız oldu (kod={result.returncode})")
    except subprocess.TimeoutExpired:
        logger.error("❌ RFM Analizi 5 dakika timeout'a uğradı.")
    except Exception as e:
        logger.error(f"❌ RFM Güncelleme hatası: {e}", exc_info=True)



def update_ai_tags():
    """AI Etiketlerini (tagging_engine) tetikler"""
    logger.info("AI Akıllı Etiketlemeler güncelleniyor...")
    try:
        engine_path = os.path.join(BASE_DIR, 'database', 'tagging_engine.py')
        if os.path.exists(engine_path):
            # Alt işlem olarak çalıştır (database kilitlenmelerini yönetmek için)
            subprocess.run([sys.executable, engine_path], check=True)
            logger.info("✅ AI Etiketleme başarıyla tamamlandı")
        else:
            logger.warning(f"⚠️ AI Tagging Engine bulunamadı: {engine_path}")
    except Exception as e:
        logger.error(f"❌ AI Etiketleme hatası: {e}")

def update_global_stats(conn):

    """Zaman alıcı global toplamları pre-calculate yap ve globalstatlar tablosuna yaz"""
    cursor = conn.cursor()
    logger.info("Global istatistikler güncelleniyor...")
    
    # 1. Toplam Tekil Müşteri (En yavaş sorgu)
    cursor.execute("SELECT COUNT(DISTINCT musteri_id) FROM satislar")
    total_customers = cursor.fetchone()[0]
    
    # 2. Toplam Ciro ve Fiş (Hızlı)
    cursor.execute("SELECT SUM(toplam_ciro), SUM(toplam_fis) FROM gunlukciroozet")
    rev, fis = cursor.fetchone()
    
    # 3. Churn Rate (RFM - 120 gün kuralı)
    # Aktif Müşteri: Son 120 günde alışveriş yapan
    # Kayıp Müşteri: Toplam - Aktif
    # Churn Rate: (Kayıp / Toplam) * 100
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            SELECT COUNT(DISTINCT musteri_id) 
            FROM satislar 
            WHERE tarih >= CURRENT_DATE - INTERVAL '120 days'
        """)
    else:
        cursor.execute("""
            SELECT COUNT(DISTINCT musteri_id) 
            FROM satislar 
            WHERE tarih >= date('now', '-120 days')
        """)
    active_customers = cursor.fetchone()[0] or 0
    
    churn_rate = 0.0
    if total_customers > 0:
        lost_customers = total_customers - active_customers
        churn_rate = (lost_customers / total_customers) * 100.0

    # Kaydet
    stats = {
        'total_unique_customers': total_customers,
        'active_customers': active_customers, # Yeni
        'total_churn_rate': round(churn_rate, 2), # Yeni
        'total_revenue': rev or 0,
        'total_receipts': fis or 0
    }
    
    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
    
    for key, val in stats.items():
        cursor.execute(f"INSERT INTO globalstatlar (key, value, updated_at) VALUES ({ph}, {ph}, {now_func}) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at={now_func}", (key, val))
    
    logger.info(f"Global istatistikler güncellendi: {stats}")


def sync_summary_for_date(target_date: str, update_heavy: bool = True) -> bool:
    """Belirli bir tarih için özet güncelle (Retry mekanizmalı)"""
    import time
    
    # Ensure target_date is string (YYYY-MM-DD)
    if hasattr(target_date, 'strftime'):
        target_date = target_date.strftime('%Y-%m-%d')
    else:
        target_date = str(target_date) # Fallback

    
    max_retries = 3
    for attempt in range(max_retries):
        conn = get_connection()
        try:
            # İşlemi hızlandırmak ve kilitleri yönetmek için IMMEDIATE kullanıyoruz
            if DB_BACKEND != "postgresql":
                conn.execute("BEGIN IMMEDIATE")

            # 1. Günlük Ana Özetleri Hesapla (gunlukozet, crmozet vb.)
            update_gunluk_ciro_ozet_daily(conn, target_date)
            update_magaza_gunluk_ozet_daily(conn, target_date)
            update_crm_ozet_daily(conn, target_date)
            update_daily_metrics_summary(conn, target_date)
            update_cache_kpi_approval(conn)

            # Yeni Tabloları Güncelle
            update_gunluk_ozet(conn, target_date)
            update_kategori_karsilastirma(conn, target_date)
            update_marka_karsilastirma(conn, target_date)
            update_kampanya_ozet(conn, target_date)
            update_genel_ozet(conn, target_date)

            # Ürün bazlı günlük özet (product_daily_summary) - portal/dashboard için kritik
            update_product_daily_summary(conn, target_date)

            if update_heavy:
                # Global istatistikleri ve en çok satanları her gün güncelle
                update_global_stats(conn)
                update_best_sellers(conn.cursor())

                if target_date == datetime.now().strftime('%Y-%m-%d'):
                    update_rfm_analysis(conn) # Önce RFM skorlarını güncelle (musteriler tablosu)
                    rebuild_musteri_detay_ozet(conn) # Sonra özet tabloyu bu verilerle beraber oluştur
                    update_brand_summary(conn)
                    update_category_analiz_ozet(conn) # Kategori analiz önbelleğini yenile
                    # AI Etiketlerini güncelle
                    update_ai_tags()
                    # Etiket özeti önbelleğini yenile
                    rebuild_etiket_ozeti_cache(conn)

            ph = "%s" if DB_BACKEND == "postgresql" else "?"
            now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
            cursor = conn.cursor()
            if DB_BACKEND == "postgresql":
                cursor.execute(f"""
                    INSERT INTO syncmeta (key, value, updated_at)
                    VALUES ('last_summary_update', {ph}, {now_func})
                    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at={now_func}
                """, (datetime.now().isoformat(),))
            else:
                cursor.execute(f"""
                    INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                    VALUES ('last_summary_update', ?, datetime('now'))
                """, (datetime.now().isoformat(),))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            if "locked" in str(e):
                logger.warning(f"Database locked ({target_date}), retrying... ({attempt+1}/{max_retries})")
                if conn: conn.close()
                time.sleep(2)
                continue
            else:
                logger.error(f"Özet güncelleme hatası ({target_date}): {e}")
                if DB_BACKEND == "postgresql" and conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                if conn: conn.close()
                return False
    return False


def sync_summary_for_today() -> bool:
    """Bugün için HAFİF özet güncelle (Saatlik Delta Sync ile birlikte çağrılır).
    Ağır işlemler (RFM, brand, müşteri detay) gece fazlı rebuild'e bırakılır."""
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"Bugünün HAFİF özeti güncelleniyor: {today}")
    return sync_summary_for_date(today, update_heavy=False)


def sync_summary_for_range(start_date: str, end_date: str) -> int:
    """Tarih aralığı için özet güncelle"""
    conn = get_connection()
    cursor = conn.cursor()

    ph = "%s" if DB_BACKEND == "postgresql" else "?"
    # Aralıktaki tüm tarihleri bul
    cursor.execute(f"""
        SELECT DISTINCT tarih FROM satislar
        WHERE tarih >= {ph} AND tarih <= {ph}
        ORDER BY tarih
    """, (start_date, end_date))

    dates = [row[0] for row in cursor.fetchall()]
    conn.close()

    updated = 0
    for d in dates:
        if sync_summary_for_date(d):
            updated += 1

    logger.info(f"{updated} gün için özet güncellendi")
    return updated



def rebuild_urun_performans_detay(conn):
    """Tüm ürünlerin performans metriklerini hesapla ve urunperformansdetay tablosuna yaz"""
    logger.info("Ürün performans detayları hesaplanıyor...")
    cursor = conn.cursor()
    
    # 1. Mevcut veriyi temizle
    cursor.execute("DELETE FROM urunperformansdetay")
    
    # 2. Temel tarihleri belirle (en son satış tarihinden geriye)
    cursor.execute("SELECT MAX(tarih) FROM satislar")
    max_date_row = cursor.fetchone()
    if not max_date_row or not max_date_row[0]:
        logger.warning("Satış verisi bulunamadı, ürün performans detayları boş bırakıldı.")
        return
    
    max_date = max_date_row[0]
    
    is_pg = (DB_BACKEND == "postgresql")
    ph = "%s" if is_pg else "?"
    
    # Tarih filtreleri için SQL expressions
    if is_pg:
        date_7 = f"'{max_date}'::DATE - INTERVAL '7 days'"
        date_30 = f"'{max_date}'::DATE - INTERVAL '30 days'"
        date_60 = f"'{max_date}'::DATE - INTERVAL '60 days'"
        date_90 = f"'{max_date}'::DATE - INTERVAL '90 days'"
        now_func = "CURRENT_TIMESTAMP"
    else:
        date_7 = f"date('{max_date}', '-7 days')"
        date_30 = f"date('{max_date}', '-30 days')"
        date_60 = f"date('{max_date}', '-60 days')"
        date_90 = f"date('{max_date}', '-90 days')"
        now_func = "datetime('now')"

    # Büyük bir sorgu ile tüm metrikleri hesapla (Kategori içi sıralama ve birliktelik dahil)
    query = f"""
        WITH SalesStats AS (
            SELECT 
                urun_id,
                SUM(CASE WHEN tarih >= {date_7} THEN miktar ELSE 0 END) as s7_qty,
                SUM(CASE WHEN tarih >= {date_7} THEN tutar ELSE 0 END) as s7_rev,
                COUNT(DISTINCT CASE WHEN tarih >= {date_7} THEN musteri_id END) as s7_cust,
                
                SUM(CASE WHEN tarih >= {date_30} THEN miktar ELSE 0 END) as s30_qty,
                SUM(CASE WHEN tarih >= {date_30} THEN tutar ELSE 0 END) as s30_rev,
                COUNT(DISTINCT CASE WHEN tarih >= {date_30} THEN musteri_id END) as s30_cust,
                
                SUM(CASE WHEN tarih >= {date_60} AND tarih < {date_30} THEN tutar ELSE 0 END) as s30_60_rev,
                
                SUM(CASE WHEN tarih >= {date_90} THEN miktar ELSE 0 END) as s90_qty,
                SUM(CASE WHEN tarih >= {date_90} THEN tutar ELSE 0 END) as s90_rev,
                COUNT(DISTINCT CASE WHEN tarih >= {date_90} THEN musteri_id END) as s90_cust,
                
                SUM(miktar) as total_qty,
                SUM(tutar) as total_rev,
                COUNT(DISTINCT musteri_id) as total_cust,
                MIN(tarih) as first_sale,
                MAX(tarih) as last_sale
            FROM satislar
            GROUP BY urun_id
        ),
        RankedStats AS (
            SELECT 
                s.*,
                u.kategori_id,
                RANK() OVER (PARTITION BY u.kategori_id ORDER BY s.total_rev DESC) as cat_rank
            FROM SalesStats s
            JOIN urunler u ON s.urun_id = u.id
        ),
        AssocStats AS (
            SELECT 
                urun_id_1,
                COUNT(*) as assoc_count,
                MAX(lift) as max_lift
            FROM urunbirliktelikleri
            GROUP BY urun_id_1
        )
        INSERT INTO urunperformansdetay (
            urunid, urunadi, kategoriid, kategoriadi, markaid, markaadi,
            guncelfiyat, stokmiktari, urunolusturmatarihi,
            son7gunsatis, son7gunciro, son7gunmusterisayisi,
            son30gunsatis, son30gunciro, son30gunmusterisayisi, son30gunortfiyat,
            son90gunsatis, son90gunciro, son90gunmusterisayisi,
            toplamsatis, toplamciro, toplammusterisayisi,
            ilksatistarihi, sonsatistarihi,
            trend_7_30, trend_30_60, hiztrendi,
            stokdurumu, gunlukortsatis, tahministokgunu,
            performanskategori, kategoriicindesira,
            birliktesatilanurunsayisi, crosssellpotansiyeli,
            guncellemetarihi
        )
        SELECT 
            u.id, u.ad, u.kategori_id, k.ana, u.marka_id, m.ad,
            0.0, 0, NULL, 
            COALESCE(rs.s7_qty, 0), COALESCE(rs.s7_rev, 0), COALESCE(rs.s7_cust, 0),
            COALESCE(rs.s30_qty, 0), COALESCE(rs.s30_rev, 0), COALESCE(rs.s30_cust, 0),
            CASE WHEN COALESCE(rs.s30_qty, 0) > 0 THEN rs.s30_rev / rs.s30_qty ELSE 0 END,
            COALESCE(rs.s90_qty, 0), COALESCE(rs.s90_rev, 0), COALESCE(rs.s90_cust, 0),
            COALESCE(rs.total_qty, 0), COALESCE(rs.total_rev, 0), COALESCE(rs.total_cust, 0),
            rs.first_sale, rs.last_sale,
            CASE 
                WHEN (COALESCE(rs.s7_rev, 0) / 7.0) > (COALESCE(rs.s30_rev, 0) / 30.0) * 1.2 THEN 1
                WHEN (COALESCE(rs.s7_rev, 0) / 7.0) < (COALESCE(rs.s30_rev, 0) / 30.0) * 0.8 THEN -1
                ELSE 0
            END,
            CASE 
                WHEN COALESCE(rs.s30_rev, 0) > COALESCE(rs.s30_60_rev, 0) * 1.1 THEN 1
                WHEN COALESCE(rs.s30_rev, 0) < COALESCE(rs.s30_60_rev, 0) * 0.9 THEN -1
                ELSE 0
            END,
            'Stabil', 'Normal',
            COALESCE(rs.s30_qty, 0) / 30.0, 0.0,
            'Orta',
            rs.cat_rank,
            COALESCE(ast.assoc_count, 0),
            COALESCE(ast.max_lift, 0),
            {now_func}
        FROM urunler u
        LEFT JOIN RankedStats rs ON u.id = rs.urun_id
        LEFT JOIN kategoriler k ON u.kategori_id = k.id
        LEFT JOIN markalar m ON u.marka_id = m.id
        LEFT JOIN AssocStats ast ON u.id = ast.urun_id_1
        WHERE rs.urun_id IS NOT NULL
    """
    cursor.execute(query)
    
    # Performans Kategorilerini Güncelle (Global sıralamaya göre)
    update_perf_query = """
        UPDATE urunperformansdetay 
        SET performanskategori = CASE 
            WHEN toplamciro > (SELECT PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY toplamciro) FROM urunperformansdetay) THEN 'Yildiz'
            WHEN toplamciro > (SELECT PERCENTILE_CONT(0.7) WITHIN GROUP (ORDER BY toplamciro) FROM urunperformansdetay) THEN 'Populer'
            WHEN toplamciro > (SELECT PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY toplamciro) FROM urunperformansdetay) THEN 'Orta'
            WHEN son30gunciro = 0 THEN 'Durgun'
            ELSE 'Dusuk'
        END
    """
    # SQLite için BASİT percentile yaklaşımı
    if not is_pg:
        update_perf_query = """
            UPDATE urunperformansdetay 
            SET performanskategori = CASE 
                WHEN son30gunciro = 0 THEN 'Durgun'
                WHEN urunid IN (SELECT urunid FROM urunperformansdetay ORDER BY toplamciro DESC LIMIT (SELECT COUNT(*) / 10 FROM urunperformansdetay)) THEN 'Yildiz'
                WHEN urunid IN (SELECT urunid FROM urunperformansdetay ORDER BY toplamciro DESC LIMIT (SELECT COUNT(*) / 3 FROM urunperformansdetay)) THEN 'Populer'
                ELSE 'Orta'
            END
        """
    
    try:
        cursor.execute(update_perf_query)
    except Exception as e:
        logger.warning(f"Performans kategorileri güncellenemedi: {e}")

    logger.info(f"✅ urunperformansdetay güncellendi ({cursor.rowcount} ürün)")

def rebuild_kategori_performans_ozet(conn):
    """Kategori bazlı performans özetlerini hesapla"""
    logger.info("Kategori performans özetleri hesaplanıyor...")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM kategoriperformansozet")

    is_pg = (DB_BACKEND == "postgresql")
    now_func = "CURRENT_TIMESTAMP::TEXT" if is_pg else "datetime('now')"

    # Temel metrikleri tüm kategorilerden çek (satışsız kategoriler de dahil)
    query = f"""
        INSERT INTO kategoriperformansozet (
            kategori_id, kategori_adi, toplam_urun_sayisi, aktif_urun_sayisi,
            toplam_ciro, son_30_gun_toplam_ciro, karsilastirma_skoru, performans_kategori, last_updated
        )
        SELECT
            k.id, k.ana,
            COUNT(u.id) as toplam_urun,
            SUM(CASE WHEN COALESCE(upd.son30gunciro, 0) > 0 THEN 1 ELSE 0 END) as aktif_urun,
            COALESCE(SUM(upd.toplamciro), 0) as toplam_ciro,
            COALESCE(SUM(upd.son30gunciro), 0) as son30_ciro,
            COALESCE(SUM(upd.son30gunciro), 0) / NULLIF(COUNT(u.id), 0) / 100.0 as skor,
            'Normal',
            {now_func}
        FROM kategoriler k
        LEFT JOIN urunler u ON u.kategori_id = k.id
        LEFT JOIN urunperformansdetay upd ON upd.kategoriid = k.id
        GROUP BY k.id, k.ana
    """
    cursor.execute(query)

    # pazar_payi, trend ve momentum hesapla
    # Son 2 ayın ciro verisini kategorikarsilastirma'dan çek
    cursor.execute("""
        SELECT kategori, ay, toplam_ciro
        FROM kategorikarsilastirma
        ORDER BY ay DESC
    """)
    ay_rows = cursor.fetchall()

    # Ayları grupla
    from collections import defaultdict
    ay_ciro = defaultdict(dict)  # {kategori: {ay: ciro}}
    aylar_set = set()
    for row in ay_rows:
        ay_ciro[row["kategori"]][row["ay"]] = row["toplam_ciro"] or 0
        aylar_set.add(row["ay"])

    aylar = sorted(aylar_set, reverse=True)
    son_ay = aylar[0] if len(aylar) > 0 else None
    onceki_ay = aylar[1] if len(aylar) > 1 else None

    # Toplam ciro (pazar payı için)
    toplam_son_ay = sum(v.get(son_ay, 0) for v in ay_ciro.values()) if son_ay else 0

    # Her kategori için güncelle
    cursor.execute("SELECT kategori_id, kategori_adi FROM kategoriperformansozet")
    kategoriler = cursor.fetchall()

    for kat in kategoriler:
        kat_adi = kat["kategori_adi"]
        kat_id = kat["kategori_id"]

        son_ciro = ay_ciro.get(kat_adi, {}).get(son_ay, 0) if son_ay else 0
        onceki_ciro = ay_ciro.get(kat_adi, {}).get(onceki_ay, 0) if onceki_ay else 0

        # Pazar payı
        pazar_payi = round((son_ciro / toplam_son_ay) * 100, 2) if toplam_son_ay > 0 else 0

        # Trend: +1 büyüyor, -1 düşüyor, 0 stabil
        if onceki_ciro > 0:
            degisim = (son_ciro - onceki_ciro) / onceki_ciro
            if degisim > 0.02:
                trend = 1
                momentum = "Yükseliyor"
                perf_kat = "İyi"
            elif degisim < -0.02:
                trend = -1
                momentum = "Düşüyor"
                perf_kat = "Zayıf"
            else:
                trend = 0
                momentum = "Stabil"
                perf_kat = "Normal"
        else:
            trend = 0
            momentum = "Stabil"
            perf_kat = "Normal"

        ph = "%s" if is_pg else "?"
        cursor.execute(
            f"""UPDATE kategoriperformansozet
                SET pazar_payi = {ph}, trend = {ph}, momentum = {ph}, performans_kategori = {ph}
                WHERE kategori_id = {ph}""",
            [pazar_payi, trend, momentum, perf_kat, kat_id]
        )

    logger.info(f"✅ kategoriperformansozet güncellendi ({len(kategoriler)} kategori)")

def update_category_analiz_ozet(conn, where_clause=""):
    """
    Kategori Raporu sayfası için kategori_analiz_ozet tablosunu yeniler.
    (refresh_category_cache.py mantığının entegre edilmiş hali)
    """
    from backend.api import db_engine
    logger.info("Kategori Analiz Özet tablosu güncelleniyor (Pre-calculation)...")
    cursor = db_engine.get_dict_cursor(conn)
    import json
    from decimal import Decimal
    
    class _Enc(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (Decimal, float)): return float(o)
            if hasattr(o, 'isoformat'): return o.isoformat()
            return super().default(o)
            
    def safe_json(obj):
        return json.dumps(obj, cls=_Enc, ensure_ascii=False)

    ph = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
    is_pg = db_engine.DB_BACKEND == 'postgresql'
    
    # 1. Kategorileri topla
    query = f"""
        SELECT id, ana, alt1, alt2, 
               CASE 
                 WHEN alt2 IS NOT NULL THEN 'alt2'
                 WHEN alt1 IS NOT NULL THEN 'alt1'
                 ELSE 'ana' 
               END as level
        FROM kategoriler
        {where_clause}
    """
    cursor.execute(query)
    all_cats = cursor.fetchall()
    
    # Seviyelere göre grupla (ana, alt1, alt2)
    levels = {'ana': set(), 'alt1': set(), 'alt2': set()}
    cat_id_map = {'ana': defaultdict(list), 'alt1': defaultdict(list), 'alt2': defaultdict(list)}
    
    for row in all_cats:
        c_id = row['id']
        if row['ana']: 
            levels['ana'].add(row['ana'])
            cat_id_map['ana'][row['ana']].append(c_id)
        if row['alt1']: 
            levels['alt1'].add(row['alt1'])
            cat_id_map['alt1'][row['alt1']].append(c_id)
        if row['alt2']: 
            levels['alt2'].add(row['alt2'])
            cat_id_map['alt2'][row['alt2']].append(c_id)

    # 2. Her kategori için hesapla
    processed_count = 0
    for lvl, names in levels.items():
        for name in names:
            ids = cat_id_map[lvl][name]
            if not ids: continue
            
            p_str = ",".join([ph] * len(ids))
            
            # KPIs - daily_metrics_summary kullanarak optimize et
            cursor.execute(f"""
                SELECT 
                    SUM(revenue) as total_revenue, 
                    SUM(receipt_count) as total_receipts, 
                    SUM(customer_count) as total_customers, 
                    SUM(unit_count) as total_quantity
                FROM daily_metrics_summary WHERE kategori_id IN ({p_str})
            """, ids)
            kpi_row = cursor.fetchone()
            rev, fis, cust, qty = kpi_row['total_revenue'] or 0, kpi_row['total_receipts'] or 0, kpi_row['total_customers'] or 0, kpi_row['total_quantity'] or 0
            
            # Trends (Son 12 ay) - daily_metrics_summary kullanarak optimize et
            month_expr = "TO_CHAR(tarih, 'YYYY-MM')" if is_pg else "strftime('%Y-%m', tarih)"
            cursor.execute(f"""
                SELECT {month_expr} as month, SUM(revenue) as revenue, SUM(unit_count) as quantity 
                FROM daily_metrics_summary WHERE kategori_id IN ({p_str}) 
                GROUP BY month ORDER BY month DESC LIMIT 12
            """, ids)
            trends = [{'month': r['month'], 'revenue': r['revenue'], 'quantity': r['quantity']} for r in cursor.fetchall()]
            
            # Top Products - product_daily_summary kullanarak optimize et (ve sayıları ekle)
            cursor.execute(f"""
                SELECT u.id, u.ad, SUM(ps.revenue) as r, SUM(ps.customer_count) as cc, SUM(ps.receipt_count) as rc
                FROM product_daily_summary ps
                JOIN urunler u ON ps.urun_id = u.id
                WHERE u.kategori_id IN ({p_str})
                GROUP BY u.id, u.ad ORDER BY r DESC LIMIT 10
            """, ids)
            top_products = [
                {'product_id': r['id'], 'product_name': r['ad'], 'revenue': r['r'], 'customer_count': r['cc'], 'receipt_count': r['rc']} 
                for r in cursor.fetchall()
            ]
            
            # RFM Dağılımı - daily_metrics_summary kullanarak optimize et
            cursor.execute(f"""
                SELECT rfm_segment, SUM(customer_count) as customer_count
                FROM daily_metrics_summary 
                WHERE kategori_id IN ({p_str}) AND rfm_segment IS NOT NULL
                GROUP BY rfm_segment
            """, ids)
            rfm = [{'segment': r['rfm_segment'], 'count': r['customer_count']} for r in cursor.fetchall()]

            # Birliktelik Analizi (Associations) - Pre-calculate and cache (Slowest part, now cached!)
            cursor.execute(f"""
                SELECT
                    k2.ana as category_name,
                    AVG(gb.confidence) as confidence,
                    AVG(gb.lift) as lift,
                    SUM(gb.ortak_fis_sayisi) as ortak_fis_sayisi,
                    SUM(gb.ortak_musteri_sayisi) as ortak_musteri_sayisi
                FROM grupbirliktelikleri gb
                JOIN kategoriler k2 ON gb.kategori_id_2 = k2.id
                WHERE gb.kategori_id_1 IN ({p_str})
                  AND k2.ana != %s
                  AND k2.ana IS NOT NULL
                  AND gb.tip = 'CAT_ONLY_SQL'
                GROUP BY k2.ana
                ORDER BY lift DESC, ortak_fis_sayisi DESC
                LIMIT 30
            """, (*ids, name))
            assoc = [
                {'category_name': r['category_name'], 'confidence': r['confidence'], 'lift': r['lift'], 'ortak_fis_sayisi': r['ortak_fis_sayisi'], 'ortak_musteri_sayisi': r['ortak_musteri_sayisi']}
                for r in cursor.fetchall()
            ]

            # Kaydet (Upsert)
            if is_pg:
                cursor.execute("""
                    INSERT INTO kategori_analiz_ozet (
                        kategori_adi, level, total_revenue, total_receipts, total_customers, 
                        total_quantity, avg_price, trends_json, top_products_json, rfm_json, associations_json, guncelleme_tarihi
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (kategori_adi, level) DO UPDATE SET
                        total_revenue = EXCLUDED.total_revenue, total_receipts = EXCLUDED.total_receipts, 
                        total_customers = EXCLUDED.total_customers, total_quantity = EXCLUDED.total_quantity, 
                        avg_price = EXCLUDED.avg_price, trends_json = EXCLUDED.trends_json,
                        top_products_json = EXCLUDED.top_products_json, rfm_json = EXCLUDED.rfm_json, 
                        associations_json = EXCLUDED.associations_json, guncelleme_tarihi = CURRENT_TIMESTAMP
                """, (name, lvl, rev, fis, cust, qty, rev/qty if qty > 0 else 0, safe_json(trends), safe_json(top_products), safe_json(rfm), safe_json(assoc)))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO kategori_analiz_ozet (
                        kategori_adi, level, total_revenue, total_receipts, total_customers, 
                        total_quantity, avg_price, trends_json, top_products_json, rfm_json, associations_json, guncelleme_tarihi
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (name, lvl, rev, fis, cust, qty, rev/qty if qty > 0 else 0, safe_json(trends), safe_json(top_products), safe_json(rfm), safe_json(assoc)))
            
            processed_count += 1
            if processed_count % 50 == 0:
                conn.commit()
    
    conn.commit()
    logger.info(f"✅ kategori_analiz_ozet güncellendi ({processed_count} kategori)")

def rebuild_etiket_ozeti_cache(conn):
    """
    Segmentation sayfası için etiket özetlerini (global) pre-calculate eder.
    Büyük veri setlerinde 30s timeout sorununu çözmek için kritik.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Etiket Özeti Önbelleği güncelleniyor (Pre-calculation)...")
    import json
    import time
    from decimal import Decimal
    
    class _Enc(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (Decimal, float)): return float(o)
            if hasattr(o, 'isoformat'): return o.isoformat()
            return super().default(o)

    LABEL_GROUPS = {
        'ziyaret': ['sabah_alisveriscisi', 'aksam_alisveriscisi', 'gece_alisveriscisi', 'hafta_sonu_alisveriscisi', 'hafta_ici_alisveriscisi', 'aylik_duzenli_alici', 'maas_gunu_alisveriscisi', 'gunluk_ugrayan', 'seyrek_alisverisci', 'cok_magazali_musteri'],
        'sepet': ['buyuk_sepet_alisveriscisi', 'kucuk_sepet_alisveriscisi', 'premium_harcayici', 'ekonomik_harcayici', 'b2b_mahalle_esnafi', 'stokcu_alici', 'tekli_urun_alisveriscisi', 'mixed_sepet_alisveriscisi'],
        'fiyat': ['indirim_avcisi', 'promosyon_bagimli', 'fiyat_hassas', 'fiyata_duyarsiz', 'coklu_alim_firsatcisi', 'enflasyon_stokcusu', 'kampanya_tepkisi_dusuk'],
        'taze_gida': ['kasap_odakli', 'manav_odakli', 'firinci_odakli', 'sarkuteri_odakli', 'sut_urunleri_odakli', 'bakliyat_odakli', 'baharat_odakli', 'sadece_taze_gidaci', 'yoresel_urun_meraklisi', 'taze_gida_kacinani', 'taze_gida_terk_eden'],
        'urun_odak': ['atistirmalik_odakli', 'icecek_tutkunuodakli', 'kahvaltilik_odakli', 'kisisel_bakim_odakli', 'temizlik_odakli', 'bebek_urunleri_odakli', 'ev_tekstili_odakli', 'organik_saglikli_odakli', 'dondurulmus_odakli'],
        'kategori': ['saglikli_yasam_egilimli', 'hazir_tuketim_egilimli', 'protein_odakli', 'kafein_yogun_tuketici', 'atistirmalik_tuketicisi', 'temizlik_hijyen_odakli', 'kisisel_bakim_tutkunu', 'misafir_sofrasi_kurucusu'],
        'kanal': ['winback_adayi', 'reaktivasyon_potansiyeli', 'yeniden_kazanilmis', 'kampanya_duyarli', 'kampanyasiz_sadik'],
        'odeme': ['yemek_karti_kullanicisi', 'ay_sonu_yemek_karti_harcayicisi', 'fatura_musterisi'],
        'sadakat': ['sadik_musteri', 'soguyan_musteri', 'kaybedilme_riski_yuksek', 'tamamen_kaybedilmis', 'yeniden_kazanilmis_saglik', 'gidip_gelen_musteri', 'sepeti_daralan', 'kategori_terk_eden', 'marji_dusuran', 'gizli_risk', 'kaybedilmemesi_gereken'],
        'hane': ['hane_bekar_skoru', 'hane_cift_skoru', 'hane_aile_skoru', 'hane_cocuklu_skoru', 'hane_bebek_skoru', 'hane_yasli_skoru', 'hane_evcil_hayvan_skoru', 'hane_araba_skoru', 'hane_toplu_alim_skoru']
    }
    SCORE_COLUMNS = set(LABEL_GROUPS['hane'])
    all_labels = [label for group in LABEL_GROUPS.values() for label in group]
    
    cursor = conn.cursor()
    # Global DB_BACKEND'i kullan (top level'dan geliyor)
    is_pg = (DB_BACKEND == "postgresql")
    ph = "%s" if is_pg else "?"
    print(f"DEBUG: Using {DB_BACKEND} backend")
    
    # 1. Global Özet (Filtresiz)
    filter_parts = []
    for col in all_labels:
        if col in SCORE_COLUMNS:
            filter_parts.append(f"COUNT(*) FILTER (WHERE {col} >= 0.4) as {col}")
        else:
            filter_parts.append(f"COUNT(*) FILTER (WHERE {col} = TRUE) as {col}")
    
    # SQLite için FILTER uyumluluğu kontrolü (yoksa CASE kullan)
    if not is_pg:
        filter_parts = []
        for col in all_labels:
            if col in SCORE_COLUMNS:
                filter_parts.append(f"SUM(CASE WHEN {col} >= 0.4 THEN 1 ELSE 0 END) as {col}")
            else:
                filter_parts.append(f"SUM(CASE WHEN {col} = 1 THEN 1 ELSE 0 END) as {col}")

    try:
        cursor.execute("SELECT COUNT(*) FROM musterietiketler")
        total = cursor.fetchone()[0] or 1
        
        sql = f"SELECT {', '.join(filter_parts)} FROM musterietiketler"
        cursor.execute(sql)
        row = cursor.fetchone()
        
        # Row'u dict'e çevir (PG DictCursor değilse index ile al)
        if hasattr(row, 'keys'):
            counts = dict(row)
        else:
            counts = {all_labels[i]: row[i] for i in range(len(all_labels))}
            
        result = {
            'toplam_musteri': total,
            'etiketler': [],
            'kategoriler': {},
            'ts': time.time()
        }
        
        for group_name, labels in LABEL_GROUPS.items():
            group_data = []
            for col in labels:
                count = counts.get(col) or 0
                item = {
                    'kolon': col,
                    'sayi': count,
                    'oran': round(count / total * 100, 1)
                }
                group_data.append(item)
                result['etiketler'].append(item)
            result['kategoriler'][group_name] = group_data
            
        # Kaydet
        json_str = json.dumps(result, cls=_Enc)
        now_func = "CURRENT_TIMESTAMP" if is_pg else "datetime('now')"
        
        cursor.execute(f"""
            INSERT INTO syncmeta (key, value, updated_at) 
            VALUES ('etiket_ozeti_global', {ph}, {now_func})
            ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at={now_func}
        """ if is_pg else f"""
            INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
            VALUES ('etiket_ozeti_global', ?, datetime('now'))
        """, (json_str,))
        
        logger.info("✅ Global etiket özeti önbelleklendi.")
    except Exception as e:
        logger.error(f"❌ Etiket özeti önbellekleme hatası: {e}")

def rebuild_all_summaries() -> int:
    """Tüm özetleri yeniden hesapla (Retry mekanizmalı)"""
    import time
    logger.info("Tüm özetler yeniden hesaplanıyor...")

    max_retries = 5
    for attempt in range(max_retries):
        conn = get_connection()
        try:
            if DB_BACKEND == "postgresql":
                # PostgreSQL için kilit ve işlem zaman aşımı sürelerini ayarla
                cursor = conn.cursor()
                cursor.execute("SET lock_timeout = '10s'")
                cursor.execute("SET statement_timeout = '300s'")
            elif DB_BACKEND != "postgresql":
                conn.execute("BEGIN IMMEDIATE")
            
            cursor = conn.cursor()
            # Tablolari temizle
            tables_to_clear = [
                "gunlukciroozet", "magazagunlukozet", "gunlukozet", "crmozet",
                "kategorikarsilastirma", "markakarsilastirma", "kampanyaozet",
                "musterisadakat", "daily_metrics_summary", "urunperformansdetay", "kategoriperformansozet"
            ]
            for table in tables_to_clear:
                cursor.execute(f"DELETE FROM {table}")
            
            cursor.execute("DROP TABLE IF EXISTS brandsummary")
            conn.commit()
            conn.commit()
            conn.close()
            break
        except Exception as e:
            if "locked" in str(e):
                logger.warning(f"Cleanup failed (locked), retrying... ({attempt+1}/{max_retries})")
                if conn: conn.close()
                time.sleep(3)
                continue
            else:
                raise e
    else:
        logger.error("Failed to start rebuild: Database is persistently locked.")
        return 0
    # Tüm tarihleri bul
    conn = get_connection() # Re-establish connection after cleanup
    cursor = conn.cursor() # Re-establish cursor
    tarih_query = "SELECT DISTINCT tarih FROM satislar ORDER BY 1" if DB_BACKEND == "postgresql" else "SELECT DISTINCT date(tarih) FROM satislar ORDER BY 1"
    cursor.execute(tarih_query)
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()

    total = len(dates)
    logger.info(f"Toplam {total} gün işlenecek")

    updated = 0
    for i, d in enumerate(dates):
        if sync_summary_for_date(d, update_heavy=False):
            updated += 1

        if (i + 1) % 100 == 0:
            logger.info(f"  {i + 1}/{total} gün işlendi...")

    logger.info(f"Toplam {updated} gün için özet oluşturuldu")

    # En Çok Satan İstatistiklerini Güncelle (Global)
    try:
        conn = get_connection()
        update_best_sellers(conn.cursor())
        conn.commit()
        
        # RFM, brandsummary ve kategori_analiz Full Rebuild
        update_rfm_analysis(conn)
        rebuild_musteri_detay_ozet(conn)
        update_brand_summary(conn)
        update_category_analiz_ozet(conn)

        # Ürün ve Grup Birliktelikleri (Kampanya & Öneriler için)
        try:
            from update_urun_birliktelikleri_fast import update_urun_birliktelikleri_table, update_group_associations
            logger.info("Ürün ve Grup Birliktelikleri hesaplanıyor...")
            update_urun_birliktelikleri_table()
            update_group_associations()
            logger.info("✅ Birliktelik analizleri tamamlandı.")
        except ImportError:
            logger.warning("update_urun_birliktelikleri_fast.py bulunamadı, birliktelikler atlandı.")

        # Global istatistikleri güncelle
        update_global_stats(conn)
        
        # Ürün ve Kategori Performans Detaylarını Rebuild Et
        rebuild_urun_performans_detay(conn)
        rebuild_kategori_performans_ozet(conn)
        
        conn.commit()
        conn.close()
        logger.info("Tüm istatistikler (RFM, Brand, Association, Global) güncellendi.")
    except Exception as e:
        logger.error(f"Global güncellemeler sırasında hata: {e}")

    return updated


def nightly_phased_rebuild():
    """
    Gece fazlı rebuild - 5 aşamada tüm özet tablolarını günceller.
    Saatlik delta sync'ten ayrı olarak, gece 02:00'de çalışır.
    Her faz bağımsız hata yönetimine sahiptir.
    """
    import time as _time
    
    total_start = _time.time()
    phase_results = {}
    
    logger.info("=" * 60)
    logger.info("🌙 [GECE REBUILD] Fazlı yeniden hesaplama başlıyor...")
    logger.info("=" * 60)
    
    # ══════════════════════════════════════════════════════════
    # FAZ 1: Günlük Özetler (hafif, ~5dk)
    # Tablolar: gunlukciroozet, magazagunlukozet, crmozet,
    #           daily_metrics_summary, gunlukozet, kategorikarsilastirma,
    #           markakarsilastirma, kampanyaozet, genelozet
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 1/5] 📊 Günlük özetler hesaplanıyor...")
    phase_start = _time.time()
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Son 7 günün özetlerini yenile (tutarlılık için)
        tarih_query = "SELECT DISTINCT tarih FROM satislar ORDER BY 1 DESC LIMIT 7" if DB_BACKEND == "postgresql" else "SELECT DISTINCT date(tarih) FROM satislar ORDER BY 1 DESC LIMIT 7"
        cursor.execute(tarih_query)
        recent_dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        updated = 0
        for d in recent_dates:
            if sync_summary_for_date(d, update_heavy=False):
                updated += 1
        
        phase_duration = _time.time() - phase_start
        phase_results['faz1'] = True
        logger.info(f"[FAZ 1/5] ✅ {updated} gün güncellendi ({phase_duration:.1f}s)")
    except Exception as e:
        phase_results['faz1'] = False
        logger.error(f"[FAZ 1/5] ❌ HATA: {e}", exc_info=True)
    
    # ══════════════════════════════════════════════════════════
    # FAZ 2.5: Feature Tabloları + Müşteri Etiketleri (orta, ~3dk)
    # Tablolar: musterifiyatfeatures, musteriziyaretfeatures,
    #           musteridonem_karsilastirma, musterietiketler vb.
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 2.5] 🏷️ Feature tabloları ve müşteri etiketleri güncelleniyor...")
    phase_start = _time.time()
    try:
        backend_dir = os.path.join(BASE_DIR, "backend")
        feature_script = os.path.join(backend_dir, "feature_core_builder.py")
        label_script = os.path.join(backend_dir, "label_engine.py")

        if os.path.exists(feature_script):
            logger.info("   → feature_core_builder.py çalışıyor...")
            # capture_output=False: stdout/stderr'i RAM'de tutmak yerine doğrudan log'a yaz
            feat_result = subprocess.run(
                [sys.executable, feature_script],
                cwd=backend_dir, capture_output=False, text=True, timeout=600
            )
            if feat_result.returncode != 0:
                logger.warning(f"   ⚠️ feature_core_builder hata (kod={feat_result.returncode})")
            else:
                logger.info("   ✅ Feature tabloları güncellendi")
        else:
            logger.warning(f"   ⚠️ feature_core_builder.py bulunamadı: {feature_script}")

        if os.path.exists(label_script):
            logger.info("   → label_engine.py çalışıyor...")
            label_result = subprocess.run(
                [sys.executable, label_script],
                cwd=backend_dir, capture_output=False, text=True, timeout=600
            )
            if label_result.returncode != 0:
                logger.warning(f"   ⚠️ label_engine hata (kod={label_result.returncode})")
            else:
                logger.info("   ✅ Müşteri etiketleri güncellendi")
        else:
            logger.warning(f"   ⚠️ label_engine.py bulunamadı: {label_script}")

        phase_duration = _time.time() - phase_start
        phase_results['faz2_5'] = True
        logger.info(f"[FAZ 2.5] ✅ Etiketler güncellendi ({phase_duration:.1f}s)")
    except Exception as e:
        phase_results['faz2_5'] = False
        logger.error(f"[FAZ 2.5] ❌ HATA: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════════
    # FAZ 3: RFM + Segmentasyon (orta, ~1dk)
    # Tablolar: musteriler (rfm_segment, rfm_r/f/m_score güncellemesi)
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 3/5] 🎯 RFM analizi ve segmentasyon hesaplanıyor...")
    phase_start = _time.time()
    try:
        conn = get_connection()
        update_rfm_analysis(conn)
        conn.commit()

        # syncmeta'yı güncelle
        cursor = conn.cursor()
        ph = "%s" if DB_BACKEND == "postgresql" else "?"
        now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
        if DB_BACKEND == "postgresql":
            cursor.execute(f"""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('rfm_last_update', {ph}, {now_func})
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at={now_func}
            """, (datetime.now().isoformat(),))
        else:
            cursor.execute(f"""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('rfm_last_update', ?, datetime('now'))
            """, (datetime.now().isoformat(),))
        conn.commit()
        conn.close()

        # RFM sonrası musteridetayozet'i güncelle (güncel segmentlerle)
        logger.info("   → musteridetayozet güncelleniyor (güncel RFM ile)...")
        conn2 = get_connection()
        if DB_BACKEND == "postgresql":
            cursor2 = conn2.cursor()
            cursor2.execute("SET statement_timeout = '600s'")
        rebuild_musteri_detay_ozet(conn2)
        conn2.commit()
        conn2.close()

        phase_duration = _time.time() - phase_start
        phase_results['faz3'] = True
        logger.info(f"[FAZ 3/5] ✅ RFM segmentasyonu + musteridetayozet güncellendi ({phase_duration:.1f}s)")
    except Exception as e:
        phase_results['faz3'] = False
        logger.error(f"[FAZ 3/5] ❌ HATA: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════════
    # FAZ 4: Marka & Ürün Performans + Global İstatistikler (orta, ~3dk)
    # Tablolar: brandsummary, urunperformansdetay, kategoriperformansozet,
    #           globalstatlar, encoksatanlar
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 4/5] 🏷️ Marka & ürün performansı hesaplanıyor...")
    phase_start = _time.time()
    try:
        conn = get_connection()
        if DB_BACKEND == "postgresql":
            cursor = conn.cursor()
            cursor.execute("SET statement_timeout = '600s'")
        
        logger.info("   → brandsummary güncelleniyor...")
        update_brand_summary(conn)
        conn.commit()
        
        logger.info("   → urunperformansdetay güncelleniyor...")
        rebuild_urun_performans_detay(conn)
        conn.commit()
        
        logger.info("   → kategoriperformansozet güncelleniyor...")
        rebuild_kategori_performans_ozet(conn)
        conn.commit()
        
        logger.info("   → globalstatlar güncelleniyor...")
        update_global_stats(conn)
        conn.commit()
        
        logger.info("   → encoksatanlar güncelleniyor...")
        update_best_sellers(conn.cursor())
        conn.commit()
        
        conn.close()
        
        phase_duration = _time.time() - phase_start
        phase_results['faz4'] = True
        logger.info(f"[FAZ 4/5] ✅ Marka & ürün performansı güncellendi ({phase_duration:.1f}s)")
    except Exception as e:
        phase_results['faz4'] = False
        logger.error(f"[FAZ 4/5] ❌ HATA: {e}", exc_info=True)
    
    # ══════════════════════════════════════════════════════════
    # FAZ 5: Birliktelik & Kampanya Analizleri (ağır, ~5dk)
    # Tablolar: urunbirliktelik, grupbirliktelik
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 5/5] 🔗 Birliktelik ve kampanya analizleri hesaplanıyor...")
    phase_start = _time.time()
    try:
        from update_urun_birliktelikleri_fast import update_urun_birliktelikleri_table, update_group_associations
        
        logger.info("   → Ürün birliktelikleri hesaplanıyor...")
        update_urun_birliktelikleri_table()
        
        logger.info("   → Grup birliktelikleri hesaplanıyor...")
        update_group_associations()
        
        phase_duration = _time.time() - phase_start
        phase_results['faz5'] = True
        logger.info(f"[FAZ 5/5] ✅ Birliktelik analizleri tamamlandı ({phase_duration:.1f}s)")
    except ImportError:
        phase_results['faz5'] = False
        logger.warning("[FAZ 5/5] ⚠️ Birliktelik modülü bulunamadı, atlandı.")
    except Exception as e:
        phase_results['faz5'] = False
        logger.error(f"[FAZ 5/5] ❌ HATA: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════════
    # FAZ 5.5: Etiket Özeti Önbellekleme (yeni, ~10s)
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 5.5] 🏷️ Etiket özeti önbelleği güncelleniyor...")
    try:
        conn = get_connection()
        rebuild_etiket_ozeti_cache(conn)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[FAZ 5.5] ❌ HATA: {e}")
    
    # ══════════════════════════════════════════════════════════
    # FAZ 6: Kampanya Önerileri Yeniden Üretimi (orta, ~2dk)
    # Tüm bağımlı tablolar (RFM, birliktelik, ürün performans) hazır
    # ══════════════════════════════════════════════════════════
    logger.info("[FAZ 6/6] 📣 Kampanya önerileri yeniden üretiliyor...")
    phase_start = _time.time()
    try:
        import sys as _sys
        backend_dir = os.path.join(BASE_DIR, "backend")
        if backend_dir not in _sys.path:
            _sys.path.insert(0, backend_dir)
        if BASE_DIR not in _sys.path:
            _sys.path.insert(0, BASE_DIR)

        from database.campaign_manager import kampanya_onerileri_uret
        kampanya_onerileri_uret()

        phase_duration = _time.time() - phase_start
        phase_results['faz6'] = True
        logger.info(f"[FAZ 6/6] ✅ Kampanya önerileri güncellendi ({phase_duration:.1f}s)")
    except Exception as e:
        phase_results['faz6'] = False
        logger.error(f"[FAZ 6/6] ❌ HATA: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════════
    # SONUÇ RAPORU
    # ══════════════════════════════════════════════════════════
    total_duration = _time.time() - total_start
    success_count = sum(1 for v in phase_results.values() if v)
    total_count = len(phase_results)
    
    # Syncmeta güncelle
    try:
        conn = get_connection()
        cursor = conn.cursor()
        ph = "%s" if DB_BACKEND == "postgresql" else "?"
        now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
        cursor.execute(f"""
            INSERT INTO syncmeta (key, value, updated_at)
            VALUES ('last_nightly_rebuild', {ph}, {now_func})
            ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at={now_func}
        """ if DB_BACKEND == "postgresql" else f"""
            INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
            VALUES ('last_nightly_rebuild', ?, datetime('now'))
        """, (datetime.now().isoformat(),))
        conn.commit()
        conn.close()
    except Exception:
        pass
    
    logger.info("=" * 60)
    logger.info(f"🌙 [GECE REBUILD] TAMAMLANDI - {success_count}/{total_count} faz başarılı ({total_duration:.1f}s)")
    for faz, ok in phase_results.items():
        logger.info(f"   {'✅' if ok else '❌'} {faz.upper()}")
    logger.info("=" * 60)
    
    return success_count


def get_summary_stats() -> dict:
    """Özet istatistikleri döndür"""
    conn = get_connection()
    cursor = conn.cursor()

    # Toplam günlük özet
    cursor.execute("SELECT COUNT(*) FROM gunlukciroozet")
    gunluk_count = cursor.fetchone()[0]

    # Toplam mağaza özet
    cursor.execute("SELECT COUNT(*) FROM magazagunlukozet")
    magaza_count = cursor.fetchone()[0]

    # Toplam ciro (özetlerden)
    cursor.execute("SELECT SUM(toplam_ciro) FROM gunlukciroozet")
    toplam_ciro = cursor.fetchone()[0] or 0

    # Tarih aralığı
    cursor.execute("SELECT MIN(tarih), MAX(tarih) FROM gunlukciroozet")
    dates = cursor.fetchone()

    conn.close()

    return {
        'gunluk_ozet_sayisi': gunluk_count,
        'magaza_ozet_sayisi': magaza_count,
        'toplam_ciro': toplam_ciro,
        'min_tarih': dates[0],
        'max_tarih': dates[1]
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--rebuild':
            # Tüm özetleri yeniden hesapla
            rebuild_all_summaries()
        elif sys.argv[1] == '--rebuild-upd':
            # Sadece urun performans detayini yeniden hesapla
            conn = get_connection()
            try:
                rebuild_urun_performans_detay(conn)
                conn.commit()
            finally:
                conn.close()
        elif sys.argv[1] == '--rebuild-mdo':
            # Sadece müşteri detay özetini yeniden hesapla
            conn = get_connection()
            try:
                rebuild_musteri_detay_ozet(conn)
                conn.commit()
            finally:
                conn.close()
        elif sys.argv[1] == '--rebuild-cat':
            # Sadece kategori analiz özetini yeniden hesapla
            conn = get_connection()
            try:
                update_category_analiz_ozet(conn)
                conn.commit()
            finally:
                conn.close()
        elif sys.argv[1] == '--today':
            # Sadece bugün
            sync_summary_for_today()
        elif sys.argv[1] == '--stats':
            # İstatistikler
            stats = get_summary_stats()
            print(f"Günlük özet sayısı: {stats['gunluk_ozet_sayisi']}")
            print(f"Mağaza özet sayısı: {stats['magaza_ozet_sayisi']}")
            print(f"Toplam ciro: {stats['toplam_ciro']:,.2f} TL")
            print(f"Tarih aralığı: {stats['min_tarih']} - {stats['max_tarih']}")
        else:
            print("Kullanım: python sync_summary.py [--rebuild|--today|--stats]")
    else:
        # Varsayılan: tüm özetleri yeniden hesapla
        rebuild_all_summaries()
