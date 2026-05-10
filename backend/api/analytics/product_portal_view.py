"""
Product Portal View - Urun Detay Analizi
Tek bir urun icin kapsamli CRM analizi: KPI, trend, birliktelik, musteri profili, magaza, fiyat, karsilastirma, zaman oruntuleri
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import sqlite3
import os
import logging
from collections import defaultdict
from .. import db_engine

logger = logging.getLogger(__name__)

DAY_NAMES_TR = ['Pazar', 'Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma', 'Cumartesi']

# Database (lowercase/snake_case) -> Frontend (PascalCase) mapping
CASE_MAPPING = {
    # UrunPerformansDetay
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
    
    # KategoriPerformansOzet
    'kategori_id': 'KategoriID', 'kategori_ad': 'KategoriAdi', 'ust_kategori_id': 'UstKategoriID',
    'toplam_urun': 'ToplamUrun', 'aktif_urun': 'AktifUrun', 'toplam_ciro': 'ToplamCiro',
    'son30_ciro': 'Son30GunCiro', 'tonuna_oran': 'TonunaOran', 'kategori_skoru': 'KategoriSkoru',
    'performans_etiketi': 'PerformansEtiketi', 'guncelleme_tarihi': 'GuncellemeTarihi',
    'pazar_payi': 'PazarPayi', 'trend': 'Trend', 'momentum': 'Momentum',
    'performans_kategori': 'PerformansKategori', 'kategori_adi': 'KategoriAdi',
}

def _map_to_frontend_case(data):
    """Veritabanindan gelen kucuk harf/snake_case anahtarlari frontend'in bekledigi PascalCase'e cevirir."""
    if not data: return {}
    return {CASE_MAPPING.get(k, k): v for k, v in data.items()}



def _build_filters(request, product_id):
    """Ortak filtre olusturma. s=satislar, mg=magazalar, mu=musteriler alias'lari bekler."""
    ph = db_engine.ph()
    where = [f"s.urun_id = {ph}"]
    params = [product_id]

    start_date = request.GET.get('start_date') or request.GET.get('startDate')
    end_date = request.GET.get('end_date') or request.GET.get('endDate')
    year = request.GET.get('year')
    month = request.GET.get('month')
    region = request.GET.get('region')
    customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
    approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')

    if start_date:
        where.append(f"s.tarih >= {ph}"); params.append(start_date)
    if end_date:
        where.append(f"s.tarih <= {ph}"); params.append(end_date)
    if year and not start_date:
        where.append(f"s.tarih >= {ph} AND s.tarih < {ph}")
        params.extend([f"{year}-01-01", f"{int(year)+1}-01-01"])
    if month:
        if db_engine.DB_BACKEND == 'postgresql':
            where.append(f"SUBSTRING(s.tarih::text, 6, 2) = {ph}")
        else:
            where.append(f"substr(s.tarih, 6, 2) = {ph}")
        params.append(f"{int(month):02d}")
    if region:
        where.append(f"mg.bolge = {ph}"); params.append(region)
    if customer_type:
        where.append(f"mu.tip = {ph}"); params.append(customer_type)
    if approval_status:
        where.append(f"mu.onay_durumu = {ph}"); params.append(approval_status)

    return " AND ".join(where), params


