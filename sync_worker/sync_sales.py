"""
Sales Sync - Satış Verileri
Her ay çekildikten sonra SQLite-SQLServer tutarlılık kontrolü yapar
Tutarlı değilse o ayı tekrar çeker, tutarlıysa sonraki aya geçer
"""

import sqlite3
import pyodbc
import logging
import os
from datetime import datetime, timedelta
from models import get_connection, create_schema, DB_PATH, DB_BACKEND
from sync_lock import SyncType, acquire_lock, release_lock, is_sync_running
from sync_summary import sync_summary_for_date
from sync_stats import update_best_sellers
from db_logger import setup_db_logging

def _ph():
    return "%s" if DB_BACKEND == "postgresql" else "?"

def _insert_ignore():
    return "ON CONFLICT DO NOTHING" if DB_BACKEND == "postgresql" else "OR IGNORE"

def _insert_replace():
    return "" if DB_BACKEND == "postgresql" else "OR REPLACE"

# ...

# ================== TUTARLILIK KONTROL ==================
# ... (existing functions)

def sync_month_with_verification(sql_cursor, sqlite_conn, year: int, month: int) -> bool:
    """
    Bir ayın verilerini çek ve tutarlılığı doğrula.
    Tutarlı değilse tekrar dene.
    Returns: True if consistent, False otherwise
    """
    month_name = f"{year}-{month:02d}"

    for attempt in range(1, MAX_RETRY_PER_MONTH + 1):
        logger.info(f"   📅 {month_name} - Deneme {attempt}/{MAX_RETRY_PER_MONTH}")

        # Önce mevcut veriyi sil (temiz başla)
        if attempt > 1:
            deleted = delete_month_sales(sqlite_conn, year, month)
            logger.info(f"      🗑️ {deleted} eski kayıt silindi")

        # Veriyi çek
        count = sync_month_sales(sql_cursor, sqlite_conn, year, month)
        logger.info(f"      📥 {count:,} kayıt çekildi")

        # Tutarlılık kontrolü
        result = check_month_consistency(sql_cursor, sqlite_conn, year, month)

        if result['is_consistent']:
            logger.info(f"      ✅ TUTARLI - SQL: {result['sql_stats']['toplam_ciro']:,.2f} TL | "
                       f"SQLite: {result['sqlite_stats']['toplam_ciro']:,.2f} TL")
            
            # En Çok Satan İstatistiklerini Güncelle
            update_best_sellers(sqlite_conn.cursor(), year, month)
            sqlite_conn.commit()
            
            return True


from decouple import config

SQL_SERVER_CONFIG = {
    'server': config('SQL_SERVER', default=config('SQL_SERVER_HOST', default='100.109.143.127')),
    'port': config('SQL_PORT', default=config('SQL_SERVER_PORT', default='14330')),
    'database': config('SQL_DATABASE', default=config('SQL_SERVER_DB', default='DerinSISShow')),
    'username': config('SQL_USERNAME', default=config('SQL_SERVER_USER', default='sa2')),
    'password': config('SQL_PASSWORD', default=config('SQL_SERVER_PW', default='1478236950Mm..')),
    'drivers': [
        '{ODBC Driver 18 for SQL Server}',
        '{ODBC Driver 17 for SQL Server}',
        '{SQL Server Native Client 11.0}',
        '{SQL Server}'
    ]
}

# Railway Fallback: Eğer Tailscale bridge (socat) kullanılıyorsa, 
# Tailscale IP'si yerine localhost tercih edilmelidir.
if config('RAILWAY_ENVIRONMENT', default=None) or config('RAILWAY_SERVICE_ID', default=None):
    # Eğer SQL_SERVER bir Tailscale IP'si ise ve bağlantı hatası alıyorsanız,
    # manuel olarak 'localhost' veya '127.0.0.1' e çekilebilir.
    # Şimdilik mevcut ayarı koruyalım ama loglara ekleyelim.
    pass


LOG_FILE = os.path.join(os.path.dirname(__file__), 'sync_sales.log')

# Tutarlılık toleransı (TL cinsinden fark)
CONSISTENCY_TOLERANCE = 1.0

# Kaç yıl geriye gidilsin
SYNC_YEARS_BACK = 3

