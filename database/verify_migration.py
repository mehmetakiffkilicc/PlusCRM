import sqlite3
import psycopg2
import json

DATABASE_URL = "postgresql://postgres:kWwFXwjRzqmNFBqvGtjlJBQZqZeBnbjP@crossover.proxy.rlwy.net:48854/railway"
SQLITE_DB_PATH = r'C:\Users\Akif\Desktop\BackendFronend\database\sales_cache.db'

def verify():
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    print(f"Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cursor = pg_conn.cursor()

    schema_path = r'C:\Users\Akif\Desktop\BackendFronend\database\schema.json'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    report_path = r'C:\Users\Akif\Desktop\BackendFronend\database\migration_report.txt'
    with open(report_path, 'w', encoding='utf-8') as report_file:
        header = f"{'Table Name':<30} | {'SQLite':<10} | {'PostgreSQL':<10} | {'Status':<10}\n"
        report_file.write(header)
        report_file.write("-" * 70 + "\n")
        print(header)

        for table_name in schema.keys():
            if table_name.lower().startswith('sqlite_'):
                continue
                
            # SQLite count
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
            sqlite_count = sqlite_cursor.fetchone()[0]
            
            # PostgreSQL count
            try:
                pg_cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
                pg_count = pg_cursor.fetchone()[0]
            except:
                pg_count = "ERROR"
                pg_conn.rollback()

            status = "OK" if str(sqlite_count) == str(pg_count) else "MISMATCH"
            line = f"{table_name:<30} | {sqlite_count:<10} | {pg_count:<10} | {status:<10}\n"
            report_file.write(line)
            print(line, end='')

    print(f"\nReport written to {report_path}")
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    verify()
