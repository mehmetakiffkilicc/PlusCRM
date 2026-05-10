import os
import psycopg2
from decouple import Config, RepositoryEnv

BASE_DIR = 'c:\\Users\\Akif\\Desktop\\BackendFronend'
env_path = os.path.join(BASE_DIR, '.env')
config = Config(RepositoryEnv(env_path))

DATABASE_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def cleanup_indexes():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("--- CLEANING UP REDUNDANT INDEXES ---")
        
        # List of redundant indexes to drop
        to_drop = [
            "idx_satislar_kategori_id", # Duplicate of idx_satislar_kategori
            "idx_satislar_marka_id",    # Duplicate of idx_satislar_marka
            "idx_satislar_musteri_id"   # Duplicate of idx_satislar_musteri
        ]
        
        for idx in to_drop:
            print(f"Dropping {idx}...")
            try:
                cur.execute(f"DROP INDEX IF EXISTS {idx}")
                conn.commit()
                print(f"DONE: {idx}")
            except Exception as e:
                print(f"FAIL: {idx} - {e}")
                conn.rollback()

        # Check for unused indexes
        print("\nChecking for unused indexes...")
        cur.execute("""
            SELECT 
                relname AS table_name,
                indexrelname AS index_name,
                idx_scan,
                pg_size_pretty(pg_relation_size(indexrelid)) AS size
            FROM pg_stat_user_indexes
            JOIN pg_index USING (indexrelid)
            WHERE idx_scan = 0 
            AND indisunique = false
            AND pg_relation_size(indexrelid) > 1024*1024 -- > 1MB
            ORDER BY pg_relation_size(indexrelid) DESC
        """)
        for row in cur.fetchall():
            print(f"  Unused Index: {row['table_name']}.{row['index_name']} (Size: {row['size']})")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup_indexes()
