import sqlite3
import os

db_path = r'C:\Users\Akif\Desktop\BackendFronend\database\sales_cache.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']

stats = {}
for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    stats[table] = cursor.fetchone()[0]

for table, count in stats.items():
    print(f"{table}: {count} rows")

conn.close()
