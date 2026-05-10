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

def run_detailed_audit():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("=== DETAILED INDEX AUDIT ===")
        
        tables = ['satislar', 'markalar', 'kategoriler', 'daily_metrics_summary', 'musteriler']
        
        for table in tables:
            print(f"\nIndexes for {table}:")
            cursor.execute(f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = '{table}'
            """)
            for row in cursor.fetchall():
                print(f"  {row['indexname']}: {row['indexdef']}")
                
        print("\n=== FOREIGN KEY CHECK ===")
        # Check if FK columns are indexed
        cursor.execute("""
            SELECT
                conname AS constraint_name,
                conrelid::regclass AS table_name,
                a.attname AS column_name,
                confrelid::regclass AS foreign_table_name,
                af.attname AS foreign_column_name
            FROM
                pg_constraint AS c
                JOIN pg_attribute AS a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                JOIN pg_attribute AS af ON af.attrelid = c.confrelid AND af.attnum = ANY(c.confkey)
            WHERE
                c.contype = 'f'
        """)
        for row in cursor.fetchall():
            # print(f"  {row['table_name']}({row['column_name']}) -> {row['foreign_table_name']}({row['foreign_column_name']})")
            pass # Too much output potentially
            
        print("\n=== UNINDEXED FOREIGN KEYS ===")
        cursor.execute("""
            SELECT 
                conname AS fk_name,
                conrelid::regclass AS table_name,
                attname AS col_name
            FROM pg_constraint
            JOIN pg_attribute ON attrelid = conrelid AND attnum = ANY(conkey)
            WHERE contype = 'f'
            AND NOT EXISTS (
                SELECT 1
                FROM pg_index
                WHERE indrelid = conrelid
                AND indkey[0] = attnum
            )
        """)
        for row in cursor.fetchall():
            print(f"  Table: {row['table_name']}, Col: {row['col_name']} (FK: {row['fk_name']})")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_detailed_audit()
