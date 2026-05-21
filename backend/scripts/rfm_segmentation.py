
import os
import sqlite3
import logging
import sys
from datetime import datetime

# Adjust path for imports if necessary
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from api import db_engine
except ImportError:
    # If called from root or elsewhere
    from backend.api import db_engine

logger = logging.getLogger(__name__)

# Segment definitions (Standardized to match rfm_view.py)
SEGMENT_CONFIG = {
    '01-) Şampiyonlar': {'color': '#10b981'},
    '02-) Potansiyel Şampiyonlar': {'color': '#22c55e'},
    '03-) Sadık Müşteriler': {'color': '#3b82f6'},
    '04-) Sadık Olmaya Adaylar': {'color': '#8b5cf6'},
    '05-) Yeni Müşteriler': {'color': '#06b6d4'},
    '06-) Tekrar Kazanılanlar': {'color': '#14b8a6'},
    '07-) Yüksek Harcama Yapanlar': {'color': '#a855f7'},
    '08-) İlgi Bekleyenler': {'color': '#f59e0b'},
    '09-) Risk Altındakiler': {'color': '#ef4444'},
    '10-) Uyuyanlar': {'color': '#6b7280'},
    '11-) Kayıp Müşteriler': {'color': '#1f2937'}
}

def calculate_r_score(days):
    if days <= 30: return 5
    elif days <= 60: return 4
    elif days <= 90: return 3
    elif days <= 150: return 2 # Relaxed from 120
    else: return 1

def calculate_f_score(monthly_freq):
    # Normalized by month. 3+ visits/month is very high for many retail contexts.
    if monthly_freq >= 3.0: return 5
    elif monthly_freq >= 2.0: return 4
    elif monthly_freq >= 1.0: return 3
    elif monthly_freq >= 0.5: return 2
    else: return 1

def calculate_m_score(monthly_amount):
    # Normalized by month.
    if monthly_amount >= 15000: return 5
    elif monthly_amount >= 7500: return 4
    elif monthly_amount >= 3000: return 3
    elif monthly_amount >= 1000: return 2
    else: return 1

def determine_segment(r, f, m, days_since_prev=None, first_purchase_days=None, recency_days=None, freq=None):
    # 0. YENİ MÜŞTERİ KONTROLÜ (Kayıp kontrolünden ÖNCE yapılmalı)
    # Yeni müşteri: İlk alışveriş son 30 gün içinde VE toplam ziyaret < 3
    if first_purchase_days is not None and first_purchase_days <= 30 and freq is not None and freq < 3:
        return '05-) Yeni Müşteriler'
    
    # 1. Kayıp Müşteriler (Yeni müşteri olmayanlar için)
    if recency_days is not None and recency_days > 180:
        return '11-) Kayıp Müşteriler'
    
    # 2. Loyal / High Value
    if r >= 4 and f >= 4 and m >= 4:
        return '01-) Şampiyonlar'
    if r >= 3 and f >= 3 and m >= 3:
        return '03-) Sadık Müşteriler'
    
    # 3. High Spend but very low frequency (rare but big spenders)
    if m >= 3 and f <= 1.2: # 1.2 tolerance for rounding
        return '07-) Yüksek Harcama Yapanlar'
    
    # 4. Potansiyel Şampiyonlar (after Yüksek Harcama so f==1 big spenders don't end up here)
    if r >= 4 and f >= 2 and m >= 2:
        return '02-) Potansiyel Şampiyonlar'
    
    # 5. Recent / Reactivated (uzun aradan sonra geri dönenler)
    if r >= 4 and days_since_prev is not None and days_since_prev >= 90:
        return '06-) Tekrar Kazanılanlar'
    
    # 6. Developing
    if r >= 4 and f >= 2:
        return '04-) Sadık Olmaya Adaylar'
    
    # 7. Risk
    if r == 2 and f >= 3:
        return '09-) Risk Altındakiler'
    if r <= 2 and f <= 2:
        return '10-) Uyuyanlar'
    
    # 8. Default
    return '08-) İlgi Bekleyenler'

