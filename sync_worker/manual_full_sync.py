"""
Manuel Tam Veri Çekme Scripti (Tek Seferlik)
=============================================
SQL Server'dan tüm verileri çeker ve PostgreSQL'e yazar.
Ardından tüm özet tabloları sıfırdan oluşturur.

Kullanım:
  cd sync_worker
  python manual_full_sync.py

Adımlar:
  1. Lookup Sync (markalar, kategoriler, mağazalar, ürünler, kampanyalar, müşteriler)
  2. Satış Sync (ay ay, tutarlılık kontrolüyle)
  3. Özet Tabloları Rebuild (tüm günler için)
  4. BrandSummary + GlobalStats Rebuild
  5. Doğrulama Raporu
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Imports
import pyodbc
from models import get_connection, create_schema, DB_BACKEND
from decouple import config

# Logging
LOG_FILE = os.path.join(BASE_DIR, 'manual_full_sync.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SQL Server config
SQL_SERVER_CONFIG = {
    'server': config('SQL_SERVER', default='100.109.143.127'),
    'port': config('SQL_PORT', default='14330'),
    'database': config('SQL_DATABASE', default='DerinSISShow'),
    'username': config('SQL_USERNAME', default='sa2'),
    'password': config('SQL_PASSWORD', default='1478236950Mm..'),
    'drivers': [
        '{ODBC Driver 18 for SQL Server}',
        '{ODBC Driver 17 for SQL Server}',
        '{SQL Server Native Client 11.0}',
        '{SQL Server}'
    ]
}


def get_driver():
    available = pyodbc.drivers()
    for d in SQL_SERVER_CONFIG['drivers']:
        if d.strip('{}') in available:
            return d
    return '{SQL Server}'


def connect_sql():
    driver = get_driver()
    conn_str = (
        f"DRIVER={driver};"
        f"SERVER={SQL_SERVER_CONFIG['server']},{SQL_SERVER_CONFIG['port']};"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"UID={SQL_SERVER_CONFIG['username']};"
        f"PWD={SQL_SERVER_CONFIG['password']};"
        f"Network=DBMSSOCN;Encrypt=no;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=300, autocommit=True)


def pg_conn():
    """PostgreSQL bağlantısı al"""
    return get_connection()



# ================== LOOKUP SYNC ==================

def sync_markalar(sql_cursor, pg):
    logger.info("📦 Markalar senkronize ediliyor...")
    sql_cursor.execute("""
        SELECT DISTINCT [MarkaAdi] FROM M_Crm WITH (NOLOCK)
        WHERE [MarkaAdi] IS NOT NULL AND [MarkaAdi] <> ''
    """)
    markalar = [row[0] for row in sql_cursor.fetchall()]
    cur = pg.cursor()
    # Mevcut markaları al, sadece yeni olanları ekle
    cur.execute("SELECT ad FROM markalar")
    existing = {row[0] for row in cur.fetchall()}
    new_count = 0
    for marka in markalar:
        if marka not in existing:
            cur.execute("INSERT INTO markalar (ad) VALUES (%s)", (marka,))
            new_count += 1
    pg.commit()
    logger.info(f"   ✓ {len(markalar)} marka ({new_count} yeni) işlendi")
    return len(markalar)


def sync_satinalmacilar(sql_cursor, pg):
    logger.info("👥 Kategori yöneticileri senkronize ediliyor...")
    sql_cursor.execute("""
        SELECT DISTINCT [ktgrGrupAd] FROM M_Crm WITH (NOLOCK)
        WHERE [ktgrGrupAd] IS NOT NULL AND [ktgrGrupAd] <> ''
    """)
    yoneticiler = [row[0] for row in sql_cursor.fetchall()]
    cur = pg.cursor()

    cur.execute("SELECT ad FROM kategori_yoneticileri")
    existing = {row[0] for row in cur.fetchall()}

    new_count = 0
    for y in yoneticiler:
        if y not in existing:
            cur.execute("INSERT INTO kategori_yoneticileri (ad) VALUES (%s)", (y,))
            new_count += 1

    pg.commit()
    logger.info(f"   ✓ {len(yoneticiler)} kategori yöneticisi ({new_count} yeni) işlendi")
    return len(yoneticiler)


def sync_kategoriler(sql_cursor, pg):
    logger.info("📦 Kategoriler senkronize ediliyor...")
    sql_cursor.execute("""
        SELECT DISTINCT [Ana_Kategori], [Alt_Kategori1], [Alt_Kategori2]
        FROM M_Crm WITH (NOLOCK)
        WHERE [Ana_Kategori] IS NOT NULL
    """)
    kategoriler = sql_cursor.fetchall()

    # Ana kategori → en çok tekrar eden ktgrGrupAd eşleşmesi
    sql_cursor.execute("""
        SELECT [Ana_Kategori], [ktgrGrupAd], COUNT(*) as cnt
        FROM M_Crm WITH (NOLOCK)
        WHERE [Ana_Kategori] IS NOT NULL AND [ktgrGrupAd] IS NOT NULL AND [ktgrGrupAd] <> ''
        GROUP BY [Ana_Kategori], [ktgrGrupAd]
        ORDER BY [Ana_Kategori], cnt DESC
    """)
    kat_yonetici_map = {}
    for row in sql_cursor.fetchall():
        ana = row[0]
        if ana not in kat_yonetici_map:
            kat_yonetici_map[ana] = row[1]

    cur = pg.cursor()

    # Kategori yöneticisi map
    cur.execute("SELECT id, ad FROM kategori_yoneticileri")
    yonetici_map = {row[1]: row[0] for row in cur.fetchall()}

    # Mevcut kategorileri al
    cur.execute("SELECT ana, alt1, alt2 FROM kategoriler")
    existing = {(row[0], row[1], row[2]) for row in cur.fetchall()}
    new_count = 0
    for kat in kategoriler:
        key = (kat[0], kat[1], kat[2])
        yonetici_ad = kat_yonetici_map.get(kat[0])
        yonetici_id = yonetici_map.get(yonetici_ad) if yonetici_ad else None
        if key not in existing:
            cur.execute(
                "INSERT INTO kategoriler (ana, alt1, alt2, yonetici_id) VALUES (%s, %s, %s, %s)",
                (kat[0], kat[1], kat[2], yonetici_id)
            )
            new_count += 1
        elif yonetici_id is not None:
            cur.execute(
                "UPDATE kategoriler SET yonetici_id=%s WHERE ana=%s AND alt1 IS NOT DISTINCT FROM %s AND alt2 IS NOT DISTINCT FROM %s",
                (yonetici_id, kat[0], kat[1], kat[2])
            )
    pg.commit()
    logger.info(f"   ✓ {len(kategoriler)} kategori ({new_count} yeni) işlendi")
    return len(kategoriler)


def sync_magazalar(sql_cursor, pg):
    logger.info("📦 Mağazalar senkronize ediliyor...")
    sql_cursor.execute("""
        SELECT DISTINCT [Magaza], [Alt_Kategori3]
        FROM M_Crm WITH (NOLOCK)
        WHERE [Magaza] IS NOT NULL
    """)
    magazalar = sql_cursor.fetchall()
    cur = pg.cursor()
    cur.execute("SELECT ad FROM magazalar")
    existing = {row[0] for row in cur.fetchall()}
    new_count = 0
    for mag in magazalar:
        if mag[0] not in existing:
            cur.execute("INSERT INTO magazalar (ad, bolge) VALUES (%s, %s)", (mag[0], mag[1]))
            new_count += 1
    pg.commit()
    logger.info(f"   ✓ {len(magazalar)} mağaza ({new_count} yeni) işlendi")
    return len(magazalar)


def sync_urunler(sql_cursor, pg):
    logger.info("📦 Ürünler senkronize ediliyor...")
    sql_cursor.execute("""
        SELECT DISTINCT [stkKod], [stkAd], [MarkaAdi], [Ana_Kategori], [Alt_Kategori1], [Alt_Kategori2], [ktgrGrupAd]
        FROM M_Crm WITH (NOLOCK)
        WHERE [stkKod] IS NOT NULL
    """)
    urunler = sql_cursor.fetchall()
    cur = pg.cursor()
    
    # Marka map
    cur.execute("SELECT id, ad FROM markalar")
    marka_map = {row[1]: row[0] for row in cur.fetchall()}
    
    # Kategori yöneticisi map
    cur.execute("SELECT id, ad FROM kategori_yoneticileri")
    satinalmaci_map = {row[1]: row[0] for row in cur.fetchall()}
    
    # Kategori map
    cur.execute("SELECT id, ana, alt1, alt2 FROM kategoriler")
    kategori_map = {}
    for row in cur.fetchall():
        kategori_map[(row[1], row[2], row[3])] = row[0]
    
    # Mevcut ürünleri al
    cur.execute("SELECT kod FROM urunler")
    existing = {row[0] for row in cur.fetchall()}
    
    count = 0
    new_count = 0
    for urun in urunler:
        count += 1
        if urun[0] in existing:
            continue
        
        marka_id = marka_map.get(urun[2])
        yonetici_id_urun = satinalmaci_map.get(urun[6])
        kategori_key = (urun[3], urun[4], urun[5])
        kategori_id = kategori_map.get(kategori_key)
        if not kategori_id:
            kategori_id = kategori_map.get((urun[3], urun[4], None))
        if not kategori_id:
            kategori_id = kategori_map.get((urun[3], None, None))

        cur.execute("""
            INSERT INTO urunler (kod, ad, marka_id, kategori_id, yonetici_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (urun[0], urun[1], marka_id, kategori_id, yonetici_id_urun))
        new_count += 1
    
    pg.commit()
    logger.info(f"   ✓ {count} ürün ({new_count} yeni) işlendi")
    return count