# Maksimum retry sayısı (bir ay için)
MAX_RETRY_PER_MONTH = 3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
setup_db_logging(service_name='worker-sales')


def get_driver():
    available = pyodbc.drivers()
    for d in SQL_SERVER_CONFIG['drivers']:
        if d.strip('{}') in available:
            return d
    return '{SQL Server}'


def connect_sql():
    import pyodbc
    import socket
    import time
    
    logger.info("   [BAĞLANTI] 🔍 ODBC sürücüleri taranıyor...")
    drivers = pyodbc.drivers()
    logger.info(f"   [BAĞLANTI] Mevcut sürücüler: {drivers}")
    
    # SOCKS5 Bridge testi
    logger.info("   [BAĞLANTI] 🔌 SOCKS5 köprü bağlantısı test ediliyor (127.0.0.1:14330)...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(('127.0.0.1', 14330))
        logger.info("   [BAĞLANTI] ✅ Köprü TCP bağlantısı açık.")
        s.close()
    except Exception as e:
        logger.warning(f"   [BAĞLANTI] ⚠️ Köprü henüz hazır değil: {e}")

    # Driver seçimi
    logger.info("   [BAĞLANTI] 🔧 Uygun ODBC sürücüsü seçiliyor...")
    driver = '{ODBC Driver 17 for SQL Server}'
    
    if 'FreeTDS' in drivers:
        driver = 'FreeTDS'
    elif '{ODBC Driver 17 for SQL Server}' in drivers:
        driver = '{ODBC Driver 17 for SQL Server}'
    elif '{ODBC Driver 18 for SQL Server}' in drivers:
        driver = '{ODBC Driver 18 for SQL Server}'
    elif '{ODBC Driver 17 for SQL Server}' not in drivers and '{ODBC Driver 18 for SQL Server}' not in drivers:
        driver = '{SQL Server}'
        for d in drivers:
            if 'ODBC Driver' in d:
                driver = d
                break

    logger.info(f"   [BAĞLANTI] ✅ Seçilen sürücü: {driver}")
    
    conn_str = (
        f"DRIVER={driver};"
        "SERVER=127.0.0.1;"
        "PORT=14330;"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"UID={SQL_SERVER_CONFIG['username']};"
        f"PWD={SQL_SERVER_CONFIG['password']};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
        "TDS_Version=7.3;"
        "Connection Timeout=60;"
    )
    
    logger.info("   [BAĞLANTI] ⏳ Köprünün hazır olması bekleniyor (10s)...")
    time.sleep(10)
    logger.info("   [BAĞLANTI] 🔌 SQL Server'a bağlanılıyor...")
    conn = pyodbc.connect(conn_str, timeout=60, autocommit=True)
    logger.info("   [BAĞLANTI] ✅ SQL Server bağlantısı BAŞARILI!")
    return conn






# ================== TUTARLILIK KONTROL ==================

def get_sqlserver_month_stats(sql_cursor, year: int, month: int) -> dict:
    """SQL Server'dan belirli ayın istatistiklerini al"""
    start_date = f"{year}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    sql_cursor.execute(f"""
        SELECT
            COUNT(*) as kayit_sayisi,
            ISNULL(SUM([Satış Tutarı]), 0) as toplam_ciro,
            COUNT(DISTINCT [PosDocumentId]) as fis_sayisi
        FROM M_Crm WITH (NOLOCK)
        WHERE [TARİH] >= '{start_date}' AND [TARİH] < '{end_date}'
    """)

    row = sql_cursor.fetchone()
    return {
        'kayit_sayisi': row[0] or 0,
        'toplam_ciro': float(row[1] or 0),
        'fis_sayisi': row[2] or 0
    }


def get_sqlite_month_stats(sqlite_conn, year: int, month: int) -> dict:
    """SQLite'dan belirli ayın istatistiklerini al"""
    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"

    cursor = sqlite_conn.cursor()
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            SELECT
                COUNT(*) as kayit_sayisi,
                COALESCE(SUM(tutar), 0) as toplam_ciro,
                COUNT(DISTINCT fis_no) as fis_sayisi
            FROM satislar
            WHERE tarih >= %s AND tarih <= %s
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT
                COUNT(*) as kayit_sayisi,
                COALESCE(SUM(tutar), 0) as toplam_ciro,
                COUNT(DISTINCT fis_no) as fis_sayisi
            FROM satislar
            WHERE date(tarih) >= ? AND date(tarih) <= ?
        """, (start_date, end_date))

    row = cursor.fetchone()
    return {
        'kayit_sayisi': row[0] or 0,
        'toplam_ciro': float(row[1] or 0),
        'fis_sayisi': row[2] or 0
    }


def check_month_consistency(sql_cursor, sqlite_conn, year: int, month: int) -> dict:
    """
    Belirli ay için SQLite ve SQL Server tutarlılığını kontrol et.
    Returns: {is_consistent: bool, sql_stats: dict, sqlite_stats: dict, diff: dict}
    """
    sql_stats = get_sqlserver_month_stats(sql_cursor, year, month)
    sqlite_stats = get_sqlite_month_stats(sqlite_conn, year, month)

    ciro_diff = abs(sql_stats['toplam_ciro'] - sqlite_stats['toplam_ciro'])
    kayit_diff = abs(sql_stats['kayit_sayisi'] - sqlite_stats['kayit_sayisi'])

    is_consistent = ciro_diff <= CONSISTENCY_TOLERANCE

    return {
        'is_consistent': is_consistent,
        'sql_stats': sql_stats,
        'sqlite_stats': sqlite_stats,
        'diff': {
            'ciro': ciro_diff,
            'kayit': kayit_diff
        }
    }


# ================== SYNC FONKSİYONLARI ==================

def delete_month_sales(sqlite_conn, year: int, month: int):
    """Belirli ayın satış verilerini SQLite/Postgres'den sil"""
    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"
    
    cursor = sqlite_conn.cursor()
    if DB_BACKEND == "postgresql":
        cursor.execute("""
            DELETE FROM satislar
            WHERE tarih >= %s AND tarih <= %s
        """, (start_date, end_date))
    else:
        cursor.execute("""
            DELETE FROM satislar
            WHERE date(tarih) >= ? AND date(tarih) <= ?
        """, (start_date, end_date))
    deleted = cursor.rowcount
    sqlite_conn.commit()
    return deleted


def sync_month_sales(sql_cursor, sqlite_conn, year: int, month: int) -> int:
    """Belirli ayın satış verilerini çek"""
    import time as _time
    month_label = f"{year}-{month:02d}"
    sync_start = _time.time()
    
    start_date = f"{year}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    # Lookup map'leri al
    logger.info(f"      [FETCH] 🗂️ Lookup tabloları yükleniyor...")
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("SELECT id, ad FROM magazalar")
    magaza_map = {row[1]: row[0] for row in sqlite_cursor.fetchall()}

    sqlite_cursor.execute("SELECT id, kod, kategori_id, marka_id FROM urunler")
    urun_map = {row[1]: (row[0], row[2], row[3]) for row in sqlite_cursor.fetchall()}
    logger.info(f"      [FETCH] ✅ {len(magaza_map)} mağaza, {len(urun_map)} ürün yüklendi.")

    # SQL Server'dan veri çek
    logger.info(f"      [FETCH] 📡 SQL Server'dan {month_label} verisi sorgulanıyor...")
    sql_cursor.execute(f"""
        SELECT
            [PosDocumentId],
            [Müşteri Kodu],
            [TARİH],
            [SAAT],
            [Satış Tutarı],
            [Miktar],
            [stkKod],
            [Magaza],
            [BelgeTipi],
            [kmp_sayısı],
            [telefon NUMARASI],
            [OnayDurumu],
            ROW_NUMBER() OVER (PARTITION BY [PosDocumentId] ORDER BY [stkKod], [kmp_sayısı]) as SatirNo,
            [BelgeToplami],
            [BelgeIndirimToplami],
            [SepetUrunSayisi]
        FROM M_Crm WITH (NOLOCK)
        WHERE [TARİH] >= '{start_date}' AND [TARİH] < '{end_date}'
    """)

    logger.info(f"      [FETCH] ⏳ Sonuçlar akış ile alınıyor (5000'er batch)...")

    # fetchall() yerine fetchmany ile streaming — 500K+ satırı tek seferde RAM'e yüklemiyor
    FETCH_CHUNK = 5000
    first_chunk = sql_cursor.fetchmany(FETCH_CHUNK)
    if not first_chunk:
        logger.info(f"      [FETCH] ℹ️ {month_label} için veri bulunamadı.")
        return 0

    # Eski veriyi ilk chunk geldikten sonra sil (veri doğrulama sonrası)
    logger.info(f"      [WRITE] 🗑️ Eski {month_label} verisi temizleniyor...")
    delete_month_sales(sqlite_conn, year, month)

    total_written = 0
    chunk = first_chunk
    while chunk:
        batch_data = []
        for row in chunk:
            magaza_id = magaza_map.get(row[7])
            u_info = urun_map.get(row[6])
            urun_id, k_id, m_id = u_info if u_info else (None, None, None)

            batch_data.append((
                str(row[0]),   # fis_no
                row[1],        # musteri_id
                row[2],        # tarih
                row[3],        # saat
                row[4],        # tutar
                row[5],        # miktar
                urun_id,
                magaza_id,
                row[8],        # belge_tipi
                row[9],        # kampanya_id
                row[10],       # telefon
                row[11],       # onay_durumu
                row[12],       # satir_no
                k_id,
                m_id,
                row[13],       # belge_toplami
                row[14],       # belge_indirim_toplami
                row[15],       # sepet_urun_sayisi
            ))

        if DB_BACKEND == "postgresql":
            sqlite_cursor.executemany("""
                INSERT INTO satislar
                (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, belge_tipi, kampanya_id, telefon, onay_durumu, satir_no, kategori_id, marka_id, belge_toplami, belge_indirim_toplami, sepet_urun_sayisi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fis_no, satir_no) DO UPDATE SET
                    belge_toplami = EXCLUDED.belge_toplami,
                    belge_indirim_toplami = EXCLUDED.belge_indirim_toplami,
                    sepet_urun_sayisi = EXCLUDED.sepet_urun_sayisi
            """, batch_data)
        else:
            sqlite_cursor.executemany("""
                INSERT OR IGNORE INTO satislar
                (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, belge_tipi, kampanya_id, telefon, onay_durumu, satir_no, kategori_id, marka_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)

        sqlite_conn.commit()
        total_written += len(batch_data)
        chunk = sql_cursor.fetchmany(FETCH_CHUNK)

    elapsed = _time.time() - sync_start
    logger.info(f"      [WRITE] ✅ {total_written:,} satır yazıldı ({elapsed:.1f}s)")
    
    return total_written

def sync_recent_sales(sql_cursor, sqlite_conn, days_back: int = 3) -> int:
    """Belirli son günlerin satış verilerini hızlıca çek"""
    import time as _time
    sync_start = _time.time()
    
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    date_label = f"{start_date} ile {end_date} arası"

    logger.info(f"      [FETCH] 🗂️ Lookup tabloları yükleniyor...")
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("SELECT id, ad FROM magazalar")
    magaza_map = {row[1]: row[0] for row in sqlite_cursor.fetchall()}

    sqlite_cursor.execute("SELECT id, kod, kategori_id, marka_id FROM urunler")
    urun_map = {row[1]: (row[0], row[2], row[3]) for row in sqlite_cursor.fetchall()}
    logger.info(f"      [FETCH] ✅ {len(magaza_map)} mağaza, {len(urun_map)} ürün yüklendi.")

    logger.info(f"      [FETCH] 📡 SQL Server'dan {date_label} verisi sorgulanıyor...")
    sql_cursor.execute(f"""
        SELECT
            [PosDocumentId],
            [Müşteri Kodu],
            [TARİH],
            [SAAT],
            [Satış Tutarı],
            [Miktar],
            [stkKod],
            [Magaza],
            [BelgeTipi],
            [kmp_sayısı],
            [telefon NUMARASI],
            [OnayDurumu],
            ROW_NUMBER() OVER (PARTITION BY [PosDocumentId] ORDER BY [stkKod], [kmp_sayısı]) as SatirNo,
            [BelgeToplami],
            [BelgeIndirimToplami],
            [SepetUrunSayisi]
        FROM M_Crm WITH (NOLOCK)
        WHERE [TARİH] >= '{start_date}' AND [TARİH] < '{end_date}'
    """)

    logger.info(f"      [FETCH] ⏳ Sonuçlar streaming ile alınıyor...")
    FETCH_CHUNK = 5000
    first_chunk = sql_cursor.fetchmany(FETCH_CHUNK)

    if not first_chunk:
        logger.info(f"      [FETCH] ℹ️ {date_label} için veri bulunamadı.")
        return 0

    # İlk chunk geldi — artık eski veriyi sil
    logger.info(f"      [WRITE] 🗑️ Eski {date_label} verisi temizleniyor...")
    if DB_BACKEND == "postgresql":
        sqlite_cursor.execute("DELETE FROM satislar WHERE tarih >= %s", (start_date,))
    else:
        sqlite_cursor.execute("DELETE FROM satislar WHERE date(tarih) >= ?", (start_date,))
    deleted = sqlite_cursor.rowcount
    logger.info(f"      [WRITE] 🗑️ {deleted} eski satır silindi.")

    total_written = 0
    affected_dates = set()
    chunk = first_chunk

    while chunk:
        batch_data = []
        for row in chunk:
            magaza_id = magaza_map.get(row[7])
            u_info = urun_map.get(row[6])
            urun_id, k_id, m_id = u_info if u_info else (None, None, None)

            batch_data.append((
                str(row[0]),   # fis_no
                row[1],        # musteri_id
                row[2],        # tarih
                row[3],        # saat
                row[4],        # tutar
                row[5],        # miktar
                urun_id,
                magaza_id,
                row[8],        # belge_tipi
                row[9],        # kampanya_id
                row[10],       # telefon
                row[11],       # onay_durumu
                row[12],       # satir_no
                k_id,
                m_id,
                row[13],       # belge_toplami
                row[14],       # belge_indirim_toplami
                row[15],       # sepet_urun_sayisi
            ))
            ds = row[2].strftime('%Y-%m-%d') if hasattr(row[2], 'strftime') else row[2]
            affected_dates.add(ds)

        if DB_BACKEND == "postgresql":
            sqlite_cursor.executemany("""
                INSERT INTO satislar
                (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, belge_tipi, kampanya_id, telefon, onay_durumu, satir_no, kategori_id, marka_id, belge_toplami, belge_indirim_toplami, sepet_urun_sayisi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fis_no, satir_no) DO UPDATE SET
                    belge_toplami = EXCLUDED.belge_toplami,
                    belge_indirim_toplami = EXCLUDED.belge_indirim_toplami,
                    sepet_urun_sayisi = EXCLUDED.sepet_urun_sayisi
            """, batch_data)
        else:
            sqlite_cursor.executemany("""
                INSERT OR IGNORE INTO satislar
                (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, belge_tipi, kampanya_id, telefon, onay_durumu, satir_no, kategori_id, marka_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)

        sqlite_conn.commit()
        total_written += len(batch_data)
        chunk = sql_cursor.fetchmany(FETCH_CHUNK)

    elapsed = _time.time() - sync_start
    logger.info(f"      [WRITE] ✅ {total_written:,} satır yazıldı ({elapsed:.1f}s)")

    if affected_dates:
        logger.info(f"      [ÖZET] 📊 {len(affected_dates)} gün için özet güncelleniyor...")
        for date_str in affected_dates:
            sync_summary_for_date(date_str)
        logger.info(f"      [ÖZET] ✅ Özetler güncellendi.")

    return total_written


def sync_month_with_verification(sql_cursor, sqlite_conn, year: int, month: int) -> bool:
    """
    Bir ayın verilerini çek ve tutarlılığı doğrula.
    Tutarlı değilse tekrar dene.
    Returns: True if consistent, False otherwise
    """
    month_name = f"{year}-{month:02d}"

    for attempt in range(1, MAX_RETRY_PER_MONTH + 1):
        logger.info(f"   📅 {month_name} - Deneme {attempt}/{MAX_RETRY_PER_MONTH}")

        # Önce mevcut veriyi sil (temiz başla)
        if attempt > 1:
            deleted = delete_month_sales(sqlite_conn, year, month)
            logger.info(f"      🗑️ {deleted} eski kayıt silindi")

        # Veriyi çek
        count = sync_month_sales(sql_cursor, sqlite_conn, year, month)
        logger.info(f"      📥 {count:,} kayıt çekildi")

        # Tutarlılık kontrolü
        result = check_month_consistency(sql_cursor, sqlite_conn, year, month)

        if result['is_consistent']:
            logger.info(f"      ✅ TUTARLI - SQL: {result['sql_stats']['toplam_ciro']:,.2f} TL | "
                       f"SQLite: {result['sqlite_stats']['toplam_ciro']:,.2f} TL")
            return True
        else:
            logger.warning(f"      ⚠️ TUTARSIZ - Fark: {result['diff']['ciro']:,.2f} TL, "
                          f"{result['diff']['kayit']} kayıt")
            logger.warning(f"         SQL: {result['sql_stats']['kayit_sayisi']:,} kayıt, "
                          f"{result['sql_stats']['toplam_ciro']:,.2f} TL")
            logger.warning(f"         SQLite: {result['sqlite_stats']['kayit_sayisi']:,} kayıt, "
                          f"{result['sqlite_stats']['toplam_ciro']:,.2f} TL")

    logger.error(f"   ❌ {month_name} - {MAX_RETRY_PER_MONTH} denemede tutarlı hale getirilemedi!")
    return False


def get_months_to_sync(start_year: int = None) -> list:
    """Senkronize edilecek ay listesini döndür (eski->yeni sıralı)"""
    today = datetime.now()

    if start_year is None:
        start_year = today.year - SYNC_YEARS_BACK

    months = []

    current = datetime(start_year, 1, 1)
    while current <= today:
        months.append((current.year, current.month))

        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return months


# ================== ANA FONKSİYON ==================

def run_sales_sync(full_sync: bool = False):
    """
    Satış verilerini senkronize et.

    Args:
        full_sync: True ise tüm geçmişi çek, False ise son sync'ten devam et
    """

    # Kilit kontrolü
    if is_sync_running():
        logger.warning("⚠️ Başka bir sync işlemi çalışıyor. Sales sync atlanıyor.")
        return False

    # Kilit al
    if not acquire_lock(SyncType.SALES):
        logger.error("❌ Kilit alınamadı!")
        return False

    logger.info("=" * 60)
    logger.info("🚀 SALES SYNC BAŞLADI")
    logger.info("=" * 60)

    start_time = datetime.now()
    success = False
    stats = {
        'total_months': 0,
        'consistent_months': 0,
        'inconsistent_months': 0,
        'total_records': 0
    }

    try:
        # Şemayı oluştur
        create_schema()

        # Bağlantılar
        sqlite_conn = get_connection()
        sql_conn = connect_sql()
        sql_cursor = sql_conn.cursor()

        # Son başarılı sync'i kontrol et
        sqlite_cursor = sqlite_conn.cursor()
        last_synced_month = None

        if not full_sync:
            sqlite_cursor.execute("SELECT value FROM syncmeta WHERE key='last_sales_sync_month'")
            row = sqlite_cursor.fetchone()
            if row and row[0]:
                last_synced_month = row[0]
                logger.info(f"📅 Son başarılı sync: {last_synced_month}")

        # Senkronize edilecek ayları belirle
        months = get_months_to_sync()
        stats['total_months'] = len(months)

        # Son sync'ten sonraki aylardan başla
        if last_synced_month and not full_sync:
            try:
                parts = last_synced_month.split('-')
                last_year = int(parts[0])
                last_month = int(parts[1])

                # Filtreleme
                months = [(y, m) for y, m in months if (y, m) >= (last_year, last_month)]
                logger.info(f"   {len(months)} ay işlenecek (artımlı)")
            except:
                logger.warning("Son sync tarihi parse edilemedi, full sync yapılacak")

        logger.info(f"📊 Toplam {len(months)} ay işlenecek")

        # Her ayı sırayla işle
        for year, month in months:
            month_str = f"{year}-{month:02d}"
            result = sync_month_with_verification(sql_cursor, sqlite_conn, year, month)

            if result:
                stats['consistent_months'] += 1

                # Son başarılı ay'ı güncelle
                if DB_BACKEND == "postgresql":
                    sqlite_cursor.execute("""
                        INSERT INTO syncmeta (key, value, updated_at)
                        VALUES ('last_sales_sync_month', %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
                    """, (month_str,))
                else:
                    sqlite_cursor.execute("""
                        INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                        VALUES ('last_sales_sync_month', ?, datetime('now'))
                    """, (month_str,))
                sqlite_conn.commit()
            else:
                stats['inconsistent_months'] += 1
                # Tutarsız ayda durma, devam et (veya isteğe bağlı durdurulabilir)

        # Genel sync meta güncelle
        updated_key = 'last_full_sync' if full_sync else 'last_delta_sync'
        now_iso = datetime.now().isoformat()

        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (updated_key, now_iso))

            sqlite_cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_sales_sync', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (now_iso,))

            sqlite_cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_delta_sync_datetime', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (now_iso,))
        else:
            sqlite_cursor.execute(f"""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES (?, ?, datetime('now'))
            """, (updated_key, now_iso))

            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_sales_sync', ?, datetime('now'))
            """, (now_iso,))

            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_delta_sync_datetime', ?, datetime('now'))
            """, (now_iso,))
        
        sqlite_conn.commit()

        # Toplam kayıt sayısını al
        sqlite_cursor.execute("SELECT COUNT(*) FROM satislar")
        stats['total_records'] = sqlite_cursor.fetchone()[0]

        # Bağlantıları kapat
        sql_conn.close()
        sqlite_conn.close()

        elapsed = datetime.now() - start_time
        logger.info("=" * 60)
        logger.info(f"✅ SALES SYNC TAMAMLANDI - Süre: {elapsed}")
        logger.info(f"   📊 İstatistikler:")
        logger.info(f"      - Toplam ay: {stats['total_months']}")
        logger.info(f"      - Tutarlı ay: {stats['consistent_months']}")
        logger.info(f"      - Tutarsız ay: {stats['inconsistent_months']}")
        logger.info(f"      - Toplam kayıt: {stats['total_records']:,}")
        logger.info("=" * 60)

        success = stats['inconsistent_months'] == 0

    except Exception as e:
        logger.error(f"❌ SALES SYNC HATASI: {e}", exc_info=True)

    finally:
        release_lock()

    return success


