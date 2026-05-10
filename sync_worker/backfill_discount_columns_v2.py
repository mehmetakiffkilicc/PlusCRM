"""
Backfill v2: satislar tablosundaki belge_toplami, belge_indirim_toplami, sepet_urun_sayisi
sutunlarini SQL Server M_Crm tablosundan doldurur.

v1 sorunu: ROW_NUMBER ORDER BY [stkKod] (string) vs PostgreSQL ORDER BY urun_id (numeric)
farkli siralama uretiyordu → yanlis satir eslesmeleri.

v2 cozumu: SQL Server'dan stkKod + kmp_sayisi cekilip, PostgreSQL'de
urunler.kod + kampanya_id ile dogrudan eslestirme yapilir.
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
            [stkKod],
            [kmp_sayısı],
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

    # Batch UPDATE: stkKod -> urunler.kod -> urun_id, kmp_sayisi -> kampanya_id
    pg_cursor = pg_conn.cursor()
    chunk_size = 5000
    updated = 0

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]

        fis_nos = [str(r[0]) for r in chunk]
        stk_kodlar = [str(r[1]) if r[1] is not None else None for r in chunk]
        kmp_sayilari = [int(r[2]) if r[2] is not None else None for r in chunk]
        belge_toplamlari = [r[3] for r in chunk]
        belge_indirimleri = [r[4] for r in chunk]
        sepet_urunleri = [r[5] for r in chunk]

        pg_cursor.execute("""
            UPDATE satislar AS s
            SET belge_toplami = t.bt,
                belge_indirim_toplami = t.bi,
                sepet_urun_sayisi = t.su::SMALLINT
            FROM (
                SELECT
                    UNNEST(%s::TEXT[]) as fis_no,
                    UNNEST(%s::TEXT[]) as stk_kod,
                    UNNEST(%s::INT[]) as kmp_sayisi,
                    UNNEST(%s::FLOAT[]) as bt,
                    UNNEST(%s::FLOAT[]) as bi,
                    UNNEST(%s::SMALLINT[]) as su
            ) AS t
            JOIN urunler u ON u.kod = t.stk_kod
            WHERE s.fis_no = t.fis_no
              AND s.urun_id = u.id
              AND (s.kampanya_id = t.kmp_sayisi OR (s.kampanya_id IS NULL AND t.kmp_sayisi IS NULL))
        """, (fis_nos, stk_kodlar, kmp_sayilari, belge_toplamlari, belge_indirimleri, sepet_urunleri))

        updated += pg_cursor.rowcount

    pg_conn.commit()
    elapsed = time.time() - t0
    logger.info(f"  {month_label}: {len(rows):,} satir cekildi, {updated:,} guncellendi ({elapsed:.1f}s)")
    return updated


def main():
    logger.info("=== Backfill v2 Basladi: stkKod+kmp_sayisi eslestirme ===")

    sql_conn = connect_sql()
    pg_conn = get_connection()

    # Once mevcut yanlis verileri temizle
    logger.info("Adim 0: Mevcut belge verilerini temizleniyor (v1 yanlis eslesmeler)...")
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SET statement_timeout = 0")
    pg_cursor.execute("""
        UPDATE satislar
        SET belge_toplami = NULL, belge_indirim_toplami = NULL, sepet_urun_sayisi = NULL
        WHERE belge_toplami IS NOT NULL
    """)
    pg_conn.commit()
    logger.info(f"  {pg_cursor.rowcount:,} satir temizlendi")

    total_updated = 0
    t_start = time.time()

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
    logger.info(f"=== Backfill v2 Tamamlandi: {total_updated:,} satir guncellendi ({elapsed:.1f}s) ===")

    # Dogrulama
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT COUNT(*) FROM satislar WHERE belge_toplami IS NOT NULL")
    filled = pg_cursor.fetchone()[0]
    pg_cursor.execute("SELECT COUNT(*) FROM satislar")
    total = pg_cursor.fetchone()[0]
    logger.info(f"Dogrulama: {filled:,}/{total:,} satirda belge_toplami dolu ({filled*100//total}%)")

    # Eslesmeme sayisi (NULL kalan)
    null_count = total - filled
    if null_count > 0:
        logger.info(f"  {null_count:,} satir eslesemedi (NULL kaldi)")

    # tutar = (belge_toplami - belge_indirim_toplami) * miktar kontrolu
    pg_cursor.execute("""
        SELECT COUNT(*) FROM satislar
        WHERE belge_toplami IS NOT NULL
        AND ABS(tutar - (belge_toplami - COALESCE(belge_indirim_toplami, 0)) * miktar) > 0.05
    """)
    mismatch1 = pg_cursor.fetchone()[0]
    logger.info(f"Kontrol 1: tutar = (belge-indirim)*miktar → {mismatch1:,} uyumsuz")

    # tutar = belge_toplami - belge_indirim_toplami kontrolu (birim fiyat senaryosu)
    pg_cursor.execute("""
        SELECT COUNT(*) FROM satislar
        WHERE belge_toplami IS NOT NULL
        AND ABS(tutar - (belge_toplami - COALESCE(belge_indirim_toplami, 0))) > 0.05
    """)
    mismatch2 = pg_cursor.fetchone()[0]
    logger.info(f"Kontrol 2: tutar = belge-indirim → {mismatch2:,} uyumsuz")

    release_connection(pg_conn)
    sql_conn.close()


if __name__ == "__main__":
    main()
