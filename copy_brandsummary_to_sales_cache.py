#!/usr/bin/env python
"""Copy brandsummary from backend/db.sqlite3 to database/sales_cache.db"""
import sqlite3
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

src_db = os.path.join(script_dir, 'backend', 'db.sqlite3')
tgt_db = os.path.join(script_dir, 'database', 'sales_cache.db')

print(f"Source: {src_db}")
print(f"Target: {tgt_db}")

if not os.path.exists(src_db):
    print("ERROR: Source DB not found")
    exit(1)
if not os.path.exists(tgt_db):
    print("ERROR: Target DB not found")
    exit(1)

# Connect to source
src_conn = sqlite3.connect(src_db)
src_conn.row_factory = sqlite3.Row
src_cursor = src_conn.cursor()

# Check if brandsummary exists in source
src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='brandsummary'")
if not src_cursor.fetchone():
    print("ERROR: brandsummary table not found in source")
    src_conn.close()
    exit(1)

# Get count
src_cursor.execute("SELECT COUNT(*) FROM brandsummary")
src_count = src_cursor.fetchone()[0]
print(f"brandsummary rows in source: {src_count:,}")

# Connect to target
tgt_conn = sqlite3.connect(tgt_db)
tgt_cursor = tgt_conn.cursor()

# Drop and recreate brandsummary in target
tgt_cursor.execute("DROP TABLE IF EXISTS brandsummary")
print("[OK] Dropped existing brandsummary in target")

# Create table structure (copy from source)
src_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='brandsummary'")
create_sql = src_cursor.fetchone()[0]
print(f"Create SQL: {create_sql[:100]}...")
tgt_cursor.execute(create_sql)

# Copy data in batches
print("Copying data...")
src_cursor.execute("SELECT * FROM brandsummary")
batch_size = 5000
total = 0

while True:
    rows = src_cursor.fetchmany(batch_size)
    if not rows:
        break
    
    # Insert
    placeholders = ','.join(['?'] * len(rows[0]))
    insert_sql = f"INSERT INTO brandsummary VALUES ({placeholders})"
    tgt_cursor.executemany(insert_sql, rows)
    total += len(rows)
    print(f"  Copied {total:,} rows...")

tgt_conn.commit()

# Create indexes
print("Creating indexes...")
tgt_cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_main ON brandsummary(year, month)")
tgt_cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_dims ON brandsummary(region_norm, customer_type_norm, category_norm, brand_name_norm)")
tgt_conn.commit()

# Verify
tgt_cursor.execute("SELECT COUNT(*) FROM brandsummary")
tgt_count = tgt_cursor.fetchone()[0]
print(f"[OK] Target brandsummary rows: {tgt_count:,}")

tgt_cursor.execute("SELECT * FROM brandsummary ORDER BY total_sales DESC LIMIT 3")
print("\nTop 3 brands in target:")
for row in tgt_cursor.fetchall():
    print(f"  {row[1]}: {row[11]:,.2f} TL")

src_conn.close()
tgt_conn.close()
print("\n[OK] Done!")
