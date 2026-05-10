"""
satislar tablosundan belge_toplami, belge_indirim_toplami, sepet_urun_sayisi sutunlarini kaldirir.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.db_engine import get_connection, release_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    pg_conn = get_connection()
    pg_cursor = pg_conn.cursor()

    # Mevcut sütun durumunu kontrol et
    pg_cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'satislar'
        AND column_name IN ('belge_toplami', 'belge_indirim_toplami', 'sepet_urun_sayisi')
        ORDER BY column_name
    """)
    existing = [r[0] for r in pg_cursor.fetchall()]
    logger.info(f"Mevcut sutunlar: {existing}")

    if not existing:
        logger.info("Kaldirilacak sutun yok, tablo zaten eski halinde.")
        release_connection(pg_conn)
        return

    # DROP sutunlar
    for col in existing:
        logger.info(f"DROP COLUMN: {col}")
        pg_cursor.execute(f"ALTER TABLE satislar DROP COLUMN IF EXISTS {col}")

    pg_conn.commit()
    logger.info("Tamamlandi. Sutunlar kaldirildi.")

    # Dogrulama
    pg_cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'satislar'
        ORDER BY ordinal_position
    """)
    cols = [r[0] for r in pg_cursor.fetchall()]
    logger.info(f"Kalan sutunlar: {cols}")

    release_connection(pg_conn)

if __name__ == "__main__":
    main()
