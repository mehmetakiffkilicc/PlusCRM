import sqlite3
import psycopg2
from psycopg2 import sql, extras
import json
import io
import csv

# Configuration
SQLITE_DB_PATH = r'C:\Users\Akif\Desktop\BackendFronend\database\sales_cache.db'
DATABASE_URL = "postgresql://postgres:kWwFXwjRzqmNFBqvGtjlJBQZqZeBnbjP@crossover.proxy.rlwy.net:48854/railway"

TYPE_MAP = {
    'INTEGER': 'BIGINT',
    'TEXT': 'TEXT',
    'REAL': 'DOUBLE PRECISION',
    'DATE': 'DATE',
    'DATETIME': 'TIMESTAMP',
    '': 'TEXT'
}

# Gecici/gereksiz tablolar - migrate etme
SKIP_TABLES = {
    'tmp_repair_map', 'tmp_fix', 'final_map', 'satislar_new'
}

def migrate():
    print(f"Connecting to SQLite: {SQLITE_DB_PATH}", flush=True)
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    print(f"Connecting to PostgreSQL...", flush=True)
    try:
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}", flush=True)
        return

    schema_path = r'C:\Users\Akif\Desktop\BackendFronend\database\schema.json'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    # SERIAL kolonlari takip et (sequence reset icin)
    serial_tables = []

    for original_table_name, table_info in schema.items():
        if original_table_name.lower().startswith('sqlite_'):
            continue

        # Lowercase tablo ismi - sync worker ve backend API bunu bekliyor
        table_name = original_table_name.lower()

        if table_name in SKIP_TABLES:
            print(f"\n  Skipping temp table: {original_table_name}", flush=True)
            continue

        print(f"\nProcessing table: {original_table_name} -> {table_name}", flush=True)

        pk_cols = sorted([c for c in table_info['columns'] if c['pk'] > 0], key=lambda x: x['pk'])

        cols_sql = []
        col_names = []
        has_serial = False
        serial_col_name = None
        for col in table_info['columns']:
            name = col['name'].lower()  # PostgreSQL'de lowercase kolon isimleri kullan
            col_names.append(name)

            sqlite_type = col['type'].upper()
            pg_type = TYPE_MAP.get(sqlite_type, 'TEXT')

            # Handle mixed-type columns: force to DOUBLE PRECISION if not PK
            if (sqlite_type == 'INTEGER' or sqlite_type == 'REAL') and col['pk'] == 0:
                pg_type = 'DOUBLE PRECISION'

            # Special Overrides - lowercase table name check
            if table_name == 'globalstatlar' and name == 'value':
                pg_type = 'TEXT'

            # Handle SERIAL for autoincrement
            if col['pk'] == 1 and sqlite_type == 'INTEGER' and 'AUTOINCREMENT' in table_info['sql'].upper():
                pg_type = 'SERIAL'
                has_serial = True
                serial_col_name = name
            elif col['pk'] > 0 and sqlite_type == 'INTEGER':
                pg_type = 'BIGINT'

            cols_sql.append(f'"{name}" {pg_type}')

        pk_sql = ""
        if len(pk_cols) > 0:
            pk_names = ", ".join([f'"{c["name"].lower()}"' for c in pk_cols])
            pk_sql = f", PRIMARY KEY ({pk_names})"

        # PostgreSQL'de lowercase tablo ismi kullan
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(cols_sql)} {pk_sql})'

        print(f"  Dropping and creating table...", flush=True)
        pg_cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
        pg_cursor.execute(create_sql)
        pg_conn.commit()

        if has_serial:
            serial_tables.append((table_name, serial_col_name))

        # SQLite'tan okurken ORIJINAL PascalCase isim kullan
        print(f"  Fetching data from SQLite...", flush=True)
        sqlite_cursor.execute(f'SELECT * FROM "{original_table_name}"')

        batch_size = 100000
        count = 0
        pk_indices = [col_names.index(c['name']) for c in pk_cols]

        while True:
            rows = sqlite_cursor.fetchmany(batch_size)
            if not rows:
                break

            f = io.StringIO()
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            for row in rows:
                row_list = list(row)
                # Data Cleansing: Replace NULLs in PK columns
                for idx in pk_indices:
                    if row_list[idx] is None:
                        col_type = table_info['columns'][idx]['type'].upper()
                        if 'INT' in col_type or 'REAL' in col_type:
                            row_list[idx] = 0
                        else:
                            row_list[idx] = '0'

                writer.writerow([val if val is not None else '' for val in row_list])
            f.seek(0)

            try:
                columns_str = ", ".join([f'"{n}"' for n in col_names])
                # PostgreSQL'de lowercase tablo ismi kullan
                copy_sql = f'COPY "{table_name}" ({columns_str}) FROM STDIN WITH (FORMAT CSV, DELIMITER \'\t\', NULL \'\')'
                pg_cursor.copy_expert(copy_sql, f)
                count += len(rows)
                print(f"  Migrated {count} rows...", flush=True)
            except Exception as e:
                print(f"  CRITICAL ERROR in {table_name}: {e}", flush=True)
                pg_conn.rollback()
                raise e

            pg_conn.commit()

        print(f"  Done! Total rows for {table_name}: {count}", flush=True)

    # SERIAL sequence'lari sifirla
    print("\n\nResetting SERIAL sequences...", flush=True)
    for tbl, col in serial_tables:
        try:
            pg_cursor.execute(f'SELECT setval(pg_get_serial_sequence(\'"{tbl}"\', \'{col}\'), COALESCE((SELECT MAX("{col}") FROM "{tbl}"), 1))')
            pg_conn.commit()
            print(f"  Sequence reset for {tbl}.{col}", flush=True)
        except Exception as e:
            print(f"  WARNING: Could not reset sequence for {tbl}.{col}: {e}", flush=True)
            pg_conn.rollback()

    print("\nMigration completed successfully.", flush=True)
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate()
