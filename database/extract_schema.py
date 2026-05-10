import sqlite3
import json

import os

db_path = r'C:\Users\Akif\Desktop\BackendFronend\database\sales_cache.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

schema = {}
for name, sql in tables:
    cursor.execute(f"PRAGMA table_info({name})")
    columns = cursor.fetchall()
    schema[name] = {
        'sql': sql,
        'columns': [
            {
                'id': col[0],
                'name': col[1],
                'type': col[2],
                'notnull': col[3],
                'dflt_value': col[4],
                'pk': col[5]
            }
            for col in columns
        ]
    }

with open(r'C:\Users\Akif\Desktop\BackendFronend\database\schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=2)

print("Schema saved to database/schema.json")
conn.close()