def run_incremental_sync():
    """Artımlı sync - sadece yeni veriler"""
    return run_sales_sync(full_sync=False)

def run_recent_sync(days_back=3):
    """Sadece son N günün verisini hızlıca (Delta Sync) çek"""
    if is_sync_running():
        logger.warning("⚠️ Başka bir sync işlemi çalışıyor. Recent sync atlanıyor.")
        return False

    if not acquire_lock(SyncType.SALES):
        logger.error("❌ Kilit alınamadı!")
        return False

    logger.info("=" * 60)
    logger.info(f"🚀 RECENT (DELTA) SYNC BAŞLADI (Son {days_back} gün)")
    logger.info("=" * 60)

    start_time = datetime.now()
    success = False
    
    try:
        create_schema()
        sqlite_conn = get_connection()
        sql_conn = connect_sql()
        sql_cursor = sql_conn.cursor()

        count = sync_recent_sales(sql_cursor, sqlite_conn, days_back)
        success = True

        sqlite_cursor = sqlite_conn.cursor()
        now_iso = datetime.now().isoformat()
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_delta_sync_datetime', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (now_iso,))
            sqlite_cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_delta_sync', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (now_iso,))
        else:
            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_delta_sync_datetime', ?, datetime('now'))
            """, (now_iso,))
            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_delta_sync', ?, datetime('now'))
            """, (now_iso,))
        
        sqlite_conn.commit()
        sql_conn.close()
        sqlite_conn.close()

        elapsed = datetime.now() - start_time
        logger.info("=" * 60)
        logger.info(f"✅ RECENT (DELTA) SYNC TAMAMLANDI - Süre: {elapsed} - Çekilen: {count:,}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ RECENT SYNC HATASI: {e}", exc_info=True)
    finally:
        release_lock()

    return success


def run_full_sync():
    """Tam sync - tüm geçmişi çek"""
    return run_sales_sync(full_sync=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        run_full_sync()
    else:
        run_incremental_sync()