def run_rfm_update(conn=None):
    """Main function to update RFM segments in musteriler table and sync musteridetayozet"""
    is_external_conn = conn is not None
    if not is_external_conn:
        conn = db_engine.get_connection()
    
    try:
        if db_engine.DB_BACKEND == 'postgresql':
            from psycopg2.extras import RealDictCursor, execute_batch
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            if not is_external_conn:
                conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

        # 1. Fetch ALL customers
        cursor.execute("SELECT id, kayit_tarihi FROM musteriler")
        all_customers = {row['id']: {'kayit_tarihi': row['kayit_tarihi']} for row in cursor.fetchall()}

        # 2. Fetch sales data
        cursor.execute("""
            SELECT 
                musteri_id,
                COUNT(DISTINCT fis_no) as frequency,
                SUM(tutar) as monetary,
                MAX(tarih) as last_date,
                MIN(tarih) as first_date
            FROM satislar
            WHERE musteri_id IS NOT NULL
            GROUP BY musteri_id
        """)
        rows = cursor.fetchall()

        # 2b. Fetch days_since_prev from pre-computed musteridetayozet (avoids expensive CTE self-join on satislar)
        logger.info("Loading days_since_prev from musteridetayozet...")
        days_since_prev_map = {}
        if db_engine.DB_BACKEND == 'postgresql':
            cursor.execute("""
                SELECT musteri_id, ortalama_alisveris_araligi
                FROM musteridetayozet
                WHERE ortalama_alisveris_araligi IS NOT NULL
            """)
            for gap_row in cursor.fetchall():
                cust_id = gap_row['musteri_id']
                gap = gap_row['ortalama_alisveris_araligi']
                if gap is not None:
                    days_since_prev_map[cust_id] = int(gap) if not isinstance(gap, int) else gap
        else:
            cursor.execute("""
                WITH ranked AS (
                    SELECT musteri_id, tarih,
                           ROW_NUMBER() OVER (PARTITION BY musteri_id ORDER BY tarih DESC) as rn
                    FROM (
                        SELECT DISTINCT musteri_id, tarih FROM satislar WHERE musteri_id IS NOT NULL
                    ) sub
                )
                SELECT a.musteri_id, CAST(julianday(a.tarih) - julianday(b.tarih) AS INTEGER) as gap_days
                FROM ranked a
                JOIN ranked b ON a.musteri_id = b.musteri_id AND a.rn = 1 AND b.rn = 2
            """)
            for gap_row in cursor.fetchall():
                cust_id = gap_row['musteri_id']
                gap = gap_row['gap_days']
                if gap is not None:
                    days_since_prev_map[cust_id] = int(gap) if not isinstance(gap, int) else gap
        logger.info(f"days_since_prev loaded for {len(days_since_prev_map)} customers")
        
        now_dt = datetime.now()
        now_date = now_dt.date()
        distribution = {k: 0 for k in SEGMENT_CONFIG.keys()}
        processed_ids = set()
        
        update_data_sales = []
        update_data_no_sales = []

        # Process sales data
        for row in rows:
            cust_id = row['musteri_id']
            freq = row['frequency']
            monetary = row['monetary']
            last_date_val = row['last_date']
            first_date_val = row['first_date']
            processed_ids.add(cust_id)

            try:
                # Handle both string and date/datetime objects
                if isinstance(last_date_val, str):
                    if ' ' in last_date_val: last_date_val = last_date_val.split(' ')[0]
                    last_date = datetime.strptime(last_date_val, '%Y-%m-%d').date()
                elif hasattr(last_date_val, 'date'):
                    last_date = last_date_val.date()
                else:
                    last_date = last_date_val
                
                if isinstance(first_date_val, str):
                    if ' ' in first_date_val: first_date_val = first_date_val.split(' ')[0]
                    first_date = datetime.strptime(first_date_val, '%Y-%m-%d').date()
                elif hasattr(first_date_val, 'date'):
                    first_date = first_date_val.date()
                else:
                    first_date = first_date_val
            except Exception:
                continue

            recency = (now_date - last_date).days
            first_purchase_days = (now_date - first_date).days
            tenure_months = max(1, first_purchase_days / 30.0)
            
            monthly_freq = freq / tenure_months
            monthly_amount = monetary / tenure_months
            
            r_score = calculate_r_score(recency)
            f_score = calculate_f_score(monthly_freq)
            m_score = calculate_m_score(monthly_amount)
            
            days_since_prev = days_since_prev_map.get(cust_id)
            segment = determine_segment(r_score, f_score, m_score, days_since_prev, first_purchase_days, recency, freq)
            distribution[segment] = distribution.get(segment, 0) + 1
            update_data_sales.append((segment, r_score, f_score, m_score, now_dt.isoformat(), cust_id))

        # Process no-sales data
        for cust_id, info in all_customers.items():
            if cust_id in processed_ids:
                continue
            
            kayit_tarihi_val = info['kayit_tarihi']
            try:
                if isinstance(kayit_tarihi_val, str):
                    kayit_tarihi = datetime.strptime(kayit_tarihi_val.split(' ')[0], '%Y-%m-%d').date()
                elif hasattr(kayit_tarihi_val, 'date'):
                    kayit_tarihi = kayit_tarihi_val.date()
                else:
                    kayit_tarihi = kayit_tarihi_val or now_date
            except:
                kayit_tarihi = now_date
            
            tenure_days = (now_date - kayit_tarihi).days
            # Yeni müşteri: Kayıt son 30 gün içinde ise
            segment = '05-) Yeni Müşteriler' if tenure_days <= 30 else '11-) Kayıp Müşteriler'
            distribution[segment] = distribution.get(segment, 0) + 1
            update_data_no_sales.append((segment, 0, 0, 0, now_dt.isoformat(), cust_id))

        # Execute Updates in chunks with retries
        def execute_chunked_batch(sql, data, chunk_size=10000): # Increased chunk size for UNNEST
            nonlocal conn, cursor 
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                max_retries = 3
                retry_count = 0
                success = False
                
                while not success and retry_count < max_retries:
                    try:
                        if db_engine.DB_BACKEND == 'postgresql':
                            # Fast UNNEST update for PostgreSQL
                            ids = [r[5] for r in chunk]
                            segs = [r[0] for r in chunk]
                            rs = [r[1] for r in chunk]
                            fs = [r[2] for r in chunk]
                            ms = [r[3] for r in chunk]
                            upds = [r[4] for r in chunk]
                            
                            cursor.execute("""
                                UPDATE musteriler AS m
                                SET rfm_segment = t.seg, rfm_r_score = t.r, rfm_f_score = t.f, rfm_m_score = t.m, rfm_updated_at = t.upd
                                FROM (
                                    SELECT 
                                        UNNEST(%s)::INT as id, 
                                        UNNEST(%s)::TEXT as seg, 
                                        UNNEST(%s)::INT as r, 
                                        UNNEST(%s)::INT as f, 
                                        UNNEST(%s)::INT as m, 
                                        UNNEST(%s)::TEXT as upd
                                ) AS t
                                WHERE m.id = t.id
                            """, (ids, segs, rs, fs, ms, upds))
                        else:
                            cursor.executemany(sql, chunk)
                        
                        if not is_external_conn:
                            conn.commit()
                        success = True
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"Retry {retry_count}/{max_retries} for chunk {i//chunk_size} due to error: {e}")
                        try:
                            if not is_external_conn:
                                db_engine.release_connection(conn)
                            conn = db_engine.get_connection()
                            if db_engine.DB_BACKEND == 'postgresql':
                                from psycopg2.extras import RealDictCursor
                                cursor = conn.cursor(cursor_factory=RealDictCursor)
                            else:
                                cursor = conn.cursor()
                        except:
                            pass
                
                if not success:
                    raise Exception(f"Failed to update chunk {i//chunk_size} after {max_retries} retries.")
                
                if (i + chunk_size) % 10000 == 0 or (i + chunk_size) >= len(data):
                    logger.info(f"Progress: {min(i + chunk_size, len(data))} rows updated...")

        if db_engine.DB_BACKEND == 'postgresql':
            update_sql_sales = """
                UPDATE musteriler 
                SET rfm_segment = %s, rfm_r_score = %s, rfm_f_score = %s, rfm_m_score = %s, rfm_updated_at = %s
                WHERE id = %s
            """
            update_sql_no_sales = "UPDATE musteriler SET rfm_segment = %s, rfm_r_score = %s, rfm_f_score = %s, rfm_m_score = %s, rfm_updated_at = %s WHERE id = %s"
            
            logger.info(f"Executing robust chunked update for {len(update_data_sales)} sales customers...")
            execute_chunked_batch(update_sql_sales, update_data_sales)
            
            logger.info(f"Executing robust chunked update for {len(update_data_no_sales)} no-sales customers...")
            execute_chunked_batch(update_sql_no_sales, update_data_no_sales)
        else:
            # SQLite fallback
            execute_chunked_batch("""
                UPDATE musteriler 
                SET rfm_segment = ?, rfm_r_score = ?, rfm_f_score = ?, rfm_m_score = ?, rfm_updated_at = ?
                WHERE id = ?
            """, update_data_sales)
            
            execute_chunked_batch("UPDATE musteriler SET rfm_segment = ?, rfm_r_score = ?, rfm_f_score = ?, rfm_m_score = ?, rfm_updated_at = ? WHERE id = ?", update_data_no_sales)

        if not is_external_conn:
            conn.commit()

        # 3. rfm_segment_log tablosuna bu güncellemenin snapshot'ını kaydet
        try:
            if db_engine.DB_BACKEND == 'postgresql':
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rfm_segment_log (
                        id SERIAL PRIMARY KEY,
                        musteri_id INTEGER NOT NULL,
                        rfm_segment TEXT NOT NULL,
                        kayit_tarihi DATE NOT NULL DEFAULT CURRENT_DATE,
                        UNIQUE(musteri_id, kayit_tarihi)
                    )
                """)
                # Bugünkü kayıtları toplu upsert et
                all_updates = update_data_sales + update_data_no_sales
                ids_segs = [(r[5], r[0]) for r in all_updates]
                if ids_segs:
                    cursor.execute("""
                        INSERT INTO rfm_segment_log (musteri_id, rfm_segment, kayit_tarihi)
                        SELECT UNNEST(%s::INT[]), UNNEST(%s::TEXT[]), CURRENT_DATE
                        ON CONFLICT (musteri_id, kayit_tarihi) DO UPDATE
                            SET rfm_segment = EXCLUDED.rfm_segment
                    """, (
                        [r[0] for r in ids_segs],
                        [r[1] for r in ids_segs],
                    ))
                conn.commit()
                logger.info(f"rfm_segment_log updated for {len(ids_segs)} customers")
        except Exception as e:
            logger.warning(f"rfm_segment_log yazma hatası (kritik değil): {e}")

        # 4. Müşteri detay özetini rfm_segmentation içinden silmiyoruz.
        # sync_summary.py bu işlemi çok daha kapsamlı bir şekilde yapıyor.
        # Burada sadece müşteri tablosunu güncelliyoruz.

        if not is_external_conn:
            conn.commit()

        return {
            'success': True,
            'customers_updated': len(all_customers),
            'segment_distribution': distribution,
            'updated_at': now_dt.isoformat()
        }
    except Exception as e:
        logger.error(f"RFM Update error: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if not is_external_conn:
            db_engine.release_connection(conn)

def get_segment_stats():
    conn = db_engine.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rfm_segment, COUNT(*), AVG(rfm_r_score), AVG(rfm_f_score), AVG(rfm_m_score)
            FROM musteriler
            WHERE rfm_segment IS NOT NULL
            GROUP BY rfm_segment
        """)
        stats = []
        for row in cursor.fetchall():
            stats.append({
                'segment': row[0],
                'count': row[1],
                'avg_r': round(row[2], 1) if row[2] else 0,
                'avg_f': round(row[3], 1) if row[3] else 0,
                'avg_m': round(row[4], 1) if row[4] else 0
            })
        return stats
    finally:
        db_engine.release_connection(conn)

