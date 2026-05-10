"""
satislar tablosundaki satir_no'lari deterministik ORDER BY ile yeniden numaralandirir.
ORDER BY urun_id, COALESCE(kampanya_id, -1)
Bu, SQL Server'daki ORDER BY stkKod, ISNULL(kmp_sayisi,-1) ile birebir eslesmektedir.
(urun_map: stkKod -> urun_id bire-bir mapping)

Islem sirasi:
1. Gecici sutun ekle (satir_no_yeni)
2. Yeni numaralari hesapla (ROW_NUMBER)
3. UNIQUE constraint kaldir
4. satir_no = satir_no_yeni
5. UNIQUE constraint yeniden ekle
6. Gecici sutunu sil
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from api.db_engine import get_connection, release_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    pg_conn = get_connection()
    cur = pg_conn.cursor()
    cur.execute("SET statement_timeout = 0")

    cur.execute("SELECT COUNT(*) FROM satislar")
    total = cur.fetchone()[0]
    logger.info(f"Toplam satir: {total:,}")

    # 1. Gecici sutun ekle
    logger.info("Adim 1: Gecici satir_no_yeni sutunu ekleniyor...")
    cur.execute("ALTER TABLE satislar ADD COLUMN IF NOT EXISTS satir_no_yeni INTEGER")
    pg_conn.commit()

    # 2. Yeni numaralari hesapla — onceki calistirmadan kalmissa atla
    cur.execute("SELECT COUNT(*) FROM satislar WHERE satir_no_yeni IS NOT NULL")
    already_computed = cur.fetchone()[0]
    if already_computed > 0:
        logger.info(f"Adim 2: ATLANDI — satir_no_yeni zaten {already_computed:,} satirda dolu (onceki calistirmadan).")
    else:
        logger.info("Adim 2: Yeni satir_no'lar hesaplaniyor (ROW_NUMBER)...")
        t0 = time.time()
        cur.execute("""
            UPDATE satislar s
            SET satir_no_yeni = t.yeni_no
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY fis_no
                           ORDER BY urun_id, COALESCE(kampanya_id, -1)
                       ) AS yeni_no
                FROM satislar
            ) t
            WHERE s.id = t.id
        """)
        pg_conn.commit()
        logger.info(f"  ROW_NUMBER hesaplandi ({time.time()-t0:.1f}s)")

    # Kisa kontrol: cakisma var mi yeni numaralarda?
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT fis_no, satir_no_yeni
            FROM satislar
            GROUP BY fis_no, satir_no_yeni
            HAVING COUNT(*) > 1
        ) t
    """)
    conflicts = cur.fetchone()[0]
    if conflicts > 0:
        logger.error(f"HATA: {conflicts} adet fis_no+satir_no_yeni cakismasi var! Islemi durduruluyor.")
        cur.execute("ALTER TABLE satislar DROP COLUMN IF EXISTS satir_no_yeni")
        pg_conn.commit()
        release_connection(pg_conn)
        return

    logger.info("Cakisma yok, devam ediliyor.")

    # 3. UNIQUE constraint VE index kaldir
    logger.info("Adim 3: UNIQUE constraint ve index'ler kaldiriliyor...")

    # 3a. UNIQUE constraint'ler
    cur.execute("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name='satislar' AND constraint_type='UNIQUE'
    """)
    constraints = [r[0] for r in cur.fetchall()]
    logger.info(f"  Bulunan UNIQUE constraint'ler: {constraints}")
    for c in constraints:
        cur.execute(f"ALTER TABLE satislar DROP CONSTRAINT IF EXISTS {c}")

    # 3b. UNIQUE index'ler (constraint olmayan)
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename='satislar'
        AND indexdef LIKE '%%UNIQUE%%'
        AND indexname NOT IN (
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name='satislar'
        )
    """)
    indexes = [r[0] for r in cur.fetchall()]
    logger.info(f"  Bulunan UNIQUE index'ler: {indexes}")
    for idx in indexes:
        cur.execute(f"DROP INDEX IF EXISTS {idx}")

    pg_conn.commit()

    # 4. satir_no guncelle
    logger.info("Adim 4: satir_no = satir_no_yeni guncelleniyor...")
    t0 = time.time()
    cur.execute("UPDATE satislar SET satir_no = satir_no_yeni")
    pg_conn.commit()
    logger.info(f"  Guncellendi ({time.time()-t0:.1f}s)")

    # 5. UNIQUE index yeniden ekle (orijinal index adi korunuyor)
    logger.info("Adim 5: UNIQUE INDEX idx_satislar_fis_satir yeniden olusturuluyor...")
    cur.execute("CREATE UNIQUE INDEX idx_satislar_fis_satir ON satislar (fis_no, satir_no)")
    pg_conn.commit()

    # 6. Gecici sutunu sil
    logger.info("Adim 6: Gecici sutun siliniyor...")
    cur.execute("ALTER TABLE satislar DROP COLUMN satir_no_yeni")
    pg_conn.commit()

    logger.info("=== Tamamlandi. satir_no'lar deterministik ORDER BY ile yeniden numaralandirildi. ===")
    release_connection(pg_conn)

if __name__ == "__main__":
    main()
