"""
Lookup Sync - Marka, Ürün, Kategori, Mağaza, Kampanya, Müşteri
Bu veriler nadiren değişir, günde 1-2 kez çekilmesi yeterli
"""

import sqlite3
import pyodbc
import logging
import os
from datetime import datetime
from models import get_connection, create_schema, DB_PATH, DB_BACKEND

def _ph():
    return "%s" if DB_BACKEND == "postgresql" else "?"

def _insert_ignore():
    return "ON CONFLICT DO NOTHING" if DB_BACKEND == "postgresql" else "OR IGNORE"

def _insert_replace():
    # PostgreSQL için custom conflict handling gerekebilir, şimdilik basit tutalım
    return "" if DB_BACKEND == "postgresql" else "OR REPLACE"
from sync_lock import SyncType, acquire_lock, release_lock, is_lookup_running

# ================== KONFİGÜRASYON ==================

from decouple import config

SQL_SERVER_CONFIG = {
    'server': config('SQL_SERVER', default=config('SQL_SERVER_HOST', default='100.109.143.127')),
    'port': config('SQL_PORT', default=config('SQL_SERVER_PORT', default='14330')),
    'database': config('SQL_DATABASE', default=config('SQL_SERVER_DB', default='DerinSISShow')),
    'username': config('SQL_USERNAME', default=config('SQL_SERVER_USER', default='sa')),
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
    pass


LOG_FILE = os.path.join(os.path.dirname(__file__), 'sync_lookup.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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
    
    logger.info("   [BAĞLANTI] ⏳ Köprünün hazır olması bekleniyor (1s)...")
    time.sleep(1)
    logger.info("   [BAĞLANTI] 🔌 SQL Server'a bağlanılıyor...")
    conn = pyodbc.connect(conn_str, timeout=60, autocommit=True)
    logger.info("   [BAĞLANTI] ✅ SQL Server bağlantısı BAŞARILI!")
    return conn






# ================== SYNC FONKSİYONLARI ==================

def sync_markalar(sql_cursor, sqlite_conn):
    """markaları senkronize et"""
    logger.info("📦 markalar senkronize ediliyor...")

    sql_cursor.execute("""
        SELECT DISTINCT [MarkaAdi] FROM M_Crm WITH (NOLOCK)
        WHERE [MarkaAdi] IS NOT NULL AND [MarkaAdi] <> ''
    """)

    markalar = [row[0] for row in sql_cursor.fetchall()]
    sqlite_cursor = sqlite_conn.cursor()

    for marka in markalar:
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute(
                "INSERT INTO markalar (ad) VALUES (%s) ON CONFLICT (ad) DO NOTHING",
                (marka,)
            )
        else:
            sqlite_cursor.execute(
                "INSERT OR IGNORE INTO markalar (ad) VALUES (?)",
                (marka,)
            )

    sqlite_conn.commit()
    logger.info(f"   ✓ {len(markalar)} marka işlendi")
    return len(markalar)


def sync_satinalmacilar(sql_cursor, sqlite_conn):
    """Kategori yöneticilerini (ktgrGrupAd) senkronize et"""
    logger.info("👥 Kategori yöneticileri senkronize ediliyor...")

    sql_cursor.execute("""
        SELECT DISTINCT [ktgrGrupAd] FROM M_Crm WITH (NOLOCK)
        WHERE [ktgrGrupAd] IS NOT NULL AND [ktgrGrupAd] <> ''
    """)

    yoneticiler = [row[0] for row in sql_cursor.fetchall()]
    sqlite_cursor = sqlite_conn.cursor()

    for y in yoneticiler:
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute(
                "INSERT INTO kategori_yoneticileri (ad) VALUES (%s) ON CONFLICT (ad) DO NOTHING",
                (y,)
            )
        else:
            sqlite_cursor.execute(
                "INSERT OR IGNORE INTO kategori_yoneticileri (ad) VALUES (?)",
                (y,)
            )

    sqlite_conn.commit()
    logger.info(f"   ✓ {len(yoneticiler)} kategori yöneticisi işlendi")
    return len(yoneticiler)


def sync_kategoriler(sql_cursor, sqlite_conn):
    """kategorileri senkronize et"""
    logger.info("📦 kategoriler senkronize ediliyor...")

    sql_cursor.execute("""
        SELECT DISTINCT [Ana_Kategori], [Alt_Kategori1], [Alt_Kategori2]
        FROM M_Crm WITH (NOLOCK)
        WHERE [Ana_Kategori] IS NOT NULL
    """)
    kategoriler = sql_cursor.fetchall()

    # Ana kategori → yönetici (ktgrGrupAd) eşleşmesi
    sql_cursor.execute("""
        SELECT [Ana_Kategori], [ktgrGrupAd], COUNT(*) as cnt
        FROM M_Crm WITH (NOLOCK)
        WHERE [Ana_Kategori] IS NOT NULL AND [ktgrGrupAd] IS NOT NULL AND [ktgrGrupAd] <> ''
        GROUP BY [Ana_Kategori], [ktgrGrupAd]
        ORDER BY [Ana_Kategori], cnt DESC
    """)
    # Her ana kategori için en çok tekrar eden ktgrGrupAd'ı al
    kat_yonetici_map = {}
    for row in sql_cursor.fetchall():
        ana = row[0]
        yonetici = row[1]
        if ana not in kat_yonetici_map:
            kat_yonetici_map[ana] = yonetici

    sqlite_cursor = sqlite_conn.cursor()

    # kategori_yoneticileri map
    sqlite_cursor.execute("SELECT id, ad FROM kategori_yoneticileri")
    satinalma_map = {row[1]: row[0] for row in sqlite_cursor.fetchall()}

    for kat in kategoriler:
        yonetici_ad = kat_yonetici_map.get(kat[0])
        yonetici_id = satinalma_map.get(yonetici_ad) if yonetici_ad else None
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute(
                """INSERT INTO kategoriler (ana, alt1, alt2, yonetici_id) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (ana, alt1, alt2) DO UPDATE SET yonetici_id = EXCLUDED.yonetici_id""",
                (kat[0], kat[1], kat[2], yonetici_id)
            )
        else:
            sqlite_cursor.execute(
                "INSERT OR REPLACE INTO kategoriler (ana, alt1, alt2, yonetici_id) VALUES (?, ?, ?, ?)",
                (kat[0], kat[1], kat[2], yonetici_id)
            )

    sqlite_conn.commit()
    logger.info(f"   ✓ {len(kategoriler)} kategori işlendi")
    return len(kategoriler)


def sync_magazalar(sql_cursor, sqlite_conn):
    """Mağazaları senkronize et"""
    logger.info("📦 Mağazalar senkronize ediliyor...")

    sql_cursor.execute("""
        SELECT DISTINCT [Magaza], [Alt_Kategori3]
        FROM M_Crm WITH (NOLOCK)
        WHERE [Magaza] IS NOT NULL
    """)

    magazalar = sql_cursor.fetchall()
    sqlite_cursor = sqlite_conn.cursor()

    for mag in magazalar:
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute(
                "INSERT INTO magazalar (ad, bolge) VALUES (%s, %s) ON CONFLICT (ad) DO NOTHING",
                (mag[0], mag[1])
            )
        else:
            sqlite_cursor.execute(
                "INSERT OR IGNORE INTO magazalar (ad, bolge) VALUES (?, ?)",
                (mag[0], mag[1])
            )

    sqlite_conn.commit()
    logger.info(f"   ✓ {len(magazalar)} mağaza işlendi")
    return len(magazalar)


def sync_urunler(sql_cursor, sqlite_conn):
    """Ürünleri senkronize et"""
    logger.info("📦 Ürünler senkronize ediliyor...")

    # Get products with full category hierarchy (ana, alt1, alt2) and satinalmaci
    sql_cursor.execute("""
        SELECT DISTINCT [stkKod], [stkAd], [MarkaAdi], [Ana_Kategori], [Alt_Kategori1], [Alt_Kategori2], [ktgrGrupAd]
        FROM M_Crm WITH (NOLOCK)
        WHERE [stkKod] IS NOT NULL
    """)

    urunler = sql_cursor.fetchall()
    sqlite_cursor = sqlite_conn.cursor()

    # Marka map
    sqlite_cursor.execute("SELECT id, ad FROM markalar")
    marka_map = {row[1]: row[0] for row in sqlite_cursor.fetchall()}

    # Kategori yöneticisi map
    sqlite_cursor.execute("SELECT id, ad FROM kategori_yoneticileri")
    satinalmaci_map = {row[1]: row[0] for row in sqlite_cursor.fetchall()}

    # Kategori map: Use full hierarchy (ana, alt1, alt2) as key
    sqlite_cursor.execute("SELECT id, ana, alt1, alt2 FROM kategoriler")
    kategori_map = {}
    for row in sqlite_cursor.fetchall():
        # Key: (ana, alt1, alt2) tuple
        key = (row[1], row[2], row[3])
        kategori_map[key] = row[0]

    count = 0
    for urun in urunler:
        marka_id = marka_map.get(urun[2])
        yonetici_id_urun = satinalmaci_map.get(urun[6])
        # Lookup category using full hierarchy
        kategori_key = (urun[3], urun[4], urun[5])
        kategori_id = kategori_map.get(kategori_key)

        # Fallback: try (ana, alt1, None) if alt2 doesn't match
        if not kategori_id:
            kategori_key = (urun[3], urun[4], None)
            kategori_id = kategori_map.get(kategori_key)

        # Fallback: try (ana, None, None) if nothing else matches
        if not kategori_id:
            kategori_key = (urun[3], None, None)
            kategori_id = kategori_map.get(kategori_key)

        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute("""
                INSERT INTO urunler (kod, ad, marka_id, kategori_id, yonetici_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (kod) DO UPDATE SET
                    ad=EXCLUDED.ad, marka_id=EXCLUDED.marka_id,
                    kategori_id=EXCLUDED.kategori_id, yonetici_id=EXCLUDED.yonetici_id
            """, (urun[0], urun[1], marka_id, kategori_id, yonetici_id_urun))
        else:
            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO urunler (kod, ad, marka_id, kategori_id, yonetici_id)
                VALUES (?, ?, ?, ?, ?)
            """, (urun[0], urun[1], marka_id, kategori_id, yonetici_id_urun))
        count += 1

    sqlite_conn.commit()
    logger.info(f"   ✓ {count} ürün işlendi")
    return count


def sync_kampanyalar(sql_cursor, sqlite_conn):
    """kampanyaları senkronize et"""
    logger.info("📦 kampanyalar senkronize ediliyor...")

    sql_cursor.execute("""
        SELECT DISTINCT [kmp_sayısı], [kmp_ad], [basla], [bitis]
        FROM M_Crm WITH (NOLOCK)
        WHERE [kmp_sayısı] IS NOT NULL
    """)

    kampanyalar = sql_cursor.fetchall()
    sqlite_cursor = sqlite_conn.cursor()

    for kmp in kampanyalar:
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute("""
                INSERT INTO kampanyalar (id, ad, baslangic, bitis)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET ad=EXCLUDED.ad, baslangic=EXCLUDED.baslangic, bitis=EXCLUDED.bitis
            """, (kmp[0], kmp[1], kmp[2], kmp[3]))
        else:
            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO kampanyalar (id, ad, baslangic, bitis)
                VALUES (?, ?, ?, ?)
            """, (kmp[0], kmp[1], kmp[2], kmp[3]))

    sqlite_conn.commit()
    logger.info(f"   ✓ {len(kampanyalar)} kampanya işlendi")
    return len(kampanyalar)


def reconstruct_missing_customers(sqlite_conn):
    """
    satislar tablosundaki musteri_id'leri musteriler tablosunda yoksa
    telefon ve onay_durumu ile stub kayıt oluşturur.
    SQL Server erişimi olmadan çalışır, lookup sync başarıyla çalışınca gerçek verilerle güncellenir.
    """
    cursor = sqlite_conn.cursor()
    ph = _ph()
    if DB_BACKEND == "postgresql":
        cursor.execute(f"""
            INSERT INTO musteriler (id, ad, telefon, tip, onay_durumu, kayit_tarihi)
            SELECT DISTINCT ON (musteri_id)
                musteri_id::bigint, NULL, telefon, NULL, onay_durumu,
                MIN(tarih) OVER (PARTITION BY musteri_id)
            FROM satislar
            WHERE musteri_id IS NOT NULL
            AND musteri_id NOT IN (SELECT id FROM musteriler)
            ORDER BY musteri_id, tarih
            ON CONFLICT (id) DO NOTHING
        """)
    else:
        cursor.execute("""
            INSERT OR IGNORE INTO musteriler (id, ad, telefon, tip, onay_durumu, kayit_tarihi)
            SELECT musteri_id, NULL, telefon, NULL, onay_durumu, MIN(tarih)
            FROM satislar
            WHERE musteri_id IS NOT NULL
            AND musteri_id NOT IN (SELECT id FROM musteriler)
            GROUP BY musteri_id
        """)
    count = cursor.rowcount
    sqlite_conn.commit()
    if count > 0:
        logger.warning(f"   ⚠️ {count} eksik müşteri satislar'dan reconstruct edildi (lookup sync bekliyor)")
    return count


def sync_musteriler(sql_cursor, sqlite_conn):
    """Müşterileri senkronize et"""
    logger.info("👥 Müşteriler senkronize ediliyor...")

    sql_cursor.execute("""
        SELECT
            [Müşteri Kodu],
            [Müsteri Adı],
            [telefon No],
            [Müşteri Tipi],
            [OnayDurumu],
            [Kayıt Tarihi],
            [IdentityNo]
        FROM M_PowerBimusteriler WITH (NOLOCK)
    """)

    musteriler = sql_cursor.fetchall()

    if not musteriler:
        logger.info("   - Müşteri verisi yok")
        return 0

    sqlite_cursor = sqlite_conn.cursor()

    batch_data = []
    for m in musteriler:
        batch_data.append((m[0], m[1], m[2], m[3], m[4], m[5], m[6]))

    if DB_BACKEND == "postgresql":
        sqlite_cursor.executemany("""
            INSERT INTO musteriler
            (id, ad, telefon, tip, onay_durumu, kayit_tarihi, kayit_magazasi)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                ad=EXCLUDED.ad, telefon=EXCLUDED.telefon, tip=EXCLUDED.tip, 
                onay_durumu=EXCLUDED.onay_durumu, kayit_tarihi=EXCLUDED.kayit_tarihi, 
                kayit_magazasi=EXCLUDED.kayit_magazasi
        """, batch_data)
    else:
        sqlite_cursor.executemany("""
            INSERT OR REPLACE INTO musteriler
            (id, ad, telefon, tip, onay_durumu, kayit_tarihi, kayit_magazasi)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch_data)

    sqlite_conn.commit()
    logger.info(f"   ✓ {len(musteriler)} müşteri işlendi")
    return len(musteriler)


# ================== ANA FONKSİYON ==================

def run_lookup_sync():
    """Lookup verilerini senkronize et"""

    # Lookup kendi kilidini kontrol eder (sales sync'ten bağımsız)
    if is_lookup_running():
        logger.warning("⚠️ Lookup sync zaten çalışıyor, atlanıyor.")
        return False

    if not acquire_lock(SyncType.LOOKUP):
        logger.error("❌ Lookup kilidi alınamadı!")
        return False

    logger.info("=" * 60)
    logger.info("🚀 LOOKUP SYNC BAŞLADI")
    logger.info("=" * 60)

    start_time = datetime.now()
    success = False

    sqlite_conn = None
    sql_conn = None
    try:
        # Şemayı oluştur
        create_schema()

        # Bağlantılar
        sqlite_conn = get_connection()
        sql_conn = connect_sql()
        sql_cursor = sql_conn.cursor()

        # Senkronizasyon
        stats = {
            'satinalmacilar': sync_satinalmacilar(sql_cursor, sqlite_conn),
            'markalar': sync_markalar(sql_cursor, sqlite_conn),
            'kategoriler': sync_kategoriler(sql_cursor, sqlite_conn),
            'magazalar': sync_magazalar(sql_cursor, sqlite_conn),
            'urunler': sync_urunler(sql_cursor, sqlite_conn),
            'kampanyalar': sync_kampanyalar(sql_cursor, sqlite_conn),
            'musteriler': sync_musteriler(sql_cursor, sqlite_conn)
        }

        # Meta güncelle
        sqlite_cursor = sqlite_conn.cursor()
        if DB_BACKEND == "postgresql":
            sqlite_cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_lookup_sync', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (datetime.now().isoformat(),))
        else:
            sqlite_cursor.execute("""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_lookup_sync', ?, datetime('now'))
            """, (datetime.now().isoformat(),))
        sqlite_conn.commit()

        elapsed = datetime.now() - start_time
        logger.info("=" * 60)
        logger.info(f"✅ LOOKUP SYNC TAMAMLANDI - Süre: {elapsed}")
        logger.info(f"   Özet: {stats}")
        logger.info("=" * 60)

        success = True

    except Exception as e:
        logger.error(f"❌ LOOKUP SYNC HATASI: {e}", exc_info=True)
        # Hata detayını syncmeta'ya yaz ve orphan müşterileri reconstruct et
        try:
            err_conn = get_connection()
            err_cur = err_conn.cursor()
            err_msg = f"{type(e).__name__}: {str(e)[:500]}"
            if DB_BACKEND == "postgresql":
                err_cur.execute("""
                    INSERT INTO syncmeta (key, value, updated_at)
                    VALUES ('last_lookup_sync_error', %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
                """, (err_msg,))
            else:
                err_cur.execute("""
                    INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                    VALUES ('last_lookup_sync_error', ?, datetime('now'))
                """, (err_msg,))
            err_conn.commit()
            # SQL Server bağlantısı başarısız olsa bile satislar'daki orphan müşterileri kurtarmayı dene
            reconstruct_missing_customers(err_conn)
            err_conn.close()
        except Exception:
            pass

    finally:
        try:
            if sql_conn:
                sql_conn.close()
        except Exception:
            pass
        try:
            if sqlite_conn:
                sqlite_conn.close()
        except Exception:
            pass
        release_lock(SyncType.LOOKUP)

    return success


if __name__ == "__main__":
    run_lookup_sync()
