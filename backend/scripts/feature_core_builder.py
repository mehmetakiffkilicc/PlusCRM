"""
Musteri Davranis Etiketleme Sistemi - Feature Core Builder
==========================================================
Bu script 14 feature tablosunu sifirdan olusturur.
Calistirmadan once mevcut tablolar DROP edilir, sonra yeniden CREATE edilir.

Tablolar (sirasyla olusturulur):
    GRUP A - Temel Ziyaret:
        1. MusteriGunlukZiyaretler
        2. MusteriZiyaretAraliklari
        3. MusteriZiyaretFeatures

    GRUP B - Zaman Dagilimi:
        4. MusteriSaatDagilimi
        5. MusteriGunDagilimi
        6. MusteriAyGunDagilimi
        7. MusteriAyDagilimi

    GRUP C - Kategori & Urun:
        8. MusteriKategoriDagilimi
        9. MusteriMarkaDagilimi
       10. MusteriUrunTutarliligi

    GRUP D - Fis Detay:
       11. MusteriFisSepetDetay

    GRUP E - Kampanya & Odeme:
       12. MusteriKampanyaFeatures
       13. MusteriBelgeTipiDagilimi

    GRUP F - Donem Karsilastirma:
       14. MusteriDonemKarsilastirma

    GRUP G - Fiyat & Indirim:
       15. MusteriFiyatFeatures
"""

import os
import sys
import logging
from datetime import datetime

# Path ayarlama (rfm_segmentation.py ile ayni pattern)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
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

# Tablo olusturma sirasi (DROP sirasinin tersi)
TABLE_ORDER = [
    'MusteriGunlukZiyaretler',
    'MusteriZiyaretAraliklari',
    'MusteriZiyaretFeatures',
    'MusteriSaatDagilimi',
    'MusteriGunDagilimi',
    'MusteriAyGunDagilimi',
    'MusteriAyDagilimi',
    'MusteriKategoriDagilimi',
    'MusteriMarkaDagilimi',
    'MusteriUrunTutarliligi',
    'MusteriFisSepetDetay',
    'MusteriKampanyaFeatures',
    'MusteriBelgeTipiDagilimi',
    'MusteriDonemKarsilastirma',
    'MusteriFiyatFeatures',
    'BeklenenMusteriler',
]

