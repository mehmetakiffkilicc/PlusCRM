"""
Gunluk Etiket Yenileme Scripti
================================
Her gun calistirilir. Sirasyla:
  1. Feature tablolarini yeniden olusturur (feature_core_builder.py)
  2. Musteri etiketlerini gunceller (label_engine.py)

Kullanim:
    python daily_label_refresh.py              # her iki adimi calistir
    python daily_label_refresh.py --labels-only  # sadece etiketleri guncelle (feature tablolar hazirsa)
    python daily_label_refresh.py --features-only  # sadece feature tablolari olustur
"""

import os
import sys
import logging
import subprocess
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURE_SCRIPT = os.path.join(SCRIPT_DIR, 'feature_core_builder.py')
LABEL_SCRIPT = os.path.join(SCRIPT_DIR, 'label_engine.py')


def run_script(script_path, label):
    """Bir Python scriptini subprocess olarak calistirir, ciktiyi gercek zamanli loglar."""
    logger.info(f"{'='*60}")
    logger.info(f"ADIM: {label}")
    logger.info(f"{'='*60}")
    t_start = datetime.now()

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=SCRIPT_DIR,
        capture_output=False,  # stdout/stderr dogrudan terminale akar
        text=True,
    )

    elapsed = (datetime.now() - t_start).total_seconds()

    if result.returncode != 0:
        logger.error(f"{label} BASARISIZ (exit code {result.returncode}) - {elapsed:.1f}s")
        return False

    logger.info(f"{label} TAMAMLANDI ({elapsed:.1f}s)")
    return True


def main():
    parser = argparse.ArgumentParser(description='Gunluk etiket yenileme')
    parser.add_argument('--labels-only', action='store_true',
                        help='Sadece label_engine calistir (feature tablolar hazir olmali)')
    parser.add_argument('--features-only', action='store_true',
                        help='Sadece feature_core_builder calistir')
    args = parser.parse_args()

    t_total = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"GUNLUK ETIKET YENILEME BASLADI: {t_total.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*60}")

    run_features = not args.labels_only
    run_labels = not args.features_only

    success = True

    if run_features:
        ok = run_script(FEATURE_SCRIPT, 'Feature Tabloları Olusturma (feature_core_builder.py)')
        if not ok:
            logger.error("Feature olusturma basarisiz. Etiketleme atlanıyor.")
            sys.exit(1)

    if run_labels:
        ok = run_script(LABEL_SCRIPT, 'Musteri Etiketleme (label_engine.py)')
        if not ok:
            logger.error("Etiketleme basarisiz.")
            sys.exit(1)

    elapsed_total = (datetime.now() - t_total).total_seconds()
    logger.info(f"{'='*60}")
    logger.info(f"TAMAMLANDI: {elapsed_total:.1f}s ({elapsed_total/60:.1f} dakika)")
    logger.info(f"{'='*60}")


if __name__ == '__main__':
    main()
