import sqlite3
import os

DB_PATH = r'C:\Users\Akif\Desktop\BackendFronend\database\sales_cache.db'

def calculate_tags():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("AI Etiketleme İşlemi Başladı (Gelişmiş Analiz)...")
    
    # 0. Önbellek Hazırlığı
    cursor.execute("DROP TABLE IF EXISTS tmp_musteri_ozet")
    cursor.execute("""
        CREATE TEMPORARY TABLE tmp_musteri_ozet AS
        SELECT musteri_id, COUNT(*) as total_rows, SUM(tutar) as total_rev, MAX(tarih) as last_date, COUNT(DISTINCT fis_no) as total_fis
        FROM Satislar
        GROUP BY musteri_id
    """)
    cursor.execute("CREATE INDEX idx_tmp_mo ON tmp_musteri_ozet(musteri_id)")

    # 1. EBEVEYNLİK EVRELERİ (Maturity Pipeline)
    print("Ebeveynlik evreleri tespit ediliyor...")
    # Yeni Doğan (0-6 Ay)
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT s.musteri_id, 'LIFE_EVENT', 'Ebeveynlik: Yeni Doğan (0-6 Ay)', 1.0
        FROM Satislar s
        JOIN Urunler u ON s.urun_id = u.id
        WHERE u.ad LIKE '%BEBEK BEZİ%' OR u.ad LIKE '%BİBERON%'
          OR (u.ad LIKE '%MAMA%' AND u.ad LIKE '%1%')
        GROUP BY s.musteri_id
        HAVING COUNT(*) > 2
    """)

    # Ek Gıda Geçişi
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT s.musteri_id, 'LIFE_EVENT', 'Ebeveynlik: Ek Gıda Geçişi', 1.0
        FROM Satislar s
        JOIN Urunler u ON s.urun_id = u.id
        WHERE u.ad LIKE '%KAVANOZ MAMA%' OR u.ad LIKE '%BEBE BİSKÜVİSİ%' OR u.ad LIKE '%KAŞIK MAMASI%'
        GROUP BY s.musteri_id
    """)

    # 1.1 EVCİL HAYVAN DÖNGÜSÜ
    print("Evcil hayvan döngüsü tespit ediliyor...")
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT s.musteri_id, 'LIFE_EVENT', 'Evcil Hayvan: Yeni Sahiplenme', 1.0
        FROM Satislar s
        JOIN Urunler u ON s.urun_id = u.id
        WHERE u.ad LIKE '%PUPPY%' OR u.ad LIKE '%KITTEN%' OR u.ad LIKE '%YAVRU%'
        GROUP BY s.musteri_id
    """)

    # Diyet Değişimi (Vegan/Glutensiz/Anomalisi)
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT s.musteri_id, 'LIFE_EVENT', 'Diyet Değişimi', 1.0
        FROM Satislar s
        JOIN Urunler u ON s.urun_id = u.id
        WHERE u.ad LIKE '%GLUTEN%' OR u.ad LIKE '%VEGAN%' OR u.ad LIKE '%DİYET%'
        GROUP BY s.musteri_id
        HAVING COUNT(*) >= 2
    """)

    # Yeni Evli / Ev Taşıyan (Deterjan + Mutfak + Temizlik aynı fışte veya kısa sürede)
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT s.musteri_id, 'LIFE_EVENT', 'Yeni Evli / Ev Taşıyan', 1.0
        FROM Satislar s
        JOIN Kategoriler k ON s.kategori_id = k.id
        WHERE k.ana IN ('TEMİZLİK VE KAĞIT', 'ZÜCCACİYE', 'EV & PET')
        GROUP BY s.musteri_id
        HAVING COUNT(DISTINCT k.ana) >= 2 AND COUNT(*) > 10
    """)

    # 2. İLERİYE DÖNÜK (PREDICTIVE)
    print("Gelecek tahminleri yapılıyor...")
    
    # CLV Tahmini (90 Gün)
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT musteri_id, 'PREDICTIVE', 'Tahmini 90 Günlük Ciro', 
               (total_rev / NULLIF(total_fis, 0)) * (total_fis / 6.0) * 3 
        FROM tmp_musteri_ozet
        WHERE total_fis >= 2
    """)

    # 3. DAVRANIŞSAL (BEHAVIORAL)
    print("Davranışsal etiketler işleniyor...")
    
    # Gece Kuşu (20:00 - 05:00 arası alışveriş yapanlar)
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT musteri_id, 'BEHAVIORAL', 'Gece Kuşu', 1.0
        FROM Satislar
        WHERE saat >= 20 OR saat <= 5
        GROUP BY musteri_id
        HAVING COUNT(*) >= 2
    """)

    # Hafta Sonu Kaçkını
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT musteri_id, 'BEHAVIORAL', 'Hafta Sonu Kaçkını', 1.0
        FROM Satislar
        WHERE strftime('%w', tarih) IN ('0', '5', '6')
        GROUP BY musteri_id
        HAVING COUNT(*) >= 3
    """)

    # Bulk Buyer
    cursor.execute("""
        INSERT OR REPLACE INTO MusteriEtiketleri (musteri_id, etiket_grubu, etiket_adi, skor)
        SELECT musteri_id, 'BEHAVIORAL', 'Bulk Buyer (Stokçu)', 1.0
        FROM Satislar
        GROUP BY musteri_id, urun_id
        HAVING SUM(miktar) >= 10
    """)

    conn.commit()
    conn.close()
    print("AI Etiketleme İşlemi Tamamlandı.")

if __name__ == '__main__':
    calculate_tags()
