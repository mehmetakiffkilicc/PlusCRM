"""
Musteri Davranis Etiketleme Sistemi - Label Engine
===================================================
Feature tablolarindan musteri etiketlerini hesaplayip musterietiketler
tablosunu doldurur.

Calismadan once feature tablolarinin (feature_core_builder.py) hazir olmasi gerekir.
"""

import os
import sys
import logging
from datetime import datetime

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


def run_label_update(cursor, label_name, pg_col, sql):
    """Tek bir etiketi hesaplayip musterietiketler tablosunu gunceller."""
    t0 = datetime.now()
    cursor.execute(sql)
    count = cursor.rowcount
    elapsed = (datetime.now() - t0).total_seconds()
    logger.info(f"  {label_name:<45} {count:>8,} musteri  ({elapsed:.1f}s)")
    return count


def build_labels(cursor):
    """Tum etiketleri hesaplar."""

    # ================================================================
    # ADIM 0: SIFIRLAMA (RESET) - ESKI ETIKETLERI TEMIZLE
    # ================================================================
    logger.info("Adim 0: Mevcut etiketler ve skorlar sifirlaniyor...")
    # Bool ve Skor kolonlarini belirle
    cursor.execute("""
        UPDATE musterietiketler SET 
            sabah_alisveriscisi = FALSE, aksam_alisveriscisi = FALSE, gece_alisveriscisi = FALSE,
            hafta_sonu_alisveriscisi = FALSE, hafta_ici_alisveriscisi = FALSE, aylik_duzenli_alici = FALSE,
            maas_gunu_alisveriscisi = FALSE, gunluk_ugrayan = FALSE, seyrek_alisverisci = FALSE,
            buyuk_sepet_alisveriscisi = FALSE, kucuk_sepet_alisveriscisi = FALSE, premium_harcayici = FALSE,
            ekonomik_harcayici = FALSE, stokcu_alici = FALSE, tekli_urun_alisveriscisi = FALSE,
            indirim_avcisi = FALSE, promosyon_bagimli = FALSE, fiyat_hassas = FALSE,
            fiyata_duyarsiz = FALSE, coklu_alim_firsatcisi = FALSE, enflasyon_stokcusu = FALSE,
            kampanya_tepkisi_dusuk = FALSE, kasap_odakli = FALSE, manav_odakli = FALSE,
            firinci_odakli = FALSE, sarkuteri_odakli = FALSE, sadece_taze_gidaci = FALSE,
            yoresel_urun_meraklisi = FALSE, taze_gida_kacinani = FALSE, saglikli_yasam_egilimli = FALSE,
            hazir_tuketim_egilimli = FALSE, protein_odakli = FALSE, kafein_yogun_tuketici = FALSE,
            atistirmalik_tuketicisi = FALSE, temizlik_hijyen_odakli = FALSE, kisisel_bakim_tutkunu = FALSE,
            misafir_sofrasi_kurucusu = FALSE, winback_adayi = FALSE, reaktivasyon_potansiyeli = FALSE,
            yeniden_kazanilmis = FALSE, kampanya_duyarli = FALSE, kampanyasiz_sadik = FALSE,
            yemek_karti_kullanicisi = FALSE, ay_sonu_yemek_karti_harcayicisi = FALSE, fatura_musterisi = FALSE,
            sadik_musteri = FALSE, soguyan_musteri = FALSE, kaybedilme_riski_yuksek = FALSE,
            tamamen_kaybedilmis = FALSE, yeniden_kazanilmis_saglik = FALSE, gidip_gelen_musteri = FALSE,
            sepeti_daralan = FALSE, kategori_terk_eden = FALSE, marji_dusuran = FALSE,
            gizli_risk = FALSE, kaybedilmemesi_gereken = FALSE,
            hane_bekar_skoru = 0, hane_cift_skoru = 0, hane_aile_skoru = 0,
            hane_cocuklu_skoru = 0, hane_bebek_skoru = 0, hane_yasli_skoru = 0,
            hane_evcil_hayvan_skoru = 0, hane_araba_skoru = 0, hane_toplu_alim_skoru = 0,
            churn_skoru = 0
    """)
    logger.info("  Tum etiketler sifirlandi.")

    logger.info("\nAdim 1: musterietiketler tablosu guncelleniyor...")

    # ================================================================
    # KAT 1: ZIYARET DAVRANISI
    # ================================================================
    logger.info("\nKAT 1: Ziyaret Davranisi")

    # Sabah: 06-11, Aksam: 17-21, Gece: 22-05
    run_label_update(cursor, "Sabah Alisveriscisi", "sabah_alisveriscisi", """
        UPDATE musterietiketler SET sabah_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterisaatdagilimi
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE saat BETWEEN 6 AND 11)::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.40
        )
    """)

    run_label_update(cursor, "Aksam Alisveriscisi", "aksam_alisveriscisi", """
        UPDATE musterietiketler SET aksam_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterisaatdagilimi
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE saat BETWEEN 17 AND 21)::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.40
        )
    """)

    run_label_update(cursor, "Gece Alisveriscisi", "gece_alisveriscisi", """
        UPDATE musterietiketler SET gece_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterisaatdagilimi
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE saat >= 22 OR saat <= 5)::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.20
        )
    """)

    # Hafta sonu: Cumartesi=6, Pazar=0 (PostgreSQL EXTRACT DOW: 0=Pazar, 6=Cumartesi)
    run_label_update(cursor, "Hafta Sonu Alisveriscisi", "hafta_sonu_alisveriscisi", """
        UPDATE musterietiketler SET hafta_sonu_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterigundagilimi
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE haftanin_gunu IN (0, 6))::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.45
        )
    """)

    run_label_update(cursor, "Hafta Ici Alisveriscisi", "hafta_ici_alisveriscisi", """
        UPDATE musterietiketler SET hafta_ici_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterigundagilimi
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE haftanin_gunu BETWEEN 1 AND 5)::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.70
        )
    """)

    run_label_update(cursor, "Aylik Duzenli Alici", "aylik_duzenli_alici", """
        UPDATE musterietiketler SET aylik_duzenli_alici = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriay_dagilimi
            GROUP BY musteri_id
            HAVING COUNT(*) >= 3
               AND STDDEV(fis_sayisi) / NULLIF(AVG(fis_sayisi), 0) <= 0.60
        )
    """)

    run_label_update(cursor, "Maas Gunu Alisveriscisi", "maas_gunu_alisveriscisi", """
        UPDATE musterietiketler SET maas_gunu_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musteriaygun_dagilimi
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE ayin_gunu BETWEEN 1 AND 5)::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.25
        )
    """)

    run_label_update(cursor, "Gunluk Ugrayan", "gunluk_ugrayan", """
        UPDATE musterietiketler SET gunluk_ugrayan = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE ort_ziyaret_araligi <= 5
            AND toplam_ziyaret >= 10
        )
    """)

    run_label_update(cursor, "Seyrek Alisverisci", "seyrek_alisverisci", """
        UPDATE musterietiketler SET seyrek_alisverisci = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE ort_ziyaret_araligi >= 25
            AND toplam_ziyaret >= 2
        )
    """)

    # ================================================================
    # KAT 2: SEPET & HARCAMA DAVRANISI
    # ================================================================
    logger.info("\nKAT 2: Sepet & Harcama Davranisi")

    run_label_update(cursor, "Buyuk Sepet Alisveriscisi", "buyuk_sepet_alisveriscisi", """
        UPDATE musterietiketler SET buyuk_sepet_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifis_sepet_detay
            WHERE ort_fis_tutari >= 250
            AND toplam_fis_sayisi >= 3
        )
    """)

    run_label_update(cursor, "Kucuk Sepet Alisveriscisi", "kucuk_sepet_alisveriscisi", """
        UPDATE musterietiketler SET kucuk_sepet_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifis_sepet_detay
            WHERE ort_fis_tutari <= 100
            AND toplam_fis_sayisi >= 3
        )
    """)

    run_label_update(cursor, "Premium Harcayici", "premium_harcayici", """
        UPDATE musterietiketler SET premium_harcayici = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE toplam_harcama >= 5000
            AND toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "Ekonomik Harcayici", "ekonomik_harcayici", """
        UPDATE musterietiketler SET ekonomik_harcayici = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE toplam_harcama < 500
            AND toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "B2B Mahalle Esnafi", "b2b_mahalle_esnafi", """
        UPDATE musterietiketler SET b2b_mahalle_esnafi = TRUE
        WHERE musteri_id IN (
            SELECT id FROM musteriler WHERE tip = 'Kurumsal'
        )
    """)

    run_label_update(cursor, "Stokcu Alici", "stokcu_alici", """
        UPDATE musterietiketler SET stokcu_alici = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifis_sepet_detay
            WHERE ort_fis_urun_sayisi >= 10
            AND toplam_fis_sayisi >= 3
        )
    """)

    run_label_update(cursor, "Tekli Urun Alisveriscisi", "tekli_urun_alisveriscisi", """
        UPDATE musterietiketler SET tekli_urun_alisveriscisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifis_sepet_detay
            WHERE ort_fis_urun_sayisi <= 2
            AND toplam_fis_sayisi >= 3
        )
    """)

    # ================================================================
    # KAT 3: FIYAT & KAMPANYA DUYARLILIGI
    # ================================================================
    logger.info("\nKAT 3: Fiyat & Kampanya Duyarliligi")

    run_label_update(cursor, "Indirim Avcisi", "indirim_avcisi", """
        UPDATE musterietiketler SET indirim_avcisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifiyatfeatures
            WHERE indirim_oran_yuzde >= 25
            AND ort_indirim_yuzde >= 10
            AND toplam_satis_satir >= 3
        )
    """)

    run_label_update(cursor, "Promosyon Bagimli", "promosyon_bagimli", """
        UPDATE musterietiketler SET promosyon_bagimli = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifiyatfeatures
            WHERE indirim_oran_yuzde >= 60
            AND toplam_satis_satir >= 5
        )
    """)

    run_label_update(cursor, "Fiyat Hassas", "fiyat_hassas", """
        UPDATE musterietiketler SET fiyat_hassas = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterimarka_dagilimi
            GROUP BY musteri_id
            HAVING MAX(toplam_harcama) / NULLIF(SUM(toplam_harcama), 0) < 0.40
               AND COUNT(DISTINCT marka_adi) >= 3
               AND SUM(fis_sayisi) >= 3
        )
    """)

    run_label_update(cursor, "Fiyata Duyarsiz", "fiyata_duyarsiz", """
        UPDATE musterietiketler SET fiyata_duyarsiz = TRUE
        WHERE musteri_id IN (
            SELECT md.musteri_id FROM musterimarka_dagilimi md
            JOIN musteriurun_tutarliligi ut ON md.musteri_id = ut.musteri_id
            GROUP BY md.musteri_id, ut.tekrar_alinan_urun_sayisi
            HAVING MAX(md.toplam_harcama) / NULLIF(SUM(md.toplam_harcama), 0) >= 0.60
               AND ut.tekrar_alinan_urun_sayisi >= 3
               AND SUM(md.fis_sayisi) >= 3
        )
    """)

    run_label_update(cursor, "Coklu Alim Firsatcisi", "coklu_alim_firsatcisi", """
        UPDATE musterietiketler SET coklu_alim_firsatcisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterikampanya_features
            WHERE kampanyali_toplam_miktar >= 17
            AND toplam_fis >= 3
        )
    """)

    run_label_update(cursor, "Enflasyon Stokcusu", "enflasyon_stokcusu", """
        UPDATE musterietiketler SET enflasyon_stokcusu = TRUE
        WHERE musteri_id IN (
            SELECT ad.musteri_id FROM musteriay_dagilimi ad
            JOIN musterikategoridagilimi kd ON ad.musteri_id = kd.musteri_id
            GROUP BY ad.musteri_id
            HAVING MAX(ad.toplam_harcama) / NULLIF(AVG(ad.toplam_harcama), 0) >= 2.5
               AND COUNT(DISTINCT ad.ay) >= 3
               AND SUM(CASE WHEN kd.ana_kategori IN (
                               'Et & Balık & Kümes Hayvanları',
                               'Meyve & Sebze - Yeşillik',
                               'Unlu Mamuller & Ekmek',
                               'Şarküteri & Sütlük',
                               'Bakliyat, Makarna',
                               'Kahvaltılık Ürünler & Süt'
                           ) THEN kd.toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(kd.toplam_harcama), 0) >= 0.40
        )
    """)

    run_label_update(cursor, "Kampanya Tepkisi Dusuk", "kampanya_tepkisi_dusuk", """
        UPDATE musterietiketler SET kampanya_tepkisi_dusuk = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifiyatfeatures
            WHERE indirim_oran_yuzde < 5
            AND toplam_satis_satir >= 3
        )
    """)

    # ================================================================
    # KAT 4: TAZE GIDA & YEREL MARKET GUCU
    # ================================================================
    logger.info("\nKAT 4: Taze Gida & Yerel Market Gucu")

    # Gercek kategori adlari (PostgreSQL'den dogrulandi)
    # kategori_payi = musteri icindeki harcama orani (subquery ile hesaplanir)
    taze_gida_labels = [
        # (label_name, pg_col, ana_kategori_adi, payi_esik, min_fis)
        ("Kasap Odakli",     "kasap_odakli",     "Et & Balık & Kümes Hayvanları", 0.35, 3),
        ("Manav Odakli",     "manav_odakli",     "Meyve & Sebze - Yeşillik",      0.30, 3),
        ("Firinci Odakli",   "firinci_odakli",   "Unlu Mamuller & Ekmek",         0.10, 3),
        ("Sarkuteri Odakli", "sarkuteri_odakli", "Şarküteri & Sütlük",            0.30, 3),
    ]

    for label_name, pg_col, ana_kat, payi_esik, min_fis in taze_gida_labels:
        run_label_update(cursor, label_name, pg_col, f"""
            UPDATE musterietiketler SET {pg_col} = TRUE
            WHERE musteri_id IN (
                WITH musteri_toplam AS (
                    SELECT musteri_id, SUM(toplam_harcama) AS toplam
                    FROM musterikategoridagilimi
                    GROUP BY musteri_id
                )
                SELECT k.musteri_id
                FROM musterikategoridagilimi k
                JOIN musteri_toplam mt ON k.musteri_id = mt.musteri_id
                WHERE k.ana_kategori = '{ana_kat}'
                  AND k.toplam_harcama / NULLIF(mt.toplam, 0) >= {payi_esik}
                  AND k.fis_sayisi >= {min_fis}
            )
        """)

    run_label_update(cursor, "Sadece Taze Gidaci", "sadece_taze_gidaci", """
        UPDATE musterietiketler SET sadece_taze_gidaci = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterikategoridagilimi
            GROUP BY musteri_id
            HAVING SUM(CASE WHEN ana_kategori IN (
                        'Et & Balık & Kümes Hayvanları',
                        'Meyve & Sebze - Yeşillik',
                        'Şarküteri & Sütlük',
                        'Unlu Mamuller & Ekmek'
                    ) THEN toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(toplam_harcama), 0) >= 0.60
            AND COUNT(DISTINCT CASE WHEN ana_kategori IN (
                        'Et & Balık & Kümes Hayvanları',
                        'Meyve & Sebze - Yeşillik',
                        'Şarküteri & Sütlük',
                        'Unlu Mamuller & Ekmek'
                    ) THEN ana_kategori END) >= 2
            AND SUM(fis_sayisi) >= 3
        )
    """)

    run_label_update(cursor, "Yoresel Urun Meraklisi", "yoresel_urun_meraklisi", """
        UPDATE musterietiketler SET yoresel_urun_meraklisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterikategoridagilimi
            GROUP BY musteri_id
            HAVING SUM(CASE WHEN ana_kategori IN (
                        'Bakliyat, Makarna',
                        'Baharat & Tuz',
                        'Konserve & Salça & Hazır Yemek'
                    ) THEN toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(toplam_harcama), 0) >= 0.20
            AND SUM(fis_sayisi) >= 3
        )
    """)

    run_label_update(cursor, "Taze Gida Kacinani", "taze_gida_kacinani", """
        UPDATE musterietiketler SET taze_gida_kacinani = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterikategoridagilimi
            GROUP BY musteri_id
            HAVING SUM(CASE WHEN ana_kategori IN (
                        'Et & Balık & Kümes Hayvanları',
                        'Meyve & Sebze - Yeşillik',
                        'Şarküteri & Sütlük',
                        'Unlu Mamuller & Ekmek'
                    ) THEN toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(toplam_harcama), 0) < 0.10
            AND SUM(fis_sayisi) >= 5
        )
    """)

    # ================================================================
    # KAT 5: KATEGORI ILGI ALANLARI
    # ================================================================
    logger.info("\nKAT 5: Kategori Ilgi Alanlari")

    # (label_name, pg_col, ana_kategori_adi, payi_esik, min_fis)
    kat5_labels = [
        ("Saglikli Yasam Egilimli",  "saglikli_yasam_egilimli",  None,                                None, 3),
        ("Hazir Tuketim Egilimli",   "hazir_tuketim_egilimli",   "Konserve & Salça & Hazır Yemek",    0.15, 3),
        ("Protein Odakli",           "protein_odakli",           None,                                None, 3),
        ("Kafein Yogun Tuketici",    "kafein_yogun_tuketici",    "Çay & Kahve & Şeker ",              0.15, 3),
        ("Atistirmalik Tuketicisi",  "atistirmalik_tuketicisi",  "Atıştırmalık & Bisküvi",            0.15, 3),
        ("Temizlik Hijyen Odakli",   "temizlik_hijyen_odakli",   "Temizlik & Kağıt Ürünler",          0.10, 3),
        ("Kisisel Bakim Tutkunu",    "kisisel_bakim_tutkunu",    "Kozmetik & Kişisel Bakım",          0.10, 3),
        ("Misafir Sofrasi Kurucusu", "misafir_sofrasi_kurucusu", None,                                None, 3),
    ]

    for label_name, pg_col, ana_kat, payi_esik, min_fis in kat5_labels:
        if ana_kat is None:
            continue  # Ozel hesaplama gerektiren etiketler asagida
        run_label_update(cursor, label_name, pg_col, f"""
            UPDATE musterietiketler SET {pg_col} = TRUE
            WHERE musteri_id IN (
                WITH musteri_toplam AS (
                    SELECT musteri_id, SUM(toplam_harcama) AS toplam
                    FROM musterikategoridagilimi
                    GROUP BY musteri_id
                )
                SELECT k.musteri_id
                FROM musterikategoridagilimi k
                JOIN musteri_toplam mt ON k.musteri_id = mt.musteri_id
                WHERE k.ana_kategori = '{ana_kat}'
                  AND k.toplam_harcama / NULLIF(mt.toplam, 0) >= {payi_esik}
                  AND k.fis_sayisi >= {min_fis}
            )
        """)

    # Saglikli Yasam: Meyve/Sebze payi >= 0.25 VE (Atistirmalik+Konserve+Dondurulmus) <= 0.15
    run_label_update(cursor, "Saglikli Yasam Egilimli", "saglikli_yasam_egilimli", """
        UPDATE musterietiketler SET saglikli_yasam_egilimli = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterikategoridagilimi
            GROUP BY musteri_id
            HAVING SUM(CASE WHEN ana_kategori = 'Meyve & Sebze - Yeşillik'
                        THEN toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(toplam_harcama), 0) >= 0.25
            AND SUM(CASE WHEN ana_kategori IN (
                        'Atıştırmalık & Bisküvi',
                        'Konserve & Salça & Hazır Yemek',
                        'Dondurulmuş Ürünler'
                    ) THEN toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(toplam_harcama), 0) <= 0.15
            AND SUM(fis_sayisi) >= 5
        )
    """)

    # Protein Odakli: Et + Islenmis Et toplam payi >= 0.30
    run_label_update(cursor, "Protein Odakli", "protein_odakli", """
        UPDATE musterietiketler SET protein_odakli = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musterikategoridagilimi
            GROUP BY musteri_id
            HAVING SUM(CASE WHEN ana_kategori IN (
                        'Et & Balık & Kümes Hayvanları',
                        'İşlenmiş Et Ürünleri'
                    ) THEN toplam_harcama ELSE 0 END)
                   / NULLIF(SUM(toplam_harcama), 0) >= 0.30
            AND SUM(fis_sayisi) >= 3
        )
    """)

    # Misafir Sofrasi: ort_fis_tutari >= 1000 AND ort_fis_kategori >= 5
    run_label_update(cursor, "Misafir Sofrasi Kurucusu", "misafir_sofrasi_kurucusu", """
        UPDATE musterietiketler SET misafir_sofrasi_kurucusu = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterifis_sepet_detay
            WHERE ort_fis_tutari >= 1000
            AND ort_fis_kategori_sayisi >= 5
            AND toplam_fis_sayisi >= 3
        )
    """)

    # ================================================================
    # KAT 6: HANE YAPISI (SKORLAR)
    # ================================================================
    logger.info("\nKAT 6: Hane Yapisi Skorlari")

    # Hane Yapisi skorlari - mevcut feature tablolarindan hesaplanir (0.0-1.0 arasi)

    # Percentile esikleri (musteriziyaretfeatures, min 3 ziyaret)
    # P25 tutar=309, P75 tutar=984, P25 urun=5.5, P75 urun=13.9, P25 kat=6, P75 kat=14

    # BEKAR / TEK KISILIK: kucuk sepet + az urun
    # Sepet P25=309 TL, P75=984 TL. Bekar skor yalnizca P25 altinda yuksek kalsin;
    # P75 ustundeyse sifira yaklassin. Bu sayede cift ve aile skorlariyla cakisma engellenir.
    cursor.execute("""
        UPDATE musterietiketler SET hane_bekar_skoru = sub.skor
        FROM (
            WITH harcama AS (
                SELECT musteri_id,
                    SUM(fis_sayisi) AS toplam_fis,
                    SUM(toplam_harcama) AS toplam_harcama,
                    SUM(toplam_miktar) AS toplam_miktar
                FROM musterikategoridagilimi GROUP BY musteri_id
            )
            SELECT musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    -- Tutar: P25(309) altinda maks, P75(984) ustunde sifir
                    GREATEST(0.0, 1.0 - LEAST(toplam_harcama / NULLIF(toplam_fis,0), 984) / 309.0) * 0.5 +
                    -- Miktar: P25(5.5) altinda maks, P75(13.9) ustunde sifir
                    GREATEST(0.0, 1.0 - LEAST(toplam_miktar / NULLIF(toplam_fis,0), 13.9) / 5.5) * 0.5
                )) AS NUMERIC), 3) AS skor
            FROM harcama WHERE toplam_fis >= 1
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Bekar/Tek Kisilik Skoru':<45} {cursor.rowcount:>8,} musteri")

    # GENIS AILE: buyuk sepet + cok urun + cok kategori
    cursor.execute("""
        UPDATE musterietiketler SET hane_aile_skoru = sub.skor
        FROM (
            WITH harcama AS (
                SELECT musteri_id,
                    SUM(fis_sayisi) AS toplam_fis,
                    SUM(toplam_harcama) AS toplam_harcama,
                    SUM(toplam_miktar) AS toplam_miktar,
                    COUNT(DISTINCT ana_kategori) AS kat_sayisi
                FROM musterikategoridagilimi GROUP BY musteri_id
            )
            SELECT musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    LEAST(toplam_harcama / NULLIF(toplam_fis,0), 1968) / 1968.0 * 0.4 +
                    LEAST(toplam_miktar / NULLIF(toplam_fis,0), 27.8) / 27.8 * 0.4 +
                    LEAST(kat_sayisi, 28) / 28.0 * 0.2
                )) AS NUMERIC), 3) AS skor
            FROM harcama WHERE toplam_fis >= 1
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Genis Aile Skoru':<45} {cursor.rowcount:>8,} musteri")

    # CIFT HANE: orta sepet (P25-P75 arasi = 309-984 TL) + orta miktar (5.5-13.9)
    # Kucuk sepetler bekar, buyuk sepetler aile kategorisinde olmali.
    # Cift skor yalnizca P25-P75 araligi icinde yuksek kalsin; bu araliktan uzakinca duser.
    cursor.execute("""
        UPDATE musterietiketler SET hane_cift_skoru = sub.skor
        FROM (
            WITH harcama AS (
                SELECT musteri_id,
                    SUM(fis_sayisi) AS toplam_fis,
                    SUM(toplam_harcama) AS toplam_harcama,
                    SUM(toplam_miktar) AS toplam_miktar
                FROM musterikategoridagilimi GROUP BY musteri_id
            ),
            normalized AS (
                SELECT musteri_id,
                    toplam_harcama / NULLIF(toplam_fis, 0) AS ort_tutar,
                    toplam_miktar / NULLIF(toplam_fis, 0) AS ort_miktar
                FROM harcama WHERE toplam_fis >= 1
            )
            SELECT musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    -- Tutar P25(309)-P75(984) araliginda en yuksek, disinda hizla duser
                    CASE
                        WHEN ort_tutar < 309 THEN 0.0
                        WHEN ort_tutar <= 984 THEN (ort_tutar - 309) / (984.0 - 309.0)
                        ELSE GREATEST(0.0, 1.0 - (ort_tutar - 984) / 984.0)
                    END * 0.5 +
                    -- Miktar P25(5.5)-P75(13.9) araliginda en yuksek
                    CASE
                        WHEN ort_miktar < 5.5 THEN 0.0
                        WHEN ort_miktar <= 13.9 THEN (ort_miktar - 5.5) / (13.9 - 5.5)
                        ELSE GREATEST(0.0, 1.0 - (ort_miktar - 13.9) / 13.9)
                    END * 0.5
                )) AS NUMERIC), 3) AS skor
            FROM normalized
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Cift Hane Skoru':<45} {cursor.rowcount:>8,} musteri")

    # COCUKLU HANE: Sadece cocuklara yonelik kategoriler (Oyuncak, Cocuk urunleri) ve yuksek frekans
    # NOT: bebek maması/bebek bisküvisi kasıtlı olarak çıkarıldı — bunlar bebek etiketine ait.
    # Çocuklu hane = okul çağı çocuk sinyali (oyuncak, çocuk giyim, kırtasiye vb.)
    cursor.execute("""
        UPDATE musterietiketler SET hane_cocuklu_skoru = sub.skor
        FROM (
            WITH cocuk_kat AS (
                SELECT musteri_id,
                    SUM(toplam_harcama) FILTER (WHERE
                        alt_kategori ILIKE '%oyuncak%'
                        OR alt_kategori ILIKE '%çocuk%'
                        OR alt_kategori ILIKE '%kırtasiye%'
                        OR alt_kategori ILIKE '%okul%'
                    ) AS cocuk_harcama,
                    SUM(toplam_harcama) AS toplam_harcama,
                    SUM(fis_sayisi) FILTER (WHERE
                        alt_kategori ILIKE '%oyuncak%'
                        OR alt_kategori ILIKE '%çocuk%'
                        OR alt_kategori ILIKE '%kırtasiye%'
                    ) AS cocuk_fis
                FROM musterikategoridagilimi
                GROUP BY musteri_id
                HAVING SUM(fis_sayisi) >= 3
            )
            SELECT musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    (COALESCE(cocuk_harcama, 0) / NULLIF(toplam_harcama, 0) / 0.10) * 0.6 +
                    (LEAST(COALESCE(cocuk_fis, 0), 5) / 5.0) * 0.4
                )) AS NUMERIC), 3) AS skor
            FROM cocuk_kat
            WHERE COALESCE(cocuk_harcama, 0) > 0
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Cocuklu Hane Skoru':<45} {cursor.rowcount:>8,} musteri")

    # BEBEKLI HANE: Bebek Bakim Urunleri kategorisinden gercek ve tekrarlayan alim
    # Kriter: min 5 fis (3 yetersiz — tesadüfi alımı eliyor) VE bebek harcama payi >= %5
    # (onceki %10 esigi cok düşüktü: bir kez büyük bebek bezi alimi skoru 1.0'a cikiyordu)
    cursor.execute("""
        UPDATE musterietiketler SET hane_bebek_skoru = sub.skor
        FROM (
            WITH bebek AS (
                SELECT musteri_id,
                    SUM(toplam_harcama) AS bebek_harcama,
                    SUM(fis_sayisi) AS bebek_fis
                FROM musterikategoridagilimi
                WHERE (ana_kategori ILIKE '%bebek%' OR alt_kategori ILIKE '%bebek%')
                  AND alt_kategori NOT ILIKE '%oyuncak%'
                  AND alt_kategori NOT ILIKE '%su%'
                GROUP BY musteri_id
                HAVING SUM(fis_sayisi) >= 5
            ),
            toplam AS (
                SELECT musteri_id, SUM(toplam_harcama) AS toplam
                FROM musterikategoridagilimi GROUP BY musteri_id
            )
            SELECT b.musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    (b.bebek_harcama / NULLIF(t.toplam, 0) - 0.05) / 0.15 * 0.6 +
                    (LEAST(b.bebek_fis, 10) / 10.0) * 0.4
                )) AS NUMERIC), 3) AS skor
            FROM bebek b
            JOIN toplam t ON b.musteri_id = t.musteri_id
            WHERE b.bebek_harcama / NULLIF(t.toplam, 0) >= 0.05
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Bebekli Hane Skoru':<45} {cursor.rowcount:>8,} musteri")

    # YASLI BIREY: Saglik/bakim agirlikli, duzenli kucuk-orta sepet. 
    # Not: %bakliyat% ve %temizlik% cok genel oldugu icin cikarildi, %kozmetik% icindeki bakim urunlerine odaklanildi.
    cursor.execute("""
        UPDATE musterietiketler SET hane_yasli_skoru = sub.skor
        FROM (
            WITH saglik AS (
                SELECT musteri_id,
                    SUM(toplam_harcama) FILTER (WHERE
                        ana_kategori ILIKE '%kozmetik%' OR ana_kategori ILIKE '%saglik%' OR alt_kategori ILIKE '%hasta%'
                    ) AS saglik_harcama,
                    SUM(toplam_harcama) AS toplam
                FROM musterikategoridagilimi GROUP BY musteri_id
            )
            SELECT s.musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    COALESCE(s.saglik_harcama, 0) / NULLIF(s.toplam, 0) / 0.20 * 0.5 +
                    CASE WHEN v.ort_ziyaret_araligi BETWEEN 10 AND 25
                         THEN 0.5 ELSE 0.0 END
                )) AS NUMERIC), 3) AS skor
            FROM saglik s
            JOIN musteriziyaretfeatures v ON s.musteri_id = v.musteri_id
            WHERE v.toplam_ziyaret >= 5
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Yasli Birey Hane Skoru':<45} {cursor.rowcount:>8,} musteri")

    # EVCIL HAYVAN SAHIBI: Hayvan Yemleri alt kategorisi. Duzenli alim (fis >= 2) sart.
    cursor.execute("""
        UPDATE musterietiketler SET hane_evcil_hayvan_skoru = sub.skor
        FROM (
            WITH evcil AS (
                SELECT musteri_id,
                    SUM(toplam_harcama) AS evcil_harcama,
                    SUM(fis_sayisi) AS evcil_fis
                FROM musterikategoridagilimi
                WHERE (alt_kategori ILIKE '%hayvan%' OR alt_kategori ILIKE '%evcil%')
                GROUP BY musteri_id
                HAVING SUM(fis_sayisi) >= 2
            ),
            toplam AS (
                SELECT musteri_id, SUM(toplam_harcama) AS toplam
                FROM musterikategoridagilimi GROUP BY musteri_id
            )
            SELECT e.musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    (e.evcil_harcama / NULLIF(t.toplam, 0)) / 0.05 * 0.6 +
                    LEAST(e.evcil_fis, 5) / 5.0 * 0.4
                )) AS NUMERIC), 3) AS skor
            FROM evcil e JOIN toplam t ON e.musteri_id = t.musteri_id
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Evcil Hayvan Sahibi Skoru':<45} {cursor.rowcount:>8,} musteri")

    # ARACLI MUSTERI: Buyuk sepet + Icecek (su/kola) payi yuksek + hafta sonu yogunlasma
    cursor.execute("""
        UPDATE musterietiketler SET hane_araba_skoru = sub.skor
        FROM (
            WITH icecek AS (
                SELECT musteri_id,
                    SUM(toplam_harcama) FILTER (WHERE ana_kategori ILIKE '%ecek%') AS icecek_harcama,
                    SUM(toplam_harcama) AS toplam
                FROM musterikategoridagilimi GROUP BY musteri_id
            ),
            hafta_sonu AS (
                SELECT musteri_id,
                    SUM(fis_sayisi) FILTER (WHERE haftanin_gunu IN (0, 6)) AS hs_fis,
                    SUM(fis_sayisi) AS toplam_fis
                FROM musterigundagilimi GROUP BY musteri_id
            )
            SELECT v.musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    LEAST(v.ort_sepet_tutari, 984*2) / (984*2.0) * 0.4 +
                    COALESCE(i.icecek_harcama, 0) / NULLIF(i.toplam, 0) / 0.15 * 0.3 +
                    COALESCE(h.hs_fis::FLOAT / NULLIF(h.toplam_fis, 0), 0) / 0.5 * 0.3
                )) AS NUMERIC), 3) AS skor
            FROM musteriziyaretfeatures v
            LEFT JOIN icecek i ON v.musteri_id = i.musteri_id
            LEFT JOIN hafta_sonu h ON v.musteri_id = h.musteri_id
            WHERE v.toplam_ziyaret >= 3
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Aracli Musteri Skoru':<45} {cursor.rowcount:>8,} musteri")

    # TOPLU ALIM EGILIMLI: Fis basina max tekil miktar yuksek
    cursor.execute("""
        UPDATE musterietiketler SET hane_toplu_alim_skoru = sub.skor
        FROM (
            SELECT musteri_id,
                ROUND(CAST(LEAST(1.0, GREATEST(0.0,
                    LEAST(ort_max_tekil_miktar, 10) / 10.0
                )) AS NUMERIC), 3) AS skor
            FROM musterifis_sepet_detay
            WHERE toplam_fis_sayisi >= 1
        ) sub
        WHERE musterietiketler.musteri_id = sub.musteri_id
    """)
    logger.info(f"  {'Toplu Alim Egilimli Skoru':<45} {cursor.rowcount:>8,} musteri")

    # ================================================================
    # KAT 7: KANAL & KAMPANYA
    # ================================================================
    logger.info("\nKAT 7: Kanal & Kampanya")

    run_label_update(cursor, "Winback Adayi", "winback_adayi", """
        UPDATE musterietiketler SET winback_adayi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE recency_gun BETWEEN 90 AND 270
            AND toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "Reaktivasyon Potansiyeli", "reaktivasyon_potansiyeli", """
        UPDATE musterietiketler SET reaktivasyon_potansiyeli = TRUE
        WHERE musteri_id IN (
            SELECT v.musteri_id FROM musteriziyaretfeatures v
            JOIN musteridonem_karsilastirma d ON v.musteri_id = d.musteri_id
            WHERE v.recency_gun BETWEEN 90 AND 180
            AND d.ziyaret_degisim_3ay_yuzde < -50
            AND v.toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "Yeniden Kazanilmis (Kanal)", "yeniden_kazanilmis", """
        UPDATE musterietiketler SET yeniden_kazanilmis = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE max_ziyaret_araligi >= 90
            AND recency_gun <= 30
            AND toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "Kampanya Duyarli", "kampanya_duyarli", """
        UPDATE musterietiketler SET kampanya_duyarli = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterikampanya_features
            WHERE kampanya_oran_yuzde >= 80
            AND toplam_fis >= 3
        )
    """)

    run_label_update(cursor, "Kampanyasiz Sadik", "kampanyasiz_sadik", """
        UPDATE musterietiketler SET kampanyasiz_sadik = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musterikampanya_features
            WHERE kampanya_oran_yuzde <= 10
            AND toplam_fis >= 3
        )
    """)

    # ================================================================
    # KAT 8: ODEME & FINANSAL DAVRANIS
    # ================================================================
    logger.info("\nKAT 8: Odeme & Finansal Davranis")

    run_label_update(cursor, "Yemek Karti Kullanicisi", "yemek_karti_kullanicisi", """
        UPDATE musterietiketler SET yemek_karti_kullanicisi = TRUE
        WHERE musteri_id IN (
            SELECT DISTINCT musteri_id FROM musteribelge_tipi_dagilimi
            WHERE belge_tipi LIKE '%emek%'
        )
    """)

    run_label_update(cursor, "Ay Sonu YK Harcayicisi", "ay_sonu_yemek_karti_harcayicisi", """
        UPDATE musterietiketler SET ay_sonu_yemek_karti_harcayicisi = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id
            FROM musteribelge_tipi_dagilimi
            WHERE belge_tipi LIKE '%emek%'
            GROUP BY musteri_id
            HAVING SUM(fis_sayisi) >= 3
               AND SUM(fis_sayisi) FILTER (WHERE ayin_gunu >= 25)::float
                   / NULLIF(SUM(fis_sayisi), 0) >= 0.30
        )
    """)

    run_label_update(cursor, "Fatura Musterisi", "fatura_musterisi", """
        UPDATE musterietiketler SET fatura_musterisi = TRUE
        WHERE musteri_id IN (
            SELECT DISTINCT musteri_id FROM musteribelge_tipi_dagilimi
            WHERE belge_tipi = 'Fatura'
        )
    """)

    # ================================================================
    # KAT 9: SADAKAT, RISK & MUSTERI SAGLIGI
    # ================================================================
    logger.info("\nKAT 9: Sadakat, Risk & Musteri Sagligi")

    run_label_update(cursor, "Sadik Musteri", "sadik_musteri", """
        UPDATE musterietiketler SET sadik_musteri = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE toplam_ziyaret >= 5
            AND recency_gun <= 60
            AND musteri_yasam_gun >= 180
        )
    """)

    run_label_update(cursor, "Soguyan Musteri", "soguyan_musteri", """
        UPDATE musterietiketler SET soguyan_musteri = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteridonem_karsilastirma
            WHERE ziyaret_degisim_3ay_yuzde < -50
            AND ziyaret_onceki3ay >= 3
        )
    """)

    run_label_update(cursor, "Kaybedilme Riski Yuksek", "kaybedilme_riski_yuksek", """
        UPDATE musterietiketler SET kaybedilme_riski_yuksek = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteridonem_karsilastirma
            WHERE harcama_degisim_3ay_yuzde < -50
            AND ziyaret_degisim_3ay_yuzde < -30
            AND ziyaret_onceki3ay >= 3
        )
    """)

    run_label_update(cursor, "Tamamen Kaybedilmis", "tamamen_kaybedilmis", """
        UPDATE musterietiketler SET tamamen_kaybedilmis = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE recency_gun > 180
            AND toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "Yeniden Kazanilmis (Saglik)", "yeniden_kazanilmis_saglik", """
        UPDATE musterietiketler SET yeniden_kazanilmis_saglik = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretfeatures
            WHERE max_ziyaret_araligi >= 90
            AND recency_gun <= 30
            AND toplam_ziyaret >= 3
        )
    """)

    run_label_update(cursor, "Gidip Gelen Musteri", "gidip_gelen_musteri", """
        UPDATE musterietiketler SET gidip_gelen_musteri = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteriziyaretaraliklari
            WHERE ziyaretler_arasi_gun >= 60
            GROUP BY musteri_id
            HAVING COUNT(*) >= 2
               AND COUNT(*) + 1 >= 4
        )
    """)

    run_label_update(cursor, "Sepeti Daralan", "sepeti_daralan", """
        UPDATE musterietiketler SET sepeti_daralan = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteridonem_karsilastirma
            WHERE ort_fis_3ay < ort_fis_onceki3ay * 0.70
            AND ziyaret_3ay >= 2
            AND ziyaret_onceki3ay >= 2
        )
    """)

    run_label_update(cursor, "Kategori Terk Eden", "kategori_terk_eden", """
        UPDATE musterietiketler SET kategori_terk_eden = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteridonem_karsilastirma
            WHERE terk_edilen_kategori >= 3
            AND ziyaret_onceki6ay >= 2
        )
    """)

    run_label_update(cursor, "Marji Dusuran", "marji_dusuran", """
        UPDATE musterietiketler SET marji_dusuran = TRUE
        WHERE musteri_id IN (
            SELECT musteri_id FROM musteridonem_karsilastirma
            WHERE harcama_degisim_3ay_yuzde < -30
            AND (ziyaret_degisim_3ay_yuzde > -10 OR ziyaret_degisim_3ay_yuzde IS NULL)
            AND ziyaret_onceki3ay >= 3
        )
    """)

    run_label_update(cursor, "Gizli Risk", "gizli_risk", """
        UPDATE musterietiketler SET gizli_risk = TRUE
        WHERE musteri_id IN (
            SELECT v.musteri_id FROM musteriziyaretfeatures v
            JOIN musteridonem_karsilastirma d ON v.musteri_id = d.musteri_id
            WHERE v.recency_gun <= 60
            AND d.ziyaret_degisim_3ay_yuzde < -30
            AND d.ziyaret_onceki3ay >= 3
        )
    """)

    run_label_update(cursor, "Kaybedilmemesi Gereken", "kaybedilmemesi_gereken", """
        UPDATE musterietiketler SET kaybedilmemesi_gereken = TRUE
        WHERE musteri_id IN (
            SELECT v.musteri_id FROM musteriziyaretfeatures v
            LEFT JOIN musteridonem_karsilastirma d ON v.musteri_id = d.musteri_id
            WHERE v.toplam_harcama >= 5000
            AND v.toplam_ziyaret >= 3
            AND (
                v.recency_gun BETWEEN 60 AND 180
                OR (d.ziyaret_degisim_3ay_yuzde < -30 AND d.ziyaret_onceki3ay >= 3)
            )
        )
    """)

    # ================================================================
    # CHURN SKORU (0-1 arasi)
    # ================================================================
    logger.info("\nChurn Skoru hesaplaniyor...")
    cursor.execute("""
        UPDATE musterietiketler e
        SET churn_skoru = ROUND(LEAST(1.0, GREATEST(0.0,
            -- recency_vs_expected agirlik 0.40
            LEAST(1.0, (v.recency_gun::float / NULLIF(v.ort_ziyaret_araligi, 1)) / 5.0) * 0.40
            -- ziyaret trendi agirlik 0.30
            + CASE
                WHEN d.ziyaret_degisim_3ay_yuzde IS NULL THEN 0.15
                ELSE LEAST(1.0, GREATEST(0.0, (0 - d.ziyaret_degisim_3ay_yuzde) / 100.0)) * 0.30
              END
            -- duzensizlik agirlik 0.20
            + LEAST(1.0, COALESCE(v.std_ziyaret_araligi, 0) / NULLIF(v.ort_ziyaret_araligi, 1) / 2.0) * 0.20
            -- sepet trendi agirlik 0.10
            + CASE
                WHEN d.ort_fis_3ay IS NULL OR d.ort_fis_onceki3ay IS NULL THEN 0.05
                ELSE LEAST(1.0, GREATEST(0.0, 1.0 - d.ort_fis_3ay / NULLIF(d.ort_fis_onceki3ay, 0))) * 0.10
              END
        ))::numeric, 3)
        FROM musteriziyaretfeatures v
        LEFT JOIN musteridonem_karsilastirma d ON v.musteri_id = d.musteri_id
        WHERE e.musteri_id = v.musteri_id
        AND v.toplam_ziyaret >= 2
    """)
    logger.info(f"  Churn skoru guncellendi: {cursor.rowcount:,} musteri")


