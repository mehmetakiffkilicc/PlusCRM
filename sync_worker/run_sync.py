"""
Ana Sync Orchestrator
Lookup ve Sales sync'lerini sırayla çalıştırır
Birden fazla sync aynı anda başlamaz
"""

import logging
import sys
import os
from datetime import datetime
from db_logger import setup_db_logging

# Logging ayarları
LOG_FILE = os.path.join(os.path.dirname(__file__), 'sync_orchestrator.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = setup_db_logging(service_name='worker')


def run_full_sync():
    """
    Tam senkronizasyon:
    1. Önce Lookup verileri (Marka, Ürün, Kategori, Mağaza, Kampanya, Müşteri)
    2. Sonra Satış verileri (aylık + tutarlılık kontrolü)
    """
    from sync_lock import is_sync_running, get_lock_info
    from sync_lookup import run_lookup_sync
    from sync_sales import run_sales_sync

    logger.info("=" * 70)
    logger.info("🚀 TAM SENKRONİZASYON BAŞLADI")
    logger.info("=" * 70)

    start_time = datetime.now()

    # Önceden çalışan sync var mı?
    if is_sync_running():
        info = get_lock_info()
        logger.error(f"❌ Başka bir sync zaten çalışıyor: {info}")
        return False

    # 1. Lookup Sync
    logger.info("")
    logger.info("📦 ADIM 1/2: LOOKUP SYNC")
    logger.info("-" * 50)

    lookup_success = run_lookup_sync()

    if not lookup_success:
        logger.error("❌ Lookup sync başarısız! Sales sync atlanıyor.")
        return False

    logger.info("✅ Lookup sync tamamlandı")

    # 2. Sales Sync
    logger.info("")
    logger.info("🛒 ADIM 2/2: SALES SYNC")
    logger.info("-" * 50)

    sales_success = run_sales_sync(full_sync=False)

    elapsed = datetime.now() - start_time

    logger.info("")
    logger.info("=" * 70)
    if lookup_success and sales_success:
        logger.info(f"✅ TAM SENKRONİZASYON BAŞARILI - Süre: {elapsed}")
    else:
        logger.warning(f"⚠️ SENKRONİZASYON TAMAMLANDI (bazı hatalar var) - Süre: {elapsed}")
    logger.info("=" * 70)

    return lookup_success and sales_success


def run_lookup_only():
    """Sadece lookup verilerini senkronize et"""
    from sync_lookup import run_lookup_sync
    return run_lookup_sync()


def run_sales_only(full: bool = False):
    """Sadece satış verilerini senkronize et"""
    from sync_sales import run_sales_sync
    return run_sales_sync(full_sync=full)


def show_status():
    """Mevcut sync durumunu göster"""
    from sync_lock import is_sync_running, get_lock_info
    from models import get_connection

    print("\n" + "=" * 50)
    print("📊 SYNC DURUMU")
    print("=" * 50)

    # Kilit durumu
    if is_sync_running():
        info = get_lock_info()
        print(f"\n🔒 Aktif Sync: {info}")
    else:
        print("\n🔓 Şu an çalışan sync yok")

    # Meta bilgileri
    try:
        conn = get_connection()
        cursor = conn.cursor()

        print("\n📅 Son Sync Tarihleri:")
        cursor.execute("SELECT key, value, updated_at FROM syncmeta ORDER BY key")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]}")

        # Tablo sayıları
        print("\n📈 Tablo İstatistikleri:")

        tables = [
            ('markalar', 'Marka'),
            ('kategoriler', 'Kategori'),
            ('magazalar', 'Mağaza'),
            ('urunler', 'Ürün'),
            ('kampanyalar', 'Kampanya'),
            ('musteriler', 'Müşteri'),
            ('satislar', 'Satış')
        ]

        for table, name in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {name}: {count:,}")

        conn.close()

    except Exception as e:
        print(f"\n❌ Veritabanı okunamadı: {e}")

    print("\n" + "=" * 50)


def show_help():
    """Yardım mesajı"""
    print("""
Sync Orchestrator - Kullanım:

  python run_sync.py              Tam sync (Lookup + Sales)
  python run_sync.py --lookup     Sadece lookup verileri
  python run_sync.py --sales      Sadece satış verileri (artımlı)
  python run_sync.py --sales-full Tüm satış geçmişi (full)
  python run_sync.py --status     Sync durumunu göster
  python run_sync.py --help       Bu yardım mesajı

Sync Sırası:
  1. Lookup (Marka, Ürün, Kategori, Mağaza, Kampanya, Müşteri)
  2. Sales (Aylık + Tutarlılık kontrolü)

Not:
  - Birden fazla sync aynı anda çalışamaz (kilit mekanizması)
  - Her ay çekildikten sonra SQLite-SQLServer tutarlılığı kontrol edilir
  - Tutarsız ay tespit edilirse tekrar çekilir
""")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg == '--lookup':
            run_lookup_only()
        elif arg == '--sales':
            run_sales_only(full=False)
        elif arg == '--sales-full':
            run_sales_only(full=True)
        elif arg == '--status':
            show_status()
        elif arg in ['--help', '-h']:
            show_help()
        else:
            print(f"Bilinmeyen argüman: {arg}")
            show_help()
    else:
        run_full_sync()
