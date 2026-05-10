"""
Backfill: satislar tablosundaki belge_toplami, belge_indirim_toplami, sepet_urun_sayisi
sutunlarini SQL Server M_Crm tablosundan doldurur.

Tek seferlik script. Mevcut satirlari fis_no + satir_no eslesme ile gunceller.
"""
import sys
import os
import time
import pyodbc
import logging

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from decouple import config
from api.db_engine import get_connection, release_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SQL_SERVER_CONFIG = {
    'server': config('SQL_SERVER', default='100.109.143.127'),
    'port': config('SQL_PORT', default='14330'),
    'database': config('SQL_DATABASE', default='DerinSISShow'),
    'username': config('SQL_USERNAME', default='sa2'),
    'password': config('SQL_PASSWORD', default='1478236950Mm..'),
}


def connect_sql():
    drivers = ['{ODBC Driver 17 for SQL Server}', '{SQL Server}']
    available = pyodbc.drivers()
    driver = None
    for d in drivers:
        if d.strip('{}') in available:
            driver = d
            break
    if not driver:
        driver = '{SQL Server}'

    conn_str = (
        f"DRIVER={driver};"
        f"SERVER={SQL_SERVER_CONFIG['server']},{SQL_SERVER_CONFIG['port']};"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"UID={SQL_SERVER_CONFIG['username']};"
        f"PWD={SQL_SERVER_CONFIG['password']};"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=30"
    )
    return pyodbc.connect(conn_str)


def backfill_month(sql_conn, pg_conn, year, month):
    """Bir ayin verilerini SQL Server'dan cekip PostgreSQL'deki mevcut satirlari guncelle."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    month_label = f"{year}-{month:02d}"
    t0 = time.time()

    sql_cursor = sql_conn.cursor()
    sql_cursor.execute(f"""
        SELECT
            [PosDocumentId],
            ROW_NUMBER() OVER (PARTITION BY [PosDocumentId] ORDER BY [stkKod], [kmp_sayısı]) as SatirNo,
            [BelgeToplami],
            [BelgeIndirimToplami],
            [SepetUrunSayisi]
        FROM M_Crm WITH (NOLOCK)
        WHERE [TARİH] >= '{start_date}' AND [TARİH] < '{end_date}'
    """)
    rows = sql_cursor.fetchall()

    if not rows:
        logger.info(f"  {month_label}: veri yok, atlandi")
        return 0

    # Batch UPDATE via temp approach: chunk and update
    pg_cursor = pg_conn.cursor()
    chunk_size = 5000
    updated = 0

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]

        fis_nos = [str(r[0]) for r in chunk]
        satir_nos = [float(r[1]) for r in chunk]
        belge_toplamlari = [r[2] for r in chunk]
        belge_indirimleri = [r[3] for r in chunk]
        sepet_urunleri = [r[4] for r in chunk]

        pg_cursor.execute("""
            UPDATE satislar AS s
            SET belge_toplami = t.bt, belge_indirim_toplami = t.bi, sepet_urun_sayisi = t.su::SMALLINT
            FROM (
                SELECT
                    UNNEST(%s::TEXT[]) as fis_no,
                    UNNEST(%s::FLOAT[]) as satir_no,
                    UNNEST(%s::FLOAT[]) as bt,
                    UNNEST(%s::FLOAT[]) as bi,
                    UNNEST(%s::SMALLINT[]) as su
            ) AS t
            WHERE s.fis_no = t.fis_no AND s.satir_no = t.satir_no
        """, (fis_nos, satir_nos, belge_toplamlari, belge_indirimleri, sepet_urunleri))

        updated += pg_cursor.rowcount

    pg_conn.commit()
    elapsed = time.time() - t0
    logger.info(f"  {month_label}: {len(rows):,} satir cekildi, {updated:,} guncellendi ({elapsed:.1f}s)")
    return updated


def main():
    logger.info("=== Backfill Basladi: belge_toplami, belge_indirim_toplami, sepet_urun_sayisi ===")

    sql_conn = connect_sql()
    pg_conn = get_connection()

    total_updated = 0
    t_start = time.time()

    # Son 3 yil (sync_sales.py ile ayni aralik)
    from datetime import datetime
    current_year = datetime.now().year
    current_month = datetime.now().month

    for year in range(current_year - 2, current_year + 1):
        max_month = current_month if year == current_year else 12
        for month in range(1, max_month + 1):
            try:
                updated = backfill_month(sql_conn, pg_conn, year, month)
                total_updated += updated
            except Exception as e:
                logger.error(f"  {year}-{month:02d}: HATA - {e}")
                pg_conn.rollback()

    elapsed = time.time() - t_start
    logger.info(f"=== Backfill Tamamlandi: {total_updated:,} satir guncellendi ({elapsed:.1f}s) ===")

    # Dogrulama
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT COUNT(*) FROM satislar WHERE belge_toplami IS NOT NULL")
    filled = pg_cursor.fetchone()[0]
    pg_cursor.execute("SELECT COUNT(*) FROM satislar")
    total = pg_cursor.fetchone()[0]
    logger.info(f"Dogrulama: {filled:,}/{total:,} satirda belge_toplami dolu ({filled*100//total}%)")

    # tutar = belge_toplami - belge_indirim_toplami kontrolu
    pg_cursor.execute("""
        SELECT COUNT(*) FROM satislar
        WHERE belge_toplami IS NOT NULL
        AND ABS(tutar - (belge_toplami - COALESCE(belge_indirim_toplami, 0))) > 0.01
    """)
    mismatch = pg_cursor.fetchone()[0]
    logger.info(f"Tutarsizlik kontrolu: {mismatch} satir uyumsuz (0 bekleniyor)")

    release_connection(pg_conn)
    sql_conn.close()


if __name__ == "__main__":
    main()
