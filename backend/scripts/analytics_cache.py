"""
Analytics Cache Builder
=======================
Pahalı analizleri önceden hesaplayıp veritabanı tablolarına yazar.
Günlük sync sırasında rfm_daily_update.py tarafından çağrılır.

Cache tabloları (JSON blob + hesaplama tarihi):
    cache_kohort_analizi
    cache_enflasyon_dayaniklilik
    cache_rakip_riski
    cache_hane_analizi
    cache_marka_sadakati
    cache_kategori_terk

Kullanım:
    python analytics_cache.py              # Tümünü hesapla
    python analytics_cache.py --kohort     # Sadece kohort
    python analytics_cache.py --list       # Hangi tablolar var, son güncelleme ne zaman
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from collections import defaultdict

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from api import db_engine
except ImportError:
    from backend.api import db_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ─── Yardımcı: Cache tablo altyapısı ─────────────────────────────────────────

def ensure_cache_tables(cursor, conn):
    """Tüm cache tablolarını oluştur (yoksa)."""
    tables = [
        'cache_kohort_analizi',
        'cache_enflasyon_dayaniklilik',
        'cache_rakip_riski',
        'cache_hane_analizi',
        'cache_marka_sadakati',
        'cache_kategori_terk',
    ]
    for tablo in tables:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {tablo} (
                id SERIAL PRIMARY KEY,
                veri JSONB NOT NULL,
                hesaplama_tarihi TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sure_saniye FLOAT
            )
        """)
    conn.commit()
    logger.info("Cache tabloları kontrol edildi / oluşturuldu.")


def write_cache(cursor, conn, tablo: str, veri: dict, sure: float):
    """Cache tablosuna yaz — eski kaydı sil, yeni ekle."""
    cursor.execute(f"DELETE FROM {tablo}")
    cursor.execute(
        f"INSERT INTO {tablo} (veri, hesaplama_tarihi, sure_saniye) VALUES (%s, %s, %s)",
        (json.dumps(veri, ensure_ascii=False, default=str), datetime.now(), round(sure, 2))
    )
    conn.commit()
    logger.info(f"  → {tablo}: {sure:.1f}s'de yazıldı.")


def val(row, key, default=None):
    if row is None:
        return default
    if hasattr(row, '__getitem__'):
        try:
            v = row[key]
            return v if v is not None else default
        except (KeyError, IndexError):
            return default
    return default


# ─── 1. Kohort Analizi ───────────────────────────────────────────────────────

def build_kohort(cursor, conn, max_ay=18):
    logger.info("Kohort analizi hesaplanıyor...")
    t0 = datetime.now()

    cursor.execute("""
        SELECT
            md.musteri_id,
            TO_CHAR(md.ilk_alisveris_tarihi, 'YYYY-MM') as kohort_ay
        FROM musteridetayozet md
        WHERE md.ilk_alisveris_tarihi IS NOT NULL
    """)
    rows = cursor.fetchall()

    if not rows:
        write_cache(cursor, conn, 'cache_kohort_analizi',
                    {'kohortlar': [], 'max_ay': 0, 'mesaj': 'Müşteri verisi bulunamadı'},
                    (datetime.now() - t0).total_seconds())
        return

    musteri_kohort = {}
    kohort_boyutlari = {}
    for r in rows:
        mid = val(r, 'musteri_id')
        k = val(r, 'kohort_ay')
        if mid and k:
            musteri_kohort[mid] = k
            kohort_boyutlari[k] = kohort_boyutlari.get(k, 0) + 1

    cursor.execute("""
        SELECT
            musteri_id,
            TO_CHAR(tarih, 'YYYY-MM') as alis_ay
        FROM satislar
        WHERE musteri_id IS NOT NULL
          AND tarih IS NOT NULL
        GROUP BY musteri_id, TO_CHAR(tarih, 'YYYY-MM')
    """)

    kohort_aktivite = defaultdict(lambda: defaultdict(set))
    CHUNK = 10000
    while True:
        alis_rows = cursor.fetchmany(CHUNK)
        if not alis_rows:
            break
        for r in alis_rows:
            mid = val(r, 'musteri_id')
            alis_ay = val(r, 'alis_ay')
            if mid is None or alis_ay is None:
                continue
            kohort_ay = musteri_kohort.get(mid)
            if not kohort_ay:
                continue
            try:
                ky, km = int(kohort_ay[:4]), int(kohort_ay[5:7])
                ay, am = int(alis_ay[:4]), int(alis_ay[5:7])
                indeks = (ay - ky) * 12 + (am - km)
                if 0 <= indeks <= max_ay:
                    kohort_aktivite[kohort_ay][indeks].add(mid)
            except (ValueError, IndexError):
                continue

    sonuc = []
    for kohort_ay in sorted(kohort_aktivite.keys()):
        boyut = kohort_boyutlari.get(kohort_ay, 0)
        if boyut == 0:
            continue
        retention = {}
        aktivite = kohort_aktivite[kohort_ay]
        for ay_idx in range(max_ay + 1):
            aktif = len(aktivite.get(ay_idx, set()))
            retention[ay_idx] = round(aktif / boyut * 100, 1) if boyut > 0 else 0
        sonuc.append({
            'kohort_ay': kohort_ay,
            'kohort_boyutu': boyut,
            'retention': retention,
        })

    sonuc = sonuc[-24:]
    sure = (datetime.now() - t0).total_seconds()
    write_cache(cursor, conn, 'cache_kohort_analizi',
                {'kohortlar': sonuc, 'max_ay': max_ay, 'toplam_kohort': len(sonuc)},
                sure)


