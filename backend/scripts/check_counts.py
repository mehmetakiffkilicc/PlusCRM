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

def check_counts():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        tables = ['satislar', 'urunler', 'musteriler', 'markalar', 'kategoriler', 'daily_metrics_summary']
        print("=== TABLE ROW COUNTS ===")
        for table in tables:
            cursor.execute(f"SELECT count(*) FROM {table}")
            count = cursor.fetchone()['count']
            print(f"  {table}: {count}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_counts()
