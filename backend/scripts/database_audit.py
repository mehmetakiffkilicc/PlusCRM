import os
import psycopg2
from psycopg2.extras import RealDictCursor
from decouple import Config, RepositoryEnv

BASE_DIR = 'c:\\Users\\Akif\\Desktop\\BackendFronend'
env_path = os.path.join(BASE_DIR, '.env')
config = Config(RepositoryEnv(env_path))

DATABASE_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def run_audit():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=== DATABASE AUDIT ===")
        
        # 1. Active Connections
        cursor.execute("SELECT count(*), state FROM pg_stat_activity GROUP BY state")
        print("\nConnections by State:")
        for row in cursor.fetchall():
            print(f"  {row['state'] or 'unknown'}: {row['count']}")
            
        # 2. Long Running Queries (> 1 second)
        cursor.execute("""
            SELECT pid, now() - query_start AS duration, query, state
            FROM pg_stat_activity
            WHERE state != 'idle' AND (now() - query_start) > interval '1 second'
            ORDER BY duration DESC
        """)
        print("\nLong Running Queries (>1s):")
        for row in cursor.fetchall():
            print(f"  PID: {row['pid']}, Duration: {row['duration']}, State: {row['state']}")
            print(f"  Query: {row['query'][:200]}...")
            
        # 3. Table Sizes
        cursor.execute("""
            SELECT relname AS table_name, 
                   pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                   pg_size_pretty(pg_relation_size(relid)) AS table_size,
                   pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC
            LIMIT 10
        """)
        print("\nTop 10 Tables by Size:")
        for row in cursor.fetchall():
            print(f"  {row['table_name']}: {row['total_size']} (Table: {row['table_size']}, Index: {row['index_size']})")
            
        # 4. Sequential Scans (Indicating missing indexes)
        cursor.execute("""
            SELECT relname AS table_name, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
            FROM pg_stat_user_tables
            WHERE seq_scan > 0
            ORDER BY seq_tup_read DESC
            LIMIT 5
        """)
        print("\nTop Tables with Sequential Scans:")
        for row in cursor.fetchall():
            print(f"  {row['table_name']}: Seq Scans: {row['seq_scan']}, Tuples Read: {row['seq_tup_read']}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_audit()
