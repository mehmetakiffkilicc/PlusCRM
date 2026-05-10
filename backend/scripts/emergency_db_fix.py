import os
import psycopg2
from decouple import Config, RepositoryEnv

BASE_DIR = 'c:\\Users\\Akif\\Desktop\\BackendFronend'
env_path = os.path.join(BASE_DIR, '.env')
config = Config(RepositoryEnv(env_path))

DATABASE_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def apply_emergency_fixes():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("--- APPLYING EMERGENCY DB FIXES ---")
        
        # Enable extension
        try:
            print("Enabling pg_trgm extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            conn.commit()
            print("pg_trgm enabled.")
        except Exception as e:
            print(f"Could not enable pg_trgm: {e}")
            conn.rollback()

        fixes = [
            ("idx_markalar_ad", "CREATE INDEX IF NOT EXISTS idx_markalar_ad ON markalar (ad)"),
            ("idx_kategoriler_ana", "CREATE INDEX IF NOT EXISTS idx_kategoriler_ana ON kategoriler (ana)"),
            ("idx_dms_tarih_desc", "CREATE INDEX IF NOT EXISTS idx_dms_tarih_desc ON daily_metrics_summary (tarih DESC)"),
            ("idx_urunler_ad_trgm", "CREATE INDEX IF NOT EXISTS idx_urunler_ad_trgm ON urunler USING gin (ad gin_trgm_ops)")
        ]
        
        for name, sql in fixes:
            print(f"Applying {name}...")
            try:
                cur.execute(sql)
                conn.commit()
                print(f"DONE: {name}")
            except Exception as e:
                print(f"FAIL: {name} - {e}")
                conn.rollback()

        print("Running ANALYZE...")
        tables = ['markalar', 'kategoriler', 'satislar', 'daily_metrics_summary']
        for table in tables:
            try:
                cur.execute(f"ANALYZE {table}")
                conn.commit()
                print(f"ANALYZE {table} DONE")
            except Exception as e:
                print(f"ANALYZE {table} FAIL: {e}")
                conn.rollback()
        
        print("All operations attempted.")
        
    except Exception as e:
        print(f"Setup Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    apply_emergency_fixes()