BASE_JOINS = """
    FROM satislar s
    LEFT JOIN magazalar mg ON s.magaza_id = mg.id
    LEFT JOIN musteriler mu ON s.musteri_id = mu.id
"""


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_portal(request, data_source_id, product_id):
    """Urun portali - tek urun icin kapsamli analiz"""
    import time as _time
    _t0 = _time.time()
    def _log(label):
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[PP_TIMING] {label}: {(_time.time()-_t0)*1000:.0f}ms")
        
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()

        where_stmt, params = _build_filters(request, product_id)

        # ============================
        # 1. URUN KIMLIGI
        # --- 1. Temel Ürün Bilgileri ---
        cursor.execute(f"""
            SELECT u.*, k.ana, k.alt1, k.alt2, m.ad as marka_ad
            FROM urunler u
            LEFT JOIN kategoriler k ON u.kategori_id = k.id
            LEFT JOIN markalar m ON u.marka_id = m.id
            WHERE u.id = {ph}
        """, (product_id,))
        prod_row = cursor.fetchone()
        if not prod_row:
            return Response({'error': 'Urun bulunamadi'}, status=404)

        kategori_parts = [p for p in [db_engine.val(prod_row, 'ana'), db_engine.val(prod_row, 'alt1'), db_engine.val(prod_row, 'alt2')] if p]
        product_info = {
            'id': db_engine.val(prod_row, 'id'),
            'kod': db_engine.val(prod_row, 'kod') or '',
            'ad': db_engine.val(prod_row, 'ad'),
            'marka': db_engine.val(prod_row, 'marka_ad') or '-',
            'marka_id': db_engine.val(prod_row, 'marka_id'),
            'kategori': ' > '.join(kategori_parts) if kategori_parts else '-',
            'kategori_id': db_engine.val(prod_row, 'kategori_id'),
            'birim': 'Adet',
        }

        # Check if we can use summary tables (Fast Path)
        use_pds = not any([request.GET.get('region'), request.GET.get('customer_type'), request.GET.get('approval_status')])
        
        has_filters = any([
            request.GET.get('region'), request.GET.get('customer_type'), request.GET.get('customerType'),
            request.GET.get('approval_status'), request.GET.get('approvalStatus'),
            request.GET.get('start_date'), request.GET.get('startDate'), request.GET.get('end_date'), request.GET.get('endDate'),
            request.GET.get('year'), request.GET.get('month')
        ])
        if not has_filters:
            try:
                cursor.execute(f"SELECT portal_data FROM urun_portal_ozet WHERE urun_id = {ph}", [product_id])
                c_row = cursor.fetchone()
                if c_row and db_engine.val(c_row, 'portal_data'):
                    import json
                    pd = db_engine.val(c_row, 'portal_data')
                    if isinstance(pd, str):
                        pd = json.loads(pd)
                    
                    response_dict = {
                        'product': product_info,
                        'summary': pd.get('summary', {}),
                        'monthlyTrend': pd.get('monthly_trend', []),
                        'crossSell': pd.get('cross_sell', {
                            'PRODUCT': [],
                            'BRAND_CAT': [],
                            'CAT_ONLY': []
                        }),
                        'performance': pd.get('performance', {}),
                        'segmentPreferences': pd.get('segment_preferences', []),
                        'categoryPerformance': pd.get('category_performance', {}),
                        'customerProfile': pd.get('customer_profile', {}),
                        'storePerformance': pd.get('store_performance', []),
                        'priceDistribution': pd.get('price_distribution', []),
                        'timePatterns': pd.get('time_patterns', {}),
                        'comparison': pd.get('comparison', {
                            'product': {'revenue': 0, 'units': 0, 'customers': 0},
                            'categoryAvg': {'revenue': 0, 'units': 0, 'customers': 0},
                            'brandAvg': {'revenue': 0, 'units': 0, 'customers': 0}
                        })
                    }
                    from django.http import HttpResponse
                    return HttpResponse(json.dumps(response_dict), content_type='application/json')
            except Exception as e:
                logger.warning(f"Cache okuma hatasi: {e}")
                if db_engine.DB_BACKEND == 'postgresql': conn.rollback()
                
        # 2. KPI OZET
        # ============================
        summary = {'totalRevenue': 0, 'totalUnits': 0, 'totalReceipts': 0, 'totalCustomers': 0, 'avgPrice': 0, 'avgBasketSize': 0}
        try:
            if use_pds:
                cursor.execute(f"""
                    SELECT SUM(revenue) as rev, SUM(unit_count) as units,
                           SUM(customer_count) as daily_customers,
                           SUM(receipt_count) as receipts
                    FROM product_daily_summary
                    WHERE {where_stmt.replace('s.', '')}
                """, params)
                r = cursor.fetchone()
                rev = r['rev'] or 0
                units = r['units'] or 0
                receipts = r['receipts'] or 0
                summary.update({
                    'totalRevenue': round(rev, 2),
                    'totalUnits': round(units, 2),
                    'totalReceipts': receipts,
                    'totalCustomers': r['daily_customers'] or 0, # Note: This is sum of daily distincts, slightly higher but fast
                    'avgPrice': round(rev / units, 2) if units else 0,
                    'avgBasketSize': round(rev / receipts, 2) if receipts else 0
                })
            else:
                cursor.execute(f"""
                    SELECT SUM(s.tutar) as rev, SUM(s.miktar) as units,
                           COUNT(DISTINCT s.fis_no) as receipts, COUNT(DISTINCT s.musteri_id) as customers
                    {BASE_JOINS}
                    WHERE {where_stmt}
                """, params)
                r = cursor.fetchone()
                rev = r['rev'] or 0
                units = r['units'] or 0
                receipts = r['receipts'] or 0
                summary = {
                    'totalRevenue': round(rev, 2),
                    'totalUnits': round(units, 2),
                    'totalReceipts': receipts,
                    'totalCustomers': r['customers'] or 0,
                    'avgPrice': round(rev / units, 2) if units else 0,
                    'avgBasketSize': round(rev / receipts, 2) if receipts else 0
                }
        except Exception as e:
            logger.warning(f"Product portal summary error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 3. AYLIK trend
        # ============================
        monthly_trend = []
        try:
            if use_pds:
                month_expr = "SUBSTRING(tarih::text, 1, 7)" if db_engine.DB_BACKEND == 'postgresql' else "substr(tarih, 1, 7)"
                cursor.execute(f"""
                    SELECT {month_expr} as month,
                           SUM(revenue) as revenue, SUM(unit_count) as units,
                           SUM(receipt_count) as receipts,
                           SUM(revenue) / NULLIF(SUM(unit_count), 0) as avg_price
                    FROM product_daily_summary
                    WHERE {where_stmt.replace('s.', '')}
                    GROUP BY month ORDER BY month
                """, params)
            else:
                month_expr = db_engine.strftime_expr('%Y-%m', 's.tarih')
                cursor.execute(f"""
                    SELECT {month_expr} as month,
                           SUM(s.tutar) as revenue, SUM(s.miktar) as units,
                           COUNT(DISTINCT s.fis_no) as receipts,
                           SUM(s.tutar) / NULLIF(SUM(s.miktar), 0) as avg_price
                    {BASE_JOINS}
                    WHERE {where_stmt}
                    GROUP BY month ORDER BY month
                """, params)
            monthly_trend = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Product portal trend error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 4. BIRLIKTELIK (CROSS-SELL)
        # ============================
        cross_sell = {'PRODUCT': [], 'BRAND_CAT': [], 'CAT_ONLY': []}
        try:
            prod_kategori_id = product_info.get('kategori_id')
            prod_marka_id = product_info.get('marka_id')

            # 1. PRODUCT
            cursor.execute(db_engine.adapt_query("""
                SELECT b.urun_id_2 as productId, u.ad as productName, m.ad as brand,
                       COALESCE(k.alt2, k.ana) as category,
                       b.ortak_fis_sayisi as coOccurrence, b.confidence, b.lift
                FROM urunbirliktelikleri b
                JOIN urunler u ON b.urun_id_2 = u.id
                LEFT JOIN markalar m ON u.marka_id = m.id
                LEFT JOIN kategoriler k ON u.kategori_id = k.id
                WHERE b.urun_id_1 = ?
                  AND u.kategori_id != ?
                ORDER BY b.lift DESC, b.ortak_fis_sayisi DESC
                LIMIT 15
            """), [product_id, prod_kategori_id or -1])
            cross_sell['PRODUCT'] = [dict(row) for row in cursor.fetchall()]

            # Fallback purely on receipt count if few results
            if len(cross_sell['PRODUCT']) < 5:
                cursor.execute(db_engine.adapt_query("""
                    SELECT fis_no FROM satislar
                    WHERE urun_id = ?
                    GROUP BY fis_no
                    ORDER BY MAX(tarih) DESC
                    LIMIT 5000
                """), [product_id])
                fis_list = [r['fis_no'] for r in cursor.fetchall()]
                if fis_list:
                    existing_ids = {c['productId'] for c in cross_sell['PRODUCT']}
                    fis_ph = ','.join([ph] * len(fis_list[:3000]))
                    cursor.execute(f"""
                        SELECT s.urun_id as "productId", u.ad as "productName", m.ad as "brand",
                               COALESCE(k.alt2, k.ana) as "category",
                               COUNT(DISTINCT s.fis_no) as "coOccurrence"
                        FROM satislar s
                        JOIN urunler u ON s.urun_id = u.id
                        LEFT JOIN markalar m ON u.marka_id = m.id
                        LEFT JOIN kategoriler k ON s.kategori_id = k.id
                        WHERE s.fis_no IN ({fis_ph})
                          AND s.urun_id != {ph}
                          AND u.kategori_id != {ph}
                          AND (k.ana IS NULL OR k.ana NOT IN ('Meyve & Sebze - Yeşillik', 'Unlu Mamuller & Ekmek', 'Sarf & Gider', 'Sigara & Gazete', 'Horeca', 'İşletici kategorileri'))
                          AND u.ad NOT LIKE '%%POŞET%%' AND u.ad NOT LIKE '%%EKMEK%%'
                        GROUP BY s.urun_id, u.ad, m.ad, k.alt2, k.ana
                        ORDER BY "coOccurrence" DESC
                        LIMIT 15
                    """, fis_list[:3000] + [product_id, prod_kategori_id or -1])
                    for row in cursor.fetchall():
                        if row['productId'] not in existing_ids:
                            cross_sell['PRODUCT'].append({**dict(row), 'confidence': 0, 'lift': None})
            
            # 2. BRAND_CAT
            concat_op = "CONCAT(m2.ad, ' (', COALESCE(k2.alt2, k2.ana), ')')" if db_engine.DB_BACKEND == 'postgresql' else "m2.ad || ' (' || COALESCE(k2.alt2, k2.ana) || ')'"
            concat_op1 = "CONCAT(m1.ad, ' (', COALESCE(k1.alt2, k1.ana), ')')" if db_engine.DB_BACKEND == 'postgresql' else "m1.ad || ' (' || COALESCE(k1.alt2, k1.ana) || ')'"
            cursor.execute(db_engine.adapt_query(f"""
                SELECT
                    {concat_op} as productName,
                    m2.ad as brand, COALESCE(k2.alt2, k2.ana) as category,
                    b.ortak_fis_sayisi as coOccurrence, b.confidence, b.lift
                FROM grupbirliktelikleri b
                JOIN markalar m2 ON b.marka_id_2 = m2.id
                JOIN kategoriler k2 ON b.kategori_id_2 = k2.id
                WHERE b.marka_id_1 = ? AND b.kategori_id_1 = ? AND b.tip = 'BRAND_CAT_SQL'
                UNION ALL
                SELECT
                    {concat_op1} as productName,
                    m1.ad as brand, COALESCE(k1.alt2, k1.ana) as category,
                    b.ortak_fis_sayisi as coOccurrence, b.confidence, b.lift
                FROM grupbirliktelikleri b
                JOIN markalar m1 ON b.marka_id_1 = m1.id
                JOIN kategoriler k1 ON b.kategori_id_1 = k1.id
                WHERE b.marka_id_2 = ? AND b.kategori_id_2 = ? AND b.tip = 'BRAND_CAT_SQL'
                ORDER BY lift DESC, coOccurrence DESC
                LIMIT 15
            """), [prod_marka_id, prod_kategori_id, prod_marka_id, prod_kategori_id])
            cross_sell['BRAND_CAT'] = [dict(row) for row in cursor.fetchall()][:15]

            # 3. CAT_ONLY
            cursor.execute(db_engine.adapt_query("""
                SELECT
                    COALESCE(k2.alt2, k2.ana) as productName,
                    '-' as brand, COALESCE(k2.alt2, k2.ana) as category,
                    b.ortak_fis_sayisi as coOccurrence, b.confidence, b.lift
                FROM grupbirliktelikleri b
                JOIN kategoriler k2 ON b.kategori_id_2 = k2.id
                WHERE b.kategori_id_1 = ? AND b.tip = 'CAT_ONLY_SQL'
                UNION ALL
                SELECT
                    COALESCE(k1.alt2, k1.ana) as productName,
                    '-' as brand, COALESCE(k1.alt2, k1.ana) as category,
                    b.ortak_fis_sayisi as coOccurrence, b.confidence, b.lift
                FROM grupbirliktelikleri b
                JOIN kategoriler k1 ON b.kategori_id_1 = k1.id
                WHERE b.kategori_id_2 = ? AND b.tip = 'CAT_ONLY_SQL'
                ORDER BY lift DESC, coOccurrence DESC
                LIMIT 15
            """), [prod_kategori_id, prod_kategori_id])
            cross_sell['CAT_ONLY'] = [dict(row) for row in cursor.fetchall()][:15]

            cross_sell['PRODUCT'] = cross_sell['PRODUCT'][:15]
        except Exception as e:
            logger.warning(f"Product portal cross-sell error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 5. MUSTERI PROFILI (3 GROUP BY sorgusu — DB aggregation)
        # ============================
        customer_profile = {'byType': [], 'bySegment': [], 'byApproval': []}
        try:
            cursor.execute(f"""
                SELECT COALESCE(mu.tip, 'Bilinmiyor') as grp,
                       COUNT(DISTINCT s.musteri_id) as cnt, SUM(s.tutar) as rev
                {BASE_JOINS}
                WHERE {where_stmt}
                GROUP BY grp ORDER BY rev DESC
            """, params)
            customer_profile['byType'] = [{'type': r['grp'], 'count': r['cnt'], 'revenue': round(r['rev'] or 0, 2)} for r in cursor.fetchall()]

            cursor.execute(f"""
                SELECT COALESCE(mu.rfm_segment, 'Bilinmiyor') as grp,
                       COUNT(DISTINCT s.musteri_id) as cnt, SUM(s.tutar) as rev
                {BASE_JOINS}
                WHERE {where_stmt}
                GROUP BY grp ORDER BY rev DESC
            """, params)
            customer_profile['bySegment'] = [{'segment': r['grp'], 'count': r['cnt'], 'revenue': round(r['rev'] or 0, 2)} for r in cursor.fetchall()]

            cursor.execute(f"""
                SELECT COALESCE(mu.onay_durumu, 'Bilinmiyor') as grp,
                       COUNT(DISTINCT s.musteri_id) as cnt, SUM(s.tutar) as rev
                {BASE_JOINS}
                WHERE {where_stmt}
                GROUP BY grp ORDER BY rev DESC
            """, params)
            customer_profile['byApproval'] = [{'status': r['grp'], 'count': r['cnt'], 'revenue': round(r['rev'] or 0, 2)} for r in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Product portal customer profile error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 6. MAGAZA PERFORMANSI (GROUP BY sorgusu)
        # ============================
        store_performance = []
        try:
            cursor.execute(f"""
                SELECT mg.id as store_id, mg.ad as store_name, mg.bolge as region,
                       SUM(s.tutar) as revenue, SUM(s.miktar) as units,
                       COUNT(DISTINCT s.fis_no) as receipts
                {BASE_JOINS}
                WHERE {where_stmt}
                GROUP BY mg.id, mg.ad, mg.bolge
                ORDER BY revenue DESC
                LIMIT 15
            """, params)
            store_performance = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Product portal store performance error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 7. FIYAT DAGILIMI (GROUP BY CASE sorgusu)
        # ============================
        price_distribution = []
        try:
            if db_engine.DB_BACKEND == 'postgresql':
                case_expr = """
                    CASE
                        WHEN s.miktar > 0 AND s.tutar/s.miktar < 10 THEN '0-10'
                        WHEN s.miktar > 0 AND s.tutar/s.miktar < 25 THEN '10-25'
                        WHEN s.miktar > 0 AND s.tutar/s.miktar < 50 THEN '25-50'
                        WHEN s.miktar > 0 AND s.tutar/s.miktar < 100 THEN '50-100'
                        WHEN s.miktar > 0 AND s.tutar/s.miktar < 250 THEN '100-250'
                        WHEN s.miktar > 0 AND s.tutar/s.miktar < 500 THEN '250-500'
                        WHEN s.miktar > 0 THEN '500+'
                        ELSE NULL
                    END"""
            else:
                case_expr = """
                    CASE
                        WHEN s.miktar > 0 AND CAST(s.tutar AS REAL)/s.miktar < 10 THEN '0-10'
                        WHEN s.miktar > 0 AND CAST(s.tutar AS REAL)/s.miktar < 25 THEN '10-25'
                        WHEN s.miktar > 0 AND CAST(s.tutar AS REAL)/s.miktar < 50 THEN '25-50'
                        WHEN s.miktar > 0 AND CAST(s.tutar AS REAL)/s.miktar < 100 THEN '50-100'
                        WHEN s.miktar > 0 AND CAST(s.tutar AS REAL)/s.miktar < 250 THEN '100-250'
                        WHEN s.miktar > 0 AND CAST(s.tutar AS REAL)/s.miktar < 500 THEN '250-500'
                        WHEN s.miktar > 0 THEN '500+'
                        ELSE NULL
                    END"""
            cursor.execute(f"""
                SELECT {case_expr} as range_label, COUNT(DISTINCT musteri_id) as count
                {BASE_JOINS}
                WHERE {where_stmt}
                GROUP BY range_label
                HAVING range_label IS NOT NULL
                ORDER BY MIN(CASE range_label
                    WHEN '0-10' THEN 1 WHEN '10-25' THEN 2 WHEN '25-50' THEN 3
                    WHEN '50-100' THEN 4 WHEN '100-250' THEN 5 WHEN '250-500' THEN 6 ELSE 7 END)
            """, params)
            price_distribution = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"Product portal price dist error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 8. KARSILASTIRMA
        # ============================
        comparison = {
            'product': {'revenue': summary['totalRevenue'], 'units': summary['totalUnits'], 'customers': summary['totalCustomers']},
            'categoryAvg': {'revenue': 0, 'units': 0, 'customers': 0},
            'brandAvg': {'revenue': 0, 'units': 0, 'customers': 0}
        }
        try:
            # Tarih filtreleri icin basit where
            date_where = []
            date_params = []
            start_date = request.GET.get('start_date') or request.GET.get('startDate')
            end_date = request.GET.get('end_date') or request.GET.get('endDate')
            year = request.GET.get('year')
            if start_date:
                date_where.append(f"s.tarih >= {ph}"); date_params.append(start_date)
            if end_date:
                date_where.append(f"s.tarih <= {ph}"); date_params.append(end_date)
            if year and not start_date:
                date_where.append(f"s.tarih >= {ph} AND s.tarih < {ph}")
                date_params.extend([f"{year}-01-01", f"{int(year)+1}-01-01"])
            date_clause = " AND ".join(date_where) if date_where else "1=1"

            # Kategori ortalamasi
            if product_info['kategori_id']:
                if use_pds:
                    # HEAVY QUERY OPTIMIZATION: Use product_daily_summary instead of satislar
                    cursor.execute(f"""
                        SELECT SUM(revenue) / NULLIF(COUNT(DISTINCT urun_id), 0) as avg_rev,
                               SUM(unit_count) / NULLIF(COUNT(DISTINCT urun_id), 0) as avg_units,
                               SUM(customer_count) * 1.0 / NULLIF(COUNT(DISTINCT urun_id), 0) as avg_cust
                        FROM product_daily_summary
                        WHERE urun_id IN (SELECT id FROM urunler WHERE kategori_id = {ph})
                          AND {date_clause.replace('s.', '')}
                    """, [product_info['kategori_id']] + date_params)
                else:
                    max_func = "GREATEST(1, COUNT(DISTINCT s.urun_id))" if db_engine.DB_BACKEND == 'postgresql' else "MAX(1, COUNT(DISTINCT s.urun_id))"
                    cursor.execute(f"""
                        SELECT SUM(s.tutar) / {max_func} as avg_rev,
                               SUM(s.miktar) / {max_func} as avg_units,
                               COUNT(DISTINCT s.musteri_id) * 1.0 / {max_func} as avg_cust
                        FROM satislar s
                        WHERE s.kategori_id = {ph} AND {date_clause}
                    """, [product_info['kategori_id']] + date_params)
                cr = cursor.fetchone()
                if cr:
                    comparison['categoryAvg'] = {
                        'revenue': round(cr['avg_rev'] or 0, 2),
                        'units': round(cr['avg_units'] or 0, 2),
                        'customers': round(cr['avg_cust'] or 0, 1)
                    }

            # Marka ortalamasi
            if product_info['marka_id']:
                if use_pds:
                    cursor.execute(f"""
                        SELECT SUM(revenue) / NULLIF(COUNT(DISTINCT urun_id), 0) as avg_rev,
                               SUM(unit_count) / NULLIF(COUNT(DISTINCT urun_id), 0) as avg_units,
                               SUM(customer_count) * 1.0 / NULLIF(COUNT(DISTINCT urun_id), 0) as avg_cust
                        FROM product_daily_summary
                        WHERE urun_id IN (SELECT id FROM urunler WHERE marka_id = {ph})
                          AND {date_clause.replace('s.', '')}
                    """, [product_info['marka_id']] + date_params)
                else:
                    max_func = "GREATEST(1, COUNT(DISTINCT s.urun_id))" if db_engine.DB_BACKEND == 'postgresql' else "MAX(1, COUNT(DISTINCT s.urun_id))"
                    cursor.execute(f"""
                        SELECT SUM(s.tutar) / {max_func} as avg_rev,
                               SUM(s.miktar) / {max_func} as avg_units,
                               COUNT(DISTINCT s.musteri_id) * 1.0 / {max_func} as avg_cust
                        FROM satislar s
                        WHERE s.marka_id = {ph} AND {date_clause}
                    """, [product_info['marka_id']] + date_params)
                br = cursor.fetchone()
                if br:
                    comparison['brandAvg'] = {
                        'revenue': round(br['avg_rev'] or 0, 2),
                        'units': round(br['avg_units'] or 0, 2),
                        'customers': round(br['avg_cust'] or 0, 1)
                    }
        except Exception as e:
            logger.warning(f"Product portal comparison error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 9. ZAMAN ORUNTULERI (DB GROUP BY — ek sorgu yok, Python agregasyon yok)
        # ============================
        time_patterns = {'byHour': [], 'byDayOfWeek': []}
        try:
            dow_expr = db_engine.strftime_expr('%w', 's.tarih')
            cursor.execute(f"""
                SELECT s.saat as hour,
                       {dow_expr} as dow,
                       COUNT(DISTINCT s.fis_no) as cnt,
                       SUM(s.tutar) as rev
                {BASE_JOINS}
                WHERE {where_stmt} AND s.saat IS NOT NULL AND s.tarih IS NOT NULL
                GROUP BY s.saat, {dow_expr}
            """, params)
            hour_map = defaultdict(lambda: {'count': 0, 'revenue': 0.0})
            dow_map  = defaultdict(lambda: {'count': 0, 'revenue': 0.0})
            for row in cursor.fetchall():
                h = row['hour']; d = int(row['dow'] or 0)
                c = row['cnt'] or 0; r = row['rev'] or 0
                hour_map[h]['count'] += c; hour_map[h]['revenue'] += r
                dow_map[d]['count'] += c; dow_map[d]['revenue'] += r
            time_patterns['byHour'] = [{'hour': h, 'count': v['count'], 'revenue': round(v['revenue'], 2)}
                                        for h, v in sorted(hour_map.items())]
            time_patterns['byDayOfWeek'] = [
                {'day': d, 'dayName': DAY_NAMES_TR[d], 'count': v['count'], 'revenue': round(v['revenue'], 2)}
                for d, v in sorted(dow_map.items()) if 0 <= d <= 6
            ]
        except Exception as e:
            logger.warning(f"Product portal time patterns error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 10. PERFORMANS DETAYLARI
        # ============================
        performance = {}
        try:
            cursor.execute(db_engine.adapt_query("""
                SELECT * FROM urunperformansdetay WHERE urunid = ?
            """), [product_id])
            perf_row = cursor.fetchone()
            if perf_row:
                performance = _map_to_frontend_case(dict(perf_row))
            
            # OVERRIDE with fresh data from PDS if available
            # NOTE: PDS only maintains ~7 days of daily data (nightly sync LIMIT 7).
            # Only override s7 values from PDS; s30/s90 stay from UPDF/satislar.
            if use_pds:
                if db_engine.DB_BACKEND == 'postgresql':
                    date7 = "CURRENT_DATE - INTERVAL '7 days'"
                else:
                    date7 = "date('now', '-7 days')"
                cursor.execute(f"""
                    SELECT
                        SUM(CASE WHEN tarih >= {date7} THEN unit_count ELSE 0 END) as s7_units,
                        SUM(CASE WHEN tarih >= {date7} THEN revenue ELSE 0 END) as s7_rev,
                        SUM(CASE WHEN tarih >= {date7} THEN customer_count ELSE 0 END) as s7_cust
                    FROM product_daily_summary
                    WHERE urun_id = {ph}
                """, (product_id,))
                dynamic_perf = cursor.fetchone()
                if dynamic_perf:
                    perf_overrides = {
                        'Son7GunSatis': (dynamic_perf['s7_units'], 's7_units'),
                        'Son7GunCiro': (dynamic_perf['s7_rev'], 's7_rev'),
                        'Son7GunMusteriSayisi': (dynamic_perf['s7_cust'], 's7_cust'),
                    }
                    for perf_key, (val, _) in perf_overrides.items():
                        if val and val > 0:
                            performance[perf_key] = val

            # Fallback: PDS/UPDF bos ise satislar'dan canli sorgu
            if not performance.get('Son7GunSatis') or not performance.get('Son7GunCiro') or not performance.get('Son30GunSatis') or not performance.get('Son30GunCiro'):
                if db_engine.DB_BACKEND == 'postgresql':
                    date7 = "CURRENT_DATE - INTERVAL '7 days'"
                    date30 = "CURRENT_DATE - INTERVAL '30 days'"
                    date90 = "CURRENT_DATE - INTERVAL '90 days'"
                else:
                    date7 = "date('now', '-7 days')"
                    date30 = "date('now', '-30 days')"
                    date90 = "date('now', '-90 days')"
                cursor.execute(f"""
                    SELECT
                        COALESCE(SUM(CASE WHEN s.tarih >= {date7} THEN s.miktar ELSE 0 END), 0) as s7_units,
                        COALESCE(SUM(CASE WHEN s.tarih >= {date7} THEN s.tutar ELSE 0 END), 0) as s7_rev,
                        COALESCE(COUNT(DISTINCT CASE WHEN s.tarih >= {date7} THEN s.musteri_id END), 0) as s7_cust,
                        COALESCE(SUM(CASE WHEN s.tarih >= {date30} THEN s.miktar ELSE 0 END), 0) as s30_units,
                        COALESCE(SUM(CASE WHEN s.tarih >= {date30} THEN s.tutar ELSE 0 END), 0) as s30_rev,
                        COALESCE(COUNT(DISTINCT CASE WHEN s.tarih >= {date30} THEN s.musteri_id END), 0) as s30_cust,
                        COALESCE(SUM(CASE WHEN s.tarih >= {date90} THEN s.miktar ELSE 0 END), 0) as s90_units,
                        COALESCE(SUM(CASE WHEN s.tarih >= {date90} THEN s.tutar ELSE 0 END), 0) as s90_rev,
                        COALESCE(COUNT(DISTINCT CASE WHEN s.tarih >= {date90} THEN s.musteri_id END), 0) as s90_cust
                    FROM satislar s
                    WHERE s.urun_id = {ph}
                """, (product_id,))
                live_row = cursor.fetchone()
                if live_row:
                    live_overrides = {
                        'Son7GunSatis': live_row['s7_units'],
                        'Son7GunCiro': live_row['s7_rev'],
                        'Son7GunMusteriSayisi': live_row['s7_cust'],
                        'Son30GunSatis': live_row['s30_units'],
                        'Son30GunCiro': live_row['s30_rev'],
                        'Son30GunMusteriSayisi': live_row['s30_cust'],
                        'Son90GunSatis': live_row['s90_units'],
                        'Son90GunCiro': live_row['s90_rev'],
                        'Son90GunMusteriSayisi': live_row['s90_cust'],
                    }
                    for perf_key in ['Son7GunCiro', 'Son7GunSatis', 'Son7GunMusteriSayisi',
                                     'Son30GunCiro', 'Son30GunSatis', 'Son30GunMusteriSayisi',
                                     'Son90GunCiro', 'Son90GunSatis', 'Son90GunMusteriSayisi']:
                        val = live_overrides.get(perf_key, 0) or 0
                        if val > 0:
                            performance[perf_key] = val
        except Exception as e:
            logger.warning(f"Product portal performance error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 11. SEGMENT TERCIHLERI
        # ============================
        segment_preferences = []
        try:
            cursor.execute(db_engine.adapt_query("""
                SELECT rfm_segment as segment, segment_indeks as index_score,
                       penetrasyon as penetration, genel_penetrasyon,
                       alan_musteri_sayisi as buyer_count,
                       tercih_seviye as preference, oneri_durumu as recommendation
                FROM segmenturuntercihleri
                WHERE urun_id = ?
                ORDER BY segment_indeks DESC
            """), [product_id])
            raw_prefs = [dict(r) for r in cursor.fetchall()]
            segment_preferences = []
            for sp in raw_prefs:
                pen = float(sp.get('penetration') or 0)
                genel = float(sp.get('genel_penetrasyon') or 0)
                if genel > 0:
                    index_score = round((pen / genel) * 100, 1)
                else:
                    raw_idx = float(sp.get('index_score') or 0)
                    index_score = raw_idx if raw_idx <= 2000 else round(raw_idx / 100, 1)
                segment_preferences.append({
                    'segment': sp['segment'],
                    'index_score': index_score,
                    'penetration': pen,
                    'buyer_count': sp['buyer_count'],
                    'preference': sp['preference'],
                    'recommendation': sp['recommendation'],
                })
        except Exception as e:
            logger.warning(f"Product portal segment preferences error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        # ============================
        # 12. KATEGORI PERFORMANSI
        # ============================
        category_performance = {}
        try:
            kat_id = product_info.get('kategori_id')
            if kat_id is not None:
                cursor.execute(db_engine.adapt_query("SELECT * FROM kategoriperformansozet WHERE kategori_id = ?"), [int(kat_id)])
                row = cursor.fetchone()
            else:
                row = None
            if not row and product_info.get('kategori'):
                ana_kategori = product_info['kategori'].split(' > ')[0]
                cursor.execute(db_engine.adapt_query("SELECT * FROM kategoriperformansozet WHERE kategori_adi = ? LIMIT 1"), [ana_kategori])
                row = cursor.fetchone()
            if row:
                category_performance = _map_to_frontend_case(dict(row))
        except Exception as e:
            logger.warning(f"Product portal category performance error: {e}")
            if db_engine.DB_BACKEND == 'postgresql': conn.rollback()

        return Response({
            'product': product_info,
            'summary': summary,
            'monthlyTrend': monthly_trend,
            'crossSell': cross_sell,
            'performance': performance,
            'segmentPreferences': segment_preferences,
            'categoryPerformance': category_performance,
            'customerProfile': customer_profile,
            'storePerformance': store_performance,
            'priceDistribution': price_distribution,
            'comparison': comparison,
            'timePatterns': time_patterns
        })

    except Exception as e:
        logger.error(f"Product portal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({'error': f'Sunucu hatasi: {str(e)}'}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)