# Her tablo icin CREATE SQL
CREATE_SQLS = {

    # -------------------------------------------------------------------------
    # GRUP A: Temel Ziyaret Feature'lari
    # -------------------------------------------------------------------------

    'MusteriGunlukZiyaretler': """
        CREATE TABLE musterigunlukziyaretler AS
        SELECT
            musteri_id,
            tarih AS ziyaret_tarihi,
            COUNT(DISTINCT fis_no)  AS gunluk_ziyaret_sayisi,
            SUM(tutar)              AS gunluk_harcama,
            SUM(miktar)             AS gunluk_urun_adedi
        FROM satislar
        WHERE musteri_id IS NOT NULL
        GROUP BY musteri_id, tarih
    """,

    'MusteriZiyaretAraliklari': """
        CREATE TABLE musteriziyaretaraliklari AS
        SELECT
            musteri_id,
            ziyaret_tarihi,
            LAG(ziyaret_tarihi) OVER (
                PARTITION BY musteri_id ORDER BY ziyaret_tarihi
            ) AS onceki_ziyaret_tarihi,
            (ziyaret_tarihi - LAG(ziyaret_tarihi) OVER (
                PARTITION BY musteri_id ORDER BY ziyaret_tarihi
            )) AS ziyaretler_arasi_gun
        FROM musterigunlukziyaretler
    """,

    'MusteriZiyaretFeatures': """
        CREATE TABLE musteriziyaretfeatures AS
        WITH ziyaret AS (
            SELECT
                musteri_id,
                COUNT(*)                                        AS toplam_ziyaret,
                AVG(ziyaretler_arasi_gun)                       AS ort_ziyaret_araligi,
                STDDEV(ziyaretler_arasi_gun)                    AS std_ziyaret_araligi,
                MIN(ziyaretler_arasi_gun)                       AS min_ziyaret_araligi,
                MAX(ziyaretler_arasi_gun)                       AS max_ziyaret_araligi,
                MAX(ziyaret_tarihi)                             AS son_ziyaret_tarihi,
                MIN(ziyaret_tarihi)                             AS ilk_ziyaret_tarihi,
                (CURRENT_DATE - MAX(ziyaret_tarihi))            AS recency_gun,
                (MAX(ziyaret_tarihi) - MIN(ziyaret_tarihi))     AS musteri_yasam_gun
            FROM musteriziyaretaraliklari
            GROUP BY musteri_id
        ),
        sepet AS (
            SELECT
                musteri_id,
                AVG(gunluk_harcama)     AS ort_sepet_tutari,
                AVG(gunluk_urun_adedi)  AS ort_sepet_urun_adedi,
                SUM(gunluk_harcama)     AS toplam_harcama
            FROM musterigunlukziyaretler
            GROUP BY musteri_id
        ),
        kategori AS (
            SELECT
                s.musteri_id,
                COUNT(DISTINCT k.ana) AS kategori_cesitliligi
            FROM satislar s
            JOIN urunler u  ON s.urun_id      = u.id
            JOIN kategoriler k ON u.kategori_id = k.id
            WHERE s.musteri_id IS NOT NULL
            GROUP BY s.musteri_id
        )
        SELECT
            z.*,
            s.ort_sepet_tutari,
            s.ort_sepet_urun_adedi,
            s.toplam_harcama,
            kt.kategori_cesitliligi
        FROM ziyaret z
        JOIN sepet s        ON z.musteri_id = s.musteri_id
        LEFT JOIN kategori kt ON z.musteri_id = kt.musteri_id
    """,

    # -------------------------------------------------------------------------
    # GRUP B: Zaman Dagilim Tablolari
    # -------------------------------------------------------------------------

    'MusteriSaatDagilimi': """
        CREATE TABLE musterisaatdagilimi AS
        SELECT
            musteri_id,
            saat,
            COUNT(DISTINCT fis_no) AS fis_sayisi
        FROM satislar
        WHERE musteri_id IS NOT NULL
        GROUP BY musteri_id, saat
    """,

    'MusteriGunDagilimi': """
        CREATE TABLE musterigundagilimi AS
        SELECT
            musteri_id,
            EXTRACT(DOW FROM tarih)::INTEGER AS haftanin_gunu,
            COUNT(DISTINCT fis_no)           AS fis_sayisi
        FROM satislar
        WHERE musteri_id IS NOT NULL
        GROUP BY musteri_id, EXTRACT(DOW FROM tarih)
    """,

    'MusteriAyGunDagilimi': """
        CREATE TABLE musteriaygun_dagilimi AS
        SELECT
            musteri_id,
            EXTRACT(DAY FROM tarih)::INTEGER AS ayin_gunu,
            COUNT(DISTINCT fis_no)           AS fis_sayisi
        FROM satislar
        WHERE musteri_id IS NOT NULL
        GROUP BY musteri_id, EXTRACT(DAY FROM tarih)
    """,

    'MusteriAyDagilimi': """
        CREATE TABLE musteriay_dagilimi AS
        SELECT
            musteri_id,
            EXTRACT(MONTH FROM tarih)::INTEGER AS ay,
            EXTRACT(YEAR  FROM tarih)::INTEGER AS yil,
            COUNT(DISTINCT fis_no)             AS fis_sayisi,
            SUM(tutar)                         AS toplam_harcama
        FROM satislar
        WHERE musteri_id IS NOT NULL
        GROUP BY musteri_id,
                 EXTRACT(MONTH FROM tarih),
                 EXTRACT(YEAR  FROM tarih)
    """,

    # -------------------------------------------------------------------------
    # GRUP C: Kategori & Urun Tablolari
    # -------------------------------------------------------------------------

    'MusteriKategoriDagilimi': """
        CREATE TABLE musterikategoridagilimi AS
        SELECT
            s.musteri_id,
            k.ana  AS ana_kategori,
            k.alt1 AS alt_kategori,
            COUNT(DISTINCT s.fis_no) AS fis_sayisi,
            SUM(s.tutar)             AS toplam_harcama,
            SUM(s.miktar)            AS toplam_miktar
        FROM satislar s
        JOIN urunler u     ON s.urun_id      = u.id
        JOIN kategoriler k ON u.kategori_id  = k.id
        WHERE s.musteri_id IS NOT NULL
        GROUP BY s.musteri_id, k.ana, k.alt1
    """,

    'MusteriMarkaDagilimi': """
        CREATE TABLE musterimarka_dagilimi AS
        SELECT
            s.musteri_id,
            m.ad                     AS marka_adi,
            COUNT(DISTINCT s.fis_no) AS fis_sayisi,
            SUM(s.tutar)             AS toplam_harcama,
            SUM(s.miktar)            AS toplam_miktar
        FROM satislar s
        JOIN markalar m ON s.marka_id = m.id
        WHERE s.musteri_id IS NOT NULL
          AND s.marka_id IS NOT NULL
        GROUP BY s.musteri_id, m.ad
    """,

    'MusteriUrunTutarliligi': """
        CREATE TABLE musteriurun_tutarliligi AS
        WITH musteri_urunler AS (
            SELECT
                musteri_id,
                urun_id,
                COUNT(DISTINCT tarih) AS alim_gun_sayisi,
                COUNT(DISTINCT fis_no) AS alim_fis_sayisi,
                SUM(miktar)            AS toplam_miktar
            FROM satislar
            WHERE musteri_id IS NOT NULL
            GROUP BY musteri_id, urun_id
            HAVING COUNT(DISTINCT tarih) >= 2
        )
        SELECT
            musteri_id,
            COUNT(*)                AS tekrar_alinan_urun_sayisi,
            SUM(alim_fis_sayisi)    AS tekrar_toplam_fis,
            AVG(alim_gun_sayisi)    AS ort_urun_tekrar_sayisi,
            MAX(alim_gun_sayisi)    AS max_urun_tekrar_sayisi
        FROM musteri_urunler
        GROUP BY musteri_id
    """,

    # -------------------------------------------------------------------------
    # GRUP D: Fis Bazli Detay (3 eski tablo 1 tabloya birlestirildi)
    # -------------------------------------------------------------------------

    'MusteriFisSepetDetay': """
        CREATE TABLE musterifis_sepet_detay AS
        WITH fis_detay AS (
            SELECT
                s.musteri_id,
                s.fis_no,
                s.tarih,
                COUNT(DISTINCT k.ana)  AS fis_kategori_cesitliligi,
                COUNT(DISTINCT s.urun_id) AS fis_urun_cesitliligi,
                SUM(s.tutar)           AS fis_tutari,
                SUM(s.miktar)          AS fis_toplam_miktar,
                MAX(s.miktar)          AS fis_max_tekil_miktar,
                -- Kategori kombinasyon flagleri (gercek PostgreSQL kategori isimleri)
                BOOL_OR(k.ana  = 'Et & Balık & Kümes Hayvanları') AS kasap_var,
                BOOL_OR(k.ana  = 'Meyve & Sebze - Yeşillik')      AS manav_var,
                BOOL_OR(k.alt1 = 'Piknik Malzemeleri')             AS mangal_malzeme_var,
                BOOL_OR(k.ana  = 'Şarküteri & Sütlük')            AS sarkuteri_var,
                BOOL_OR(k.ana  = 'Unlu Mamuller & Ekmek')         AS firin_var
            FROM satislar s
            JOIN urunler u     ON s.urun_id      = u.id
            JOIN kategoriler k ON u.kategori_id  = k.id
            WHERE s.musteri_id IS NOT NULL
            GROUP BY s.musteri_id, s.fis_no, s.tarih
        )
        SELECT
            musteri_id,
            -- Kategori cesitliligi (Tek Gorevli vs Kategori Gezgini)
            ROUND(AVG(fis_kategori_cesitliligi)::NUMERIC, 2) AS ort_fis_kategori_sayisi,
            MIN(fis_kategori_cesitliligi)                     AS min_fis_kategori_sayisi,
            MAX(fis_kategori_cesitliligi)                     AS max_fis_kategori_sayisi,
            -- Urun cesitliligi
            ROUND(AVG(fis_urun_cesitliligi)::NUMERIC, 2)     AS ort_fis_urun_sayisi,
            -- Tutar dagilimi (Sepet Buyutucu)
            ROUND(AVG(fis_tutari)::NUMERIC, 2)               AS ort_fis_tutari,
            ROUND(STDDEV(fis_tutari)::NUMERIC, 2)            AS std_fis_tutari,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY fis_tutari)::NUMERIC, 2)             AS medyan_fis_tutari,
            -- Tekil urun max miktar (Mahalle Esnafi tespiti)
            ROUND(AVG(fis_max_tekil_miktar)::NUMERIC, 2)     AS ort_max_tekil_miktar,
            MAX(fis_max_tekil_miktar)                         AS max_tekil_miktar,
            -- Kombinasyon skorlari
            COUNT(*) FILTER (WHERE kasap_var AND mangal_malzeme_var) AS mangal_fis_sayisi,
            COUNT(*) FILTER (WHERE kasap_var AND manav_var)          AS kasap_manav_birlikte_fis,
            COUNT(*) FILTER (WHERE kasap_var AND sarkuteri_var)      AS kasap_sarkuteri_birlikte_fis,
            COUNT(*) FILTER (WHERE kasap_var AND manav_var
                                AND fis_kategori_cesitliligi >= 4)   AS ev_tipi_sef_fis_sayisi,
            COUNT(*)                                                  AS toplam_fis_sayisi
        FROM fis_detay
        GROUP BY musteri_id
    """,

    # -------------------------------------------------------------------------
    # GRUP E: Kampanya & Odeme Tablolari
    # -------------------------------------------------------------------------

    'MusteriKampanyaFeatures': """
        CREATE TABLE musterikampanya_features AS
        SELECT
            musteri_id,
            COUNT(DISTINCT fis_no)                                               AS toplam_fis,
            COUNT(DISTINCT fis_no) FILTER (WHERE kampanya_id IS NOT NULL)        AS kampanyali_fis,
            COUNT(DISTINCT fis_no) FILTER (WHERE kampanya_id IS NULL)            AS kampanyasiz_fis,
            ROUND(
                COUNT(DISTINCT fis_no) FILTER (WHERE kampanya_id IS NOT NULL)
                ::NUMERIC /
                NULLIF(COUNT(DISTINCT fis_no), 0) * 100
            , 2)                                                                 AS kampanya_oran_yuzde,
            ROUND(SUM(tutar) FILTER (WHERE kampanya_id IS NOT NULL)::NUMERIC, 2) AS kampanyali_toplam_tutar,
            ROUND(SUM(tutar) FILTER (WHERE kampanya_id IS NULL)::NUMERIC, 2)     AS kampanyasiz_toplam_tutar,
            SUM(miktar) FILTER (WHERE kampanya_id IS NOT NULL)                   AS kampanyali_toplam_miktar
        FROM satislar
        WHERE musteri_id IS NOT NULL
        GROUP BY musteri_id
    """,

    'MusteriBelgeTipiDagilimi': """
        CREATE TABLE musteribelge_tipi_dagilimi AS
        SELECT
            musteri_id,
            belge_tipi,
            EXTRACT(MONTH FROM tarih)::INTEGER AS ay,
            EXTRACT(YEAR  FROM tarih)::INTEGER AS yil,
            EXTRACT(DAY   FROM tarih)::INTEGER AS ayin_gunu,
            COUNT(DISTINCT fis_no)             AS fis_sayisi,
            ROUND(SUM(tutar)::NUMERIC, 2)      AS toplam_harcama
        FROM satislar
        WHERE musteri_id IS NOT NULL
          AND belge_tipi IS NOT NULL
        GROUP BY musteri_id,
                 belge_tipi,
                 EXTRACT(MONTH FROM tarih),
                 EXTRACT(YEAR  FROM tarih),
                 EXTRACT(DAY   FROM tarih)
    """,

    # -------------------------------------------------------------------------
    # GRUP F: Donem Karsilastirma (3 ay + 6 ay)
    # -------------------------------------------------------------------------

    'MusteriDonemKarsilastirma': """
        CREATE TABLE musteridonem_karsilastirma AS
        WITH son3ay AS (
            SELECT
                musteri_id,
                COUNT(DISTINCT tarih)  AS ziyaret_3ay,
                ROUND(SUM(tutar)::NUMERIC, 2)  AS harcama_3ay,
                ROUND(AVG(tutar)::NUMERIC, 2)  AS ort_fis_3ay,
                COUNT(DISTINCT fis_no) AS fis_3ay
            FROM satislar
            WHERE musteri_id IS NOT NULL
              AND tarih >= CURRENT_DATE - INTERVAL '3 months'
            GROUP BY musteri_id
        ),
        onceki3ay AS (
            SELECT
                musteri_id,
                COUNT(DISTINCT tarih)  AS ziyaret_onceki3ay,
                ROUND(SUM(tutar)::NUMERIC, 2)  AS harcama_onceki3ay,
                ROUND(AVG(tutar)::NUMERIC, 2)  AS ort_fis_onceki3ay,
                COUNT(DISTINCT fis_no) AS fis_onceki3ay
            FROM satislar
            WHERE musteri_id IS NOT NULL
              AND tarih >= CURRENT_DATE - INTERVAL '6 months'
              AND tarih <  CURRENT_DATE - INTERVAL '3 months'
            GROUP BY musteri_id
        ),
        son6ay AS (
            SELECT
                musteri_id,
                COUNT(DISTINCT tarih)  AS ziyaret_6ay,
                ROUND(SUM(tutar)::NUMERIC, 2)  AS harcama_6ay
            FROM satislar
            WHERE musteri_id IS NOT NULL
              AND tarih >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY musteri_id
        ),
        onceki6ay AS (
            SELECT
                musteri_id,
                COUNT(DISTINCT tarih)  AS ziyaret_onceki6ay,
                ROUND(SUM(tutar)::NUMERIC, 2)  AS harcama_onceki6ay
            FROM satislar
            WHERE musteri_id IS NOT NULL
              AND tarih >= CURRENT_DATE - INTERVAL '12 months'
              AND tarih <  CURRENT_DATE - INTERVAL '6 months'
            GROUP BY musteri_id
        ),
        son6ay_kat AS (
            SELECT s.musteri_id, k.ana AS ana_kategori,
                   SUM(s.tutar) AS harcama
            FROM satislar s
            JOIN urunler u     ON s.urun_id     = u.id
            JOIN kategoriler k ON u.kategori_id = k.id
            WHERE s.musteri_id IS NOT NULL
              AND s.tarih >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY s.musteri_id, k.ana
        ),
        onceki6ay_kat AS (
            SELECT s.musteri_id, k.ana AS ana_kategori,
                   SUM(s.tutar) AS harcama
            FROM satislar s
            JOIN urunler u     ON s.urun_id     = u.id
            JOIN kategoriler k ON u.kategori_id = k.id
            WHERE s.musteri_id IS NOT NULL
              AND s.tarih >= CURRENT_DATE - INTERVAL '12 months'
              AND s.tarih <  CURRENT_DATE - INTERVAL '6 months'
            GROUP BY s.musteri_id, k.ana
        ),
        kategori_degisim AS (
            SELECT
                COALESCE(s.musteri_id, o.musteri_id)           AS musteri_id,
                COUNT(DISTINCT s.ana_kategori)                  AS son_kategori_sayisi,
                COUNT(DISTINCT o.ana_kategori)                  AS onceki_kategori_sayisi,
                COUNT(DISTINCT o.ana_kategori)
                    FILTER (WHERE s.ana_kategori IS NULL)       AS terk_edilen_kategori
            FROM onceki6ay_kat o
            FULL OUTER JOIN son6ay_kat s
                ON o.musteri_id = s.musteri_id
               AND o.ana_kategori = s.ana_kategori
            GROUP BY COALESCE(s.musteri_id, o.musteri_id)
        )
        SELECT
            COALESCE(s3.musteri_id, o3.musteri_id,
                     s6.musteri_id, o6.musteri_id)  AS musteri_id,
            -- 3 aylik (acil aksiyon etiketleri)
            s3.ziyaret_3ay,
            o3.ziyaret_onceki3ay,
            s3.harcama_3ay,
            o3.harcama_onceki3ay,
            s3.ort_fis_3ay,
            o3.ort_fis_onceki3ay,
            CASE WHEN COALESCE(o3.ziyaret_onceki3ay, 0) > 0
                THEN ROUND(
                    (COALESCE(s3.ziyaret_3ay, 0)::NUMERIC
                     - o3.ziyaret_onceki3ay)
                    / o3.ziyaret_onceki3ay * 100, 2)
            END AS ziyaret_degisim_3ay_yuzde,
            CASE WHEN COALESCE(o3.harcama_onceki3ay, 0) > 0
                THEN ROUND(
                    (COALESCE(s3.harcama_3ay, 0)
                     - o3.harcama_onceki3ay)
                    / o3.harcama_onceki3ay * 100, 2)
            END AS harcama_degisim_3ay_yuzde,
            -- 6 aylik (yapisal kayma etiketleri)
            s6.ziyaret_6ay,
            o6.ziyaret_onceki6ay,
            s6.harcama_6ay,
            o6.harcama_onceki6ay,
            CASE WHEN COALESCE(o6.ziyaret_onceki6ay, 0) > 0
                THEN ROUND(
                    (COALESCE(s6.ziyaret_6ay, 0)::NUMERIC
                     - o6.ziyaret_onceki6ay)
                    / o6.ziyaret_onceki6ay * 100, 2)
            END AS ziyaret_degisim_6ay_yuzde,
            CASE WHEN COALESCE(o6.harcama_onceki6ay, 0) > 0
                THEN ROUND(
                    (COALESCE(s6.harcama_6ay, 0)
                     - o6.harcama_onceki6ay)
                    / o6.harcama_onceki6ay * 100, 2)
            END AS harcama_degisim_6ay_yuzde,
            -- Kategori degisimi
            kd.son_kategori_sayisi,
            kd.onceki_kategori_sayisi,
            kd.terk_edilen_kategori
        FROM son3ay s3
        FULL OUTER JOIN onceki3ay o3
            ON s3.musteri_id = o3.musteri_id
        FULL OUTER JOIN son6ay s6
            ON COALESCE(s3.musteri_id, o3.musteri_id) = s6.musteri_id
        FULL OUTER JOIN onceki6ay o6
            ON COALESCE(s3.musteri_id, o3.musteri_id) = o6.musteri_id
        LEFT JOIN kategori_degisim kd
            ON COALESCE(s3.musteri_id, o3.musteri_id,
                        s6.musteri_id, o6.musteri_id) = kd.musteri_id
    """,

    # -------------------------------------------------------------------------
    # GRUP G: Fiyat & Indirim Feature'lari
    # -------------------------------------------------------------------------

    'MusteriFiyatFeatures': """
        CREATE TABLE musterifiyatfeatures AS
        SELECT
            musteri_id,
            COUNT(*)                                                              AS toplam_satis_satir,
            COUNT(*) FILTER (WHERE belge_indirim_toplami > 0)                    AS indirimli_satir_sayisi,
            COUNT(*) FILTER (WHERE belge_indirim_toplami = 0
                               OR belge_indirim_toplami IS NULL)                 AS indirimsiz_satir_sayisi,
            ROUND(
                COUNT(*) FILTER (WHERE belge_indirim_toplami > 0)::numeric
                / NULLIF(COUNT(*), 0) * 100, 1)                                  AS indirim_oran_yuzde,
            ROUND(
                AVG(CASE WHEN belge_indirim_toplami > 0 AND belge_toplami > 0
                    THEN belge_indirim_toplami / belge_toplami * 100 END)::numeric,
                1)                                                                AS ort_indirim_yuzde,
            SUM(COALESCE(belge_indirim_toplami, 0))                              AS toplam_indirim_tutari,
            SUM(COALESCE(belge_toplami, 0))                                      AS toplam_brut_tutar
        FROM satislar
        WHERE belge_toplami IS NOT NULL AND belge_toplami > 0
        GROUP BY musteri_id
    """,

    # -------------------------------------------------------------------------
    # GRUP G: Beklenen Musteriler (bu hafta ziyareti beklenen duzenli musteriler)
    # -------------------------------------------------------------------------

    'BeklenenMusteriler': """
        CREATE TABLE beklenenmusteriler AS
        SELECT
            v.musteri_id,
            o.ad_soyad,
            m.telefon,
            o.rfm_segment,
            v.son_ziyaret_tarihi,
            (v.son_ziyaret_tarihi::date + ROUND(v.ort_ziyaret_araligi)::int) AS tahmini_ziyaret_tarihi,
            ROUND(v.ort_ziyaret_araligi::numeric, 1)                         AS ort_aralik_gun,
            v.toplam_ziyaret::int                                             AS toplam_ziyaret,
            CASE
                WHEN v.std_ziyaret_araligi / NULLIF(v.ort_ziyaret_araligi, 0) < 0.3
                     AND v.toplam_ziyaret >= 10 THEN 'Yuksek'
                WHEN v.std_ziyaret_araligi / NULLIF(v.ort_ziyaret_araligi, 0) < 0.5
                     AND v.toplam_ziyaret >= 5  THEN 'Orta'
                ELSE 'Dusuk'
            END                                                               AS guven_skoru
        FROM musteriziyaretfeatures v
        JOIN musteriler m ON v.musteri_id = m.id
        JOIN musteridetayozet o ON v.musteri_id = o.musteri_id
        LEFT JOIN musterietiketler e ON v.musteri_id = e.musteri_id
        WHERE v.ort_ziyaret_araligi IS NOT NULL
          AND v.toplam_ziyaret >= 3
          AND COALESCE(e.tamamen_kaybedilmis, FALSE) = FALSE
          AND (v.son_ziyaret_tarihi::date + ROUND(v.ort_ziyaret_araligi)::int)
              BETWEEN date_trunc('week', CURRENT_DATE)::date
                  AND (date_trunc('week', CURRENT_DATE) + INTERVAL '6 days')::date
    """,
}

