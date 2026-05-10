"""
Bağımsız Scheduler Servisi
Backend'den bağımsız çalışır, yeni sync scriptlerini kullanır

Zamanlamalar:
- Gece Özet Güncelleme: Her gece 02:00 (Lookup + Sales + Özet rebuild)
- Bakım: Her gece 03:00
"""

import logging
import os
import time
import signal
import sys
from datetime import datetime
from db_logger import setup_db_logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Logging
LOG_FILE = os.path.join(os.path.dirname(__file__), 'scheduler_service.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
setup_db_logging(service_name='worker-scheduler')

# Scheduler instance
scheduler = None


# ================== JOB FONKSİYONLARI ==================





def lookup_sync_job():
    """
    Lookup Sync - Marka, Ürün, Kategori vb.
    Günde 2 kez çalışır (06:00 ve 18:00)
    """
    logger.info("📦 Lookup Sync başladı...")

    try:
        from sync_lookup import run_lookup_sync
        success = run_lookup_sync()

        if success:
            logger.info("✅ Lookup Sync tamamlandı")
        else:
            logger.warning("⚠️ Lookup Sync başarısız")

    except Exception as e:
        logger.error(f"❌ Lookup Sync hatası: {e}", exc_info=True)


def full_sales_sync_job():
    """
    Full Sales Sync - Tüm ayları kontrol et
    Haftada bir çalışır (Pazar 04:00)
    """
    logger.info("🛒 Full Sales Sync başladı...")

    try:
        from sync_sales import run_sales_sync
        success = run_sales_sync(full_sync=False)  # Artımlı, son sync'ten devam

        if success:
            logger.info("✅ Full Sales Sync tamamlandı")
            # Özetleri Tümden Yenile
            from sync_summary import rebuild_all_summaries
            rebuild_all_summaries()
        else:
            logger.warning("⚠️ Full Sales Sync bazı hatalarla tamamlandı")

    except Exception as e:
        logger.error(f"❌ Full Sales Sync hatası: {e}", exc_info=True)


def maintenance_job():
    """
    Gece Bakımı - Veritabanı optimizasyonu
    Her gece 03:00
    """
    logger.info("🧹 Gece bakımı başladı...")

    try:
        from models import run_maintenance, get_connection

        run_maintenance()

        # Meta güncelle
        conn = get_connection()
        cursor = conn.cursor()
        from models import DB_BACKEND
        ph = "%s" if DB_BACKEND == "postgresql" else "?"
        now_func = "CURRENT_TIMESTAMP" if DB_BACKEND == "postgresql" else "datetime('now')"
        
        if DB_BACKEND == "postgresql":
            cursor.execute(f"""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_maintenance', {ph}, {now_func})
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at={now_func}
            """, (datetime.now().isoformat(),))
        else:
            cursor.execute(f"""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_maintenance', ?, datetime('now'))
            """, (datetime.now().isoformat(),))
        conn.commit()
        conn.close()

        logger.info("✅ Gece bakımı tamamlandı")

    except Exception as e:
        logger.error(f"❌ Bakım hatası: {e}", exc_info=True)


# ================== SCHEDULER YÖNETİMİ ==================

def create_scheduler():
    """Scheduler oluştur ve jobları ekle"""
    global scheduler

    scheduler = BlockingScheduler(
        timezone=pytz.timezone('Europe/Istanbul'),
        job_defaults={
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300
        }
    )

    # Full Sales Sync - Haftada bir (Pazar 04:00)
    scheduler.add_job(
        full_sales_sync_job,
        trigger=CronTrigger(day_of_week='sun', hour=4, minute=0),
        id='full_sales_sync',
        name='Full Sales Sync (Pazar 04:00)'
    )

    # Gece Bakımı - Her gece 03:00
    scheduler.add_job(
        maintenance_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='maintenance',
        name='Gece Bakımı (03:00)'
    )

    # Gece Özet Güncelleme - Her gece 02:00 (YENİ)
    # Tüm özet tablolarını (CRM, Marka, RFM, AI vb.) günceller
    scheduler.add_job(
        nightly_summary_job,
        trigger=CronTrigger(hour=2, minute=0),
        id='nightly_summary',
        name='Gece Özet Güncelleme (02:00)'
    )

    # Haftalık Kampanya Önerileri Yenileme - Pazartesi 05:00
    # Güncel satış verilerine göre kampanya önerilerini haftalık olarak yeniden hesaplar
    scheduler.add_job(
        weekly_campaign_refresh_job,
        trigger=CronTrigger(day_of_week='mon', hour=5, minute=0),
        id='weekly_campaign_refresh',
        name='Haftalık Kampanya Yenileme (Pazartesi 05:00)'
    )

    return scheduler


def nightly_summary_job():
    """
    Gece Özet Güncelleme - 5 fazda tüm özet tablolarını yeniler
    Her gece 02:00
    """
    from sync_lock import is_sync_running, acquire_lock, release_lock, SyncType
    
    logger.info("=" * 60)
    logger.info("🌙 [GECE ÖZET] Başlatılıyor...")
    logger.info("=" * 60)
    
    # Kilit kontrolü
    if is_sync_running():
        logger.warning("⚠️ Başka sync çalışıyor, Gece Özet Güncelleme atlanıyor.")
        return
    
    if not acquire_lock(SyncType.SALES):
        logger.warning("⚠️ Kilit alınamadı, Gece Özet Güncelleme atlanıyor.")
        return
    
    start_time = datetime.now()
    
    try:
        # FAZ 1: Lookup sync (marka, kategori, ürün, müşteri, kampanya)
        logger.info("🔄 [GECE ÖZET] Lookup sync başlatılıyor...")
        try:
            from sync_lookup import run_lookup_sync
            run_lookup_sync()
        except Exception as e:
            logger.error(f"❌ [GECE ÖZET] Lookup sync hatası: {e}")

        # FAZ 2: Delta sales sync (son 7 gün verisini SQL Server'dan çek)
        logger.info("🔄 [GECE ÖZET] Delta sales sync başlatılıyor...")
        try:
            from sync_sales import run_recent_sync
            run_recent_sync(days_back=7)
        except Exception as e:
            logger.error(f"❌ [GECE ÖZET] Delta sales sync hatası: {e}")

        # FAZ 3: Özet rebuild (tüm PostgreSQL tabloları + PDS)
        from sync_summary import nightly_phased_rebuild
        success_count = nightly_phased_rebuild()
        
        # FAZ 4: Portal cache temizle (canlı sorguya düşsün, PDS override çalışsın)
        logger.info("🔄 [GECE ÖZET] Portal cache temizleniyor...")
        try:
            from models import get_connection
            c_conn = get_connection()
            c_cur = c_conn.cursor()
            c_cur.execute("DELETE FROM urun_portal_ozet")
            c_conn.commit()
            c_conn.close()
            logger.info("   ✅ Portal cache temizlendi")
        except Exception as e:
            logger.warning(f"   ⚠️ Cache temizleme hatası: {e}")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ [GECE ÖZET] TAMAMLANDI: {success_count}/6 faz başarılı ({elapsed:.1f}s)")
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ [GECE ÖZET] HATA ({elapsed:.1f}s): {e}", exc_info=True)
    
    finally:
        release_lock()
        logger.info("🔓 Kilit serbest bırakıldı.")


def weekly_campaign_refresh_job():
    """
    Haftalık Kampanya Önerileri Yenileme
    Her Pazartesi 05:00 - Güncel satış verilerine göre kampanya önerilerini yeniden hesaplar.
    Nightly rebuild'den bağımsız çalışır, böylece rebuild başarısız olsa bile
    kampanyalar en az haftalık olarak güncellenir.
    """
    from sync_lock import is_sync_running, acquire_lock, release_lock, SyncType

    logger.info("=" * 60)
    logger.info("📣 [HAFTALIK KAMPANYA] Kampanya önerileri yenileniyor...")
    logger.info("=" * 60)

    # Kilit kontrolü
    if is_sync_running():
        logger.warning("⚠️ Başka sync çalışıyor, Haftalık Kampanya Yenileme atlanıyor.")
        return

    if not acquire_lock(SyncType.SALES):
        logger.warning("⚠️ Kilit alınamadı, Haftalık Kampanya Yenileme atlanıyor.")
        return

    start_time = datetime.now()

    try:
        import sys as _sys
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend_dir = os.path.join(BASE_DIR, "backend")
        if backend_dir not in _sys.path:
            _sys.path.insert(0, backend_dir)
        if BASE_DIR not in _sys.path:
            _sys.path.insert(0, BASE_DIR)

        from database.campaign_manager import kampanya_onerileri_uret
        kampanya_onerileri_uret()

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ [HAFTALIK KAMPANYA] TAMAMLANDI ({elapsed:.1f}s)")

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ [HAFTALIK KAMPANYA] HATA ({elapsed:.1f}s): {e}", exc_info=True)

    finally:
        release_lock()
        logger.info("🔓 Kilit serbest bırakıldı.")


def show_jobs():
    """Zamanlanmış jobları göster"""
    print("\n" + "=" * 60)
    print("ZAMANLANMIS GOREVLER")
    print("=" * 60)

    for job in scheduler.get_jobs():
        try:
            next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(job, 'next_run_time') and job.next_run_time else 'Bekleniyor'
        except:
            next_run = 'Bekleniyor'
        print(f"  - {job.name if hasattr(job, 'name') else job.id}")
        print(f"    Sonraki calisma: {next_run}")
        print()


def signal_handler(signum, frame):
    """Graceful shutdown"""
    logger.info("⏹️ Scheduler durduruluyor...")
    if scheduler:
        scheduler.shutdown(wait=False)
    sys.exit(0)


def main():
    """Ana fonksiyon"""
    global scheduler

    # Signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 60)
    logger.info("🚀 SCHEDULER SERVİSİ BAŞLATILIYOR")
    logger.info("=" * 60)

    # Scheduler oluştur
    scheduler = create_scheduler()

    # Jobları göster
    show_jobs()

    logger.info("=" * 60)
    logger.info("✅ Scheduler başlatıldı. Durdurmak için Ctrl+C")
    logger.info("=" * 60)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏹️ Scheduler durduruldu")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == '--status':
            print("Scheduler durumu kontrol ediliyor...")
            # Basit durum kontrolü
            from sync_lock import is_sync_running, get_lock_info
            print(f"Sync çalışıyor mu: {is_sync_running()}")
            print(f"Lock bilgisi: {get_lock_info()}")
        elif sys.argv[1] == '--test':
            # Test modu - gece sync'ini bir kere çalıştır
            print("Test modu - Gece Sync çalıştırılıyor...")
            nightly_summary_job()
        else:
            print(f"Bilinmeyen argüman: {sys.argv[1]}")
            print("Kullanım: python scheduler_service.py [--status|--test]")
    else:
        main()
