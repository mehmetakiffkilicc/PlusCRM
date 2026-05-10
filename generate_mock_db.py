import sqlite3
import random
import datetime
import os

DB_PATH = 'database/demo.sqlite3'

def run():
    print("Populating mock data into", DB_PATH)
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            print("Warning: Could not delete DB file. Using DROP TABLE instead.")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE Kategoriler (id INTEGER PRIMARY KEY AUTOINCREMENT, ana TEXT, alt1 TEXT, alt2 TEXT);
        CREATE TABLE Markalar (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT);
        CREATE TABLE Magazalar (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT, bolge TEXT);
        CREATE TABLE Urunler (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, ad TEXT, marka_id INTEGER, kategori_id INTEGER);
        CREATE TABLE Musteriler (id INTEGER PRIMARY KEY, ad TEXT, telefon TEXT, tip TEXT, kayit_tarihi DATE, rfm_segment TEXT, rfm_r_score INTEGER, rfm_f_score INTEGER, rfm_m_score INTEGER, onay_durumu TEXT DEFAULT 'Onaylı', kayit_magazasi TEXT);
        
        CREATE TABLE musteridetayozet (
            musteri_id INTEGER PRIMARY KEY,
            MusteriID INTEGER,
            AdSoyad TEXT,
            Email TEXT,
            Telefon TEXT,
            Sehir TEXT,
            KayitTarihi DATE,
            RFM_Segment TEXT,
            R_Score INTEGER,
            F_Score INTEGER,
            M_Score INTEGER,
            FavoriKategori TEXT,
            FavoriMarka TEXT,
            FavoriMagaza TEXT,
            FavoriUrun TEXT,
            TercihEdilenSaat TEXT,
            GunTercihi TEXT,
            OrtalamaSiparisBuyuklugu REAL,
            IlkAlisverisTarihi DATETIME,
            SonAlisverisTarihi DATETIME,
            MusteriYasiGun INTEGER,
            ToplamAlisveris INTEGER,
            ToplamHarcama REAL,
            OrtalamaSepetTutari REAL,
            Son30GunAlisveris INTEGER,
            Son30GunHarcama REAL,
            Son90GunAlisveris INTEGER,
            Son90GunHarcama REAL,
            Trend TEXT,
            AktiviteDurumu TEXT,
            ChurnRiskSkoru INTEGER,
            LifetimeValueTahmini REAL,
            SepetCesitlendirme INTEGER,
            MarkaSadakati REAL,
            Saat_Sabah INTEGER,
            Saat_Ogle INTEGER,
            Saat_Aksam INTEGER,
            Saat_Gece INTEGER
        );

        CREATE TABLE musterietiketler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_id INTEGER,
            sadik_musteri BOOLEAN DEFAULT 0,
            gizli_risk BOOLEAN DEFAULT 0,
            kaybedilmemesi_gereken BOOLEAN DEFAULT 0,
            soguyan_musteri BOOLEAN DEFAULT 0,
            indirim_avcisi BOOLEAN DEFAULT 0,
            promosyon_bagimli BOOLEAN DEFAULT 0,
            fiyat_hassas BOOLEAN DEFAULT 0,
            atistirmalik_odakli BOOLEAN DEFAULT 0,
            icecek_tutkunuodakli BOOLEAN DEFAULT 0,
            hane_bebek_skoru REAL DEFAULT 0,
            hane_cocuklu_skoru REAL DEFAULT 0,
            churn_skoru REAL DEFAULT 0,
            UNIQUE(musteri_id)
        );

        CREATE TABLE Satislar (
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
            marka_id INTEGER
        );

        CREATE TABLE GunlukOzet (tarih DATE, magaza_id INTEGER, kategori_id INTEGER, marka_id INTEGER, toplam_ciro REAL, fis_sayisi INTEGER, musteri_sayisi INTEGER, urun_adedi INTEGER);
        CREATE TABLE GenelOzet (ay TEXT, magaza_id INTEGER, toplam_ciro REAL, toplam_fis INTEGER, toplam_miktar REAL, crm_ciro REAL, crm_fis INTEGER, crm_musteri INTEGER);
        CREATE TABLE KategoriKarsilastirma (ay TEXT, kategori TEXT, toplam_ciro REAL, crm_ciro REAL, anonim_ciro REAL, crm_fis INTEGER, anonim_fis INTEGER);
        CREATE TABLE MarkaKarsilastirma (ay TEXT, marka TEXT, toplam_ciro REAL, crm_ciro REAL, crm_musteri INTEGER);
        CREATE TABLE GunlukCiroOzet (tarih DATE, toplam_ciro REAL, toplam_fis INTEGER, toplam_musteri INTEGER, toplam_miktar REAL, sepet_ortalamasi REAL, musteri_basina_ciro REAL, sku_sayisi INTEGER);
        CREATE TABLE daily_metrics_summary (
            tarih TEXT, magaza_id INTEGER, kategori_id INTEGER, marka_id INTEGER, bolge TEXT, 
            customer_type TEXT, onay_durumu TEXT, rfm_segment TEXT, revenue REAL, receipt_count INTEGER, quantity INTEGER, customer_count INTEGER
        );
        CREATE TABLE urunbirliktelikleri (urun_id_1 INTEGER, urun_id_2 INTEGER, ortak_fis_sayisi INTEGER, confidence REAL, lift REAL, urun_id INTEGER);
        CREATE TABLE grupbirliktelikleri (kategori_id_1 INTEGER, kategori_id_2 INTEGER, tip TEXT, kural TEXT, lift REAL, ortak_fis_sayisi INTEGER);
        CREATE TABLE musterimarka_dagilimi (musteri_id INTEGER, marka_adi TEXT, toplam_harcama REAL);
        CREATE TABLE segmenturuntercihleri (rfm_segment TEXT, kategori_ad TEXT, penetrasyon REAL);
        CREATE TABLE rfm_segment_log (musteri_id INTEGER, rfm_segment TEXT, kayit_tarihi DATE);
        CREATE TABLE etiket_snapshot (etiket_kolon TEXT, sayi INTEGER, tarih DATE);
        CREATE TABLE cache_kohort_analizi (key TEXT, value TEXT);
        CREATE TABLE syncmeta (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    """)

    kategoriler = ['Elektronik', 'Giyim', 'Kozmetik', 'Gıda', 'Ev Yaşam']
    for cat in kategoriler:
        c.execute("INSERT INTO Kategoriler (ana, alt1) VALUES (?, ?)", (cat, f"{cat} Alt"))
    c.execute("SELECT id, ana FROM Kategoriler")
    cat_map = {row[1]: row[0] for row in c.fetchall()}

    markalar = ['Marka A', 'Marka B', 'Marka C', 'Marka D', 'Marka E']
    for m in markalar:
        c.execute("INSERT INTO Markalar (ad) VALUES (?)", (m,))
    c.execute("SELECT id, ad FROM Markalar")
    marka_map = {row[1]: row[0] for row in c.fetchall()}

    magazalar = ['Merkez Şube', 'AVM Şube', 'Kadıköy Şube', 'Beşiktaş Şube']
    for m in magazalar:
        c.execute("INSERT INTO Magazalar (ad, bolge) VALUES (?, ?)", (m, 'İstanbul'))
    c.execute("SELECT id, ad FROM Magazalar")
    magaza_rows = c.fetchall()
    magaza_ids = [r[0] for r in magaza_rows]
    magaza_map = {r[0]: r[1] for r in magaza_rows}

    for i in range(1, 51):
        cat_id = random.choice(list(cat_map.values()))
        marka_id = random.choice(list(marka_map.values()))
        c.execute("INSERT INTO Urunler (kod, ad, marka_id, kategori_id) VALUES (?, ?, ?, ?)",
                  (f"PRD{i:03d}", f"Ürün {i}", marka_id, cat_id))
    c.execute("SELECT id, ad FROM Urunler")
    urun_ids = [r[0] for r in c.fetchall()]

    segments = ['Şampiyonlar', 'Sadık Müşteriler', 'Potansiyel Sadıklar', 'Yeni Müşteriler', 'Uykudakiler', 'Riskli', 'Kaybedilenler']
    for i in range(1, 1001):
        tip = random.choice(['Bireysel', 'Kurumsal'])
        segment = random.choice(segments)
        magaza_id = random.choice(magaza_ids)
        magaza_ad = magaza_map[magaza_id]
        
        c.execute("""
            INSERT INTO Musteriler (id, ad, telefon, tip, kayit_tarihi, rfm_segment, rfm_r_score, rfm_f_score, rfm_m_score, onay_durumu, kayit_magazasi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, f"Müşteri {i}", f"555{random.randint(1000000, 9999999)}", tip, '2023-01-01', segment, random.randint(1,5), random.randint(1,5), random.randint(1,5), 'Onaylı', magaza_ad))
        
        c.execute("""
            INSERT INTO musteridetayozet (
                musteri_id, MusteriID, AdSoyad, Email, Telefon, Sehir, KayitTarihi, RFM_Segment, 
                R_Score, F_Score, M_Score, ToplamHarcama, ToplamAlisveris, OrtalamaSepetTutari,
                AktiviteDurumu, Trend, ChurnRiskSkoru, LifetimeValueTahmini,
                FavoriKategori, FavoriMarka, FavoriMagaza, FavoriUrun,
                SonAlisverisTarihi, IlkAlisverisTarihi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, i, f"Müşteri {i}", f"musteri{i}@example.com", f"555{random.randint(1000000, 9999999)}", "İstanbul", "2023-01-01", segment, 
              random.randint(1,5), random.randint(1,5), random.randint(1,5), random.uniform(500, 5000),
              random.randint(1, 50), random.uniform(100, 500),
              random.choice(['Aktif', 'Pasif', 'Yeni']), random.choice(['Yükselen', 'Düşen', 'Stabil']),
              random.randint(0, 100), random.uniform(1000, 10000),
              random.choice(list(kategoriler)), random.choice(list(markalar)), random.choice(magazalar), f"Ürün {random.randint(1,50)}",
              (datetime.date.today() - datetime.timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
              '2023-01-01'))

        c.execute("""
            INSERT INTO musterietiketler (
                musteri_id, sadik_musteri, gizli_risk, kaybedilmemesi_gereken, soguyan_musteri, 
                indirim_avcisi, hane_bebek_skoru, hane_cocuklu_skoru, churn_skoru
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (i, random.random() > 0.7, random.random() > 0.8, random.random() > 0.9, random.random() > 0.8,
              random.random() > 0.6, random.random(), random.random(), random.random() * 100))

        c.execute("INSERT INTO musterimarka_dagilimi (musteri_id, marka_adi, toplam_harcama) VALUES (?, ?, ?)",
                  (i, random.choice(markalar), random.uniform(100, 1000)))
        
        c.execute("INSERT INTO rfm_segment_log (musteri_id, rfm_segment, kayit_tarihi) VALUES (?, ?, ?)",
                  (i, segment, (datetime.date.today() - datetime.timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d")))

    for i in range(1, 5001):
        sale_date = datetime.date.today() - datetime.timedelta(days=random.randint(0, 365))
        c.execute("""
            INSERT INTO Satislar (fis_no, musteri_id, tarih, saat, tutar, miktar, urun_id, magaza_id, kategori_id, marka_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"FIS{i}", random.randint(1, 1000), sale_date.strftime("%Y-%m-%d"), 
            f"{random.randint(9, 21):02d}:{random.randint(0, 59):02d}",
            round(random.uniform(50, 500), 2), random.randint(1, 5),
            random.choice(urun_ids), random.choice(magaza_ids),
            random.choice(list(cat_map.values())), random.choice(list(marka_map.values()))
        ))

    for seg in segments:
        for cat in kategoriler:
            c.execute("INSERT INTO segmenturuntercihleri (rfm_segment, kategori_ad, penetrasyon) VALUES (?, ?, ?)",
                      (seg, cat, random.uniform(0.05, 0.4)))

    for cat in kategoriler:
        c.execute("INSERT INTO etiket_snapshot (etiket_kolon, sayi, tarih) VALUES (?, ?, ?)",
                  (cat, random.randint(100, 500), (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")))

    # Aggregates
    c.execute("INSERT INTO daily_metrics_summary (tarih, revenue, receipt_count, customer_count) SELECT tarih, SUM(tutar), COUNT(DISTINCT fis_no), COUNT(DISTINCT musteri_id) FROM Satislar GROUP BY tarih")

    conn.commit()
    conn.close()
    print("Mock database generation complete!")

if __name__ == '__main__':
    run()
