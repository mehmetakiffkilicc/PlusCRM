import sys
import os
import logging

# Set current working directory
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'sync_worker'))

# Configure root logger to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

import models
# Override DB_PATH to point to demo.sqlite3
models.DB_PATH = os.path.abspath('database/demo.sqlite3')
print("Overridden models.DB_PATH to:", models.DB_PATH, flush=True)

# Ensure schema exists in demo.sqlite3
print("Dropping old summary tables to ensure schema freshness...", flush=True)
conn = models.get_connection()
cursor = conn.cursor()
tables_to_drop = [
    "gunlukciroozet", "magazagunlukozet", "gunlukozet", "crmozet",
    "kategorikarsilastirma", "markakarsilastirma", "kampanyaozet",
    "musterisadakat", "daily_metrics_summary", "urunperformansdetay", 
    "kategoriperformansozet", "genelozet", "brandsummary", "product_daily_summary", "cache_kpi",
    "musteridetayozet", "globalstatlar", "gunlukmevsimsellik", "birliktelikstratejiskorlari",
    "grupbirliktelikleri", "urunbirliktelikleri", "musterietiketleri", "etiket_snapshot",
    "syncmeta", "encoksatanlar", "musterionerileri", "otomatikkampanyaonerileri",
    "aylikmusteriozet", "yillikmusteriozet", "kategori_analiz_ozet"
]
for t in tables_to_drop:
    cursor.execute(f"DROP TABLE IF EXISTS {t}")
conn.commit()
conn.close()

print("Creating missing schemas in demo.sqlite3...", flush=True)
models.create_schema()

import sync_summary
# Override DB_PATH in sync_summary as well
sync_summary.DB_PATH = models.DB_PATH

# Run rebuild_all_summaries
print("Rebuilding all summaries for demo.sqlite3...", flush=True)
sync_summary.rebuild_all_summaries()

# Run rebuild_cache_kpi
print("Running rebuild_cache_kpi...", flush=True)
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
import scripts.rebuild_cache_kpi as rebuild_cache_kpi
rebuild_cache_kpi.rebuild_cache()

print("Demo database summary rebuilding complete!", flush=True)
