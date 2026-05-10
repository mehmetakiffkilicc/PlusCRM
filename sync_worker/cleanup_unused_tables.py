"""
Kullanilmayan / bos PostgreSQL tablolarini siler.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from api.db_engine import get_connection, release_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SILINECEK_TABLOLAR = [
    ("musterietiketleri",      "Yeni MusteriEtiketler sistemi ile degistirilecek, hicbir yerden okunmuyor"),
    ("musterisadakat",         "Hicbir yerden READ edilmiyor"),
    ("aylikmusteriozet",       "Hicbir yerden kullanilmiyor"),
    ("yillikmusteriozet",      "Hicbir yerden kullanilmiyor"),
    ("gunlukmevsimsellik",     "Hicbir yerden kullanilmiyor"),
    ("urunperformansdetay",    "0 satir, bos tablo"),
    ("kategoriperformansozet", "0 satir, bos tablo"),
    ("kategorietiketleri",     "0 satir, bos tablo"),
]

def main():
    pg_conn = get_connection()
    cur = pg_conn.cursor()
    cur.execute("SET statement_timeout = 0")

    # Oncesinde boyut ve satir sayisi goster
    logger.info("=== SILINECEK TABLOLAR ===")
    for tablo, sebep in SILINECEK_TABLOLAR:
        cur.execute("""
            SELECT
                pg_size_pretty(pg_total_relation_size(%s)) as boyut,
                COALESCE((SELECT n_live_tup FROM pg_stat_user_tables WHERE relname=%s), 0) as satirlar
        """, (tablo, tablo))
        r = cur.fetchone()
        logger.info(f"  {tablo:<30} boyut={r[0]:<10} satirlar={r[1]:>8,}  ({sebep})")

    logger.info("")
    logger.info("Silme islemi basliyor...")

    for tablo, sebep in SILINECEK_TABLOLAR:
        cur.execute(f"DROP TABLE IF EXISTS {tablo} CASCADE")
        logger.info(f"  SILINDI: {tablo}")

    pg_conn.commit()
    logger.info("")
    logger.info("=== KALAN TABLOLAR ===")
    cur.execute("""
        SELECT table_name,
               pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as boyut
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC
    """)
    for r in cur.fetchall():
        logger.info(f"  {r[0]:<45} {r[1]}")

    release_connection(pg_conn)

if __name__ == "__main__":
    main()