# ─── 2. Enflasyon Dayanıklılık ───────────────────────────────────────────────

def build_enflasyon(cursor, conn):
    logger.info("Enflasyon dayanıklılık profili hesaplanıyor...")
    t0 = datetime.now()

    cursor.execute("""
        SELECT
            m.rfm_segment,
            COUNT(*) as musteri_sayisi,
            AVG(pf.indirim_oran_yuzde) as ort_indirim_oran,
            AVG(pf.ort_indirim_yuzde) as ort_indirim_yuzde,
            AVG(dk.harcama_degisim_3ay_yuzde) as ort_harcama_degisim_3ay,
            AVG(dk.ziyaret_degisim_3ay_yuzde) as ort_ziyaret_degisim_3ay,
            AVG(dk.harcama_degisim_6ay_yuzde) as ort_harcama_degisim_6ay,
            COUNT(CASE WHEN me.enflasyon_stokcusu = TRUE THEN 1 END) as stokcu_sayisi,
            COUNT(CASE WHEN me.fiyat_hassas = TRUE THEN 1 END) as fiyat_hassas_sayisi
        FROM musteriler m
        JOIN musterifiyatfeatures pf ON m.id = pf.musteri_id
        JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
        JOIN musterietiketler me ON m.id = me.musteri_id
        WHERE 1=1
          AND m.rfm_segment IS NOT NULL
        GROUP BY m.rfm_segment
        ORDER BY musteri_sayisi DESC
    """)
    segment_analiz = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT
            m.id, m.ad, m.rfm_segment,
            md.toplam_harcama as toplam_harcama,
            pf.indirim_oran_yuzde,
            pf.ort_indirim_yuzde,
            dk.harcama_degisim_3ay_yuzde as harcama_degisim_3ay,
            dk.ziyaret_degisim_3ay_yuzde as ziyaret_degisim_3ay
        FROM musteriler m
        JOIN musterietiketler me ON m.id = me.musteri_id
        JOIN musterifiyatfeatures pf ON m.id = pf.musteri_id
        JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
        LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
        WHERE me.enflasyon_stokcusu = TRUE
        ORDER BY dk.harcama_degisim_3ay_yuzde DESC
        LIMIT 50
    """)
    stokcu_liste = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT
            COUNT(*) as toplam_musteri,
            COUNT(CASE WHEN me.enflasyon_stokcusu = TRUE THEN 1 END) as stokcu_sayisi,
            COUNT(CASE WHEN me.fiyat_hassas = TRUE THEN 1 END) as fiyat_hassas_sayisi,
            AVG(pf.indirim_oran_yuzde) as genel_indirim_oran,
            AVG(dk.harcama_degisim_3ay_yuzde) as genel_harcama_degisim
        FROM musteriler m
        JOIN musterifiyatfeatures pf ON m.id = pf.musteri_id
        JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
        JOIN musterietiketler me ON m.id = me.musteri_id
        WHERE 1=1
    """)
    ozet_row = cursor.fetchone()
    ozet = dict(ozet_row) if ozet_row else {}

    sure = (datetime.now() - t0).total_seconds()
    write_cache(cursor, conn, 'cache_enflasyon_dayaniklilik',
                {'segment_analiz': segment_analiz, 'stokcu_liste': stokcu_liste, 'ozet': ozet},
                sure)


