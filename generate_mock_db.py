import sqlite3
import random
import datetime
import os

DB_PATH = 'database/demo.sqlite3'

def run():
    print("Populating MarketFlow Mock Database into", DB_PATH)
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            print("Warning: Could not delete DB file. Re-creating connection.")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Normalleştirilmiş MarketFlow Şeması
    c.executescript("""
        CREATE TABLE kategoriler (id INTEGER PRIMARY KEY AUTOINCREMENT, ana TEXT, alt1 TEXT, alt2 TEXT);
        CREATE TABLE markalar (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT);
        CREATE TABLE magazalar (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT, bolge TEXT);
        CREATE TABLE urunler (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, ad TEXT, marka_id INTEGER, kategori_id INTEGER);
        CREATE TABLE musteriler (
            id INTEGER PRIMARY KEY, 
            ad TEXT, 
            telefon TEXT, 
            tip TEXT, 
            kayit_tarihi DATE, 
            rfm_segment TEXT, 
            rfm_r_score INTEGER, 
            rfm_f_score INTEGER, 
            rfm_m_score INTEGER, 
            onay_durumu TEXT DEFAULT 'Onaylı', 
            kayit_magazasi TEXT
        );
        
        CREATE TABLE musteridetayozet (
            musteri_id INTEGER PRIMARY KEY,
            ad_soyad TEXT, 
            email TEXT, 
            telefon TEXT, 
            sehir TEXT, 
            kayit_tarihi DATE, 
            rfm_segment TEXT, 
            r_score INTEGER, 
            f_score INTEGER, 
            m_score INTEGER, 
            toplam_harcama REAL, 
            toplam_alisveris INTEGER, 
            ortalama_sepet_tutari REAL,
            aktivite_durumu TEXT, 
            trend TEXT, 
            churn_risk_skoru INTEGER, 
            lifetime_value_tahmini REAL,
            favori_kategori TEXT, 
            favori_marka TEXT, 
            favori_magaza TEXT, 
            favori_urun TEXT,
            son_alisveris_tarihi DATETIME, 
            ilk_alisveris_tarihi DATETIME
        );

        CREATE TABLE satislar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fis_no TEXT, 
            musteri_id INTEGER, 
            tarih DATE, 
            saat TEXT, 
            tutar REAL, 
            miktar REAL, 
            urun_id INTEGER, 
            magaza_id INTEGER, 
            kategori_id INTEGER, 
            marka_id INTEGER, 
            kampanya_id INTEGER,
            onay_durumu TEXT
        );

        CREATE TABLE kampanyalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT, 
            baslangic DATE, 
            bitis DATE, 
            hedef_segment TEXT, 
            butce REAL, 
            durum TEXT DEFAULT 'Aktif'
        );

        CREATE TABLE otomatikkampanyaonerileri (
            oneri_id INTEGER PRIMARY KEY AUTOINCREMENT,
            olusturma_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
            kampanya_tipi TEXT, 
            hedef_segment TEXT, 
            hedef_musteri_sayisi INTEGER, 
            oncelik_seviye TEXT,
            urun_ad TEXT, 
            kategori_ad TEXT, 
            ikinci_urun_ad TEXT, 
            gerekcesi TEXT, 
            veri_ozeti TEXT,
            onerilen_indirim TEXT, 
            onerilen_min_tutar REAL, 
            gecerlilik_suresi INTEGER, 
            tahmini_katilim INTEGER,
            potansiyel_ciro REAL, 
            birlikte_ciro REAL, 
            mevcut_birlikte_ciro REAL, 
            roi_tahmini REAL, 
            tahmini_kar REAL,
            beklenen_sonuc TEXT, 
            oneri_durumu TEXT DEFAULT 'Bekliyor', 
            lift REAL, 
            guven REAL, 
            fis_sayisi INTEGER,
            onerilen_urunler TEXT, 
            kaynak_kategori_ad TEXT, 
            yonetici_id TEXT, 
            kaynak_marka_id TEXT
        );

        CREATE TABLE daily_metrics_summary (
            tarih TEXT, 
            magaza_id INTEGER, 
            kategori_id INTEGER, 
            marka_id INTEGER, 
            bolge TEXT, 
            customer_type TEXT, 
            onay_durumu TEXT, 
            rfm_segment TEXT, 
            revenue REAL, 
            receipt_count INTEGER, 
            unit_count INTEGER, 
            customer_count INTEGER
        );

        CREATE TABLE product_daily_summary (
            tarih TEXT, 
            urun_id INTEGER, 
            revenue REAL, 
            unit_count INTEGER, 
            customer_count INTEGER
        );

        CREATE TABLE encoksatanlar (
            donem_tipi TEXT, 
            donem_degeri TEXT, 
            grup_tipi TEXT, 
            grup_degeri TEXT,
            urun_ad TEXT, 
            toplam_ciro REAL, 
            toplam_adet INTEGER
        );

        CREATE TABLE segmentozet (segment TEXT, customer_count INTEGER);
        
        CREATE TABLE genelozet (
            ay TEXT, 
            toplam_ciro REAL, 
            crm_ciro REAL, 
            anonim_ciro REAL, 
            toplam_fis INTEGER, 
            crm_fis INTEGER, 
            anonim_fis INTEGER, 
            crm_musteri INTEGER,
            crm_sepet_ort REAL, 
            anonim_sepet_ort REAL, 
            crm_oran_ciro REAL
        );
        
        CREATE TABLE syncmeta (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        
        -- Analitik Ek Tablolar (PostgreSQL bagimliligini SQLite icin mocklamak adina)
        CREATE TABLE musterietiketler (
            musteri_id INTEGER PRIMARY KEY,
            sabah_alisveriscisi BOOLEAN DEFAULT 0,
            aksam_alisveriscisi BOOLEAN DEFAULT 0,
            gece_alisveriscisi BOOLEAN DEFAULT 0,
            hafta_sonu_alisveriscisi BOOLEAN DEFAULT 0,
            hafta_ici_alisveriscisi BOOLEAN DEFAULT 0,
            aylik_duzenli_alici BOOLEAN DEFAULT 0,
            maas_gunu_alisveriscisi BOOLEAN DEFAULT 0,
            gunluk_ugrayan BOOLEAN DEFAULT 0,
            seyrek_alisverisci BOOLEAN DEFAULT 0,
            cok_magazali_musteri BOOLEAN DEFAULT 0,
            buyuk_sepet_alisveriscisi BOOLEAN DEFAULT 0,
            kucuk_sepet_alisveriscisi BOOLEAN DEFAULT 0,
            premium_harcayici BOOLEAN DEFAULT 0,
            ekonomik_harcayici BOOLEAN DEFAULT 0,
            b2b_mahalle_esnafi BOOLEAN DEFAULT 0,
            stokcu_alici BOOLEAN DEFAULT 0,
            tekli_urun_alisveriscisi BOOLEAN DEFAULT 0,
            mixed_sepet_alisveriscisi BOOLEAN DEFAULT 0,
            indirim_avcisi BOOLEAN DEFAULT 0,
            promosyon_bagimli BOOLEAN DEFAULT 0,
            fiyat_hassas BOOLEAN DEFAULT 0,
            fiyata_duyarsiz BOOLEAN DEFAULT 0,
            coklu_alim_firsatcisi BOOLEAN DEFAULT 0,
            enflasyon_stokcusu BOOLEAN DEFAULT 0,
            kampanya_tepkisi_dusuk BOOLEAN DEFAULT 0,
            kasap_odakli BOOLEAN DEFAULT 0,
            manav_odakli BOOLEAN DEFAULT 0,
            firinci_odakli BOOLEAN DEFAULT 0,
            sarkuteri_odakli BOOLEAN DEFAULT 0,
            sut_urunleri_odakli BOOLEAN DEFAULT 0,
            bakliyat_odakli BOOLEAN DEFAULT 0,
            baharat_odakli BOOLEAN DEFAULT 0,
            sadece_taze_gidaci BOOLEAN DEFAULT 0,
            yoresel_urun_meraklisi BOOLEAN DEFAULT 0,
            taze_gida_kacinani BOOLEAN DEFAULT 0,
            taze_gida_terk_eden BOOLEAN DEFAULT 0,
            atistirmalik_odakli BOOLEAN DEFAULT 0,
            icecek_tutkunuodakli BOOLEAN DEFAULT 0,
            kahvaltilik_odakli BOOLEAN DEFAULT 0,
            kisisel_bakim_odakli BOOLEAN DEFAULT 0,
            temizlik_odakli BOOLEAN DEFAULT 0,
            bebek_urunleri_odakli BOOLEAN DEFAULT 0,
            ev_tekstili_odakli BOOLEAN DEFAULT 0,
            organik_saglikli_odakli BOOLEAN DEFAULT 0,
            dondurulmus_odakli BOOLEAN DEFAULT 0,
            saglikli_yasam_egilimli BOOLEAN DEFAULT 0,
            hazir_tuketim_egilimli BOOLEAN DEFAULT 0,
            protein_odakli BOOLEAN DEFAULT 0,
            kafein_yogun_tuketici BOOLEAN DEFAULT 0,
            atistirmalik_tuketicisi BOOLEAN DEFAULT 0,
            temizlik_hijyen_odakli BOOLEAN DEFAULT 0,
            kisisel_bakim_tutkunu BOOLEAN DEFAULT 0,
            misafir_sofrasi_kurucusu BOOLEAN DEFAULT 0,
            winback_adayi BOOLEAN DEFAULT 0,
            reaktivasyon_potansiyeli BOOLEAN DEFAULT 0,
            yeniden_kazanilmis BOOLEAN DEFAULT 0,
            kampanya_duyarli BOOLEAN DEFAULT 0,
            kampanyasiz_sadik BOOLEAN DEFAULT 0,
            yemek_karti_kullanicisi BOOLEAN DEFAULT 0,
            ay_sonu_yemek_karti_harcayicisi BOOLEAN DEFAULT 0,
            fatura_musterisi BOOLEAN DEFAULT 0,
            sadik_musteri BOOLEAN DEFAULT 0,
            soguyan_musteri BOOLEAN DEFAULT 0,
            kaybedilme_riski_yuksek BOOLEAN DEFAULT 0,
            tamamen_kaybedilmis BOOLEAN DEFAULT 0,
            yeniden_kazanilmis_saglik BOOLEAN DEFAULT 0,
            gidip_gelen_musteri BOOLEAN DEFAULT 0,
            sepeti_daralan BOOLEAN DEFAULT 0,
            kategori_terk_eden BOOLEAN DEFAULT 0,
            marji_dusuran BOOLEAN DEFAULT 0,
            gizli_risk BOOLEAN DEFAULT 0,
            kaybedilmemesi_gereken BOOLEAN DEFAULT 0,
            hane_bekar_skoru REAL DEFAULT 0.0,
            hane_cift_skoru REAL DEFAULT 0.0,
            hane_aile_skoru REAL DEFAULT 0.0,
            hane_cocuklu_skoru REAL DEFAULT 0.0,
            hane_bebek_skoru REAL DEFAULT 0.0,
            hane_yasli_skoru REAL DEFAULT 0.0,
            hane_evcil_hayvan_skoru REAL DEFAULT 0.0,
            hane_araba_skoru REAL DEFAULT 0.0,
            hane_toplu_alim_skoru REAL DEFAULT 0.0,
            churn_skoru REAL DEFAULT 0.0
        );

        CREATE TABLE musterifiyatfeatures (
            musteri_id INTEGER PRIMARY KEY,
            toplam_satis_satir INTEGER DEFAULT 0,
            indirimli_satir_sayisi INTEGER DEFAULT 0,
            indirimsiz_satir_sayisi INTEGER DEFAULT 0,
            indirim_oran_yuzde REAL DEFAULT 0.0,
            ort_indirim_yuzde REAL DEFAULT 0.0,
            toplam_indirim_tutari REAL DEFAULT 0.0,
            toplam_brut_tutar REAL DEFAULT 0.0
        );

        CREATE TABLE musteridonem_karsilastirma (
            musteri_id INTEGER PRIMARY KEY,
            ziyaret_3ay INTEGER DEFAULT 0,
            ziyaret_onceki3ay INTEGER DEFAULT 0,
            harcama_3ay REAL DEFAULT 0.0,
            harcama_onceki3ay REAL DEFAULT 0.0,
            ort_fis_3ay REAL DEFAULT 0.0,
            ort_fis_onceki3ay REAL DEFAULT 0.0,
            ziyaret_degisim_3ay_yuzde REAL DEFAULT 0.0,
            harcama_degisim_3ay_yuzde REAL DEFAULT 0.0,
            ziyaret_6ay INTEGER DEFAULT 0,
            ziyaret_onceki6ay INTEGER DEFAULT 0,
            harcama_6ay REAL DEFAULT 0.0,
            harcama_onceki6ay REAL DEFAULT 0.0,
            ziyaret_degisim_6ay_yuzde REAL DEFAULT 0.0,
            harcama_degisim_6ay_yuzde REAL DEFAULT 0.0,
            son_kategori_sayisi INTEGER DEFAULT 0,
            onceki_kategori_sayisi INTEGER DEFAULT 0,
            terk_edilen_kategori INTEGER DEFAULT 0
        );

        CREATE TABLE musterimarka_dagilimi (
            musteri_id INTEGER,
            marka_adi TEXT,
            fis_sayisi INTEGER DEFAULT 0,
            toplam_harcama REAL DEFAULT 0.0,
            toplam_miktar REAL DEFAULT 0.0,
            PRIMARY KEY (musteri_id, marka_adi)
        );
    """)

    # --- Data Generation ---
    cats = ['Elektronik', 'Giyim', 'Kozmetik', 'Gıda', 'Ev Yaşam']
    for c_ad in cats:
        c.execute("INSERT INTO kategoriler (ana, alt1) VALUES (?, ?)", (c_ad, f"{c_ad} Alt"))
    c.execute("SELECT id, ana FROM kategoriler")
    cat_map = {r[1]: r[0] for r in c.fetchall()}

    brands = ['Apple', 'Samsung', 'Nike', 'Adidas', 'Loreal', 'Nestle', 'IKEA']
    for b_ad in brands:
        c.execute("INSERT INTO markalar (ad) VALUES (?)", (b_ad,))
    c.execute("SELECT id, ad FROM markalar")
    brand_map = {r[1]: r[0] for r in c.fetchall()}

    stores = ['Şube A', 'Şube B', 'Şube C', 'Şube D']
    for s_ad in stores:
        c.execute("INSERT INTO magazalar (ad, bolge) VALUES (?, ?)", (s_ad, 'Bölge 1' if s_ad in ['Şube A', 'Şube B'] else 'Bölge 2'))
    c.execute("SELECT id, ad FROM magazalar")
    store_rows = c.fetchall()
    store_ids = [r[0] for r in store_rows]

    for i in range(1, 51):
        c.execute("INSERT INTO urunler (kod, ad, marka_id, kategori_id) VALUES (?, ?, ?, ?)",
                  (f"KOD{i:03d}", f"Ürün {i}", random.choice(list(brand_map.values())), random.choice(list(cat_map.values()))))
    c.execute("SELECT id, ad FROM urunler")
    urun_rows = c.fetchall()
    urun_ids = [r[0] for r in urun_rows]

    segments = ['Şampiyonlar', 'Sadık Müşteriler', 'Potansiyel Sadıklar', 'Yeni Müşteriler', 'Uykudakiler', 'Riskli', 'Kaybedilenler']
    for i in range(1, 201):
        seg = random.choice(segments)
        c.execute("INSERT INTO musteriler (id, ad, telefon, tip, kayit_tarihi, rfm_segment, onay_durumu) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (i, f"Müşteri {i}", f"555{i:04d}", random.choice(['Bireysel', 'Kurumsal']), '2023-01-01', seg, 'Onaylı'))
        
        # Populate musteridetayozet with snake_case columns
        total_h = random.uniform(1000, 10000)
        total_a = random.randint(5, 50)
        avg_basket = total_h / total_a if total_a > 0 else 0
        ilk_alisveris = "2023-01-01 10:00:00"
        son_alisveris = "2026-05-20 18:30:00"
        c.execute("""
            INSERT INTO musteridetayozet (
                musteri_id, ad_soyad, rfm_segment, toplam_harcama, toplam_alisveris, 
                ortalama_sepet_tutari, aktivite_durumu, churn_risk_skoru, lifetime_value_tahmini,
                ilk_alisveris_tarihi, son_alisveris_tarihi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, f"Müşteri {i}", seg, total_h, total_a, avg_basket, 'Aktif', random.randint(10, 90), total_h * 1.5, ilk_alisveris, son_alisveris))

        # Diger analitik tabloları mock verilerle doldur
        # 1. musterietiketler
        enflasyon_stok = 1 if random.random() < 0.25 else 0
        f_hassas = 1 if random.random() < 0.35 else 0
        c.execute("""
            INSERT INTO musterietiketler (
                musteri_id, enflasyon_stokcusu, fiyat_hassas, sabah_alisveriscisi, aksam_alisveriscisi,
                hafta_sonu_alisveriscisi, hafta_ici_alisveriscisi, premium_harcayici, sadik_musteri,
                cok_magazali_musteri, b2b_mahalle_esnafi, mixed_sepet_alisveriscisi,
                sut_urunleri_odakli, bakliyat_odakli, baharat_odakli, taze_gida_terk_eden,
                atistirmalik_odakli, icecek_tutkunuodakli, kahvaltilik_odakli, kisisel_bakim_odakli,
                temizlik_odakli, bebek_urunleri_odakli, ev_tekstili_odakli, organik_saglikli_odakli,
                dondurulmus_odakli, hane_bekar_skoru, hane_cift_skoru, hane_aile_skoru,
                hane_cocuklu_skoru, hane_bebek_skoru, hane_yasli_skoru, hane_evcil_hayvan_skoru,
                hane_araba_skoru, hane_toplu_alim_skoru, churn_skoru
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, enflasyon_stok, f_hassas, random.choice([0, 1]), random.choice([0, 1]),
              random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]),
              random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]),
              random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]),
              random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]),
              random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]), random.choice([0, 1]),
              random.choice([0, 1]), random.random(), random.random(), random.random(),
              random.random(), random.random(), random.random(), random.random(),
              random.random(), random.random(), random.uniform(0, 100)))

        # 2. musterifiyatfeatures
        tot_satir = random.randint(10, 100)
        ind_satir = random.randint(0, tot_satir)
        ind_oran = (ind_satir / tot_satir) * 100
        c.execute("""
            INSERT INTO musterifiyatfeatures (
                musteri_id, toplam_satis_satir, indirimli_satir_sayisi, indirimsiz_satir_sayisi,
                indirim_oran_yuzde, ort_indirim_yuzde, toplam_indirim_tutari, toplam_brut_tutar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, tot_satir, ind_satir, tot_satir - ind_satir, ind_oran, random.uniform(5, 25), total_h * 0.1, total_h * 1.1))

        # 3. musteridonem_karsilastirma
        c.execute("""
            INSERT INTO musteridonem_karsilastirma (
                musteri_id, ziyaret_3ay, ziyaret_onceki3ay, harcama_3ay, harcama_onceki3ay,
                ort_fis_3ay, ort_fis_onceki3ay, ziyaret_degisim_3ay_yuzde, harcama_degisim_3ay_yuzde,
                ziyaret_6ay, ziyaret_onceki6ay, harcama_6ay, harcama_onceki6ay,
                ziyaret_degisim_6ay_yuzde, harcama_degisim_6ay_yuzde, son_kategori_sayisi,
                onceki_kategori_sayisi, terk_edilen_kategori
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, random.randint(1, 10), random.randint(1, 10), total_h * 0.2, total_h * 0.25,
              total_h * 0.2 / 5, total_h * 0.25 / 5, random.uniform(-30, 30), random.uniform(-30, 30),
              random.randint(2, 20), random.randint(2, 20), total_h * 0.4, total_h * 0.5,
              random.uniform(-30, 30), random.uniform(-30, 30), random.randint(1, 4),
              random.randint(1, 4), random.randint(0, 1)))

        # 4. musterimarka_dagilimi
        for brand_name in random.sample(brands, k=2):
            c.execute("""
                INSERT INTO musterimarka_dagilimi (
                    musteri_id, marka_adi, fis_sayisi, toplam_harcama, toplam_miktar
                ) VALUES (?, ?, ?, ?, ?)
            """, (i, brand_name, random.randint(1, 10), total_h * random.uniform(0.1, 0.4), random.randint(1, 20)))

    camp_names = ['Bahar Fırsatı', 'Yaz Kampanyası', 'Efsane Cuma']
    for name in camp_names:
        c.execute("INSERT INTO kampanyalar (ad, baslangic, bitis, durum) VALUES (?, ?, ?, ?)",
                  (name, '2024-01-01', '2024-12-31', 'Aktif'))
    c.execute("SELECT id FROM kampanyalar")
    camp_ids = [r[0] for r in c.fetchall()]

    for i in range(1, 2001):
        # Generate dates for 2024, 2025, 2026 to match comparison charts
        year = random.choice([2024, 2025, 2026])
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        tarih = datetime.date(year, month, day).strftime("%Y-%m-%d")
        
        tutar = random.uniform(50, 1000)
        c.execute("INSERT INTO satislar (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, kategori_id, marka_id, kampanya_id, onay_durumu) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (f"FIS{i}", random.randint(1, 200), tarih, "14:00", tutar, random.randint(1, 5), random.choice(urun_ids), random.choice(store_ids), random.choice(list(cat_map.values())), random.choice(list(brand_map.values())), random.choice(camp_ids), 'Onaylı'))

    # Aggregates
    c.execute("INSERT INTO daily_metrics_summary (tarih, revenue, receipt_count, unit_count, customer_count) SELECT tarih, SUM(tutar), COUNT(DISTINCT fis_no), SUM(miktar), COUNT(DISTINCT musteri_id) FROM satislar GROUP BY tarih")
    c.execute("INSERT INTO product_daily_summary (tarih, urun_id, revenue, unit_count, customer_count) SELECT tarih, urun_id, SUM(tutar), SUM(miktar), COUNT(DISTINCT musteri_id) FROM satislar GROUP BY tarih, urun_id")
    c.execute("INSERT INTO segmentozet (segment, customer_count) SELECT rfm_segment, COUNT(*) FROM musteriler GROUP BY rfm_segment")
    
    for u_id, u_ad in urun_rows:
        c.execute("INSERT INTO encoksatanlar (donem_tipi, donem_degeri, grup_tipi, grup_degeri, urun_ad, toplam_ciro, toplam_adet) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('GLOBAL', 'ALL', 'GENEL', 'ALL', u_ad, random.uniform(5000, 20000), random.randint(100, 500)))

    c.execute("INSERT INTO otomatikkampanyaonerileri (kampanya_tipi, hedef_segment, urun_ad, kategori_ad, oneri_durumu) VALUES (?, ?, ?, ?, ?)",
              ('Çapraz Satış', 'Şampiyonlar', 'Akıllı Saat', 'Elektronik', 'Bekliyor'))

    # Populate genelozet for comparison charts
    for year in [2024, 2025, 2026]:
        for month in range(1, 13):
            ay_str = f"{year}-{month:02d}"
            c.execute("""
                INSERT INTO genelozet (ay, toplam_ciro, crm_ciro, anonim_ciro, toplam_fis, crm_fis, anonim_fis, crm_musteri)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ay_str, random.uniform(50000, 150000), random.uniform(30000, 100000), random.uniform(20000, 50000),
                  random.randint(500, 1500), random.randint(300, 1000), random.randint(200, 500), random.randint(100, 300)))

    conn.commit()
    conn.close()
    print("MarketFlow Mock Database Population Complete!")

if __name__ == '__main__':
    run()
