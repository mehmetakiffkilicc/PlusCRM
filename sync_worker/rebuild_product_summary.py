import sys
import os
import time
from datetime import datetime
import logging

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from models import get_connection, DB_BACKEND
from manual_full_sync import update_product_daily_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    pg = get_connection()
    cur = pg.cursor()
    
    logger.info("Finding dates from satislar...")
    cur.execute("SELECT DISTINCT tarih FROM satislar ORDER BY tarih")
    dates = [str(r[0]) for r in cur.fetchall()]
    logger.info(f"Found {len(dates)} dates to process.")
    
    # Optional: Clear table
    cur.execute("DELETE FROM product_daily_summary")
    pg.commit()
    
    for i, target_date in enumerate(dates):
        start = time.time()
        # update_product_daily_summary(pg, target_date)
        # Directly implementing it here to be safe and avoid import issues if any
        cur.execute("DELETE FROM product_daily_summary WHERE tarih = %s", (target_date,))
        cur.execute("""
            INSERT INTO product_daily_summary
            (tarih, urun_id, revenue, unit_count, customer_count, receipt_count)
            SELECT 
                tarih, urun_id, 
                SUM(tutar), SUM(miktar), COUNT(DISTINCT musteri_id), COUNT(DISTINCT fis_no)
            FROM satislar
            WHERE tarih = %s AND urun_id IS NOT NULL
            GROUP BY tarih, urun_id
        """, (target_date,))
        
        pg.commit()
        if (i+1) % 10 == 0 or i == len(dates) - 1:
            logger.info(f"[{i+1}/{len(dates)}] Processed up to {target_date} ({time.time()-start:.2f}s)")
        
    logger.info("Product daily summary rebuild complete!")
    pg.close()

if __name__ == "__main__":
    main()