# ─── 3. Rakip Riski ──────────────────────────────────────────────────────────

def build_rakip_riski(cursor, conn):
    logger.info("Rakip riski skoru hesaplanıyor...")
    t0 = datetime.now()

    cursor.execute("""
        SELECT
            m.id, m.ad, m.rfm_segment,
            md.toplam_harcama as toplam_harcama,
            COALESCE(dk.terk_edilen_kategori, 0) as terk_edilen_kategori,
            COALESCE(dk.harcama_degisim_3ay_yuzde, 0) as harcama_degisim_3ay,
            COALESCE(dk.ziyaret_degisim_3ay_yuzde, 0) as ziyaret_degisim_3ay,
            LEAST(100, GREATEST(0,
                CASE WHEN me.kategori_terk_eden = TRUE THEN 30 ELSE 0 END +
                CASE WHEN me.sepeti_daralan = TRUE THEN 20 ELSE 0 END +
                CASE WHEN me.kaybedilme_riski_yuksek = TRUE THEN 25 ELSE 0 END +
                CASE WHEN me.soguyan_musteri = TRUE THEN 15 ELSE 0 END +
                CASE WHEN COALESCE(dk.terk_edilen_kategori, 0) > 2 THEN 10 ELSE 0 END
            )) as rakip_riski_skoru
        FROM musteriler m
        JOIN musterietiketler me ON m.id = me.musteri_id
        LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
        LEFT JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
        WHERE 1=1
          AND (
            me.kategori_terk_eden = TRUE
            OR me.sepeti_daralan = TRUE
            OR me.kaybedilme_riski_yuksek = TRUE
          )
        ORDER BY rakip_riski_skoru DESC, toplam_harcama DESC
        LIMIT 200
    """)
    risk_liste = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE skor >= 60) as yuksek,
            COUNT(*) FILTER (WHERE skor >= 30 AND skor < 60) as orta,
            COUNT(*) FILTER (WHERE skor < 30) as dusuk,
            COUNT(*) as toplam
        FROM (
            SELECT LEAST(100, GREATEST(0,
                CASE WHEN me.kategori_terk_eden = TRUE THEN 30 ELSE 0 END +
                CASE WHEN me.sepeti_daralan = TRUE THEN 20 ELSE 0 END +
                CASE WHEN me.kaybedilme_riski_yuksek = TRUE THEN 25 ELSE 0 END +
                CASE WHEN me.soguyan_musteri = TRUE THEN 15 ELSE 0 END +
                CASE WHEN COALESCE(dk.terk_edilen_kategori, 0) > 2 THEN 10 ELSE 0 END
            )) as skor
            FROM musteriler m
            JOIN musterietiketler me ON m.id = me.musteri_id
            LEFT JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
            WHERE me.kategori_terk_eden = TRUE
               OR me.sepeti_daralan = TRUE
               OR me.kaybedilme_riski_yuksek = TRUE
        ) sub
    """)
    dagilim_row = cursor.fetchone()
    yuksek = int(val(dagilim_row, 'yuksek', 0))
    orta   = int(val(dagilim_row, 'orta', 0))
    dusuk  = int(val(dagilim_row, 'dusuk', 0))
    toplam = int(val(dagilim_row, 'toplam', 0))

    sure = (datetime.now() - t0).total_seconds()
    write_cache(cursor, conn, 'cache_rakip_riski',
                {'risk_listesi': risk_liste, 'dagilim': {'yuksek': yuksek, 'orta': orta, 'dusuk': dusuk, 'toplam': toplam}},
                sure)


# ─── 4. Hane Analizi ─────────────────────────────────────────────────────────

def build_hane_analizi(cursor, conn):
    logger.info("Hane analizi hesaplanıyor...")
    t0 = datetime.now()

    hane_kolonlar = [
        ('hane_bekar_skoru', 'Bekar'),
        ('hane_cift_skoru', 'Çift'),
        ('hane_aile_skoru', 'Aile'),
        ('hane_cocuklu_skoru', 'Çocuklu'),
        ('hane_bebek_skoru', 'Bebek'),
        ('hane_yasli_skoru', 'Yaşlı'),
        ('hane_evcil_hayvan_skoru', 'Evcil Hayvan'),
        ('hane_araba_skoru', 'Araba'),
    ]

    hane_dagilim = []
    for kolon, etiket in hane_kolonlar:
        try:
            cursor.execute(f"""
                SELECT
                    COUNT(*) as musteri_sayisi,
                    AVG({kolon}) as ort_skor,
                    COUNT(CASE WHEN {kolon} >= 0.6 THEN 1 END) as yuksek_skor_sayisi
                FROM musterietiketler me
                JOIN musteriler m ON m.id = me.musteri_id
                WHERE 1=1
            """)
            row = cursor.fetchone()
            if row:
                hane_dagilim.append({
                    'tip': etiket,
                    'kolon': kolon,
                    'musteri_sayisi': int(val(row, 'musteri_sayisi', 0)),
                    'ort_skor': round(float(val(row, 'ort_skor') or 0), 3),
                    'yuksek_skor_sayisi': int(val(row, 'yuksek_skor_sayisi', 0)),
                })
        except Exception as e:
            logger.warning(f"  Hane kolon hatası ({kolon}): {e}")
            continue

    cursor.execute("""
        SELECT
            m.rfm_segment,
            COUNT(*) as toplam,
            AVG(me.hane_bekar_skoru) as bekar,
            AVG(me.hane_cift_skoru) as cift,
            AVG(me.hane_aile_skoru) as aile,
            AVG(me.hane_cocuklu_skoru) as cocuklu,
            AVG(me.hane_bebek_skoru) as bebek,
            AVG(me.hane_yasli_skoru) as yasli,
            AVG(me.hane_evcil_hayvan_skoru) as evcil,
            AVG(me.hane_araba_skoru) as araba
        FROM musterietiketler me
        JOIN musteriler m ON m.id = me.musteri_id
        WHERE 1=1
          AND m.rfm_segment IS NOT NULL
        GROUP BY m.rfm_segment
        ORDER BY toplam DESC
    """)
    segment_hane = []
    for r in cursor.fetchall():
        row = dict(r)
        skorlar = {
            'Bekar':      round(float(row.get('bekar') or 0), 3),
            'Çift':       round(float(row.get('cift') or 0), 3),
            'Aile':       round(float(row.get('aile') or 0), 3),
            'Çocuklu':    round(float(row.get('cocuklu') or 0), 3),
            'Bebek':      round(float(row.get('bebek') or 0), 3),
            'Yaşlı':      round(float(row.get('yasli') or 0), 3),
            'Evcil Hayvan': round(float(row.get('evcil') or 0), 3),
            'Araba':      round(float(row.get('araba') or 0), 3),
        }
        baskin = max(skorlar, key=skorlar.get)
        segment_hane.append({
            'rfm_segment': row.get('rfm_segment'),
            'toplam': int(row.get('toplam', 0)),
            'baskin_hane': baskin,
            'baskin_skor': skorlar[baskin],
            'skorlar': skorlar,
        })

    cursor.execute("""
        SELECT
            m.id, m.ad, m.rfm_segment,
            md.toplam_harcama as toplam_harcama,
            me.hane_cocuklu_skoru,
            me.hane_bebek_skoru,
            me.hane_aile_skoru,
            me.hane_araba_skoru
        FROM musterietiketler me
        JOIN musteriler m ON m.id = me.musteri_id
        LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
        WHERE 1=1
          AND (me.hane_cocuklu_skoru >= 0.5 OR me.hane_bebek_skoru >= 0.5)
        ORDER BY md.toplam_harcama DESC
        LIMIT 30
    """)
    cocuklu_aile_liste = [dict(r) for r in cursor.fetchall()]

    sure = (datetime.now() - t0).total_seconds()
    write_cache(cursor, conn, 'cache_hane_analizi',
                {'hane_dagilim': hane_dagilim, 'segment_hane': segment_hane, 'cocuklu_aile_liste': cocuklu_aile_liste},
                sure)


# ─── 5. Marka Sadakati ───────────────────────────────────────────────────────

def build_marka_sadakati(cursor, conn):
    logger.info("Marka sadakati hesaplanıyor...")
    t0 = datetime.now()

    # musterimarka_dagilimi: musteri_id, marka_adi, fis_sayisi, toplam_harcama, toplam_miktar
    # marka_id yok — marka_adi (text) üzerinden gruplama yapıyoruz

    cursor.execute("""
        SELECT
            md.marka_adi as marka,
            COUNT(DISTINCT md.musteri_id) as musteri_sayisi,
            SUM(md.toplam_harcama) as toplam_harcama,
            AVG(md.toplam_harcama) as ort_harcama,
            COUNT(DISTINCT CASE WHEN mu.rfm_segment LIKE '%Şampiyon%' THEN md.musteri_id END) as sampiyonlar,
            COUNT(DISTINCT CASE WHEN mu.rfm_segment LIKE '%Sadık%' THEN md.musteri_id END) as sadik,
            COUNT(DISTINCT CASE WHEN mu.rfm_segment LIKE '%Risk%' OR mu.rfm_segment LIKE '%Kayıp%' THEN md.musteri_id END) as risk
        FROM musterimarka_dagilimi md
        JOIN musteriler mu ON md.musteri_id = mu.id
        WHERE md.marka_adi IS NOT NULL
        GROUP BY md.marka_adi
        ORDER BY toplam_harcama DESC
        LIMIT 30
    """)
    marka_rows = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT
            md.marka_adi as marka,
            COUNT(DISTINCT md.musteri_id) as toplam_musteri,
            COUNT(DISTINCT CASE WHEN alt.marka_sayisi = 1 THEN md.musteri_id END) as sadece_bu_marka
        FROM musterimarka_dagilimi md
        JOIN (
            SELECT musteri_id, COUNT(DISTINCT marka_adi) as marka_sayisi
            FROM musterimarka_dagilimi
            GROUP BY musteri_id
        ) alt ON md.musteri_id = alt.musteri_id
        WHERE md.marka_adi IS NOT NULL
        GROUP BY md.marka_adi
        ORDER BY toplam_musteri DESC
        LIMIT 30
    """)
    sadakat_rows = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT
            marka_adi as marka,
            COUNT(DISTINCT musteri_id) as musteri_sayisi,
            ROUND(AVG(toplam_harcama)::numeric, 0) as ort_musteri_harcama,
            SUM(toplam_harcama) as toplam_harcama
        FROM musterimarka_dagilimi
        WHERE marka_adi IS NOT NULL
        GROUP BY marka_adi
        ORDER BY musteri_sayisi DESC
        LIMIT 30
    """)
    segment_dagilim = [dict(r) for r in cursor.fetchall()]

    sure = (datetime.now() - t0).total_seconds()
    write_cache(cursor, conn, 'cache_marka_sadakati',
                {'marka_profiller': marka_rows, 'sadakat_skorlari': sadakat_rows, 'top_markalar': segment_dagilim},
                sure)


# ─── 6. Kategori Terk Listesi ────────────────────────────────────────────────

def build_kategori_terk(cursor, conn):
    logger.info("Kategori terk listesi hesaplanıyor...")
    t0 = datetime.now()

    cursor.execute("""
        SELECT
            m.id, m.ad, m.rfm_segment,
            COALESCE(md.toplam_harcama, 0) as toplam_harcama,
            COALESCE(dk.terk_edilen_kategori, 0) as terk_edilen_kategori_sayisi,
            COALESCE(dk.harcama_degisim_3ay_yuzde, 0) as harcama_degisim_3ay,
            COALESCE(dk.ziyaret_degisim_3ay_yuzde, 0) as ziyaret_degisim_3ay
        FROM musteriler m
        JOIN musterietiketler me ON m.id = me.musteri_id
        LEFT JOIN musteridonem_karsilastirma dk ON m.id = dk.musteri_id
        LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
        WHERE me.kategori_terk_eden = TRUE
        ORDER BY dk.terk_edilen_kategori DESC, md.toplam_harcama DESC
        LIMIT 100
    """)
    terk_listesi = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT COUNT(*) as toplam
        FROM musteriler m
        JOIN musterietiketler me ON m.id = me.musteri_id
        WHERE me.kategori_terk_eden = TRUE
    """)
    row = cursor.fetchone()
    toplam = int(val(row, 'toplam', 0))

    sure = (datetime.now() - t0).total_seconds()
    write_cache(cursor, conn, 'cache_kategori_terk',
                {'terk_listesi': terk_listesi, 'toplam': toplam},
                sure)


