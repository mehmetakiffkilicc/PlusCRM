import sys
import os

# Add current directory to path so we can import api
sys.path.append(os.getcwd())

from api import db_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_indexes():
    conn = None
    try:
        conn = db_engine.get_connection()
        cur = conn.cursor()
        
        if db_engine.DB_BACKEND == "postgresql":
            print("--- OPTIMIZING POSTGRESQL INDEXES ---")
            
            indexes = [
                # satislar table
                ("idx_satislar_date_cat_brand", "CREATE INDEX IF NOT EXISTS idx_satislar_date_cat_brand ON satislar (tarih, kategori_id, marka_id)"),
                ("idx_satislar_musteri_id", "CREATE INDEX IF NOT EXISTS idx_satislar_musteri_id ON satislar (musteri_id)"),
                
                # daily_metrics_summary table (Very important for Dashboard filters)
                ("idx_dms_filter_composite", "CREATE INDEX IF NOT EXISTS idx_dms_filter_composite ON daily_metrics_summary (tarih, kategori_id, marka_id, magaza_id)"),
                ("idx_dms_rfm_segment", "CREATE INDEX IF NOT EXISTS idx_dms_rfm_segment ON daily_metrics_summary (rfm_segment)"),
                ("idx_dms_customer_type", "CREATE INDEX IF NOT EXISTS idx_dms_customer_type ON daily_metrics_summary (customer_type)"),
                
                # musteridetayozet (Churn and Loyalty calculations)
                ("idx_mdo_rfm_segment", "CREATE INDEX IF NOT EXISTS idx_mdo_rfm_segment ON musteridetayozet (rfm_segment)"),
                ("idx_mdo_son_alisveris", "CREATE INDEX IF NOT EXISTS idx_mdo_son_alisveris ON musteridetayozet (son_alisveris_tarihi)"),
                ("idx_mdo_musteri_id", "CREATE INDEX IF NOT EXISTS idx_mdo_musteri_id ON musteridetayozet (musteri_id)"),
                
                # musteriziyaretfeatures (Expected Customers speed)
                ("idx_mzf_musteri_id", "CREATE INDEX IF NOT EXISTS idx_mzf_musteri_id ON musteriziyaretfeatures (musteri_id)"),
                ("idx_mzf_son_ziyaret", "CREATE INDEX IF NOT EXISTS idx_mzf_son_ziyaret ON musteriziyaretfeatures (son_ziyaret_tarihi)"),
                ("idx_mzf_ort_ziyaret", "CREATE INDEX IF NOT EXISTS idx_mzf_ort_ziyaret ON musteriziyaretfeatures (ort_ziyaret_araligi)"),
                
                # product_daily_summary (Product Analysis speed)
                ("idx_pds_composite", "CREATE INDEX IF NOT EXISTS idx_pds_composite ON product_daily_summary (tarih, urun_id, revenue)"),
                
                # musteriler (Fallback filters)
                ("idx_musteriler_tip_onay", "CREATE INDEX IF NOT EXISTS idx_musteriler_tip_onay ON musteriler (tip, onay_durumu)")
            ]
            
            for name, sql in indexes:
                print(f"Applying: {name}...")
                try:
                    cur.execute(sql)
                    conn.commit()
                    print(f"✅ {name} applied.")
                except Exception as e:
                    print(f"❌ Error applying {name}: {e}")
                    conn.rollback()
            
            print("\nRunning ANALYZE to update statistics...")
            cur.execute("ANALYZE satislar")
            cur.execute("ANALYZE daily_metrics_summary")
            cur.execute("ANALYZE musteridetayozet")
            cur.execute("ANALYZE musteriziyaretfeatures")
            cur.execute("ANALYZE product_daily_summary")
            cur.execute("ANALYZE musteriler")
            conn.commit()
            print("✅ ANALYZE completed.")
            
        else:
            print("Backend is not PostgreSQL. Index optimization skipped.")

    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        if conn:
            db_engine.release_connection(conn)

if __name__ == "__main__":
    optimize_indexes()
