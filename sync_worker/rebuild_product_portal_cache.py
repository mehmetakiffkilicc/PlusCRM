import os
import sys
import json
import logging
import time
from datetime import datetime
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api import db_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DAY_NAMES_TR = {0: 'Paz', 1: 'Pzt', 2: 'Sal', 3: 'Çar', 4: 'Per', 5: 'Cum', 6: 'Cmt'}

CASE_MAPPING = {
    'urunid': 'UrunID', 'urunadi': 'UrunAdi', 'kategoriid': 'KategoriID', 'kategoriadi': 'KategoriAdi',
    'markaid': 'MarkaID', 'markaadi': 'MarkaAdi', 'guncelfiyat': 'GuncelFiyat', 'stokmiktari': 'StokMiktari',
    'urunolusturmatarihi': 'UrunOlusturmaTarihi', 'son7gunsatis': 'Son7GunSatis', 'son7gunciro': 'Son7GunCiro',
    'son7gunmusterisayisi': 'Son7GunMusteriSayisi', 'son30gunsatis': 'Son30GunSatis', 'son30gunciro': 'Son30GunCiro',
    'son30gunmusterisayisi': 'Son30GunMusteriSayisi', 'son30gunortfiyat': 'Son30GunOrtFiyat', 
    'son90gunsatis': 'Son90GunSatis', 'son90gunciro': 'Son90GunCiro', 'son90gunmusterisayisi': 'Son90GunMusteriSayisi',
    'toplamsatis': 'ToplamSatis', 'toplamciro': 'ToplamCiro', 'toplammusterisayisi': 'ToplamMusteriSayisi',
    'ilksatistarihi': 'IlkSatisTarihi', 'sonsatistarihi': 'SonSatisTarihi', 'trend_7_30': 'Trend_7_30',
    'trend_30_60': 'Trend_30_60', 'hiztrendi': 'HizTrendi', 'stokdurumu': 'StokDurumu', 
    'gunlukortsatis': 'GunlukOrtSatis', 'tahministokgunu': 'TahminiStokGunu', 'performanskategori': 'PerformansKategori',
    'kategoriicindesira': 'KategoriIcindeSira', 'birliktesatilanurunsayisi': 'BirlikteSatilanUrunSayisi',
    'encokbirliktesatilan': 'EnCokBirlikteSatilan', 'crosssellpotansiyeli': 'CrossSellPotansiyeli',
    'uyaridurumu': 'UyariDurumu', 'guncellemetarihi': 'GuncellemeTarihi',
    'kategori_id': 'KategoriID', 'kategori_ad': 'KategoriAdi', 'ust_kategori_id': 'UstKategoriID', 
    'toplam_urun': 'ToplamUrun', 'aktif_urun': 'AktifUrun', 'toplam_ciro': 'ToplamCiro', 
    'son30_ciro': 'Son30GunCiro', 'tonuna_oran': 'TonunaOran', 'kategori_skoru': 'KategoriSkoru',
    'performans_etiketi': 'PerformansEtiketi', 'guncelleme_tarihi': 'GuncellemeTarihi',
    'pazar_payi': 'PazarPayi', 'trend': 'Trend', 'momentum': 'Momentum',
    'performans_kategori': 'PerformansKategori', 'kategori_adi': 'KategoriAdi',
}

def _map_to_frontend_case(data):
    if not data: return {}
    return {CASE_MAPPING.get(k, k): v for k, v in data.items()}
