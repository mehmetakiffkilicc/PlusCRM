"""
SQLite/PostgreSQL Veritabanı Şema Tanımlamaları
Full Local Cache Mimarisi
"""

import os
import logging
from decouple import config

logger = logging.getLogger(__name__)

DB_BACKEND = config("DB_BACKEND", default="sqlite").split('#')[0].strip().lower()
POSTGRES_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))

# Veritabanı yolu - BackendFronend/database klasöründe
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'database',
    'sales_cache.db'
)

def get_connection():
    """Get connection based on backend (SQLite or PostgreSQL)"""
    if DB_BACKEND == "postgresql":
        import psycopg2
        import psycopg2.extras
        _opts = (
            '-c work_mem=8MB '
            '-c maintenance_work_mem=64MB '
            '-c temp_file_limit=1GB '
            '-c statement_timeout=600000 '
            '-c idle_in_transaction_session_timeout=60000'
        )
        return psycopg2.connect(POSTGRES_URL, cursor_factory=psycopg2.extras.DictCursor, options=_opts)
    
    import sqlite3
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60)
    
    # Performans ve Fragmentation Önleme
    conn.execute('PRAGMA journal_mode=WAL')           # Write-Ahead Logging
    conn.execute('PRAGMA synchronous=NORMAL')         # Daha az disk sync
    conn.execute('PRAGMA cache_size=10000')           # 10MB cache
    conn.execute('PRAGMA temp_store=MEMORY')          # Temp işlemler RAM'de
    conn.execute('PRAGMA auto_vacuum=INCREMENTAL')    # Otomatik incremental vacuum
    conn.execute('PRAGMA page_size=4096')             # Optimal sayfa boyutu
    
    conn.row_factory = sqlite3.Row
    return conn

def run_maintenance():
    """Haftalık bakım - Fragmentation temizliği"""
    if DB_BACKEND == "postgresql":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("ANALYZE")
        conn.commit()
        conn.close()
        return True
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA incremental_vacuum(1000)")
    cursor.execute("ANALYZE")
    conn.commit()
    conn.close()
    return True

def run_full_maintenance():
    """Aylık bakım - Tam defragmentation"""
    if DB_BACKEND == "postgresql":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")
        conn.commit()
        conn.close()
        return True
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("VACUUM")
    cursor.execute("ANALYZE")
    conn.commit()
    conn.close()
    return True

