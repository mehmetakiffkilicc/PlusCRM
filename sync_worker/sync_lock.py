"""
Sync Lock Manager - Merkezi Kilit Yönetimi
Birden fazla sync işleminin aynı anda çalışmasını engeller
"""

import os
import time
import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

LOCK_DIR = os.path.dirname(__file__)
LOCK_FILE = os.path.join(LOCK_DIR, 'sync.lock')
LOOKUP_LOCK_FILE = os.path.join(LOCK_DIR, 'sync_lookup.lock')
LOCK_TIMEOUT_HOURS = 2


class SyncType(Enum):
    LOOKUP = "lookup"    # Marka, Ürün, Kategori, Mağaza, Kampanya, Müşteri
    SALES = "sales"      # Satış verileri


class SyncLockError(Exception):
    """Kilit alınamadı hatası"""
    pass


def _is_lock_active(lock_file: str) -> bool:
    """Belirli bir kilit dosyası aktif mi?"""
    if not os.path.exists(lock_file):
        return False
    try:
        file_time = datetime.fromtimestamp(os.path.getmtime(lock_file))
        age = datetime.now() - file_time
        if age > timedelta(hours=LOCK_TIMEOUT_HOURS):
            os.remove(lock_file)
            logger.warning(f"⚠️ Eski kilit dosyası silindi ({lock_file}, {age})")
            return False
        return True
    except:
        return False


def is_sync_running() -> bool:
    """Sales/summary sync çalışıyor mu? (lookup'ı bloke etmez)"""
    return _is_lock_active(LOCK_FILE)


def is_lookup_running() -> bool:
    """Lookup sync çalışıyor mu?"""
    return _is_lock_active(LOOKUP_LOCK_FILE)


def get_lock_info() -> dict:
    """Çalışan sync hakkında bilgi"""
    if not os.path.exists(LOCK_FILE):
        return None

    try:
        with open(LOCK_FILE, 'r') as f:
            content = f.read().strip()

        parts = content.split('|')
        if len(parts) >= 3:
            return {
                'type': parts[0],
                'started_at': parts[1],
                'pid': parts[2]
            }
        return {'raw': content}
    except:
        return None


def _acquire(lock_file: str, sync_type: SyncType) -> bool:
    _is_lock_active(lock_file)  # stale temizle
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as f:
            f.write(f"{sync_type.value}|{datetime.now().isoformat()}|{os.getpid()}")
        logger.info(f"🔒 Kilit alındı: {sync_type.value} ({lock_file})")
        return True
    except FileExistsError:
        logger.warning(f"⚠️ Kilit zaten var: {lock_file}")
        return False
    except Exception as e:
        logger.error(f"Kilit alma hatası: {e}")
        return False


def _release(lock_file: str):
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
        logger.info(f"🔓 Kilit serbest bırakıldı: {lock_file}")
    except Exception as e:
        logger.error(f"Kilit serbest bırakma hatası: {e}")


def acquire_lock(sync_type: SyncType) -> bool:
    """Sales/summary/maintenance için kilit al (lookup'tan bağımsız)."""
    if sync_type == SyncType.LOOKUP:
        # Lookup kendi kilit dosyasını kullanır, sales kilidi aramaz
        return _acquire(LOOKUP_LOCK_FILE, sync_type)
    return _acquire(LOCK_FILE, sync_type)


def release_lock(sync_type: SyncType = None):
    """Kilidi serbest bırak."""
    if sync_type == SyncType.LOOKUP:
        _release(LOOKUP_LOCK_FILE)
    else:
        _release(LOCK_FILE)


def force_release():
    """Her iki kilidi de zorla serbest bırak"""
    ok = True
    for lf in (LOCK_FILE, LOOKUP_LOCK_FILE):
        try:
            if os.path.exists(lf):
                os.remove(lf)
                logger.warning(f"⚠️ Kilit zorla serbest bırakıldı: {lf}")
        except:
            ok = False
    return ok


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Sync çalışıyor mu: {is_sync_running()}")
    print(f"Lock bilgisi: {get_lock_info()}")