def sync_kampanyalar(sql_cursor, pg):
    logger.info("📦 Kampanyalar senkronize ediliyor...")
    sql_cursor.execute("""
        SELECT DISTINCT [kmp_sayısı], [kmp_ad], [basla], [bitis]
        FROM M_Crm WITH (NOLOCK)
        WHERE [kmp_sayısı] IS NOT NULL
    """)
    kampanyalar = sql_cursor.fetchall()
    cur = pg.cursor()
    for kmp in kampanyalar:
        cur.execute("""
            INSERT INTO kampanyalar (id, ad, baslangic, bitis)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET ad=EXCLUDED.ad, baslangic=EXCLUDED.baslangic, bitis=EXCLUDED.bitis
        """, (kmp[0], kmp[1], kmp[2], kmp[3]))
    pg.commit()
    logger.info(f"   ✓ {len(kampanyalar)} kampanya işlendi")
    return len(kampanyalar)


def sync_musteriler(sql_cursor, pg):
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
    
    batch_data = [(m[0], m[1], m[2], m[3], m[4], m[5], m[6]) for m in musteriler]
    cur = pg.cursor()
    
    from psycopg2.extras import execute_batch
    execute_batch(cur, """
        INSERT INTO musteriler
        (id, ad, telefon, tip, onay_durumu, kayit_tarihi, kayit_magazasi)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            ad=EXCLUDED.ad, telefon=EXCLUDED.telefon, tip=EXCLUDED.tip,
            onay_durumu=EXCLUDED.onay_durumu, kayit_tarihi=EXCLUDED.kayit_tarihi,
            kayit_magazasi=EXCLUDED.kayit_magazasi
    """, batch_data, page_size=5000)
    pg.commit()
    logger.info(f"   ✓ {len(musteriler)} müşteri işlendi")
    return len(musteriler)


# ================== SATIŞ SYNC ==================