def create_schema():
    """Tüm tabloları oluştur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    is_pg = (DB_BACKEND == "postgresql")
    
    # Standardizasyon Kontrolü: grupbirliktelikleri tablosu varsa ve ortak_musteri_sayisi kolonu yoksa rebuild et
    try:
        if is_pg:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'grupbirliktelikleri' AND column_name = 'ortak_musteri_sayisi'
            """)
        else:
            cursor.execute("PRAGMA table_info(grupbirliktelikleri)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'ortak_musteri_sayisi' in cols:
                cursor.execute("SELECT 1") # Dummy to avoid empty fetch if we Skip
            else:
                cursor.execute("SELECT 0 as found") # Indicate missing
        
        found = cursor.fetchone()
        if not found and is_pg: # PG returns nothing if not found
            rebuild_needed = True
        elif not is_pg and found and found[0] == 0: # SQLite dummy check
            rebuild_needed = True
        else:
            rebuild_needed = False
            
        if rebuild_needed:
            logger.info("⚠️ Şema uyuşmazlığı tespit edildi, analitik tabloları yeniden oluşturuluyor...")
            analytics_tables = [
                'urunbirliktelikleri', 'grupbirliktelikleri', 'musterionerileri',
                'birliktelikstratejiskorlari', 'kategoriperformansozet', 'urunperformansdetay'
            ]
            for table in analytics_tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()
    except Exception as e:
        logger.warning(f"Schema check skipped/failed: {e}")

    pk_auto = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    text_type = "TEXT"
    real_type = "DOUBLE PRECISION" if is_pg else "REAL"
    date_type = "DATE"
    datetime_type = "TIMESTAMP" if is_pg else "DATETIME"

    # ========== LOOKUP TABLOLARI ==========
    
    cursor.execute(f"CREATE TABLE IF NOT EXISTS markalar (id {pk_auto}, ad {text_type} UNIQUE NOT NULL)")
    
    cursor.execute(f"CREATE TABLE IF NOT EXISTS kategori_yoneticileri (id {pk_auto}, ad {text_type} UNIQUE NOT NULL)")
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS kategoriler (
            id {pk_auto},
            ana {text_type} NOT NULL,
            alt1 {text_type},
            alt2 {text_type},
            yonetici_id INTEGER,
            UNIQUE(ana, alt1, alt2)
        )
    """)
    
    cursor.execute(f"CREATE TABLE IF NOT EXISTS magazalar (id {pk_auto}, ad {text_type} UNIQUE NOT NULL, bolge {text_type})")
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS urunler (
            id {pk_auto},
            kod {text_type} UNIQUE NOT NULL,
            ad {text_type} NOT NULL,
            marka_id INTEGER,
            kategori_id INTEGER,
            yonetici_id INTEGER,
            FOREIGN KEY (marka_id) REFERENCES markalar(id),
            FOREIGN KEY (kategori_id) REFERENCES kategoriler(id),
            FOREIGN KEY (yonetici_id) REFERENCES kategori_yoneticileri(id)
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS kampanyalar (
            id INTEGER PRIMARY KEY,
            ad {text_type},
            baslangic {date_type},
            bitis {date_type}
        )
    """)
    
    # ========== ANA TABLOLAR ==========
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS musteriler (
            id INTEGER PRIMARY KEY,
            ad {text_type},
            telefon {text_type},
            tip {text_type},
            onay_durumu {text_type},
            kayit_tarihi {date_type},
            kayit_magazasi {text_type},
            rfm_updated_at {text_type}
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS satislar (
            id {pk_auto},
            fis_no {text_type} NOT NULL,
            musteri_id INTEGER,
            tarih {date_type} NOT NULL,
            saat INTEGER,
            tutar {real_type} NOT NULL,
            miktar {real_type},
            urun_id INTEGER,
            magaza_id INTEGER,
            belge_tipi {text_type},
            kampanya_id INTEGER,
            telefon {text_type},
            onay_durumu {text_type},
            satir_no INTEGER DEFAULT 1,
            kategori_id INTEGER,
            marka_id INTEGER,
            belge_toplami {real_type},
            belge_indirim_toplami {real_type},
            sepet_urun_sayisi SMALLINT,
            FOREIGN KEY (musteri_id) REFERENCES musteriler(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id),
            FOREIGN KEY (magaza_id) REFERENCES magazalar(id),
            FOREIGN KEY (kampanya_id) REFERENCES kampanyalar(id),
            UNIQUE(fis_no, satir_no)
        )
    """)
    
    # ========== ÖZET TABLOLAR ==========
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS gunlukozet (
            tarih {date_type} NOT NULL,
            magaza_id INTEGER,
            kategori_id INTEGER,
            marka_id INTEGER,
            toplam_ciro {real_type} DEFAULT 0,
            fis_sayisi INTEGER DEFAULT 0,
            musteri_sayisi INTEGER DEFAULT 0,
            urun_adedi {real_type} DEFAULT 0,
            PRIMARY KEY (tarih, magaza_id, kategori_id, marka_id)
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS genelozet (
            ay {text_type} NOT NULL,
            magaza_id INTEGER,
            toplam_ciro {real_type} DEFAULT 0,
            toplam_fis INTEGER DEFAULT 0,
            toplam_miktar {real_type} DEFAULT 0,
            crm_ciro {real_type} DEFAULT 0,
            crm_fis INTEGER DEFAULT 0,
            crm_musteri INTEGER DEFAULT 0,
            crm_miktar {real_type} DEFAULT 0,
            anonim_ciro {real_type} DEFAULT 0,
            anonim_fis INTEGER DEFAULT 0,
            crm_sepet_ort {real_type} DEFAULT 0,
            anonim_sepet_ort {real_type} DEFAULT 0,
            crm_oran_ciro {real_type} DEFAULT 0,
            crm_oran_fis {real_type} DEFAULT 0,
            PRIMARY KEY (ay, magaza_id)
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS kategorikarsilastirma (
            ay {text_type} NOT NULL,
            kategori {text_type} NOT NULL,
            toplam_ciro {real_type} DEFAULT 0,
            crm_ciro {real_type} DEFAULT 0,
            anonim_ciro {real_type} DEFAULT 0,
            crm_fis INTEGER DEFAULT 0,
            anonim_fis INTEGER DEFAULT 0,
            crm_sepet_ort {real_type} DEFAULT 0,
            anonim_sepet_ort {real_type} DEFAULT 0,
            PRIMARY KEY (ay, kategori)
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS markakarsilastirma (
            ay {text_type} NOT NULL,
            marka {text_type} NOT NULL,
            toplam_ciro {real_type} DEFAULT 0,
            crm_ciro {real_type} DEFAULT 0,
            crm_musteri INTEGER DEFAULT 0,
            PRIMARY KEY (ay, marka)
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS kampanyaozet (
            ay {text_type} NOT NULL,
            kampanya_id INTEGER NOT NULL,
            kampanya_ad {text_type},
            katilim_sayisi INTEGER DEFAULT 0,
            toplam_ciro {real_type} DEFAULT 0,
            benzersiz_musteri INTEGER DEFAULT 0,
            PRIMARY KEY (ay, kampanya_id)
        )
    """)
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS musterisadakat (
            ay {text_type} PRIMARY KEY,
            yeni_musteri INTEGER DEFAULT 0,
            tekrar_musteri INTEGER DEFAULT 0,
            kayip_musteri INTEGER DEFAULT 0,
            yeni_musteri_sepet {real_type} DEFAULT 0,
            tekrar_musteri_sepet {real_type} DEFAULT 0
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS gunlukciroozet (
            tarih {date_type} PRIMARY KEY,
            toplam_ciro {real_type} DEFAULT 0,
            toplam_fis INTEGER DEFAULT 0,
            toplam_musteri INTEGER DEFAULT 0,
            toplam_miktar {real_type} DEFAULT 0,
            sepet_ortalamasi {real_type} DEFAULT 0,
            musteri_basina_ciro {real_type} DEFAULT 0,
            musteri_basina_fis {real_type} DEFAULT 0,
            sku_sayisi INTEGER DEFAULT 0,
            updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS magazagunlukozet (
            tarih {date_type} NOT NULL,
            magaza_id INTEGER NOT NULL,
            toplam_ciro {real_type} DEFAULT 0,
            toplam_fis INTEGER DEFAULT 0,
            toplam_musteri INTEGER DEFAULT 0,
            toplam_miktar {real_type} DEFAULT 0,
            sepet_ortalamasi {real_type} DEFAULT 0,
            sku_sayisi INTEGER DEFAULT 0,
            PRIMARY KEY (tarih, magaza_id)
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS crmozet (
            tarih {text_type} NOT NULL,
            ay {text_type} NOT NULL,
            magaza_id INTEGER,
            kategori_id INTEGER,
            marka_id INTEGER,
            toplam_ciro {real_type} DEFAULT 0,
            toplam_fis {real_type} DEFAULT 0,
            toplam_musteri {real_type} DEFAULT 0,
            toplam_miktar {real_type} DEFAULT 0,
            sepet_ort {real_type} DEFAULT 0,
            PRIMARY KEY (tarih, magaza_id, kategori_id, marka_id)
        )
    """)
    
    # Indexler
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crmozet_tarih ON crmozet(tarih)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crmozet_ay ON crmozet(ay)")

    # ========== MÜŞTERİ DETAY ÖZET (RFM & CLV) ==========
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS musteridetayozet (
            musteri_id INTEGER PRIMARY KEY,
            ad_soyad {text_type},
            email {text_type},
            telefon {text_type},
            sehir {text_type},
            kayit_tarihi {date_type},
            rfm_segment {text_type},
            r_score INTEGER,
            f_score INTEGER,
            m_score INTEGER,
            favori_kategori {text_type},
            favori_marka {text_type},
            favori_magaza {text_type},
            favori_urun {text_type},
            tercih_edilen_saat {text_type},
            gun_tercihi {text_type},
            ortalama_siparis_buyuklugu {real_type},
            ilk_alisveris_tarihi {datetime_type},
            son_alisveris_tarihi {datetime_type},
            musteri_yasi_gun INTEGER,
            toplam_alisveris INTEGER,
            toplam_harcama {real_type},
            ortalama_sepet_tutari {real_type},
            son_30_gun_alisveris INTEGER,
            son_30_gun_harcama {real_type},
            son_90_gun_alisveris INTEGER,
            son_90_gun_harcama {real_type},
            trend {text_type},
            aktivite_durumu {text_type},
            churn_risk_skoru INTEGER,
            lifetime_value_tahmini {real_type},
            toplam_miktar_calculated {real_type},
            sepet_cesitlendirme INTEGER,
            marka_sadakati {real_type},
            saat_sabah INTEGER,
            saat_ogle INTEGER,
            saat_aksam INTEGER,
            saat_gece INTEGER
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mdo_segment ON musteridetayozet(rfm_segment)")

    # En Çok Satanlar
    cursor.execute("DROP TABLE IF EXISTS encoksatanlar")
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS encoksatanlar (
            donem_tipi {text_type} NOT NULL,
            donem_degeri {text_type} NOT NULL,
            grup_tipi {text_type} NOT NULL,
            grup_degeri {text_type} NOT NULL,
            urun_ad {text_type},
            toplam_ciro {real_type} DEFAULT 0,
            toplam_adet {real_type} DEFAULT 0,
            updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (donem_tipi, donem_degeri, grup_tipi, grup_degeri)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_encoksatanlar_query ON encoksatanlar(donem_tipi, donem_degeri, grup_tipi)")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS kategori_analiz_ozet (
            kategori_adi {text_type} NOT NULL,
            level {text_type} NOT NULL,
            total_revenue {real_type} DEFAULT 0,
            total_receipts INTEGER DEFAULT 0,
            total_customers INTEGER DEFAULT 0,
            total_quantity {real_type} DEFAULT 0,
            avg_price {real_type} DEFAULT 0,
            trends_json {text_type},
            top_products_json {text_type},
            rfm_json {text_type},
            associations_json {text_type},
            guncelleme_tarihi {datetime_type} DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (kategori_adi, level)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_kao_kategori ON kategori_analiz_ozet(kategori_adi, level)")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS syncmeta (
            key {text_type} PRIMARY KEY,
            value {text_type},
            updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS globalstatlar (
            key {text_type} PRIMARY KEY,
            value {text_type},
            updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ========== GELİŞMİŞ ANALİTİK TABLOLARI ==========

    # Ürün Birliktelikleri
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS urunbirliktelikleri (
            urun_id_1 INTEGER,
            urun_id_2 INTEGER,
            confidence {real_type},
            lift {real_type},
            ortak_fis_sayisi INTEGER,
            tip {text_type},
            analiz_tarihi {datetime_type},
            PRIMARY KEY (urun_id_1, urun_id_2)
        )
    """)

    # Müşteri Önerileri
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS musterionerileri (
            musteri_id INTEGER,
            urun_id INTEGER,
            urun_ad {text_type},
            kategori_ad {text_type},
            oneri_skoru {real_type},
            oneri_nedeni {text_type},
            updated_at {datetime_type},
            PRIMARY KEY (musteri_id, urun_id)
        )
    """)

    # Günlük Mevsimsellik & Tahmin
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS gunlukmevsimsellik (
            tarih {date_type} PRIMARY KEY,
            gercek_ciro {real_type},
            tahmin_ciro {real_type},
            trend {real_type},
            weekly_effect {real_type},
            yearly_effect {real_type},
            is_anomaly INTEGER,
            anomaly_direction {text_type},
            season {text_type},
            trend_direction {text_type},
            day_of_week INTEGER,
            day_name {text_type}
        )
    """)

    # Segment Ürün Tercihleri
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS segmenturuntercihleri (
            id {pk_auto},
            rfm_segment {text_type},
            kategori_id INTEGER,
            kategori_ad {text_type},
            urun_id INTEGER,
            urun_ad {text_type},
            marka_id INTEGER,
            marka_ad {text_type},
            segment_toplam_musteri INTEGER,
            segment_toplam_ciro {real_type},
            segment_ortalama_sepet {real_type},
            alan_musteri_sayisi INTEGER,
            satis_adedi {real_type},
            toplam_ciro {real_type},
            ortalama_tutar {real_type},
            penetrasyon {real_type},
            genel_penetrasyon {real_type},
            segment_indeks {real_type},
            segment_ortalama_satis_fiyat {real_type},
            genel_ortalama_satis_fiyat {real_type},
            fiyat_toleransi {real_type},
            tekrar_alis INTEGER,
            tekrar_alis_oran {real_type},
            ortalama_satin_alma_sayisi {real_type},
            tercih_seviye {text_type},
            oneri_durumu {text_type},
            kampanya_uygunluk {text_type},
            oneri_skoru {real_type},
            potansiyel_ciro {real_type},
            risk_skoru {real_type},
            last_updated {text_type}
        )
    """)

    # Kategori Performans Özet
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS kategoriperformansozet (
            kategori_id INTEGER PRIMARY KEY,
            kategori_adi {text_type},
            ust_kategori_id INTEGER,
            toplam_urun_sayisi INTEGER,
            aktif_urun_sayisi INTEGER,
            bugun_ciro {real_type},
            dun_ciro {real_type},
            son_7_gun_toplam_ciro {real_type},
            son_30_gun_toplam_ciro {real_type},
            gunluk_ort_ciro {real_type},
            karsilastirma_skoru {real_type},
            rakip_kategoriler {text_type},
            son_30_gun_satis {real_type},
            son_90_gun_satis {real_type},
            toplam_satis {real_type},
            toplam_ciro {real_type},
            toplam_musteri_sayisi INTEGER,
            ortalama_urun_fiyat {real_type},
            ortalama_sepet_tutar {real_type},
            ortalama_siparis_buyuklugu {real_type},
            trend INTEGER,
            trend_yuzde {real_type},
            momentum {text_type},
            toplam_stok_degeri {real_type},
            toplam_stok_adedi {real_type},
            stok_devir_hizi {real_type},
            performans_kategori {text_type},
            pazar_payi {real_type},
            siralama INTEGER,
            last_updated {text_type}
        )
    """)

    # Otomatik Kampanya Önerileri
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS otomatikkampanyaonerileri (
            oneri_id {pk_auto},
            olusturma_tarihi {text_type},
            kampanya_tipi {text_type},
            hedef_segment {text_type},
            hedef_musteri_sayisi INTEGER,
            oncelik_seviye INTEGER,
            urun_id INTEGER,
            urun_ad {text_type},
            kategori_id INTEGER,
            kategori_ad {text_type},
            marka_id INTEGER,
            yonetici_id INTEGER,
            ikinci_urun_id INTEGER,
            ikinci_urun_ad {text_type},
            veri_kaynagi {text_type},
            onerilen_indirim {real_type},
            onerilen_min_tutar {real_type},
            gecerlilik_suresi INTEGER,
            tahmini_katilim INTEGER,
            potansiyel_ciro {real_type},
            birlikte_ciro {real_type},
            roi_tahmini {real_type},
            tahmini_kar {real_type},
            gerekcesi {text_type},
            veri_ozeti {text_type},
            beklenen_sonuc {text_type},
            oneri_durumu {text_type},
            kampanya_id INTEGER,
            son_guncelleme {text_type}
        )
    """)

    # Birliktelik Strateji Skorları
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS birliktelikstratejiskorlari (
            kategori_adi_1 {text_type},
            kategori_adi_2 {text_type},
            strateji {text_type},
            skor {real_type},
            tarih {datetime_type},
            PRIMARY KEY (kategori_adi_1, kategori_adi_2, strateji)
        )
    """)

    # BrandSummary (Marka Özeti)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS brandsummary (
            brand_id INTEGER,
            brand_name {text_type},
            year INTEGER,
            month INTEGER,
            region {text_type},
            customer_type {text_type},
            segment {text_type},
            approval_status {text_type},
            category_id INTEGER,
            category_main {text_type},
            category_sub1 {text_type},
            category_sub2 {text_type},
            total_sales {real_type},
            total_units {real_type},
            customer_count INTEGER,
            brand_name_norm {text_type},
            region_norm {text_type},
            customer_type_norm {text_type},
            approval_status_norm {text_type},
            segment_norm {text_type},
            category_norm {text_type},
            category_sub1_norm {text_type},
            category_sub2_norm {text_type}
        )
    """)

    # Segment Özeti
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS segmentozet (
            segment {text_type} PRIMARY KEY,
            customer_count INTEGER,
            total_revenue {real_type},
            transaction_count INTEGER,
            updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Aylık Müşteri Özeti
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS aylikmusteriozet (
            yil INTEGER,
            ay {text_type} PRIMARY KEY,
            musteri_sayisi INTEGER
        )
    """)

    # Yıllık Müşteri Özeti
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS yillikmusteriozet (
            yil INTEGER PRIMARY KEY,
            musteri_sayisi INTEGER
        )
    """)

    # Müşteri Etiketleri
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS musterietiketleri (
            id {pk_auto},
            musteri_id INTEGER,
            etiket_grubu {text_type},
            etiket_adi {text_type},
            skor {real_type} DEFAULT 1.0,
            analiz_tarihi {datetime_type} DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(musteri_id, etiket_adi)
        )
    """)

    # Cache KPI
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS cache_kpi (
            key {text_type} PRIMARY KEY,
            value {real_type},
            updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Grup Birliktelikleri (Kategori & Marka Seviyesinde)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS grupbirliktelikleri (
            id {pk_auto},
            marka_id_1 INTEGER,
            kategori_id_1 INTEGER,
            marka_id_2 INTEGER,
            kategori_id_2 INTEGER,
            confidence {real_type},
            lift {real_type},
            ortak_fis_sayisi INTEGER,
            tip {text_type},
            analiz_tarihi {datetime_type} DEFAULT CURRENT_TIMESTAMP,
            ortak_musteri_sayisi INTEGER DEFAULT 0
        )
    """)

    # daily_metrics_summary (KAPSAMLI ÖZET - Tüm dashboard filtrelerini kapsar)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS daily_metrics_summary (
            tarih {date_type} NOT NULL,
            magaza_id INTEGER DEFAULT 0,
            kategori_id INTEGER DEFAULT 0,
            marka_id INTEGER DEFAULT 0,
            customer_type {text_type} DEFAULT 'Bilinmiyor',
            rfm_segment {text_type} DEFAULT 'Diğer',
            onay_durumu {text_type} DEFAULT 'Bilinmiyor',
            revenue {real_type} DEFAULT 0,
            receipt_count INTEGER DEFAULT 0,
            customer_count INTEGER DEFAULT 0,
            unit_count {real_type} DEFAULT 0,
            PRIMARY KEY (tarih, magaza_id, kategori_id, marka_id, customer_type, rfm_segment, onay_durumu)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dms_tarih ON daily_metrics_summary(tarih)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dms_filters ON daily_metrics_summary(magaza_id, kategori_id, marka_id, rfm_segment)")

    # product_daily_summary (Ürün Bazlı Günlük Özet)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS product_daily_summary (
            tarih {date_type} NOT NULL,
            urun_id INTEGER NOT NULL,
            revenue {real_type} DEFAULT 0,
            unit_count {real_type} DEFAULT 0,
            customer_count INTEGER DEFAULT 0,
            receipt_count INTEGER DEFAULT 0,
            PRIMARY KEY (tarih, urun_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pds_tarih ON product_daily_summary(tarih)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pds_urun ON product_daily_summary(urun_id)")

    # Ürün Performans Detay
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS urunperformansdetay (
            urunid INTEGER PRIMARY KEY,
            urunadi {text_type},
            kategoriid INTEGER,
            kategoriadi {text_type},
            markaid INTEGER,
            markaadi {text_type},
            guncelfiyat {real_type},
            stokmiktari INTEGER,
            urunolusturmatarihi {datetime_type},
            son7gunsatis INTEGER DEFAULT 0,
            son7gunciro {real_type} DEFAULT 0,
            son7gunmusterisayisi INTEGER DEFAULT 0,
            son30gunsatis INTEGER DEFAULT 0,
            son30gunciro {real_type} DEFAULT 0,
            son30gunmusterisayisi INTEGER DEFAULT 0,
            son30gunortfiyat {real_type} DEFAULT 0,
            son90gunsatis INTEGER DEFAULT 0,
            son90gunciro {real_type} DEFAULT 0,
            son90gunmusterisayisi INTEGER DEFAULT 0,
            toplamsatis INTEGER DEFAULT 0,
            toplamciro {real_type} DEFAULT 0,
            toplammusterisayisi INTEGER DEFAULT 0,
            ilksatistarihi {datetime_type},
            sonsatistarihi {datetime_type},
            trend_7_30 INTEGER DEFAULT 0,
            trend_30_60 INTEGER DEFAULT 0,
            hiztrendi {text_type},
            stokdurumu {text_type},
            gunlukortsatis {real_type} DEFAULT 0,
            tahministokgunu {real_type} DEFAULT 0,
            performanskategori {text_type},
            kategoriicindesira INTEGER,
            birliktesatilanurunsayisi INTEGER DEFAULT 0,
            encokbirliktesatilan {text_type},
            crosssellpotansiyeli {real_type} DEFAULT 0,
            uyaridurumu {text_type},
            guncellemetarihi {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ========== SİSTEM LOGLARI ==========
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS system_logs (
            id {pk_auto},
            service_name {text_type} NOT NULL,
            level {text_type} NOT NULL,
            message {text_type} NOT NULL,
            timestamp {datetime_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC)")

    # Etiket Snapshot (günlük etiket sayıları — trend takibi için)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS etiket_snapshot (
            id {pk_auto},
            tarih {date_type} NOT NULL,
            etiket_kolon {text_type} NOT NULL,
            sayi INTEGER NOT NULL DEFAULT 0,
            toplam_musteri INTEGER NOT NULL DEFAULT 0,
            UNIQUE(tarih, etiket_kolon)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_etiket_snapshot_tarih ON etiket_snapshot(tarih DESC)")

    # ========== INDEXLER ==========
    # Satislar - temel indexler
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_tarih ON satislar(tarih)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_musteri ON satislar(musteri_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_magaza ON satislar(magaza_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_fis ON satislar(fis_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_urun ON satislar(urun_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_kategori ON satislar(kategori_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_marka ON satislar(marka_id)")

    # Satislar - composite indexler (dashboard sorguları için kritik)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_musteri_tarih ON satislar(musteri_id, tarih DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_tarih_magaza ON satislar(tarih, magaza_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_tarih_musteri ON satislar(tarih, musteri_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_satislar_urun_tutar ON satislar(urun_id, tutar, miktar)")

    # Özet tablolar
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gunluk_tarih ON gunlukozet(tarih)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_genel_ay ON genelozet(ay)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_urunler_kod ON urunler(kod)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gunluk_ciro_tarih ON gunlukciroozet(tarih)")

    # Müşteri tabloları
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mdo_segment ON musteridetayozet(rfm_segment)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_musteriler_tip ON musteriler(tip)")

    # Brandsummary performans indexleri
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_main ON brandsummary(year, month)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_dims ON brandsummary(region_norm, customer_type_norm, category_norm, brand_name_norm)")

    # === Mevcut Tablolara Yeni Eklenen Sütunlar (Migration) ===
    def add_col_if_not_exists(table_name, col_name, col_type):
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
            conn.commit()
            logger.info(f"➕ Yeni Sütun Eklendi: {table_name}.{col_name}")
        except Exception:
            conn.rollback() # Sütun zaten varsa veya hata oluşursa yoksay

    add_col_if_not_exists('urunler', 'yonetici_id', 'INTEGER')
    add_col_if_not_exists('kategoriler', 'yonetici_id', 'INTEGER')
    add_col_if_not_exists('otomatikkampanyaonerileri', 'yonetici_id', 'INTEGER')
    add_col_if_not_exists('musteriler', 'rfm_updated_at', text_type)
    # Eski satinalmacilar tablosunu kategori_yoneticileri olarak migrate et
    try:
        cursor.execute("ALTER TABLE satinalmacilar RENAME TO kategori_yoneticileri")
        conn.commit()
        logger.info("satinalmacilar tablosu kategori_yoneticileri olarak yeniden adlandırıldı")
    except Exception:
        pass  # Zaten yeniden adlandırılmış veya tablo yok
    add_col_if_not_exists('otomatikkampanyaonerileri', 'marka_id', 'INTEGER')
    add_col_if_not_exists('product_daily_summary', 'receipt_count', 'INTEGER')

    conn.commit()
    conn.close()
    logger.info(f"{DB_BACKEND.upper()} şeması oluşturuldu")
    return True

def reset_database():
    """Veritabanını sıfırla"""
    if DB_BACKEND == "postgresql":
        # PostgreSQL'de reset için tablo silme mantığı değişebilir ama şimdilik create_schema ile IF NOT EXISTS yeterli olabilir
        # Veya tüm tabloları DROP yapan bir fonksiyon eklenebilir.
        pass
    elif os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return create_schema()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_schema()
    print(f"Veritabanı oluşturuldu: {DB_PATH if DB_BACKEND == 'sqlite' else 'PostgreSQL'}")