# PostgreSQL'deki gercek (kucuk harf) tablo isimleri
PG_TABLE_NAMES = {
    'MusteriGunlukZiyaretler':    'musterigunlukziyaretler',
    'MusteriZiyaretAraliklari':   'musteriziyaretaraliklari',
    'MusteriZiyaretFeatures':     'musteriziyaretfeatures',
    'MusteriSaatDagilimi':        'musterisaatdagilimi',
    'MusteriGunDagilimi':         'musterigundagilimi',
    'MusteriAyGunDagilimi':       'musteriaygun_dagilimi',
    'MusteriAyDagilimi':          'musteriay_dagilimi',
    'MusteriKategoriDagilimi':    'musterikategoridagilimi',
    'MusteriMarkaDagilimi':       'musterimarka_dagilimi',
    'MusteriUrunTutarliligi':     'musteriurun_tutarliligi',
    'MusteriFisSepetDetay':       'musterifis_sepet_detay',
    'MusteriKampanyaFeatures':    'musterikampanya_features',
    'MusteriBelgeTipiDagilimi':   'musteribelge_tipi_dagilimi',
    'MusteriDonemKarsilastirma':  'musteridonem_karsilastirma',
    'MusteriFiyatFeatures':       'musterifiyatfeatures',
    'BeklenenMusteriler':         'beklenenmusteriler',
}