def sync_month_sales(sql_cursor, pg, year, month):
    """Belirli ayın satış verilerini SQL Server'dan çekip PostgreSQL'e yaz"""
    month_name = f"{year}-{month:02d}"
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    cur = pg.cursor()
    
    # Lookup map'leri al
    cur.execute("SELECT id, ad FROM magazalar")
    magaza_map = {row[1]: row[0] for row in cur.fetchall()}
    
    cur.execute("SELECT id, kod, kategori_id, marka_id FROM urunler")
    urun_map = {row[1]: (row[0], row[2], row[3]) for row in cur.fetchall()}
    
    # SQL Server'dan veri çek
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
            ROW_NUMBER() OVER (PARTITION BY [PosDocumentId] ORDER BY [stkKod], [kmp_sayısı]) as SatirNo
        FROM M_Crm WITH (NOLOCK)
        WHERE [TARİH] >= '{start_date}' AND [TARİH] < '{end_date}'
    """)
    
    rows = sql_cursor.fetchall()
    if not rows:
        logger.info(f"   {month_name}: Veri yok")
        return 0
    
    # Önce eski veriyi sil (clean sync)
    cur.execute("DELETE FROM satislar WHERE TO_CHAR(tarih, 'YYYY-MM') = %s", (month_name,))
    pg.commit()
    
    # Batch insert
    batch_data = []
    for row in rows:
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
            m_id
        ))
    
    from psycopg2.extras import execute_values
    # DELETE ile temizledik, ON CONFLICT gereksiz - direkt insert
    execute_values(cur, """
        INSERT INTO satislar
        (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, belge_tipi, kampanya_id, telefon, onay_durumu, satir_no, kategori_id, marka_id)
        VALUES %s
    """, batch_data, page_size=10000)
    pg.commit()
    
    return len(batch_data)


def verify_month(sql_cursor, pg, year, month):
    """Ay tutarlılık kontrolü"""
    month_name = f"{year}-{month:02d}"
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    sql_cursor.execute(f"""
        SELECT COUNT(*) as cnt, ISNULL(SUM([Satış Tutarı]), 0) as ciro
        FROM M_Crm WITH (NOLOCK)
        WHERE [TARİH] >= '{start_date}' AND [TARİH] < '{end_date}'
    """)
    sql_row = sql_cursor.fetchone()
    
    cur = pg.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(tutar), 0) FROM satislar WHERE TO_CHAR(tarih, 'YYYY-MM') = %s", (month_name,))
    pg_row = cur.fetchone()
    
    sql_count, sql_ciro = sql_row[0], float(sql_row[1])
    pg_count, pg_ciro = pg_row[0], float(pg_row[1])
    
    kayit_diff = abs(sql_count - pg_count)
    ciro_diff = abs(sql_ciro - pg_ciro)
    is_ok = ciro_diff < 1.0  # 1 TL tolerans
    
    return {
        'month': month_name,
        'sql_count': sql_count, 'pg_count': pg_count,
        'sql_ciro': sql_ciro, 'pg_ciro': pg_ciro,
        'kayit_diff': kayit_diff, 'ciro_diff': ciro_diff,
        'is_ok': is_ok
    }


# ================== ÖZET REBUILD ==================

def rebuild_daily_summaries(pg):
    """Tüm günler için özet tabloları yeniden hesapla (Checkpoint destekli)"""
    cur = pg.cursor()
    
    # Tüm benzersiz tarihleri al
    cur.execute("SELECT DISTINCT tarih FROM satislar ORDER BY tarih")
    dates = [row[0] for row in cur.fetchall()]
    
    total = len(dates)
    
    # Checkpoint kontrol — kaldığı yerden devam
    checkpoint_date = None
    try:
        cur.execute("SELECT value FROM syncmeta WHERE key = 'rebuild_daily_checkpoint'")
        row = cur.fetchone()
        if row:
            checkpoint_date = row[0]
            logger.info(f"📌 Checkpoint bulundu: {checkpoint_date} — kaldığı yerden devam ediliyor")
    except:
        pass
    
    # Checkpoint'ten sonraki tarihleri filtrele
    if checkpoint_date:
        original_total = total
        dates = [d for d in dates if (d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)) > checkpoint_date]
        total_remaining = len(dates)
        logger.info(f"📊 {total_remaining}/{original_total} gün kaldı (ilk {original_total - total_remaining} gün zaten tamamlanmış)")
        total = len(dates)
    else:
        logger.info(f"📊 {total} gün için özet tabloları hesaplanacak...")
    
    if total == 0:
        logger.info("   ✅ Tüm günlük özetler zaten tamamlanmış!")
        return 0
    
    start_time = time.time()
    updated = 0
    errors = 0
    
    for i, d in enumerate(dates):
        target_date = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
        try:
            # 1. GunlukCiroOzet
            update_gunluk_ciro_ozet(pg, target_date)
            # 2. MagazaGunlukOzet
            update_magaza_gunluk_ozet(pg, target_date)
            # 3. CrmOzet
            update_crm_ozet(pg, target_date)
            # 4. DailyMetricsSummary
            update_daily_metrics(pg, target_date)
            # 5. GunlukOzet (detaylı)
            update_gunluk_ozet_detay(pg, target_date)
            # 6. ProductDailySummary
            update_product_daily_summary(pg, target_date)
            
            pg.commit()
            updated += 1
            
            # Her 10 günde bir checkpoint kaydet
            if (i + 1) % 10 == 0:
                cur.execute("""
                    INSERT INTO syncmeta (key, value, updated_at)
                    VALUES ('rebuild_daily_checkpoint', %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
                """, (target_date,))
                pg.commit()
            
            if (i + 1) % 50 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate if rate > 0 else 0
                logger.info(f"   İlerleme: {i+1}/{total} ({(i+1)/total*100:.1f}%) - Hız: {rate:.1f} gün/s - Kalan: {remaining:.0f}s")
        
        except Exception as e:
            errors += 1
            logger.error(f"   ❌ Özet hatası ({target_date}): {e}")
            try:
                pg.rollback()
            except:
                pass
    
    # Tamamlandı — checkpoint'i temizle
    try:
        cur.execute("DELETE FROM syncmeta WHERE key = 'rebuild_daily_checkpoint'")
        pg.commit()
    except:
        pass
    
    elapsed = time.time() - start_time
    logger.info(f"   ✅ Günlük özetler tamamlandı: {updated}/{total} gün ({elapsed:.1f}s, {errors} hata)")
    return updated


def rebuild_monthly_summaries(pg):
    """Ay bazlı özet tabloları yeniden hesapla"""
    cur = pg.cursor()
    
    # Tüm benzersiz ayları al
    cur.execute("SELECT DISTINCT TO_CHAR(tarih, 'YYYY-MM') as ay FROM satislar ORDER BY ay")
    months = [row[0] for row in cur.fetchall()]
    
    logger.info(f"📊 {len(months)} ay için aylık özetler hesaplanacak...")
    
    for m in months:
        try:
            # Bir ayın ilk gününü kullan (tarihe dayalı fonksiyonlar için)
            first_day = f"{m}-01"
            
            # KategoriKarsilastirma
            update_kategori_karsilastirma(pg, first_day, m)
            # MarkaKarsilastirma
            update_marka_karsilastirma(pg, first_day, m)
            # KampanyaOzet
            update_kampanya_ozet(pg, first_day, m)
            # GenelOzet
            update_genel_ozet(pg, first_day, m)
            # MusteriSadakat
            update_musteri_sadakat(pg, first_day, m)
            
            pg.commit()
            logger.info(f"   ✓ {m} aylık özet tamamlandı")
        except Exception as e:
            logger.error(f"   ❌ Aylık özet hatası ({m}): {e}")
            try:
                pg.rollback()
            except:
                pass
    
    logger.info(f"   ✅ Aylık özetler tamamlandı")


# ================== ÖZET HESAPLAMA FONKSİYONLARI ==================

def update_gunluk_ciro_ozet(pg, target_date):
    cur = pg.cursor()
    cur.execute("""
        SELECT
            COALESCE(SUM(tutar), 0), COUNT(DISTINCT fis_no), COUNT(DISTINCT musteri_id),
            COALESCE(SUM(miktar), 0), COUNT(DISTINCT urun_id)
        FROM satislar WHERE tarih = %s
    """, (target_date,))
    row = cur.fetchone()
    t_ciro, t_fis, t_must, t_mikt, sku_s = row[0] or 0, row[1] or 0, row[2] or 0, row[3] or 0, row[4] or 0
    s_ort = t_ciro / t_fis if t_fis > 0 else 0
    m_ciro = t_ciro / t_must if t_must > 0 else 0
    m_fis = t_fis / t_must if t_must > 0 else 0
    
    cur.execute("""
        INSERT INTO gunlukciroozet
        (tarih, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar,
         sepet_ortalamasi, musteri_basina_ciro, musteri_basina_fis, sku_sayisi, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (tarih) DO UPDATE SET
            toplam_ciro=EXCLUDED.toplam_ciro, toplam_fis=EXCLUDED.toplam_fis,
            toplam_musteri=EXCLUDED.toplam_musteri, toplam_miktar=EXCLUDED.toplam_miktar,
            sepet_ortalamasi=EXCLUDED.sepet_ortalamasi, musteri_basina_ciro=EXCLUDED.musteri_basina_ciro,
            musteri_basina_fis=EXCLUDED.musteri_basina_fis, sku_sayisi=EXCLUDED.sku_sayisi,
            updated_at=CURRENT_TIMESTAMP
    """, (target_date, t_ciro, t_fis, t_must, t_mikt, s_ort, m_ciro, m_fis, sku_s))


def update_magaza_gunluk_ozet(pg, target_date):
    cur = pg.cursor()
    cur.execute("""
        SELECT magaza_id, COALESCE(SUM(tutar), 0), COUNT(DISTINCT fis_no),
               COUNT(DISTINCT musteri_id), COALESCE(SUM(miktar), 0), COUNT(DISTINCT urun_id)
        FROM satislar WHERE tarih = %s AND magaza_id IS NOT NULL GROUP BY magaza_id
    """, (target_date,))
    rows = cur.fetchall()
    if not rows:
        return
    final_rows = []
    for row in rows:
        s_ort = row[1] / row[2] if row[2] > 0 else 0
        final_rows.append((target_date, row[0], row[1], row[2], row[3], row[4], s_ort, row[5]))
    
    from psycopg2.extras import execute_values
    execute_values(cur, """
        INSERT INTO magazagunlukozet
        (tarih, magaza_id, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar, sepet_ortalamasi, sku_sayisi)
        VALUES %s
        ON CONFLICT (tarih, magaza_id) DO UPDATE SET
            toplam_ciro=EXCLUDED.toplam_ciro, toplam_fis=EXCLUDED.toplam_fis,
            toplam_musteri=EXCLUDED.toplam_musteri, toplam_miktar=EXCLUDED.toplam_miktar,
            sepet_ortalamasi=EXCLUDED.sepet_ortalamasi, sku_sayisi=EXCLUDED.sku_sayisi
    """, final_rows)


def update_crm_ozet(pg, target_date):
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO crmozet (tarih, ay, magaza_id, kategori_id, marka_id, toplam_ciro, toplam_fis, toplam_musteri, toplam_miktar, sepet_ort)
        SELECT 
            tarih,
            TO_CHAR(tarih, 'YYYY-MM') as ay,
            COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0),
            SUM(tutar), COUNT(DISTINCT fis_no), COUNT(DISTINCT musteri_id), SUM(miktar),
            CASE WHEN COUNT(DISTINCT fis_no) > 0 THEN SUM(tutar) / COUNT(DISTINCT fis_no) ELSE 0 END
        FROM satislar WHERE CAST(tarih AS DATE) = %s
        GROUP BY tarih, TO_CHAR(tarih, 'YYYY-MM'), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0)
        ON CONFLICT (tarih, magaza_id, kategori_id, marka_id) DO UPDATE SET
            toplam_ciro=EXCLUDED.toplam_ciro, toplam_fis=EXCLUDED.toplam_fis,
            toplam_musteri=EXCLUDED.toplam_musteri, toplam_miktar=EXCLUDED.toplam_miktar, sepet_ort=EXCLUDED.sepet_ort
    """, (target_date,))


def update_daily_metrics(pg, target_date):
    cur = pg.cursor()
    cur.execute("""
        SELECT 
            s.tarih, COALESCE(s.magaza_id, 0), COALESCE(s.kategori_id, 0), COALESCE(s.marka_id, 0),
            COALESCE(m.tip, 'Bilinmiyor'), COALESCE(mdo.rfm_segment, 'Diğer'), COALESCE(s.onay_durumu, 'Bilinmiyor'),
            SUM(s.tutar), COUNT(DISTINCT s.fis_no), COUNT(DISTINCT s.musteri_id), SUM(s.miktar)
        FROM satislar s
        LEFT JOIN musteriler m ON s.musteri_id = m.id
        LEFT JOIN musteridetayozet mdo ON s.musteri_id = mdo.musteri_id
        WHERE s.tarih = %s
        GROUP BY s.tarih, COALESCE(s.magaza_id, 0), COALESCE(s.kategori_id, 0), COALESCE(s.marka_id, 0),
                 COALESCE(m.tip, 'Bilinmiyor'), COALESCE(mdo.rfm_segment, 'Diğer'), COALESCE(s.onay_durumu, 'Bilinmiyor')
    """, (target_date,))
    rows = cur.fetchall()
    if not rows:
        return
    
    from psycopg2.extras import execute_values
    execute_values(cur, """
        INSERT INTO daily_metrics_summary (
            tarih, magaza_id, kategori_id, marka_id, customer_type,
            rfm_segment, onay_durumu, revenue, receipt_count,
            customer_count, unit_count
        ) VALUES %s
        ON CONFLICT (tarih, magaza_id, kategori_id, marka_id, customer_type, rfm_segment, onay_durumu)
        DO UPDATE SET
            revenue=EXCLUDED.revenue, receipt_count=EXCLUDED.receipt_count,
            customer_count=EXCLUDED.customer_count, unit_count=EXCLUDED.unit_count
    """, rows)


def update_product_daily_summary(pg, target_date):
    """Ürün bazlı günlük özet tablosunu güncelle"""
    cur = pg.cursor()
    cur.execute("DELETE FROM product_daily_summary WHERE tarih = %s", (target_date,))
    cur.execute("""
        INSERT INTO product_daily_summary
        (tarih, urun_id, revenue, unit_count, customer_count, receipt_count)
        SELECT 
            tarih, urun_id, 
            SUM(tutar), SUM(miktar), COUNT(DISTINCT musteri_id), COUNT(DISTINCT fis_no)
        FROM satislar
        WHERE tarih = %s AND urun_id IS NOT NULL
        GROUP BY tarih, urun_id
    """, (target_date,))


def update_gunluk_ozet_detay(pg, target_date):
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO gunlukozet 
        (tarih, magaza_id, kategori_id, marka_id, toplam_ciro, fis_sayisi, musteri_sayisi, urun_adedi)
        SELECT 
            CAST(tarih AS DATE), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0),
            SUM(tutar), COUNT(DISTINCT fis_no), COUNT(DISTINCT musteri_id), SUM(miktar)
        FROM satislar WHERE CAST(tarih AS DATE) = %s
        GROUP BY CAST(tarih AS DATE), COALESCE(magaza_id, 0), COALESCE(kategori_id, 0), COALESCE(marka_id, 0)
        ON CONFLICT (tarih, magaza_id, kategori_id, marka_id) DO UPDATE SET
            toplam_ciro=EXCLUDED.toplam_ciro, fis_sayisi=EXCLUDED.fis_sayisi,
            musteri_sayisi=EXCLUDED.musteri_sayisi, urun_adedi=EXCLUDED.urun_adedi
    """, (target_date,))


def update_kategori_karsilastirma(pg, first_day, month_str):
    cur = pg.cursor()
    cur.execute("DELETE FROM kategorikarsilastirma WHERE ay = %s", (month_str,))
    cur.execute("""
        INSERT INTO kategorikarsilastirma 
        (ay, kategori, toplam_ciro, crm_ciro, anonim_ciro, crm_fis, anonim_fis, crm_sepet_ort, anonim_sepet_ort)
        SELECT 
            TO_CHAR(s.tarih, 'YYYY-MM') as ay,
            k.ana as kategori,
            SUM(s.tutar),
            SUM(CASE WHEN s.musteri_id IS NOT NULL THEN s.tutar ELSE 0 END),
            SUM(CASE WHEN s.musteri_id IS NULL THEN s.tutar ELSE 0 END),
            COUNT(DISTINCT CASE WHEN s.musteri_id IS NOT NULL THEN s.fis_no END),
            COUNT(DISTINCT CASE WHEN s.musteri_id IS NULL THEN s.fis_no END),
            0, 0
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        JOIN kategoriler k ON u.kategori_id = k.id
        WHERE TO_CHAR(s.tarih, 'YYYY-MM') = %s
        GROUP BY TO_CHAR(s.tarih, 'YYYY-MM'), k.ana
    """, (month_str,))
    cur.execute("""
        UPDATE kategorikarsilastirma SET
            crm_sepet_ort = CASE WHEN crm_fis > 0 THEN crm_ciro / crm_fis ELSE 0 END,
            anonim_sepet_ort = CASE WHEN anonim_fis > 0 THEN anonim_ciro / anonim_fis ELSE 0 END
        WHERE ay = %s
    """, (month_str,))


def update_marka_karsilastirma(pg, first_day, month_str):
    cur = pg.cursor()
    cur.execute("DELETE FROM markakarsilastirma WHERE ay = %s", (month_str,))
    cur.execute("""
        INSERT INTO markakarsilastirma
        (ay, marka, toplam_ciro, crm_ciro, crm_musteri)
        SELECT
            TO_CHAR(s.tarih, 'YYYY-MM'),
            m.ad,
            SUM(s.tutar),
            SUM(CASE WHEN s.musteri_id IS NOT NULL THEN s.tutar ELSE 0 END),
            COUNT(DISTINCT s.musteri_id)
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        JOIN markalar m ON u.marka_id = m.id
        WHERE TO_CHAR(s.tarih, 'YYYY-MM') = %s
        GROUP BY TO_CHAR(s.tarih, 'YYYY-MM'), m.ad
    """, (month_str,))


def update_kampanya_ozet(pg, first_day, month_str):
    cur = pg.cursor()
    cur.execute("DELETE FROM kampanyaozet WHERE ay = %s", (month_str,))
    cur.execute("""
        INSERT INTO kampanyaozet
        (ay, kampanya_id, kampanya_ad, katilim_sayisi, toplam_ciro, benzersiz_musteri)
        SELECT
            TO_CHAR(s.tarih, 'YYYY-MM'),
            s.kampanya_id, k.ad,
            COUNT(*), SUM(s.tutar), COUNT(DISTINCT s.musteri_id)
        FROM satislar s
        JOIN kampanyalar k ON s.kampanya_id = k.id
        WHERE TO_CHAR(s.tarih, 'YYYY-MM') = %s AND s.kampanya_id IS NOT NULL
        GROUP BY TO_CHAR(s.tarih, 'YYYY-MM'), s.kampanya_id, k.ad
    """, (month_str,))


def update_genel_ozet(pg, first_day, month_str):
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO genelozet
        (ay, magaza_id, toplam_ciro, toplam_fis, toplam_miktar, 
         crm_ciro, crm_fis, crm_musteri, crm_miktar,
         anonim_ciro, anonim_fis,
         crm_sepet_ort, anonim_sepet_ort, crm_oran_ciro, crm_oran_fis)
        SELECT
            TO_CHAR(tarih, 'YYYY-MM'),
            COALESCE(magaza_id, 0),
            SUM(tutar), COUNT(DISTINCT fis_no), SUM(miktar),
            SUM(CASE WHEN musteri_id IS NOT NULL THEN tutar ELSE 0 END),
            COUNT(DISTINCT CASE WHEN musteri_id IS NOT NULL THEN fis_no END),
            COUNT(DISTINCT musteri_id),
            SUM(CASE WHEN musteri_id IS NOT NULL THEN miktar ELSE 0 END),
            SUM(CASE WHEN musteri_id IS NULL THEN tutar ELSE 0 END),
            COUNT(DISTINCT CASE WHEN musteri_id IS NULL THEN fis_no END),
            0, 0, 0, 0
        FROM satislar
        WHERE TO_CHAR(tarih, 'YYYY-MM') = %s
        GROUP BY TO_CHAR(tarih, 'YYYY-MM'), COALESCE(magaza_id, 0)
        ON CONFLICT (ay, magaza_id) DO UPDATE SET
            toplam_ciro=EXCLUDED.toplam_ciro, toplam_fis=EXCLUDED.toplam_fis,
            toplam_miktar=EXCLUDED.toplam_miktar, crm_ciro=EXCLUDED.crm_ciro,
            crm_fis=EXCLUDED.crm_fis, crm_musteri=EXCLUDED.crm_musteri,
            crm_miktar=EXCLUDED.crm_miktar, anonim_ciro=EXCLUDED.anonim_ciro,
            anonim_fis=EXCLUDED.anonim_fis
    """, (month_str,))
    
    cur.execute("""
        UPDATE genelozet SET
            crm_sepet_ort = CASE WHEN crm_fis > 0 THEN crm_ciro / crm_fis ELSE 0 END,
            anonim_sepet_ort = CASE WHEN anonim_fis > 0 THEN anonim_ciro / anonim_fis ELSE 0 END,
            crm_oran_ciro = CASE WHEN toplam_ciro > 0 THEN (crm_ciro / toplam_ciro) * 100 ELSE 0 END,
            crm_oran_fis = CASE WHEN toplam_fis > 0 THEN (crm_fis * 1.0 / toplam_fis) * 100 ELSE 0 END
        WHERE ay = %s
    """, (month_str,))