# ─── Ana fonksiyon ───────────────────────────────────────────────────────────

def run_all(secim: dict | None = None):
    """
    Tüm cache'leri veya seçili olanları hesaplar.
    secim: {'kohort': True, 'enflasyon': True, ...} şeklinde. None = tümü.
    """
    tumü = secim is None

    t_total = datetime.now()
    logger.info("=" * 60)
    logger.info("ANALYTICS CACHE BUILD BAŞLADI")
    logger.info(f"Zaman: {t_total.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        ensure_cache_tables(cursor, conn)

        if tumü or secim.get('kohort'):
            build_kohort(cursor, conn)

        if tumü or secim.get('enflasyon'):
            build_enflasyon(cursor, conn)

        if tumü or secim.get('rakip'):
            build_rakip_riski(cursor, conn)

        if tumü or secim.get('hane'):
            build_hane_analizi(cursor, conn)

        if tumü or secim.get('marka'):
            build_marka_sadakati(cursor, conn)

        if tumü or secim.get('terk'):
            build_kategori_terk(cursor, conn)

    except Exception as e:
        logger.error(f"Cache build hatası: {e}", exc_info=True)
        raise
    finally:
        if conn:
            db_engine.release_connection(conn)

    sure = (datetime.now() - t_total).total_seconds()
    logger.info("=" * 60)
    logger.info(f"ANALYTICS CACHE BUILD TAMAMLANDI — {sure:.1f}s")
    logger.info("=" * 60)
    return sure


def list_cache_status():
    """Cache tablolarının son güncelleme zamanını ve boyutunu göster."""
    tables = [
        'cache_kohort_analizi',
        'cache_enflasyon_dayaniklilik',
        'cache_rakip_riski',
        'cache_hane_analizi',
        'cache_marka_sadakati',
        'cache_kategori_terk',
    ]
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        print(f"\n{'Tablo':<35} {'Son Güncelleme':<22} {'Süre(s)':<10}")
        print("-" * 70)
        for tablo in tables:
            try:
                cursor.execute(f"SELECT hesaplama_tarihi, sure_saniye FROM {tablo} ORDER BY hesaplama_tarihi DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    tarih = str(val(row, 'hesaplama_tarihi', '-'))[:19]
                    sure = val(row, 'sure_saniye', '-')
                    print(f"{tablo:<35} {tarih:<22} {sure:<10}")
                else:
                    print(f"{tablo:<35} {'— (boş)':<22}")
            except Exception:
                print(f"{tablo:<35} {'— (tablo yok)':<22}")
        print()
    finally:
        if conn:
            db_engine.release_connection(conn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analytics cache builder')
    parser.add_argument('--kohort',    action='store_true', help='Sadece kohort analizi')
    parser.add_argument('--enflasyon', action='store_true', help='Sadece enflasyon profili')
    parser.add_argument('--rakip',     action='store_true', help='Sadece rakip riski')
    parser.add_argument('--hane',      action='store_true', help='Sadece hane analizi')
    parser.add_argument('--marka',     action='store_true', help='Sadece marka sadakati')
    parser.add_argument('--terk',      action='store_true', help='Sadece kategori terk')
    parser.add_argument('--list',      action='store_true', help='Cache durumunu göster')
    args = parser.parse_args()

    if args.list:
        list_cache_status()
        sys.exit(0)

    herhangi = any([args.kohort, args.enflasyon, args.rakip, args.hane, args.marka, args.terk])
    if herhangi:
        secim = {
            'kohort': args.kohort,
            'enflasyon': args.enflasyon,
            'rakip': args.rakip,
            'hane': args.hane,
            'marka': args.marka,
            'terk': args.terk,
        }
        run_all(secim)
    else:
        run_all()