def drop_all_tables(cursor):
    """Tum feature tablolarini DROP eder (GRUP F -> A sirasi)."""
    logger.info("Mevcut feature tablolari siliniyor...")
    for name in reversed(TABLE_ORDER):
        pg_name = PG_TABLE_NAMES[name]
        cursor.execute(f'DROP TABLE IF EXISTS {pg_name} CASCADE')
        logger.info(f"  DROP: {pg_name}")


def build_table(cursor, name):
    """Tek bir tabloyu olusturur, sure ve satir sayisini loglar."""
    pg_name = PG_TABLE_NAMES[name]
    sql = CREATE_SQLS[name]
    t0 = datetime.now()
    logger.info(f"Olusturuluyor: {pg_name} ...")
    cursor.execute(sql)
    cursor.execute(f"SELECT COUNT(*) FROM {pg_name}")
    row_count = cursor.fetchone()[0]
    elapsed = (datetime.now() - t0).total_seconds()
    logger.info(f"  Tamamlandi: {pg_name} | {row_count:,} satir | {elapsed:.1f}s")


def run_feature_build(conn=None):
    """
    Feature tablolarini sifirdan olusturan ana fonksiyon.
    Dis baglantiyla veya kendi basina calisabilir.
    """
    is_external_conn = conn is not None
    if not is_external_conn:
        conn = db_engine.get_connection()

    try:
        cursor = conn.cursor()

        total_start = datetime.now()
        logger.info("=" * 60)
        logger.info("FEATURE CORE BUILD BASLIYOR")
        logger.info(f"Toplam {len(TABLE_ORDER)} tablo olusturulacak")
        logger.info("=" * 60)

        # 1) Mevcut tablolari temizle
        drop_all_tables(cursor)
        conn.commit()

        # 2) Her tabloyu sirayla olustur
        for name in TABLE_ORDER:
            build_table(cursor, name)
            conn.commit()  # her tablodan sonra commit (uzun sorgular icin guvenlik)

        total_elapsed = (datetime.now() - total_start).total_seconds()
        logger.info("=" * 60)
        logger.info(f"FEATURE CORE BUILD TAMAMLANDI | Toplam sure: {total_elapsed:.1f}s")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Feature build hatasi: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if not is_external_conn:
            try:
                pool = db_engine.get_pg_pool()
                if pool:
                    pool.putconn(conn)
            except Exception:
                pass


if __name__ == '__main__':
    logger.info("Feature Core Builder dogrudan calistiriliyor...")
    run_feature_build()