def update_musteri_sadakat(pg, first_day, month_str):
    cur = pg.cursor()
    cur.execute("DELETE FROM musterisadakat WHERE ay = %s", (month_str,))
    cur.execute("""
        INSERT INTO musterisadakat (ay, yeni_musteri, tekrar_musteri, kayip_musteri, yeni_musteri_sepet, tekrar_musteri_sepet)
        SELECT
            %s as ay,
            (SELECT COUNT(*) FROM musteriler WHERE TO_CHAR(kayit_tarihi, 'YYYY-MM') = %s) as yeni,
            (SELECT COUNT(DISTINCT s.musteri_id) 
             FROM satislar s 
             JOIN musteriler m ON s.musteri_id = m.id 
             WHERE TO_CHAR(s.tarih, 'YYYY-MM') = %s AND TO_CHAR(m.kayit_tarihi, 'YYYY-MM') < %s) as tekrar,
             0, 0, 0
    """, (month_str, month_str, month_str, month_str))


def rebuild_brand_summary(pg):
    """brandsummary tablosunu tümüyle yeniden oluştur"""
    cur = pg.cursor()
    logger.info("📊 BrandSummary tablosu oluşturuluyor...")
    start_time = time.time()
    
    def tr_lower(s):
        if s is None: return ""
        if not isinstance(s, str): s = str(s)
        s = s.strip().replace('\xa0', ' ')
        s = s.replace('İ', 'i').replace('I', 'ı')
        s = s.lower()
        for search, replace in {'ç': 'c', 'ğ': 'g', 'ö': 'o', 'ş': 's', 'ü': 'u', 'ı': 'i'}.items():
            s = s.replace(search, replace)
        return s
    
    cur.execute("DROP TABLE IF EXISTS brandsummary")
    cur.execute("""
        CREATE TABLE brandsummary (
            brand_id INTEGER, brand_name TEXT, year INTEGER, month INTEGER,
            region TEXT, customer_type TEXT, segment TEXT, approval_status TEXT,
            category_id INTEGER, category_main TEXT, category_sub1 TEXT, category_sub2 TEXT,
            total_sales DOUBLE PRECISION, total_units DOUBLE PRECISION, customer_count INTEGER,
            brand_name_norm TEXT, region_norm TEXT, customer_type_norm TEXT,
            approval_status_norm TEXT, segment_norm TEXT, category_norm TEXT,
            category_sub1_norm TEXT, category_sub2_norm TEXT
        )
    """)
    pg.commit()
    
    cur.execute("""
        SELECT 
            u.marka_id, m.ad,
            TO_CHAR(s.tarih, 'YYYY') as year, TO_CHAR(s.tarih, 'MM') as month,
            COALESCE(mg.bolge, 'Diğer'), COALESCE(mu.tip, 'Bilinmiyor'),
            COALESCE(mdo.rfm_segment, 'Diğer'), COALESCE(s.onay_durumu, 'Bilinmiyor'),
            u.kategori_id, COALESCE(k.ana, 'Diğer'), COALESCE(k.alt1, ''), COALESCE(k.alt2, ''),
            SUM(s.tutar), SUM(s.miktar), COUNT(DISTINCT s.musteri_id)
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        LEFT JOIN markalar m ON u.marka_id = m.id
        LEFT JOIN musteriler mu ON s.musteri_id = mu.id
        LEFT JOIN musteridetayozet mdo ON s.musteri_id = mdo.musteri_id
        LEFT JOIN magazalar mg ON s.magaza_id = mg.id
        LEFT JOIN kategoriler k ON u.kategori_id = k.id
        GROUP BY u.marka_id, m.ad, TO_CHAR(s.tarih, 'YYYY'), TO_CHAR(s.tarih, 'MM'),
                 COALESCE(mg.bolge, 'Diğer'), COALESCE(mu.tip, 'Bilinmiyor'),
                 COALESCE(mdo.rfm_segment, 'Diğer'), COALESCE(s.onay_durumu, 'Bilinmiyor'),
                 u.kategori_id, COALESCE(k.ana, 'Diğer'), COALESCE(k.alt1, ''), COALESCE(k.alt2, '')
    """)
    rows = cur.fetchall()
    
    final_rows = []
    for r in rows:
        final_rows.append((
            r[0], r[1], int(r[2]) if r[2] else None, int(r[3]) if r[3] else None,
            r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11],
            r[12], r[13], r[14],
            tr_lower(r[1]), tr_lower(r[4]), tr_lower(r[5]),
            tr_lower(r[7]), tr_lower(r[6]), tr_lower(r[9]),
            tr_lower(r[10]), tr_lower(r[11])
        ))
    
    from psycopg2.extras import execute_batch
    execute_batch(cur, """
        INSERT INTO brandsummary (
            brand_id, brand_name, year, month, region, customer_type, segment, approval_status,
            category_id, category_main, category_sub1, category_sub2,
            total_sales, total_units, customer_count,
            brand_name_norm, region_norm, customer_type_norm, approval_status_norm, segment_norm, category_norm, category_sub1_norm, category_sub2_norm
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, final_rows, page_size=5000)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bs_main ON brandsummary(year, month)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bs_dims ON brandsummary(region_norm, customer_type_norm, category_norm, brand_name_norm)")
    pg.commit()
    
    elapsed = time.time() - start_time
    logger.info(f"   ✅ BrandSummary tamamlandı: {len(final_rows):,} satır ({elapsed:.1f}s)")
    return len(final_rows)


def update_global_stats(pg):
    """globalstatlar tablosunu güncelle"""
    cur = pg.cursor()
    logger.info("📊 Global istatistikler güncelleniyor...")
    
    # Toplam müşteri
    cur.execute("SELECT COUNT(*) FROM musteriler")
    total_customers = cur.fetchone()[0]
    
    # Aktif müşteriler (son 120 günde alışveriş yapanlar)
    cur.execute("""
        SELECT COUNT(DISTINCT musteri_id) FROM satislar 
        WHERE tarih >= CURRENT_DATE - INTERVAL '120 days'
    """)
    active_customers = cur.fetchone()[0]
    
    # Churn rate
    churn_rate = round((1 - active_customers / total_customers) * 100, 2) if total_customers > 0 else 0
    
    # Toplam ciro ve fiş
    cur.execute("SELECT COALESCE(SUM(tutar), 0), COUNT(DISTINCT fis_no) FROM satislar")
    row = cur.fetchone()
    total_revenue = row[0]
    total_receipts = row[1]
    
    # Upsert
    stats = {
        'total_unique_customers': str(total_customers),
        'active_customers': str(active_customers),
        'total_churn_rate': str(churn_rate),
        'total_revenue': str(total_revenue),
        'total_receipts': str(total_receipts)
    }
    
    for key, value in stats.items():
        cur.execute("""
            INSERT INTO syncmeta (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
        """, (key, value))
    
    pg.commit()
    logger.info(f"   ✅ Global istatistikler güncellendi: {stats}")


def update_sync_meta(pg):
    """SyncMeta'yı güncelle"""
    cur = pg.cursor()
    now = datetime.now().isoformat()
    
    meta_updates = {
        'last_full_sync': now,
        'last_sales_sync': now,
        'last_lookup_sync': now,
        'last_delta_sync': now,
        'last_summary_update': now,
        'last_sales_sync_month': datetime.now().strftime('%Y-%m'),
    }
    
    for key, value in meta_updates.items():
        cur.execute("""
            INSERT INTO syncmeta (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
        """, (key, value))
    
    pg.commit()
    logger.info("   ✅ SyncMeta güncellendi")


# ================== ANA FONKSİYON ==================

def main():
    overall_start = time.time()
    
    logger.info("=" * 70)
    logger.info("🚀 MANUEL FULL SYNC BAŞLADI")
    logger.info(f"   Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   DB Backend: {DB_BACKEND}")
    logger.info("=" * 70)
    
    # Schema oluştur
    create_schema()
    
    # ========== ADIM 1: SQL Server Bağlantısı ==========
    logger.info("\n" + "=" * 70)
    logger.info("ADIM 1: SQL Server Bağlantısı")
    logger.info("=" * 70)
    
    try:
        sql_conn = connect_sql()
        sql_cursor = sql_conn.cursor()
        logger.info("   ✅ SQL Server bağlantısı başarılı")
    except Exception as e:
        logger.error(f"   ❌ SQL Server bağlantı hatası: {e}")
        logger.error("   Tailscale VPN'in çalıştığından emin olun!")
        return False
    
    # ========== ADIM 2: PostgreSQL Bağlantısı ==========
    logger.info("\n" + "=" * 70)
    logger.info("ADIM 2: PostgreSQL Bağlantısı")
    logger.info("=" * 70)
    
    try:
        pg = pg_conn()
        logger.info("   ✅ PostgreSQL bağlantısı başarılı")
    except Exception as e:
        logger.error(f"   ❌ PostgreSQL bağlantı hatası: {e}")
        sql_conn.close()
        return False
    
    # ========== ADIM 3: Lookup Sync ==========
    logger.info("\n" + "=" * 70)
    logger.info("ADIM 3: Lookup Verileri Senkronize Ediliyor")
    logger.info("=" * 70)
    
    t = time.time()
    try:
        stats = {
            'satinalmacilar': sync_satinalmacilar(sql_cursor, pg),
            'markalar': sync_markalar(sql_cursor, pg),
            'kategoriler': sync_kategoriler(sql_cursor, pg),
            'magazalar': sync_magazalar(sql_cursor, pg),
            'urunler': sync_urunler(sql_cursor, pg),
            'kampanyalar': sync_kampanyalar(sql_cursor, pg),
            'musteriler': sync_musteriler(sql_cursor, pg),
        }
        logger.info(f"   ✅ Lookup sync tamamlandı ({time.time() - t:.1f}s): {stats}")
    except Exception as e:
        logger.error(f"   ❌ Lookup sync hatası: {e}", exc_info=True)
        sql_conn.close()
        return False
    
    # ========== ADIM 4: Satış Sync (Ay Ay) ==========
    logger.info("\n" + "=" * 70)
    logger.info("ADIM 4: Satış Verileri Senkronize Ediliyor (Ay Ay)")
    logger.info("=" * 70)
    
    today = datetime.now()
    months = []
    current = datetime(2024, 1, 1)
    while current <= today:
        months.append((current.year, current.month))
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)
    
    logger.info(f"   {len(months)} ay çekilecek: {months[0][0]}-{months[0][1]:02d} ~ {months[-1][0]}-{months[-1][1]:02d}")
    
    total_records = 0
    failed_months = []
    
    for year, month in months:
        month_start = time.time()
        try:
            count = sync_month_sales(sql_cursor, pg, year, month)
            total_records += count
            
            # Tutarlılık kontrolü
            v = verify_month(sql_cursor, pg, year, month)
            status = "✅" if v['is_ok'] else "⚠️"
            logger.info(f"   {status} {v['month']}: {count:,} kayıt | "
                       f"SQL:{v['sql_count']:,} PG:{v['pg_count']:,} | "
                       f"Ciro fark: {v['ciro_diff']:.2f} TL | "
                       f"{time.time() - month_start:.1f}s")
            
            if not v['is_ok']:
                failed_months.append(v['month'])
                
        except Exception as e:
            logger.error(f"   ❌ {year}-{month:02d}: HATA - {e}")
            failed_months.append(f"{year}-{month:02d}")
            try:
                pg.rollback()
            except:
                pass
    
    logger.info(f"\n   📊 Toplam: {total_records:,} satış kaydı çekildi")
    if failed_months:
        logger.warning(f"   ⚠️ Tutarsız aylar: {failed_months}")
    
    # ========== ADIM 5: Özet Tabloları Rebuild ==========
    logger.info("\n" + "=" * 70)
    logger.info("ADIM 5: Özet Tabloları Yeniden Hesaplanıyor")
    logger.info("=" * 70)
    
    # Önce checkpoint kontrolü — devam eden rebuild var mı?
    cur = pg.cursor()
    cur.execute("SELECT value FROM syncmeta WHERE key = 'rebuild_daily_checkpoint'")
    has_checkpoint = cur.fetchone()
    
    if has_checkpoint:
        logger.info(f"   📌 Rebuild checkpoint bulundu ({has_checkpoint[0]}) — tablolar temizlenmeyecek, kaldığı yerden devam edilecek")
    else:
        # İlk çalıştırma — özetleri temizle
        for table in ['gunlukciroozet', 'magazagunlukozet', 'crmozet', 'daily_metrics_summary',
                       'gunlukozet', 'kategorikarsilastirma', 'markakarsilastirma',
                       'kampanyaozet', 'genelozet', 'musterisadakat']:
            try:
                cur.execute(f"DELETE FROM {table}")
                logger.info(f"   🗑️ {table} temizlendi")
            except Exception as e:
                logger.warning(f"   ⚠️ {table} temizleme hatası: {e}")
                pg.rollback()
    pg.commit()
    
    # Günlük özetler
    t = time.time()
    rebuild_daily_summaries(pg)
    logger.info(f"   Günlük özetler: {time.time() - t:.1f}s")
    
    # Aylık özetler
    t = time.time()
    rebuild_monthly_summaries(pg)
    logger.info(f"   Aylık özetler: {time.time() - t:.1f}s")
    
    # ========== ADIM 6: BrandSummary + GlobalStats ==========
    logger.info("\n" + "=" * 70)
    logger.info("ADIM 6: BrandSummary ve Global İstatistikler")
    logger.info("=" * 70)
    
    t = time.time()
    rebuild_brand_summary(pg)
    logger.info(f"   BrandSummary: {time.time() - t:.1f}s")
    
    update_global_stats(pg)
    
    # ========== ADIM 7: SyncMeta Güncelle ==========
    update_sync_meta(pg)
    
    # ========== ADIM 8: Doğrulama Raporu ==========
    logger.info("\n" + "=" * 70)
    logger.info("DOĞRULAMA RAPORU")
    logger.info("=" * 70)
    
    cur = pg.cursor()
    tables = ['satislar', 'musteriler', 'kategori_yoneticileri', 'urunler', 'markalar', 'kategoriler', 'magazalar',
              'gunlukciroozet', 'daily_metrics_summary', 'musteridetayozet', 'genelozet',
              'crmozet', 'brandsummary', 'kampanyalar', 'gunlukozet',
              'kategorikarsilastirma', 'markakarsilastirma', 'kampanyaozet', 'musterisadakat']
    
    for t_name in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t_name}")
            logger.info(f"   {t_name}: {cur.fetchone()[0]:,}")
        except Exception as e:
            pg.rollback()
            logger.warning(f"   {t_name}: HATA - {e}")
    
    # Tarih aralığı
    cur.execute("SELECT MIN(tarih), MAX(tarih) FROM satislar")
    r = cur.fetchone()
    logger.info(f"\n   Satış tarih aralığı: {r[0]} - {r[1]}")
    
    # Toplam süre
    total_elapsed = time.time() - overall_start
    hours = int(total_elapsed // 3600)
    mins = int((total_elapsed % 3600) // 60)
    secs = int(total_elapsed % 60)
    
    logger.info(f"\n{'=' * 70}")
    logger.info(f"🎉 MANUEL FULL SYNC TAMAMLANDI!")
    logger.info(f"   Toplam süre: {hours}s {mins}dk {secs}sn")
    logger.info(f"   Toplam satış kaydı: {total_records:,}")
    logger.info(f"{'=' * 70}")
    
    # Kapat
    sql_conn.close()
    pg.close()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
