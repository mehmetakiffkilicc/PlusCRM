"""
satislar tablosuna belge_toplami, belge_indirim_toplami, sepet_urun_sayisi sutunlarini ekler.
Idempotent — zaten varsa atlar.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from api.db_engine import get_connection, release_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    pg_conn = get_connection()
    cur = pg_conn.cursor()

    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'satislar'
        ORDER BY ordinal_position
    """)
    existing = [r[0] for r in cur.fetchall()]
    logger.info(f"Mevcut sutunlar: {existing}")

    cur.execute("SELECT COUNT(*) FROM satislar")
    total = cur.fetchone()[0]
    logger.info(f"Toplam satir: {total:,}")

    cur.execute("SET statement_timeout = 0")
    cur.execute("ALTER TABLE satislar ADD COLUMN IF NOT EXISTS belge_toplami DOUBLE PRECISION")
    cur.execute("ALTER TABLE satislar ADD COLUMN IF NOT EXISTS belge_indirim_toplami DOUBLE PRECISION")
    cur.execute("ALTER TABLE satislar ADD COLUMN IF NOT EXISTS sepet_urun_sayisi SMALLINT")
    pg_conn.commit()

    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'satislar'
        AND column_name IN ('belge_toplami', 'belge_indirim_toplami', 'sepet_urun_sayisi')
    """)
    added = [r[0] for r in cur.fetchall()]
    logger.info(f"Eklenen sutunlar: {added}")
    logger.info("Tamamlandi.")
    release_connection(pg_conn)

if __name__ == "__main__":
    main()