def rebuild_product_portal_cache():
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    
    logger.info("Veritabanı tablosu 'urun_portal_ozet' oluşturuluyor...")
    col_type = "JSONB" if db_engine.DB_BACKEND == 'postgresql' else "TEXT"
    cursor.execute(f"CREATE TABLE IF NOT EXISTS urun_portal_ozet (urun_id INTEGER PRIMARY KEY, portal_data {col_type}, guncelleme_tarihi TIMESTAMP)")
    cursor.execute("DELETE FROM urun_portal_ozet")
    conn.commit()
    
    logger.info("Ürün listesi alınıyor...")
    cursor.execute("SELECT id, kategori_id, marka_id FROM urunler WHERE id IS NOT NULL")
    urun_list = cursor.fetchall()
    total_products = len(urun_list)
    logger.info(f"Toplam {total_products} ürün işlenecek.")
    
    t0 = time.time()
    batch_size = 500
    
    # 1. Kategori ve Marka Ortalamalarını Bir Kez Hesapla (RAM Tasarrufu)
    logger.info("Kategori ve Marka ortalamaları hesaplanıyor...")
    cursor.execute("""
        SELECT u.kategori_id, 
               SUM(pds.revenue) / NULLIF(COUNT(DISTINCT pds.urun_id), 0) as avg_rev,
               SUM(pds.unit_count) / NULLIF(COUNT(DISTINCT pds.urun_id), 0) as avg_units,
               SUM(pds.customer_count) * 1.0 / NULLIF(COUNT(DISTINCT pds.urun_id), 0) as avg_cust
        FROM product_daily_summary pds
        JOIN urunler u ON pds.urun_id = u.id
        WHERE u.kategori_id IS NOT NULL
        GROUP BY u.kategori_id
    """)
    cat_avg_map = {r['kategori_id']: {'revenue': round(float(r['avg_rev'] or 0), 2), 'units': round(float(r['avg_units'] or 0), 2), 'customers': round(float(r['avg_cust'] or 0), 1)} for r in cursor.fetchall()}

    cursor.execute("""
        SELECT u.marka_id, 
               SUM(pds.revenue) / NULLIF(COUNT(DISTINCT pds.urun_id), 0) as avg_rev,
               SUM(pds.unit_count) / NULLIF(COUNT(DISTINCT pds.urun_id), 0) as avg_units,
               SUM(pds.customer_count) * 1.0 / NULLIF(COUNT(DISTINCT pds.urun_id), 0) as avg_cust
        FROM product_daily_summary pds
        JOIN urunler u ON pds.urun_id = u.id
        WHERE u.marka_id IS NOT NULL
        GROUP BY u.marka_id
    """)
    brand_avg_map = {r['marka_id']: {'revenue': round(float(r['avg_rev'] or 0), 2), 'units': round(float(r['avg_units'] or 0), 2), 'customers': round(float(r['avg_cust'] or 0), 1)} for r in cursor.fetchall()}

    # 2. Ürünleri Batch Halinde İşle
    for i in range(0, total_products, batch_size):
        batch_products = urun_list[i : i + batch_size]
        batch_ids = [u['id'] for u in batch_products]
        id_str = ",".join(map(str, batch_ids))
        
        # Batch Data Structure
        pd = {uid: {
            'summary': {'totalRevenue': 0, 'totalUnits': 0, 'totalReceipts': 0, 'totalCustomers': 0, 'avgPrice': 0, 'avgBasketSize': 0},
            'monthly_trend': [],
            'customer_profile': {'byType': [], 'bySegment': [], 'byApproval': []},
            'store_performance': [],
            'price_distribution': [],
            'time_patterns': {'byHour': [], 'byDayOfWeek': []},
            'performance': {},
            'comparison': {'product': {'revenue': 0, 'units': 0, 'customers': 0}, 'categoryAvg': {'revenue': 0, 'units': 0, 'customers': 0}, 'brandAvg': {'revenue': 0, 'units': 0, 'customers': 0}},
            'segment_preferences': [],
            'category_performance': {},
            'cross_sell': {'PRODUCT': [], 'BRAND_CAT': [], 'CAT_ONLY': []}
        } for uid in batch_ids}

        # A. Summary & Trends
        cursor.execute(f"SELECT urun_id, SUM(revenue) as rev, SUM(unit_count) as units, SUM(customer_count) as cust, SUM(receipt_count) as rec FROM product_daily_summary WHERE urun_id IN ({id_str}) GROUP BY urun_id")
        for r in cursor.fetchall():
            uid = r['urun_id']
            rev, units, rec, cust = float(r['rev'] or 0), float(r['units'] or 0), int(r['rec'] or 0), int(r['cust'] or 0)
            pd[uid]['summary'] = {'totalRevenue': round(rev, 2), 'totalUnits': round(units, 2), 'totalReceipts': rec, 'totalCustomers': cust, 'avgPrice': round(rev/units, 2) if units else 0, 'avgBasketSize': round(rev/rec, 2) if rec else 0}
            pd[uid]['comparison']['product'] = {'revenue': round(rev, 2), 'units': round(units, 2), 'customers': cust}

        month_expr = "SUBSTRING(tarih::text, 1, 7)" if db_engine.DB_BACKEND == 'postgresql' else "substr(tarih, 1, 7)"
        cursor.execute(f"SELECT urun_id, {month_expr} as month, SUM(revenue) as rev, SUM(unit_count) as units FROM product_daily_summary WHERE urun_id IN ({id_str}) GROUP BY 1, 2 ORDER BY 2")
        for r in cursor.fetchall():
            pd[r['urun_id']]['monthly_trend'].append({'month': r['month'], 'revenue': round(r['rev'] or 0, 2), 'units': round(r['units'] or 0, 2)})

        # B. Customer Profiles
        cursor.execute(f"SELECT s.urun_id, COALESCE(mu.rfm_segment, 'Bilinmiyor') as grp, COUNT(DISTINCT s.musteri_id) as cnt, SUM(s.tutar) as rev FROM satislar s LEFT JOIN musteriler mu ON s.musteri_id=mu.id WHERE s.urun_id IN ({id_str}) GROUP BY 1, 2")
        for r in cursor.fetchall():
            pd[r['urun_id']]['customer_profile']['bySegment'].append({'segment': r['grp'], 'count': r['cnt'], 'revenue': round(r['rev'] or 0, 2)})

        # C. Performance & Preferences
        cursor.execute(f"SELECT * FROM urunperformansdetay WHERE urunid IN ({id_str})")
        for r in cursor.fetchall():
            pd[r['urunid']]['performance'] = _map_to_frontend_case(dict(r))

        # C2. PDS override: PDS only has ~7 days of data (nightly sync LIMIT 7).
        # Only override s7 values; s30/s90 stay from UPDF for correct longer-range metrics.
        date7 = "CURRENT_DATE - INTERVAL '7 days'"
        cursor.execute(f"""
            SELECT urun_id,
                SUM(CASE WHEN tarih >= {date7} THEN unit_count ELSE 0 END) as s7_units,
                SUM(CASE WHEN tarih >= {date7} THEN revenue ELSE 0 END) as s7_rev,
                SUM(CASE WHEN tarih >= {date7} THEN customer_count ELSE 0 END) as s7_cust
            FROM product_daily_summary
            WHERE urun_id IN ({id_str})
            GROUP BY urun_id
        """)
        pds_overrides = {
            's7_units': 'Son7GunSatis', 's7_rev': 'Son7GunCiro', 's7_cust': 'Son7GunMusteriSayisi',
        }
        for r in cursor.fetchall():
            uid = r['urun_id']
            for src_key, perf_key in pds_overrides.items():
                val = r[src_key]
                if val and val > 0:
                    pd[uid]['performance'][perf_key] = float(val)

        cursor.execute(f"SELECT urun_id, rfm_segment as segment, segment_indeks as index_score FROM segmenturuntercihleri WHERE urun_id IN ({id_str}) ORDER BY index_score DESC")
        for r in cursor.fetchall():
            pd[r['urun_id']]['segment_preferences'].append({'segment': r['segment'], 'index_score': r['index_score']})

        # D. Cross-Sell (Limit results per product)
        cursor.execute(f"SELECT b.urun_id_1, b.urun_id_2, u.ad as pname, b.lift FROM urunbirliktelikleri b JOIN urunler u ON b.urun_id_2=u.id WHERE b.urun_id_1 IN ({id_str}) ORDER BY b.urun_id_1, b.lift DESC")
        for r in cursor.fetchall():
            uid = r['urun_id_1']
            if len(pd[uid]['cross_sell']['PRODUCT']) < 10:
                pd[uid]['cross_sell']['PRODUCT'].append({'productId': r['urun_id_2'], 'productName': r['pname'], 'lift': r['lift']})

        # E. Finish & Insert Batch
        now = datetime.now()
        insert_data = []
        for uid, u_info in zip(batch_ids, batch_products):
            # Add comparison data
            k_id, m_id = u_info['kategori_id'], u_info['marka_id']
            if k_id in cat_avg_map: pd[uid]['comparison']['categoryAvg'] = cat_avg_map[k_id]
            if m_id in brand_avg_map: pd[uid]['comparison']['brandAvg'] = brand_avg_map[m_id]
            
            insert_data.append((uid, json.dumps(pd[uid], ensure_ascii=False, default=lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)), now))

        ph = "%s, %s, %s" if db_engine.DB_BACKEND == 'postgresql' else "?, ?, ?"
        cursor.executemany(f"INSERT INTO urun_portal_ozet (urun_id, portal_data, guncelleme_tarihi) VALUES ({ph})", insert_data)
        conn.commit()
        logger.info(f"Processed {min(i + batch_size, total_products)} / {total_products} products...")

    logger.info(f"✅ Product portal cache rebuilt in {time.time() - t0:.1f}s")
    conn.close()

if __name__ == '__main__':
    rebuild_product_portal_cache()