def capture_etiket_snapshot(cursor):
    """Gunluk etiket sayilarini etiket_snapshot tablosuna kaydeder (trend takibi icin)."""
    logger.info("\nEtiket Snapshot Kaydediliyor...")
    t0 = datetime.now()

    # customer_portal_view.py:628-641 ile ayni liste
    LABEL_GROUPS = {
        'ziyaret': ['sabah_alisveriscisi', 'aksam_alisveriscisi', 'gece_alisveriscisi', 'hafta_sonu_alisveriscisi', 'hafta_ici_alisveriscisi', 'aylik_duzenli_alici', 'maas_gunu_alisveriscisi', 'gunluk_ugrayan', 'seyrek_alisverisci', 'cok_magazali_musteri'],
        'sepet': ['buyuk_sepet_alisveriscisi', 'kucuk_sepet_alisveriscisi', 'premium_harcayici', 'ekonomik_harcayici', 'b2b_mahalle_esnafi', 'stokcu_alici', 'tekli_urun_alisveriscisi', 'mixed_sepet_alisveriscisi'],
        'fiyat': ['indirim_avcisi', 'promosyon_bagimli', 'fiyat_hassas', 'fiyata_duyarsiz', 'coklu_alim_firsatcisi', 'enflasyon_stokcusu', 'kampanya_tepkisi_dusuk'],
        'taze_gida': ['kasap_odakli', 'manav_odakli', 'firinci_odakli', 'sarkuteri_odakli', 'sut_urunleri_odakli', 'bakliyat_odakli', 'baharat_odakli', 'sadece_taze_gidaci', 'yoresel_urun_meraklisi', 'taze_gida_kacinani', 'taze_gida_terk_eden'],
        'urun_odak': ['atistirmalik_odakli', 'icecek_tutkunuodakli', 'kahvaltilik_odakli', 'kisisel_bakim_odakli', 'temizlik_odakli', 'bebek_urunleri_odakli', 'ev_tekstili_odakli', 'organik_saglikli_odakli', 'dondurulmus_odakli'],
        'kategori': ['saglikli_yasam_egilimli', 'hazir_tuketim_egilimli', 'protein_odakli', 'kafein_yogun_tuketici', 'atistirmalik_tuketicisi', 'temizlik_hijyen_odakli', 'kisisel_bakim_tutkunu', 'misafir_sofrasi_kurucusu'],
        'kanal': ['winback_adayi', 'reaktivasyon_potansiyeli', 'yeniden_kazanilmis', 'kampanya_duyarli', 'kampanyasiz_sadik'],
        'odeme': ['yemek_karti_kullanicisi', 'ay_sonu_yemek_karti_harcayicisi', 'fatura_musterisi'],
        'sadakat': ['sadik_musteri', 'soguyan_musteri', 'kaybedilme_riski_yuksek', 'tamamen_kaybedilmis', 'yeniden_kazanilmis_saglik', 'gidip_gelen_musteri', 'sepeti_daralan', 'kategori_terk_eden', 'marji_dusuran', 'gizli_risk', 'kaybedilmemesi_gereken'],
        'hane': ['hane_bekar_skoru', 'hane_cift_skoru', 'hane_aile_skoru', 'hane_cocuklu_skoru', 'hane_bebek_skoru', 'hane_yasli_skoru', 'hane_evcil_hayvan_skoru', 'hane_araba_skoru', 'hane_toplu_alim_skoru']
    }
    SCORE_COLUMNS = set(LABEL_GROUPS['hane'])
    all_labels = [label for group in LABEL_GROUPS.values() for label in group]

    try:
        # Tablo var mi kontrol et, yoksa olustur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS etiket_snapshot (
                id SERIAL PRIMARY KEY,
                tarih DATE NOT NULL,
                etiket_kolon TEXT NOT NULL,
                sayi INTEGER NOT NULL DEFAULT 0,
                toplam_musteri INTEGER NOT NULL DEFAULT 0,
                UNIQUE(tarih, etiket_kolon)
            )
        """)

        # Tek SQL ile tum etiket sayilarini cek
        parts = ["COUNT(*) as toplam"]
        for col in all_labels:
            if col in SCORE_COLUMNS:
                parts.append(f"COUNT(*) FILTER (WHERE {col} >= 0.4) as {col}")
            else:
                parts.append(f"COUNT(*) FILTER (WHERE {col} = TRUE) as {col}")

        cursor.execute(f"SELECT {', '.join(parts)} FROM musterietiketler")
        row = cursor.fetchone()

        # dict veya tuple olabilir
        if hasattr(row, 'keys'):
            toplam = row.get('toplam', 0) or 0
            get_val = lambda col: row.get(col, 0) or 0
        else:
            toplam = row[0] or 0
            col_map = {col: i + 1 for i, col in enumerate(all_labels)}
            get_val = lambda col: row[col_map[col]] if col in col_map else 0

        # UPSERT: her etiket icin snapshot kaydet
        inserted = 0
        for col in all_labels:
            sayi = get_val(col)
            cursor.execute("""
                INSERT INTO etiket_snapshot (tarih, etiket_kolon, sayi, toplam_musteri)
                VALUES (CURRENT_DATE, %s, %s, %s)
                ON CONFLICT (tarih, etiket_kolon) DO UPDATE
                SET sayi = EXCLUDED.sayi, toplam_musteri = EXCLUDED.toplam_musteri
            """, (col, sayi, toplam))
            inserted += 1

        elapsed = (datetime.now() - t0).total_seconds()
        logger.info(f"  Snapshot kaydedildi: {inserted} etiket, toplam {toplam:,} musteri ({elapsed:.1f}s)")

    except Exception as e:
        logger.warning(f"  Etiket snapshot hatasi (devam ediliyor): {e}")


def main():
    logger.info("=" * 60)
    logger.info("Label Engine Basladi")
    logger.info("=" * 60)

    conn = db_engine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SET statement_timeout = 0")

    t_start = datetime.now()

    try:
        build_labels(cursor)
        conn.commit()

        # Gunluk etiket snapshot (trend takibi)
        capture_etiket_snapshot(cursor)
        conn.commit()

        # Ozet istatistik
        logger.info("\n" + "=" * 60)
        logger.info("OZET ISTATISTIKLER")
        logger.info("=" * 60)
        cursor.execute("SELECT COUNT(*) FROM musterietiketler")
        total = cursor.fetchone()[0]
        logger.info(f"Toplam musteri: {total:,}")

        # Her etiket icin musteri sayisi
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'musterietiketler'
            AND data_type = 'boolean'
            ORDER BY ordinal_position
        """)
        bool_cols = [r[0] for r in cursor.fetchall()]

        for col in bool_cols:
            cursor.execute(f"SELECT COUNT(*) FROM musterietiketler WHERE {col} = TRUE")
            count = cursor.fetchone()[0]
            if count > 0:
                logger.info(f"  {col:<45} {count:>8,}  (%{count*100/total:.1f})")

        elapsed = (datetime.now() - t_start).total_seconds()
        logger.info(f"\nToplam sure: {elapsed:.1f}s")

    except Exception as e:
        conn.rollback()
        logger.error(f"HATA: {e}")
        raise
    finally:
        db_engine.release_connection(conn)


if __name__ == "__main__":
    main()
