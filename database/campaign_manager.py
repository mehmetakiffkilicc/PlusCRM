import os
import sys
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path

# Django bağlamında backend/ root'ta, sync_worker bağlamında proje kökünde
_BASE = Path(__file__).resolve().parents[1]  # BackendFronend/
_BACKEND = _BASE / 'backend'
for _p in [str(_BASE), str(_BACKEND)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.api import db_engine

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def kampanya_tablo_olustur():
    """
    otomatikkampanyaonerileri tablosunu oluşturur
    """
    conn = db_engine.get_connection()
    cursor = conn.cursor()

    logger.info("otomatikkampanyaonerileri tablosu oluşturuluyor...")
    
    logger.info("otomatikkampanyaonerileri tablosu kontrol ediliyor...")
    
    if db_engine.DB_BACKEND == "postgresql":
        # ALTER TABLE IF EXISTS for sources
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS otomatikkampanyaonerileri (
            oneri_id SERIAL PRIMARY KEY,
            olusturma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            kampanya_tipi TEXT, 
            hedef_segment TEXT,
            hedef_musteri_sayisi INTEGER,
            oncelik_seviye INTEGER,
            urun_id INTEGER,
            urun_ad TEXT,
            kategori_id INTEGER,
            kategori_ad TEXT,
            ikinci_urun_id INTEGER,
            ikinci_urun_ad TEXT,
            veri_kaynagi TEXT,
            onerilen_indirim REAL,
            onerilen_min_tutar REAL,
            gecerlilik_suresi INTEGER,
            tahmini_katilim INTEGER,
            potansiyel_ciro REAL,
            birlikte_ciro REAL,
            roi_tahmini REAL,
            tahmini_kar REAL,
            gerekcesi TEXT,
            veri_ozeti TEXT,
            beklenen_sonuc TEXT,
            oneri_durumu TEXT DEFAULT 'Bekliyor',
            kaynak_kategori_ad TEXT,
            lift REAL,
            guven REAL,
            fis_sayisi INTEGER,
            yonetici_id INTEGER,
            marka_id INTEGER,
            kampanya_id INTEGER,
            son_guncelleme TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS kaynak_kategori_ad TEXT")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS lift REAL")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS guven REAL")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS yonetici_id INTEGER")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS marka_id INTEGER")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS fis_sayisi INTEGER")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS lift REAL")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS guven REAL")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN IF NOT EXISTS onerilen_urunler TEXT")
        except: pass
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS otomatikkampanyaonerileri (
            oneriid INTEGER PRIMARY KEY AUTOINCREMENT,
            olusturmatarihi TEXT,
            kampanyatipi TEXT, 
            hedefsegment TEXT,
            hedefmusterisayisi INTEGER,
            oncelikseviye INTEGER,
            urunid INTEGER,
            urunadi TEXT,
            kategoriid INTEGER,
            kategoriadi TEXT,
            ikinciurunid INTEGER,
            ikinciurunadi TEXT,
            verikaynagi TEXT,
            onerilenindirim REAL,
            onerilenmintutar REAL,
            gecerliliksuresi INTEGER,
            tahminikatilim INTEGER,
            potansiyelciro REAL,
            tahminikar REAL,
            roitahmini REAL,
            gerekcesi TEXT,
            veriozeti TEXT,
            beklenensonuc TEXT,
            oneridurumu TEXT DEFAULT 'Bekliyor',
            kaynakkategoriad TEXT,
            yonetici_id INTEGER,
            marka_id INTEGER,
            fis_sayisi INTEGER,
            lift REAL,
            guven REAL,
            kampanyaid INTEGER,
            songuncelleme TEXT
        )
        """)
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN kaynakkategoriad TEXT")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN yonetici_id INTEGER")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN marka_id INTEGER")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN fis_sayisi INTEGER")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN lift REAL")
        except: pass
        try:
            cursor.execute("ALTER TABLE otomatikkampanyaonerileri ADD COLUMN guven REAL")
        except: pass
    
    conn.commit()
    db_engine.release_connection(conn)
    logger.info("otomatikkampanyaonerileri tablosu hazir.")

def _get_loyalty_products_for_segment(cursor, ph, segment_name, order_expr, excluded_ids, limit=6):
    """
    Her loyalty segmenti için kendi sıralama stratejisine göre ürün çeker.
    excluded_ids: zaten başka segmentlere verilmiş ürün id'leri (SQL NOT IN ile dışlanır).
    """
    if excluded_ids:
        excl_placeholders = ','.join([ph] * len(excluded_ids))
        excl_clause = f"AND urun_id NOT IN ({excl_placeholders})"
        excl_params = list(excluded_ids)
    else:
        excl_clause = ""
        excl_params = []

    cursor.execute(f"""
        SELECT urun_id, urun_ad, kategori_id, kategori_ad,
               segment_toplam_musteri, segment_ortalama_sepet, penetrasyon, toplam_ciro
        FROM segmenturuntercihleri
        WHERE tercih_seviye IN ('Favori', 'Sevilen')
          AND TRIM(rfm_segment) = {ph}
          {excl_clause}
        ORDER BY {order_expr}
        LIMIT {ph}
    """, [segment_name] + excl_params + [limit])
    return cursor.fetchall()


def kampanya_onerileri_uret():
    """
    Analiz tablolarından öneri üretir
    """
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    ph = db_engine.ph()
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    oneriler = []

    # Sadece yeniden üretilecek tipler temizlenir — Cross-Sell ve Clearance korunur.
    logger.info("Eski Win-Back ve Loyalty kampanyalar temizleniyor (Cross-Sell korunuyor)...")
    cursor.execute("""
        DELETE FROM otomatikkampanyaonerileri
        WHERE oneri_durumu = 'Bekliyor'
          AND kampanya_tipi IN ('Win-Back', 'Loyalty')
    """)
    conn.commit()

    # Tüm kampanya tipleri için ortak: kategori bazlı gerçek ortalama birim fiyat
    kat_avg_fiyat = {}
    urun_avg_fiyat = {}
    try:
        cursor.execute("""
            SELECT s.urun_id,
                   u.kategori_id,
                   AVG(s.tutar / NULLIF(s.miktar, 0)) as avg_birim_fiyat
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            WHERE s.musteri_id IS NOT NULL AND s.miktar > 0 AND s.tutar > 0
            GROUP BY s.urun_id, u.kategori_id
        """)
        for r in cursor.fetchall():
            try:
                uid = int(r['urun_id'] or 0)
                kid = int(r['kategori_id'] or 0)
                avg = float(r['avg_birim_fiyat'] or 0)
                if uid and avg:
                    urun_avg_fiyat[uid] = avg
                if kid and avg:
                    if kid not in kat_avg_fiyat:
                        kat_avg_fiyat[kid] = avg
                    else:
                        # running average — kampanya üretiminde kategori ortalaması kullanılıyor
                        # basitçe ilk değeri koru (GROUP BY zaten ortalıyor)
                        pass
            except:
                pass
    except Exception as e:
        logger.error(f"kat_avg_fiyat sorgusu hatası: {e}")

    # Kategori ortalamasını düzgün hesapla (urun bazlı gruplamadan ayrı)
    try:
        cursor.execute("""
            SELECT u.kategori_id,
                   AVG(s.tutar / NULLIF(s.miktar, 0)) as avg_birim_fiyat
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            WHERE s.musteri_id IS NOT NULL AND s.miktar > 0 AND s.tutar > 0
            GROUP BY u.kategori_id
        """)
        for r in cursor.fetchall():
            try:
                kid = int(r['kategori_id'] or 0)
                if kid:
                    kat_avg_fiyat[kid] = float(r['avg_birim_fiyat'] or 0)
            except:
                pass
    except Exception as e:
        logger.error(f"kat_avg_fiyat (kategori) sorgusu hatası: {e}")

    # 1. CROSS-SELL KAMPANYALARI
    logger.info("Cross-sell kampanyaları oluşturuluyor...")

    try:
        # Timeout ayarı (3 dakika)
        cursor.execute("SET statement_timeout = 180000")
        
        # 1. Adım: Tüm Kategorileri Çek
        cursor.execute("SELECT id, ana, alt1, alt2 FROM kategoriler")
        kat_map = {}
        for r in cursor.fetchall():
            try:
                # Kategori isimlerini Ana kategori olarak al (eski yöntem)
                kid = int(r['id'])
                kad = str(r['alt2']) if r['alt2'] else (str(r['alt1']) if r['alt1'] else str(r['ana']))
                kat_map[kid] = kad
            except Exception as e:
                logger.error(f"Error parsing category map: {e}")
                continue

        # 2. Adım: Temel Birliktelikleri Çek
        # Her kategori için (kategori_id_1'e göre partition yaparak) en yüksek liftli en fazla 5 birlikteliği alıyoruz.
        # Bu şekilde "Temizlik Eldivenleri" gibi daha niş kategorilerin bile kampanyasız kalması engelleniyor.
        cursor.execute("""
            SELECT kategori_id_1, kategori_id_2, lift, confidence, ortak_fis_sayisi, ortak_musteri_sayisi
            FROM grupbirliktelikleri
            WHERE tip = 'CAT_ONLY_SQL' AND lift >= 2.0 AND ortak_fis_sayisi >= 500
            ORDER BY kategori_id_1, lift DESC, ortak_fis_sayisi DESC
        """)
        associations = cursor.fetchall()

        # 3. Adım: Ürün Tercihlerini ve Kategori İstatistiklerini Çek
        cursor.execute("""
            SELECT kategoriid as kategori_id, urunid as urun_id, urunadi as urun_ad,
                   toplamciro as toplam_ciro, guncelfiyat as ortalama_tutar
            FROM (
                SELECT kategoriid, urunid, urunadi, toplamciro, guncelfiyat,
                       ROW_NUMBER() OVER(PARTITION BY kategoriid ORDER BY toplamsatis DESC) as rn
                FROM urunperformansdetay
                WHERE stokdurumu != 'Yok'
            ) t
            WHERE rn <= 10
        """)

        top_products = {}
        top_product_ids = {}
        for r in cursor.fetchall():
            try:
                kid = int(r['kategori_id'] or 0)
                if not kid: continue
                uid = int(r['urun_id'])
                uad = str(r['urun_ad'])
                ciro = float(r['toplam_ciro'] or 0)
                # Gerçek ortalama birim fiyatı: satislar tablosundan hesaplanan > guncelfiyat
                ort = urun_avg_fiyat.get(uid) or float(r['ortalama_tutar'] or 0) or kat_avg_fiyat.get(kid, 0)

                if kid not in top_products:
                    top_products[kid] = []
                    top_product_ids[kid] = set()

                if uid not in top_product_ids[kid] and len(top_products[kid]) < 10:
                    top_products[kid].append({'id': uid, 'ad': uad, 'ciro': ciro, 'ort': round(ort, 2)})
                    top_product_ids[kid].add(uid)
            except Exception as e:
                logger.error(f"Error parsing top products: {e}")
                continue

        # Kategori istatistiklerini satislar tablosundan gerçek zamanlı al
        cursor.execute("""
            SELECT u.kategori_id,
                   COUNT(DISTINCT s.musteri_id) as musteri_sayisi
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            WHERE s.musteri_id IS NOT NULL AND s.miktar > 0 AND s.tutar > 0
            GROUP BY u.kategori_id
        """)
        kat_stats = {}
        for r in cursor.fetchall():
            try:
                kid = int(r['kategori_id'] or 0)
                if kid:
                    kat_stats[kid] = int(r['musteri_sayisi'] or 0)
            except:
                pass

        # 4. Adım: Birleştir — tek yönlü (A->B), kat_usage limiti yok
        for row in associations:
            try:
                k1_id = int(row['kategori_id_1'])
                k2_id = int(row['kategori_id_2'])

                lift = float(row['lift'])
                o_cust = int(row['ortak_musteri_sayisi'] or 0)
                o_fis = int(row['ortak_fis_sayisi'] or 0)

                k1_ad = kat_map.get(k1_id, f"Kat_{k1_id}")
                k2_ad = kat_map.get(k2_id, f"Kat_{k2_id}")

                if k1_id == k2_id or k1_ad == k2_ad:
                    continue

                priority = 2 if lift > 1.5 else 3

                # Gerçek Hedef Müşteri: 1. Kategoriyi almış ama 2. Kategoriyi ALMAMIŞ kişiler
                k1_musteri = kat_stats.get(k1_id, 0)
                hedef_musteri = max((k1_musteri - o_cust), 10) if k1_musteri > o_cust else max(k1_musteri, 10)

                # Hedef kategorinin ortalama fiyatı: satislar gerçek ortalaması > fallback
                avg_ort = kat_avg_fiyat.get(k2_id) or 150

                # Simetrik kontrol: her iki yönde de birliktelik varsa alfabetik grup adı
                is_bilateral = any(
                    int(r2['kategori_id_1']) == k2_id and int(r2['kategori_id_2']) == k1_id
                    for r2 in associations
                )
                if is_bilateral:
                    grup_adlari = sorted([k1_ad, k2_ad])
                    group_key = f"{grup_adlari[0]} & {grup_adlari[1]}"
                elif " & " in k1_ad:
                    grup_adlari = sorted([p.strip() for p in k1_ad.split('&')])
                    group_key = " & ".join(grup_adlari)
                else:
                    group_key = k1_ad

                hedef_segment = f"{group_key} Alıcıları"

                # Lift bazlı dinamik dönüşüm oranı hesaplaması
                # Kampanyanın organik alımdan daha düşük bir katılım öngörmesini engellemek için
                # hem hedef kitle büyüklüğünü hem de mevcut organik katılımı dikkate alıyoruz.
                _lift = float(row['lift'] or 2.0)
                
                # 1. Kitle odaklı organik dönüşüm potansiyeli (Lift arttıkça hedef kitlenin %5'i ile %25'i arası)
                dinamik_donusum_orani = min(0.25, max(0.05, _lift * 0.05))
                kitle_bazli_katilim = hedef_musteri * dinamik_donusum_orani
                
                # 2. Organik alışkanlığın kampanyayla hızlandırılmış hali
                # Zaten alanların (o_cust) sayısı üzerine lift etkisini ekliyoruz
                organik_bazli_katilim = o_cust * max(1.5, _lift * 0.8)
                
                # İkisinden yüksek olanı alıyoruz, fakat var olan hedef müşteriyi geçemez
                tahmini_katilim_raw = max(kitle_bazli_katilim, organik_bazli_katilim)
                tahmini_katilim = max(1, min(round(tahmini_katilim_raw), hedef_musteri))

                oneriler.append({
                    'KampanyaTipi': 'Cross-Sell',
                    'HedefSegment': hedef_segment,
                    'HedefMusteriSayisi': hedef_musteri,
                    'OncelikSeviye': priority,
                    'UrunID': top_products[k2_id][0]['id'] if k2_id in top_products and top_products[k2_id] else None,
                    'UrunAdi': top_products[k2_id][0]['ad'] if k2_id in top_products and top_products[k2_id] else k2_ad,
                    'KategoriID': k2_id,
                    'KategoriAdi': k2_ad,
                    'IkinciUrunID': k1_id,
                    'IkinciUrunAdi': group_key,
                    'VeriKaynagi': 'Kategori Birlikteliği (CAT_ONLY)',
                    'OnerilenIndirim': 25.0,
                    'OnerilenMinTutar': round(avg_ort * 0.75, 2),  # %25 indirimli kampanya fiyatı
                    'GecerlilikSuresi': 15,
                    'TahminiKatilim': tahmini_katilim,
                    'PotansiyelCiro': round(tahmini_katilim * avg_ort * 0.75, 2),
                    'BirlikteCiro': round(o_cust * avg_ort, 2),  # ortak musterilerin mevcut birlikte alim cirosu
                    'RoiTahmini': round((tahmini_katilim * avg_ort * 0.75) / max(tahmini_katilim * avg_ort * 0.25, 1), 2),
                    'Gerekcesi': f"{k1_ad} alan müşterilere {k2_ad} kategorisinden çapraz satış önerisi.",
                    'VeriOzeti': f"Lift: {lift:.2f}, Güven: %{float(row['confidence'])*100:.0f}, Fiş: {o_fis}, Ortak müşteri: {o_cust}",
                    'KaynakKategoriAd': k1_ad,
                    'Lift': lift,
                    'Guven': float(row['confidence']),
                    'FisSayisi': o_fis,
                    'OrtakMusteriSayisi': o_cust,
                    'OnerilenUrunler': json.dumps(top_products.get(k2_id, []))
                })
            except Exception as e:
                logger.error(f"Error merging row for cross-sell: {e}")
                continue

    except Exception as e:
        logger.error(f"Error generating cross-sell campaigns: {e}")

    # 2. CLEARANCE
    cursor.execute("""
        SELECT upd.urunid, upd.stokmiktari, upd.performanskategori, upd.son30gunciro, upd.son30gunsatis, upd.tahministokgunu,
               u.ad as urun_adi, k.ana as kat_ad
        FROM urunperformansdetay upd
        JOIN urunler u ON upd.urunid = u.id
        JOIN kategoriler k ON u.kategori_id = k.id
        WHERE upd.stokdurumu = 'Fazla' AND upd.performanskategori IN ('Dusuk', 'Durgun')
        ORDER BY upd.stokmiktari DESC LIMIT 5
    """)
    for r in cursor.fetchall():
        # r fetchall() sonucu olduğu için tuple/dict olabilir, db_engine.val ile güvenli erişim
        oneriler.append({
            'KampanyaTipi': 'Clearance',
            'HedefSegment': 'All Active Customers',
            'HedefMusteriSayisi': 5000,
            'OncelikSeviye': 1,
            'UrunID': db_engine.val(r, 'urunid'),
            'UrunAdi': db_engine.val(r, 'urun_adi'),
            'KategoriID': 0,
            'KategoriAdi': db_engine.val(r, 'kat_ad'),
            'VeriKaynagi': 'urunperformansdetay',
            'OnerilenIndirim': 35.0,
            'OnerilenMinTutar': 0,
            'GecerlilikSuresi': 7,
            'TahminiKatilim': 250,
            'PotansiyelCiro': int(250 * (db_engine.val(r, 'son30gunciro') or 0) / max(1, db_engine.val(r, 'son30gunsatis') or 1)),
            'Gerekcesi': f"Ürün stokta fazla ({db_engine.val(r, 'stokmiktari') or 0:.0f} adet) ve satış hızı düşük. Tahmini stok ömrü {db_engine.val(r, 'tahministokgunu') or 0:.0f} gün.",
            'VeriOzeti': f"Stok: {db_engine.val(r, 'stokmiktari')}, Performans: {db_engine.val(r, 'performanskategori')}, Tahmini Stok Gunu: {db_engine.val(r, 'tahministokgunu')}",
            'BeklenenSonuc': "Stok seviyesini 'Normal'e indirmek.",
            'KaynakKategoriAd': db_engine.val(r, 'kat_ad')
        })

    # Clearance kampanyalar üretilmişse onları da temizle (Cross-Sell hariç)
    clearance_uretildi = any(o['KampanyaTipi'] == 'Clearance' for o in oneriler)
    if clearance_uretildi:
        cursor.execute("DELETE FROM otomatikkampanyaonerileri WHERE oneri_durumu = 'Bekliyor' AND kampanya_tipi = 'Clearance'")
    
    # 3. WIN-BACK (Diversified across top categories)
    logger.info("Win-back kampanyaları oluşturuluyor (çeşitlendirilmiş)...")
    try:
        # Churn-risk segments with numbered format (matching musteriler.rfm_segment)
        churn_segments = [
            ('11-) Kayıp Müşteriler', 'Kayip Musteriler'),
            ('10-) Uyuyanlar', 'Uyuyanlar'),
            ('08-) İlgi Bekleyenler', 'Ilgi Bekleyenler'),
            ('09-) Risk Altındakiler', 'Risk Altindakiler'),
        ]
        
        # Step 1: Get segment counts and churn risk from musteridetayozet
        segment_info = {}
        for seg_numbered, seg_display in churn_segments:
            cursor.execute(f"""
                SELECT COUNT(*) as cnt, AVG(churn_risk_skoru) as avg_risk
                FROM musteridetayozet
                WHERE TRIM(rfm_segment) = {ph} OR TRIM(rfm_segment) = {ph}
            """, [seg_numbered, seg_display])
            row = cursor.fetchone()
            cnt = db_engine.val(row, 'cnt', 0) or 0
            if cnt == 0:
                # Fallback: count from musteriler
                cursor.execute(f"SELECT COUNT(*) as cnt FROM musteriler WHERE rfm_segment = {ph}", [seg_numbered])
                cnt = db_engine.val(cursor.fetchone(), 'cnt', 0) or 0
            avg_risk = db_engine.val(row, 'avg_risk', 80) or 80
            if cnt > 0:
                segment_info[seg_numbered] = {
                    'display': seg_display,
                    'count': cnt,
                    'avg_risk': avg_risk
                }
        
        logger.info(f"  Churn segments found: {list(segment_info.keys())}")

        # Step 2: Get top products per 'ana' category for each churn segment
        # Each segment uses a DIFFERENT behavioral ordering signal to avoid identical recommendations
        used_urun_ids_winback = set()   # global product dedup across all win-back segments
        used_categories_per_seg = {}    # {seg_numbered: set(ana)} — per-segment category dedup

        def _get_winback_products(cursor, ph, seg_numbered, seg_display, is_pg):
            if seg_display == 'Kayip Musteriler':
                cursor.execute(f"""
                    WITH churn_custs AS (
                        SELECT id FROM musteriler WHERE rfm_segment = {ph}
                    ),
                    cat_products AS (
                        SELECT k.ana,
                               COALESCE(k.alt2, k.alt1, k.ana) as kat_ad,
                               k.id as kat_id,
                               u.id as urun_id, u.ad as urun_ad,
                               SUM(s.tutar) as ciro,
                               COUNT(DISTINCT s.musteri_id) as musteri,
                               MAX(s.tarih) as son_alis,
                               ROW_NUMBER() OVER (
                                   PARTITION BY k.ana
                                   ORDER BY COUNT(DISTINCT s.musteri_id) DESC, SUM(s.tutar) DESC
                               ) as rn
                        FROM satislar s
                        JOIN urunler u ON s.urun_id = u.id
                        JOIN kategoriler k ON s.kategori_id = k.id
                        WHERE s.musteri_id IN (SELECT id FROM churn_custs)
                          AND s.tutar > 0
                        GROUP BY k.ana, k.id, k.alt2, k.alt1, u.id, u.ad
                    )
                    SELECT ana, kat_ad, kat_id, urun_id, urun_ad, ciro, musteri, son_alis
                    FROM cat_products WHERE rn = 1 AND ciro > 1000
                    ORDER BY son_alis DESC, musteri DESC, ciro DESC
                    LIMIT 20
                """, [seg_numbered])
            elif seg_display == 'Uyuyanlar':
                recent_date = "CURRENT_DATE - INTERVAL '90 days'" if is_pg else "date('now', '-90 days')"
                cursor.execute(f"""
                    WITH churn_custs AS (
                        SELECT id FROM musteriler WHERE rfm_segment = {ph}
                    ),
                    all_cat AS (
                        SELECT k.ana,
                               COALESCE(k.alt2, k.alt1, k.ana) as kat_ad,
                               k.id as kat_id,
                               u.id as urun_id, u.ad as urun_ad,
                               SUM(s.tutar) as ciro,
                               COUNT(DISTINCT s.musteri_id) as musteri,
                               MAX(s.tarih) as son_alis,
                               SUM(CASE WHEN s.tarih >= {recent_date} THEN s.tutar ELSE 0 END) as son90_ciro,
                               ROW_NUMBER() OVER (
                                   PARTITION BY k.ana
                                   ORDER BY COUNT(DISTINCT s.musteri_id) DESC, SUM(s.tutar) DESC
                               ) as rn
                        FROM satislar s
                        JOIN urunler u ON s.urun_id = u.id
                        JOIN kategoriler k ON s.kategori_id = k.id
                        WHERE s.musteri_id IN (SELECT id FROM churn_custs)
                          AND s.tutar > 0
                        GROUP BY k.ana, k.id, k.alt2, k.alt1, u.id, u.ad
                    )
                    SELECT ana, kat_ad, kat_id, urun_id, urun_ad, ciro, musteri, son_alis,
                           (ciro - son90_ciro) as nostalji_skoru
                    FROM all_cat WHERE rn = 1 AND ciro > 1000
                    ORDER BY nostalji_skoru DESC, musteri DESC, ciro DESC
                    LIMIT 20
                """, [seg_numbered])
            elif seg_display == 'Risk Altindakiler':
                cursor.execute(f"""
                    WITH churn_custs AS (
                        SELECT id FROM musteriler WHERE rfm_segment = {ph}
                    ),
                    cat_agg AS (
                        SELECT k.ana,
                               COALESCE(k.alt2, k.alt1, k.ana) as kat_ad,
                               k.id as kat_id,
                               u.id as urun_id, u.ad as urun_ad,
                               SUM(s.tutar) as ciro,
                               COUNT(DISTINCT s.musteri_id) as musteri,
                               COUNT(s.id) as islem_sayisi,
                               MAX(s.tarih) as son_alis,
                               CAST(COUNT(s.id) AS FLOAT) / NULLIF(COUNT(DISTINCT s.musteri_id), 0) as tekrar_oran,
                               ROW_NUMBER() OVER (
                                   PARTITION BY k.ana
                                   ORDER BY
                                       CAST(COUNT(s.id) AS FLOAT) / NULLIF(COUNT(DISTINCT s.musteri_id), 0) DESC,
                                       COUNT(DISTINCT s.musteri_id) DESC
                               ) as rn
                        FROM satislar s
                        JOIN urunler u ON s.urun_id = u.id
                        JOIN kategoriler k ON s.kategori_id = k.id
                        WHERE s.musteri_id IN (SELECT id FROM churn_custs)
                          AND s.tutar > 0
                        GROUP BY k.ana, k.id, k.alt2, k.alt1, u.id, u.ad
                    )
                    SELECT ana, kat_ad, kat_id, urun_id, urun_ad, ciro, musteri, son_alis, tekrar_oran
                    FROM cat_agg WHERE rn = 1 AND ciro > 1000
                    ORDER BY tekrar_oran DESC, musteri DESC, ciro DESC
                    LIMIT 20
                """, [seg_numbered])
            else:
                cursor.execute(f"""
                    WITH churn_custs AS (
                        SELECT id FROM musteriler WHERE rfm_segment = {ph}
                    ),
                    cat_products AS (
                        SELECT k.ana,
                               COALESCE(k.alt2, k.alt1, k.ana) as kat_ad,
                               k.id as kat_id,
                               u.id as urun_id, u.ad as urun_ad,
                               SUM(s.tutar) as ciro,
                               COUNT(DISTINCT s.musteri_id) as musteri,
                               MAX(s.tarih) as son_alis,
                               ROW_NUMBER() OVER (
                                   PARTITION BY k.ana
                                   ORDER BY SUM(s.tutar) DESC, COUNT(DISTINCT s.musteri_id) DESC
                               ) as rn
                        FROM satislar s
                        JOIN urunler u ON s.urun_id = u.id
                        JOIN kategoriler k ON s.kategori_id = k.id
                        WHERE s.musteri_id IN (SELECT id FROM churn_custs)
                          AND s.tutar > 0
                        GROUP BY k.ana, k.id, k.alt2, k.alt1, u.id, u.ad
                    )
                    SELECT ana, kat_ad, kat_id, urun_id, urun_ad, ciro, musteri, son_alis
                    FROM cat_products WHERE rn = 1 AND ciro > 1000
                    ORDER BY ciro DESC, musteri DESC
                    LIMIT 20
                """, [seg_numbered])
            return cursor.fetchall()

        is_pg = db_engine.DB_BACKEND == 'postgresql'
        for seg_numbered, info in segment_info.items():
            seg_display_for_query = info['display']
            products = _get_winback_products(cursor, ph, seg_numbered, seg_display_for_query, is_pg)
            used_categories_per_seg[seg_numbered] = set()
            seg_added = 0
            for p in products:
                if seg_added >= 5:
                    break
                urun_id_p = db_engine.val(p, 'urun_id')
                if urun_id_p and urun_id_p in used_urun_ids_winback:
                    continue
                ana = db_engine.val(p, 'ana', '')
                if ana and ana in used_categories_per_seg[seg_numbered]:
                    continue
                ciro = db_engine.val(p, 'ciro', 0) or 0
                musteri_count = db_engine.val(p, 'musteri', 0) or 0
                urun_ad = db_engine.val(p, 'urun_ad', 'Genel Ürün')

                if info['count'] < 1000: dynamic_rate = 0.25
                elif info['count'] < 5000: dynamic_rate = 0.20
                else: dynamic_rate = 0.15
                tahmini_katilim = round(info['count'] * dynamic_rate)

                seg_disp = info['display']
                if seg_disp == 'Kayip Musteriler':
                    indirim_wb = 40.0; sure_wb = 7; oncelik_wb = 1
                    gerekcesi_wb = (
                        f"Bu {info['count']:,} müşteri 180+ gün önce '{ana}' kategorisinden "
                        f"'{urun_ad}' ürününü en son aldı — ayrılmadan önceki son tercihleri. "
                        f"%40 indirimle kısa süreli (7 gün) son şans teklifiniz onları en iyi tanıdığınız "
                        f"ürünle karşılıyor. Geri kazanım başarısı için en kritik pencere bu."
                    )
                    beklenen_wb = f"Kayıp müşterilerin %5-10'unu ({round(info['count'] * 0.07):,} kişi) geri kazanmak."
                elif seg_disp == 'Uyuyanlar':
                    indirim_wb = 30.0; sure_wb = 10; oncelik_wb = 1
                    gerekcesi_wb = (
                        f"Uyuyan {info['count']:,} müşteri '{ana}' kategorisini geçmişte yoğun kullandı "
                        f"ama son 90 günde alışveriş yapmadı. '{urun_ad}' eskiden favori ürünleri arasındaydı. "
                        f"Nostaljik bir hatırlatma + %30 indirim kombinasyonu en yüksek "
                        f"yeniden aktivasyon oranını yakalamak için tasarlandı."
                    )
                    beklenen_wb = f"Uyuyan müşterilerin %10-15'ini ({round(info['count'] * 0.12):,} kişi) yeniden aktifleştirmek."
                elif seg_disp == 'Risk Altindakiler':
                    indirim_wb = 20.0; sure_wb = 14; oncelik_wb = 2
                    gerekcesi_wb = (
                        f"Risk altındaki {info['count']:,} müşteri '{ana}' kategorisinde "
                        f"en yüksek tekrar satın alma davranışı gösteriyor. '{urun_ad}' "
                        f"bu segmentin en bağlayıcı ürünü — henüz kaybetmeden %20 indirimle "
                        f"alışveriş alışkanlığını yeniden tetiklemek için 14 günlük pencere kritik."
                    )
                    beklenen_wb = f"Risk altındaki müşterilerin churn oranını %20 azaltmak ({round(info['count'] * 0.20):,} kişiyi kurtarmak)."
                else:
                    indirim_wb = 15.0; sure_wb = 14; oncelik_wb = 2
                    gerekcesi_wb = (
                        f"İlgi Bekleyen {info['count']:,} müşteri sinyaller veriyor: alışveriş sıklığı "
                        f"düşüyor ama henüz uyumadı. '{urun_ad}' bu segmentte popüler bir ürün. "
                        f"Hafif bir %15 indirimle doğru zamanda dokunmak bu müşterileri "
                        f"tekrar aktif hale getirebilir."
                    )
                    beklenen_wb = "İlgi bekleyen müşterilerin alışveriş sıklığını artırmak ve churn yolculuğunu durdurmak."

                kat_id_wb = db_engine.val(p, 'kat_id')
                avg_fiyat_wb = kat_avg_fiyat.get(kat_id_wb) or 150
                indirim_carpan_wb = 1 - (indirim_wb / 100)

                oneriler.append({
                    'KampanyaTipi': 'Win-Back',
                    'HedefSegment': seg_disp,
                    'HedefMusteriSayisi': info['count'],
                    'OncelikSeviye': oncelik_wb,
                    'UrunID': urun_id_p,
                    'UrunAdi': urun_ad,
                    'KategoriID': kat_id_wb,
                    'KategoriAdi': db_engine.val(p, 'kat_ad', ''),
                    'IkinciUrunAdi': ana,
                    'VeriKaynagi': 'musteriler + satislar (çeşitlendirilmiş)',
                    'OnerilenIndirim': indirim_wb,
                    'OnerilenMinTutar': round(avg_fiyat_wb * indirim_carpan_wb, 2),
                    'GecerlilikSuresi': sure_wb,
                    'TahminiKatilim': tahmini_katilim,
                    'PotansiyelCiro': round(tahmini_katilim * avg_fiyat_wb * indirim_carpan_wb, 2),
                    'Gerekcesi': gerekcesi_wb,
                    'VeriOzeti': (f"Müşteri Sayısı: {info['count']}, Ort. Churn Riski: %{info['avg_risk']:.0f}, "
                                  f"Kategori: {ana}, Ürün Cirosu: {ciro:.0f} TL"),
                    'BeklenenSonuc': beklened_wb if False else beklenen_wb,
                    'KaynakKategoriAd': f"{seg_disp}|{ana}"
                })
                if urun_id_p:
                    used_urun_ids_winback.add(urun_id_p)
                if ana:
                    used_categories_per_seg[seg_numbered].add(ana)
                seg_added += 1

            logger.info(f"  {info['display']}: {seg_added} farklı kategori önerisi oluşturuldu")
    
    except Exception as e:
        logger.error(f"Error generating win-back campaigns: {e}")

    # 4. LOYALTY
    logger.info("Loyalty kampanyaları oluşturuluyor...")
    try:
        # musteriler tablosundan gerçek segment müşteri sayılarını çek
        # musteriler.rfm_segment formatı: "04-) Sadık Olmaya Adaylar"
        # segmenturuntercihleri formatı: "Sadik Olmaya Adaylar" (Türkçe-siz, ön-ek yok)
        # Normalize fonksiyonu: ön-eki kaldır, Türkçe → ASCII
        def _normalize_seg(s):
            import re as _re2
            s = str(s).strip()
            s = _re2.sub(r'^\d+[-.)]+\s*', '', s)  # "04-) " ön-ekini kaldır
            tr_map = str.maketrans('ÇĞİÖŞÜçğışöşü', 'CGIOSUcgisosu')
            # Düzeltme: tam karakter tablosu
            tr_map2 = {
                ord('Ç'): 'C', ord('Ğ'): 'G', ord('İ'): 'I', ord('Ö'): 'O',
                ord('Ş'): 'S', ord('Ü'): 'U', ord('ç'): 'c', ord('ğ'): 'g',
                ord('ı'): 'i', ord('ö'): 'o', ord('ş'): 's', ord('ü'): 'u',
                ord('â'): 'a', ord('î'): 'i', ord('û'): 'u',
            }
            return s.translate(tr_map2).strip()

        cursor.execute("""
            SELECT TRIM(rfm_segment) as rfm_segment, COUNT(*) as gercek_musteri_sayisi
            FROM musteriler
            WHERE rfm_segment IS NOT NULL AND LENGTH(TRIM(rfm_segment)) > 0
            GROUP BY TRIM(rfm_segment)
        """)
        segment_musteri_map = {}
        for r in cursor.fetchall():
            seg_raw = db_engine.val(r, 'rfm_segment', '')
            cnt = int(db_engine.val(r, 'gercek_musteri_sayisi', 0) or 0)
            if seg_raw:
                normalized = _normalize_seg(seg_raw)
                segment_musteri_map[normalized] = cnt
                # Orijinal hali de ekle (tam eşleşme için)
                segment_musteri_map[seg_raw.strip()] = cnt

        # Per-segment isolated queries with segment-specific behavioral ordering.
        # NOT: tabloda 'Sadiklar' var, 'Sadik Musteriler' değil.
        LOYALTY_SEGMENT_STRATEGIES = [
            ('Sampiyonlar',             'penetrasyon * -1',   15.0, 14, 1),
            ('Sadiklar',                'penetrasyon * -1',   15.0, 14, 1),
            ('Yuksek Harcama Yapanlar', 'toplam_ciro * -1',   10.0, 14, 1),
            ('Potansiyel Sampiyonlar',  'toplam_ciro * -1',   20.0, 21, 2),
            ('Tekrar Kazanilanlar',     'toplam_ciro * -1',   30.0, 21, 2),
            ('Yeni Musteriler',         'toplam_ciro * -1',   25.0, 30, 2),
            ('Sadik Olmaya Adaylar',    'toplam_ciro * -1',   20.0, 30, 3),
            ('Ilgi Bekleyenler',        'toplam_ciro * -1',   25.0, 30, 3),
        ]

        for seg_name_db, order_expr, indirim, sure, oncelik in LOYALTY_SEGMENT_STRATEGIES:
            rows = _get_loyalty_products_for_segment(
                cursor, ph, seg_name_db, order_expr,
                excluded_ids=set(),
                limit=20
            )
            seg_added = 0
            used_cats_this_seg = set()
            for r in rows:
                if seg_added >= 3:
                    break
                urun_id_l = db_engine.val(r, 'urun_id')
                kat_ad = db_engine.val(r, 'kategori_ad', '') or ''
                ana_kat = kat_ad.split(' > ')[0].strip() if ' > ' in kat_ad else kat_ad
                if ana_kat and ana_kat in used_cats_this_seg:
                    continue

                gercek_musteri = (
                    segment_musteri_map.get(seg_name_db, 0) or
                    int(db_engine.val(r, 'segment_toplam_musteri', 0) or 0)
                )

                u_ad = db_engine.val(r, 'urun_ad', None)
                if not u_ad or u_ad == 0 or u_ad == "": u_ad = "Favori Ürün"

                if gercek_musteri < 1000: dynamic_rate = 0.25
                elif gercek_musteri < 5000: dynamic_rate = 0.20
                else: dynamic_rate = 0.15
                tahmini_katilim = round(gercek_musteri * dynamic_rate)

                penetrasyon = float(db_engine.val(r, 'penetrasyon', 0) or 0)

                toplam_ciro = float(db_engine.val(r, 'toplam_ciro', 0) or 0)
                if seg_name_db == 'Sampiyonlar':
                    gerekcesi = (
                        f"Şampiyonlar segmenti en yüksek penetrasyon (%{penetrasyon:.1f}) gösterdiği "
                        f"'{u_ad}' ürününde ödüllendirilmeli. Bu segment zaten bu ürünü seviyor — "
                        f"sadakat pekiştirilirse rakibe geçiş riski minimize edilir."
                    )
                    beklenen = "Şampiyon müşterilerin marka bağlılığını artırmak ve sepet büyüklüğünü korumak."
                elif seg_name_db == 'Sadik Musteriler':
                    gerekcesi = (
                        f"Sadık müşteriler '{u_ad}' ürününü düzenli alıyor (penetrasyon: %{penetrasyon:.1f}). "
                        f"Özel sadakat indirimi ile bu alışkanlığı pekiştir ve frekansı artır."
                    )
                    beklenen = "Sadık müşterilerin alışveriş sıklığını artırmak, uzun vadeli LTV'yi yükseltmek."
                elif seg_name_db == 'Potansiyel Sampiyonlar':
                    gerekcesi = (
                        f"Potansiyel Şampiyonlar '{u_ad}' kategorisinde {toplam_ciro:,.0f} TL ciro üretiyor. "
                        f"Şampiyon segmentine geçiş için gereken son itici kampanya bu olabilir."
                    )
                    beklenen = "Potansiyel şampiyonları 1 alışveriş daha yaparak Şampiyonlar segmentine taşımak."
                elif seg_name_db == 'Yuksek Harcama Yapanlar':
                    gerekcesi = (
                        f"Yüksek Harcama Yapanlar fiyat duyarlılığı düşük bir segment. "
                        f"'{u_ad}' ürününde küçük bir teşvik ile sepet tutarını daha da büyütme fırsatı var."
                    )
                    beklenen = "Ortalama sepet tutarını artırmak; yüksek marjlı ürün satışını güçlendirmek."
                elif seg_name_db == 'Tekrar Kazanilanlar':
                    gerekcesi = (
                        f"Tekrar kazanılan müşteriler henüz alışkanlık oluşturmamış. "
                        f"'{u_ad}' ürününde büyüme potansiyeli yüksek — düşük penetrasyona rağmen "
                        f"kategori cirosu {toplam_ciro:,.0f} TL. İkinci alışverişi tetiklemek kritik."
                    )
                    beklenen = "Tekrar kazanılan müşterilerin 2. alışverişini sağlayarak kaybı önlemek."
                elif seg_name_db == 'Yeni Musteriler':
                    gerekcesi = (
                        f"Yeni müşteriler için ilk 30 günde ikinci alışveriş yapmaları hayati. "
                        f"'{u_ad}' segmentteki en popüler ürün — yeni müşterinin markayı tekrar "
                        f"tercih etmesi için en güçlü aday."
                    )
                    beklenen = "İlk 30 günde ikinci alışverişi tetikleyerek yeni müşteri churn riskini %30 azaltmak."
                elif seg_name_db == 'Sadik Olmaya Adaylar':
                    gerekcesi = (
                        f"Sadık Olmaya Adaylar segmenti '{u_ad}' kategorisinde düşük penetrasyon "
                        f"(%{penetrasyon:.1f}) ama yüksek ciro potansiyeli taşıyor. "
                        f"Bu ürünü denettirmek sadakat yolculuğunu hızlandırır."
                    )
                    beklenen = "Sadık olmaya aday müşterilerin kategori çeşitliliğini artırarak Sadık Müşteri segmentine yükseltmek."
                elif seg_name_db == 'Ilgi Bekleyenler':
                    gerekcesi = (
                        f"İlgi Bekleyenler son dönemde alışveriş sıklığı düşmüş bir segment. "
                        f"'{u_ad}' kategorisinde %{penetrasyon:.1f} penetrasyon var — cazip teklif "
                        f"ile yeniden aktive edilebilirler."
                    )
                    beklenen = "İlgi bekleyen müşterilerin alışveriş sıklığını yeniden artırmak ve churn riskini azaltmak."
                else:
                    gerekcesi = f"{seg_name_db} segmentindeki müşterilere '{u_ad}' ürününde özel teklif."
                    beklenen = "Müşteri ömür boyu değerini (LTV) artırmak."

                kat_id_int = int(db_engine.val(r, 'kategori_id') or 0)
                avg_fiyat = kat_avg_fiyat.get(kat_id_int) or float(db_engine.val(r, 'segment_ortalama_sepet', 150) or 150)
                indirim_carpan = 1 - (indirim / 100)

                oneriler.append({
                    'KampanyaTipi': 'Loyalty',
                    'HedefSegment': seg_name_db,
                    'HedefMusteriSayisi': gercek_musteri,
                    'OncelikSeviye': oncelik,
                    'UrunID': urun_id_l,
                    'UrunAdi': u_ad,
                    'KategoriID': db_engine.val(r, 'kategori_id'),
                    'KategoriAdi': db_engine.val(r, 'kategori_ad', ""),
                    'VeriKaynagi': 'segmenturuntercihleri (segment-izole)',
                    'OnerilenIndirim': indirim,
                    'OnerilenMinTutar': round(avg_fiyat * indirim_carpan, 2),
                    'GecerlilikSuresi': sure,
                    'TahminiKatilim': tahmini_katilim,
                    'PotansiyelCiro': round(tahmini_katilim * avg_fiyat * indirim_carpan, 2),
                    'Gerekcesi': gerekcesi,
                    'VeriOzeti': f"Segment: {seg_name_db}, Ürün: {u_ad}, Penetrasyon: %{penetrasyon:.1f}",
                    'BeklenenSonuc': beklenen,
                    'KaynakKategoriAd': seg_name_db
                })

                if ana_kat:
                    used_cats_this_seg.add(ana_kat)
                seg_added += 1

            logger.info(f"  Loyalty {seg_name_db}: {seg_added} ürün önerisi oluşturuldu")
    except Exception as e:
        logger.error(f"Error generating loyalty campaigns: {e}")

    # Save using executemany for performance
    logger.info(f"Saving {len(oneriler)} campaigns to DB...")
    
    cols = "olusturma_tarihi, kampanya_tipi, hedef_segment, hedef_musteri_sayisi, oncelik_seviye, urun_id, urun_ad, kategori_id, kategori_ad, ikinci_urun_id, ikinci_urun_ad, veri_kaynagi, onerilen_indirim, onerilen_min_tutar, gecerlilik_suresi, tahmini_katilim, potansiyel_ciro, birlikte_ciro, roi_tahmini, gerekcesi, veri_ozeti, beklenen_sonuc, oneri_durumu, kaynak_kategori_ad, lift, guven, fis_sayisi, son_guncelleme, onerilen_urunler"
    vals = ",".join([ph] * 29)
    if db_engine.DB_BACKEND == 'postgresql':
        sql = f"""
        INSERT INTO otomatikkampanyaonerileri ({cols}) VALUES ({vals})
        ON CONFLICT (kaynak_kategori_ad, kategori_id, kampanya_tipi)
        DO UPDATE SET
            tahmini_katilim = EXCLUDED.tahmini_katilim,
            hedef_musteri_sayisi = EXCLUDED.hedef_musteri_sayisi,
            potansiyel_ciro = EXCLUDED.potansiyel_ciro,
            birlikte_ciro = EXCLUDED.birlikte_ciro,
            roi_tahmini = EXCLUDED.roi_tahmini,
            lift = EXCLUDED.lift,
            guven = EXCLUDED.guven,
            fis_sayisi = EXCLUDED.fis_sayisi,
            son_guncelleme = EXCLUDED.son_guncelleme,
            onerilen_urunler = EXCLUDED.onerilen_urunler,
            olusturma_tarihi = EXCLUDED.olusturma_tarihi
        WHERE otomatikkampanyaonerileri.oneri_durumu = 'Bekliyor'
        """
    else:
        sql = f"INSERT OR REPLACE INTO otomatikkampanyaonerileri ({cols}) VALUES ({vals})"

    batch_data = []
    for o in oneriler:
        batch_data.append((
            now_str, o['KampanyaTipi'], o['HedefSegment'], o['HedefMusteriSayisi'], o['OncelikSeviye'],
            o.get('UrunID'), o.get('UrunAdi'), o.get('KategoriID'), o.get('KategoriAdi'),
            o.get('IkinciUrunID'), o.get('IkinciUrunAdi'), o['VeriKaynagi'],
            o['OnerilenIndirim'], o['OnerilenMinTutar'], o['GecerlilikSuresi'],
            o['TahminiKatilim'], o['PotansiyelCiro'], o.get('BirlikteCiro'), o.get('RoiTahmini'),
            o['Gerekcesi'], o['VeriOzeti'], o.get('BeklenenSonuc'),
            'Bekliyor', o.get('KaynakKategoriAd'), o.get('Lift'), o.get('Guven'), o.get('FisSayisi', 0), now_str,
            o.get('OnerilenUrunler')
        ))
    
    # Batch insert to avoid timeout
    logger.info(f"Saving {len(oneriler)} campaigns to DB in batches...")
    batch_size = 500
    for i in range(0, len(oneriler), batch_size):
        batch = batch_data[i:i + batch_size]
        try:
            cursor.executemany(sql, batch)
            conn.commit()
            logger.info(f" Saved {min(i + batch_size, len(oneriler))} / {len(oneriler)}")
        except Exception as e:
            logger.error(f"Error in batch insert at {i}: {e}")
            conn.rollback()
            raise e
            
    # Marka bilgisini ürün id'sine göre eşleştir
    logger.info("Marka bilgileri kampanya önerilerine ekleniyor...")
    try:
        cursor.execute("""
            UPDATE otomatikkampanyaonerileri
            SET marka_id = (SELECT marka_id FROM urunler WHERE id = otomatikkampanyaonerileri.urun_id)
            WHERE urun_id IS NOT NULL AND oneri_durumu = 'Bekliyor'
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Marka eşleştirme hatası: {e}")
        conn.rollback()

    # Kategori yöneticisini kaynak kategoriden ata (kaynak_kategori_ad = kategoriler.alt2)
    # Fallback: kaynak_kategori_ad boşsa hedef kategori yöneticisini kullan
    logger.info("Kategori yöneticisi kampanya önerilerine ekleniyor...")
    try:
        cursor.execute("""
            UPDATE otomatikkampanyaonerileri
            SET yonetici_id = COALESCE(
                (SELECT yonetici_id FROM kategoriler
                 WHERE alt2 = otomatikkampanyaonerileri.kaynak_kategori_ad
                   AND yonetici_id IS NOT NULL LIMIT 1),
                (SELECT yonetici_id FROM kategoriler
                 WHERE id = otomatikkampanyaonerileri.kategori_id
                   AND yonetici_id IS NOT NULL LIMIT 1)
            )
            WHERE oneri_durumu = 'Bekliyor'
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Kategori yöneticisi eşleştirme hatası: {e}")
        conn.rollback()
    
    # Syncmeta'ya son kampanya yenileme tarihini kaydet
    logger.info("Kampanya yenileme tarihi syncmeta'ya kaydediliyor...")
    try:
        if db_engine.DB_BACKEND == 'postgresql':
            cursor.execute("""
                INSERT INTO syncmeta (key, value, updated_at)
                VALUES ('last_campaign_refresh', %s, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
            """, (now_str,))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO syncmeta (key, value, updated_at)
                VALUES ('last_campaign_refresh', ?, datetime('now'))
            """, (now_str,))
        conn.commit()
        logger.info(f"✅ Kampanya yenileme tarihi kaydedildi: {now_str}")
    except Exception as e:
        logger.warning(f"Syncmeta güncelleme hatası (kampanya): {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    db_engine.release_connection(conn)
    logger.info(f"{len(oneriler)} yeni kampanya önerisi üretildi.")

def ai_icin_kampanya_ozeti_hazirlama(oneri_id):
    """
    Belirli bir öneri için AI'ya gönderilecek özet metni hazırlar
    """
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    ph = db_engine.ph()
    
    cursor.execute(f"SELECT * FROM otomatikkampanyaonerileri WHERE oneri_id = {ph}", [oneri_id])
    r = cursor.fetchone()
    db_engine.release_connection(conn)
    
    if not r: return "Öneri bulunamadı."
    
    return f"""
KAMPANYA TİPİ: {r.get('kampanya_tipi', r.get('kampanyatipi', ''))}
HEDEF SEGMENT: {r.get('hedef_segment', r.get('hedefsegment', ''))} ({r.get('hedef_musteri_sayisi', r.get('hedefmusterisayisi', ''))} müşteri)
ÜRÜN/KATEGORİ: {r.get('urun_ad', r.get('urunadi', '')) or r.get('kategori_ad', r.get('kategoriadi', ''))}

VERİ ANALİZİ:
{r.get('veri_ozeti', r.get('veriozeti', ''))}
GEREKÇE: {r.get('gerekcesi', '')}

ÖNERİ:
%{r.get('onerilen_indirim', r.get('onerilenindirim', ''))} indirim
Minimum sepet: {r.get('onerilen_min_tutar', r.get('onerilenmintutar', ''))} TL
Geçerlilik: {r.get('gecerlilik_suresi', r.get('gecerliliksuresi', ''))} gün

TAHMİNLER:
Tahmini katılım: {r.get('tahmini_katilim', r.get('tahminikatilim', ''))} müşteri
Potansiyel ciro: {r.get('potansiyel_ciro', r.get('potansiyelciro', ''))} TL
BEKLENEN SONUÇ: {r.get('beklenen_sonuc', r.get('beklenensonuc', ''))}
"""

def get_campaign_target_customers(oneri_id, limit=2000):
    """
    Belirli bir kampanya önerisi için hedef müşteri listesini döner.
    Gelecekteki SMS/E-mail entegrasyonu için gerekli tüm iletişim bilgilerini içerir.
    """
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    ph = db_engine.ph()
    
    # 1. Öneri detaylarını al
    cursor.execute(f"SELECT * FROM otomatikkampanyaonerileri WHERE oneri_id = {ph}", [oneri_id])
    r = cursor.fetchone()
    if not r:
        db_engine.release_connection(conn)
        return []
    
    # DB Backend'e göre keyleri normalize et
    oneri_tipi = db_engine.val(r, 'kampanya_tipi', '')
    target_cat_id = db_engine.val(r, 'kategori_id')
    source_cat_id = db_engine.val(r, 'ikinci_urun_id')
    source_cat_ad = db_engine.val(r, 'ikinci_urun_ad') or db_engine.val(r, 'kaynak_kategori_ad', '')
    hedef_segment = db_engine.val(r, 'hedef_segment', '')

    # Fallback: Eğer source_cat_id yoksa ama kaynak_kategori_ad/ikinci_urun_ad varsa kategoriler tablosundan bulmayı dene
    if oneri_id and oneri_tipi == 'Cross-Sell' and not source_cat_id and source_cat_ad:
        try:
            # Grup isimlerini ayır (örn: "Pekmez & Tahin" -> ["Pekmez", "Tahin"])
            cat_names = [c.strip() for c in source_cat_ad.split('&')]
            for cat_n in cat_names:
                cursor.execute(f"SELECT id FROM kategoriler WHERE (alt2 = {ph} OR alt1 = {ph} OR ana = {ph}) LIMIT 1", [cat_n, cat_n, cat_n])
                row = cursor.fetchone()
                if row:
                    row_id = row['id']
                    # Hedef kategori ile aynı olmayan bir kategori seç ki 0 sonuç çıkmasın
                    if row_id != target_cat_id:
                        source_cat_id = row_id
                        logger.info(f"Source ID recovered for {cat_n} (from group {source_cat_ad}): {source_cat_id}")
                        break
                    else:
                        # Eğer grubun ilk elemanı hedef ise, devam et diğerini bul
                        logger.debug(f"Skipping target category {cat_n} in group {source_cat_ad}")
                        continue
        except Exception as e:
            logger.warning(f"Category recovery error: {e}")
            pass
    
    # Sütun isimleri PostgreSQL/SQLite farkı için
    id_col = "id"
    ad_col = "ad"
    tel_col = "telefon"
    rfm_col = "rfm_segment"
    tip_col = "tip"
    onay_col = "onay_durumu"
    
    customers = []
    
    try:
        if oneri_tipi == 'Cross-Sell' and source_cat_id:
            # Kaynak kategoriden alan ama hedef kategoriden almayanlar
            query = f"""
                SELECT DISTINCT m.{id_col}, m.{ad_col}, m.{tel_col}, m.{rfm_col}, m.{tip_col}, m.{onay_col}
                FROM musteriler m
                JOIN satislar s1 ON m.{id_col} = s1.musteri_id
                WHERE s1.kategori_id = {ph}
                AND NOT EXISTS (
                    SELECT 1 FROM satislar s2 
                    WHERE s2.musteri_id = m.{id_col} 
                    AND s2.kategori_id = {ph}
                )
                LIMIT {ph}
            """
            cursor.execute(query, [source_cat_id, target_cat_id, limit])
            customers = cursor.fetchall()
            
        elif oneri_tipi in ['Loyalty', 'Win-Back', 'Retention'] or 'Alıcıları' in hedef_segment:
            # Segment bazlı hedefleme
            segment_clean = hedef_segment.replace(' Alıcıları', '').strip()
            
            # Daha esnek eşleşme: "01-) Şampiyonlar" gibi değerleri yakalamak için %Segment% kullan
            # Prefix bazlı "01-)" gibi yapılara karşı korumalı
            query = f"""
                SELECT {id_col}, {ad_col}, {tel_col}, {rfm_col}, {tip_col}, {onay_col}
                FROM musteriler
                WHERE {rfm_col} LIKE {ph}
                LIMIT {ph}
            """
            cursor.execute(query, [f"%{segment_clean}%", limit])
            customers = cursor.fetchall()
            
            # Eğer RFM tabanlı sonuç çıkmadıysa ve bu bir kategori grubuna işaret ediyorsa (örn: "Tahin & Pekmez")
            # Satislar tablosundan bu kategoriyi alan müşterileri çekmeyi deneyebiliriz (opsiyonel geliştirme)
            
    except Exception as e:
        logger.error(f"Target customer fetch error: {e}")
        
    db_engine.release_connection(conn)
    return [dict(c) if not isinstance(c, dict) else c for c in customers]

def onaylanan_kampanyalari_uygula():
    """
    Onaylanan kampanyaları işler (Placeholder)
    """
    logger.info("Onaylanan kampanyalar işleniyor...")
    pass

if __name__ == "__main__":
    kampanya_tablo_olustur()
    kampanya_onerileri_uret()
    print(ai_icin_kampanya_ozeti_hazirlama(1))
