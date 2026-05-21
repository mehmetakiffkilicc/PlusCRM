"""
RFM Gunluk Otomatik Guncelleme Scripti
Windows Task Scheduler ile her gece 02:00'de calistirilabilir

Kullanim:
    python rfm_daily_update.py

Task Scheduler kurulumu:
    1. Task Scheduler ac
    2. "Create Basic Task" tikla
    3. Isim: "RFM Daily Update"
    4. Tetikleyici: Daily, 02:00
    5. Aksiyon: Start a program
       Program: python.exe (veya python yolu)
       Arguments: "C:\\Users\\Akif\\Desktop\\BackendFronend\\backend\\rfm_daily_update.py"
       Start in: "C:\\Users\\Akif\\Desktop\\BackendFronend\\backend"
"""
import sys
import os
from datetime import datetime
from pathlib import Path
import logging

# Adjust path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Logging ayarlari
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"rfm_update_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Ana guncelleme fonksiyonu"""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("RFM Gunluk Guncelleme Baslatiliyor")
    logger.info(f"Baslangic zamani: {start_time}")
    logger.info("=" * 60)

    try:
        # rfm_segmentation modulunu import et
        from rfm_segmentation import run_rfm_update, get_segment_stats

        # RFM guncellemesini calistir
        logger.info("RFM hesaplamalari basliyor...")
        result = run_rfm_update()

        if result['success']:
            logger.info("RFM guncelleme BASARILI")
            logger.info(f"Guncellenen musteri sayisi: {result['customers_updated']}")
            logger.info(f"Guncelleme zamani: {result['updated_at']}")

            # Segment dagilimini logla
            logger.info("\n=== Segment Dagilimi ===")
            for segment, count in sorted(result['segment_distribution'].items(), key=lambda x: -x[1]):
                if count > 0:
                    logger.info(f"  {segment}: {count} musteri")

            # Detayli istatistikleri al
            stats = get_segment_stats()
            if stats:
                logger.info("\n=== Detayli Segment Istatistikleri ===")
                for stat in stats:
                    logger.info(
                        f"  {stat['segment']}: {stat['count']} musteri | "
                        f"Ort R: {stat['avg_r']} | Ort F: {stat['avg_f']} | Ort M: {stat['avg_m']}"
                    )

        else:
            logger.error(f"RFM guncelleme BASARISIZ: {result.get('error')}")
            sys.exit(1)

        # Analytics cache'leri guncelle (kohort, enflasyon, rakip, hane, marka, terk)
        logger.info("\n=== Analytics Cache Guncelleme ===")
        try:
            from analytics_cache import run_all as build_analytics_cache
            cache_sure = build_analytics_cache()
            logger.info(f"Analytics cache guncelleme BASARILI ({cache_sure:.1f}s)")
        except Exception as cache_err:
            logger.error(f"Analytics cache guncelleme BASARISIZ: {cache_err}")
            # Cache hatasi RFM guncellemesini durdurmaz — sadece log

    except ImportError as e:
        logger.error(f"Modul import hatasi: {e}")
        logger.error("rfm_segmentation.py dosyasinin ayni dizinde oldugundan emin olun.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info("=" * 60)
        logger.info(f"Bitis zamani: {end_time}")
        logger.info(f"Toplam sure: {duration}")
        logger.info("=" * 60)


def create_task_scheduler_xml():
    """Windows Task Scheduler icin XML dosyasi olustur"""
    xml_content = '''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>RFM Musteri Segmentasyonu Gunluk Guncelleme</Description>
    <Author>System</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T02:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>python</Command>
      <Arguments>"C:\\Users\\Akif\\Desktop\\BackendFronend\\backend\\rfm_daily_update.py"</Arguments>
      <WorkingDirectory>C:\\Users\\Akif\\Desktop\\BackendFronend\\backend</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''

    xml_path = Path(__file__).parent / 'RFM_Daily_Update_Task.xml'
    with open(xml_path, 'w', encoding='utf-16') as f:
        f.write(xml_content)

    logger.info(f"Task Scheduler XML dosyasi olusturuldu: {xml_path}")
    logger.info("Gorevi iceri aktarmak icin su komutu calistirin:")
    logger.info(f'  schtasks /create /xml "{xml_path}" /tn "RFM Daily Update"')

    return xml_path


if __name__ == "__main__":
    # Eger --setup argumani verilmisse, Task Scheduler XML olustur
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        create_task_scheduler_xml()
    else:
        main()
