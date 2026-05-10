"""Manuel sync tetikleme scripti - railway run ile çalıştırılır"""
from sync_sales import run_recent_sync
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

result = run_recent_sync(days_back=7)
print(f"Sync sonucu: {'Başarılı' if result else 'Başarısız'}")
