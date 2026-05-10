"""
Data Access Module - SQLite Cache'ten Veri Çekme
Full Local Mimarisi - Tüm sorgular SQLite'tan
"""

import os
import logging
from datetime import datetime
# Optional pyodbc import
try:
    import pyodbc
except ImportError:
    pyodbc = None

from decouple import config
from . import db_engine


logger = logging.getLogger(__name__)

# SQLite veritabanı yolu (legacy - only used in SQLite mode)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'sales_cache.db')

# SQL Server konfigürasyonu (Tailscale üzerinden erişim için)
SQL_SERVER_CONFIG = {
    'server': os.environ.get('SQL_SERVER_HOST', '100.109.143.127'),
    'port': os.environ.get('SQL_SERVER_PORT', '14330'),
    'database': os.environ.get('SQL_SERVER_DB', 'DerinSISShow'),
    'username': os.environ.get('SQL_SERVER_USER', 'sa2'),
    'password': os.environ.get('SQL_SERVER_PASS', '1478236950Mm..'),
    'drivers': [
        '{ODBC Driver 18 for SQL Server}',
        '{ODBC Driver 17 for SQL Server}',
        '{SQL Server Native Client 11.0}',
        '{SQL Server}'
    ]
}


def _get_sql_driver():
    """Mevcut SQL Server driver'ını bul"""
    if not pyodbc:
        return '{SQL Server}'
    try:
        available = pyodbc.drivers()
        for d in SQL_SERVER_CONFIG['drivers']:
            if d.strip('{}') in available:
                return d
    except:
        pass
    return '{SQL Server}'

def connect_sql():
    """SQL Server bağlantısı oluştur"""
    if not pyodbc:
        raise ImportError("pyodbc is not installed. SQL Server access is only available via sync worker.")
    driver = _get_sql_driver()
    conn_str = (
        f"DRIVER={driver};"
        f"SERVER={SQL_SERVER_CONFIG['server']},{SQL_SERVER_CONFIG['port']};"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"UID={SQL_SERVER_CONFIG['username']};"
        f"PWD={SQL_SERVER_CONFIG['password']};"
        f"Network=DBMSSOCN;Encrypt=no;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=300, autocommit=True)

def get_connection():
    """Get database connection from central engine"""
    return db_engine.get_connection()

def _get_cursor(conn):
    """Get dictionary cursor based on backend"""
    if db_engine.DB_BACKEND == "postgresql":
        from psycopg2.extras import RealDictCursor
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()

def _placeholder():
    """Get appropriate placeholder for SQL queries"""
    return "%s" if db_engine.DB_BACKEND == "postgresql" else "?"

def run_maintenance():
    """Veritabanı bakımı (PostgreSQL için VACUUM)"""
    if db_engine.DB_BACKEND == "postgresql":
        # Vacuum cannot run in a transaction block
        conn = db_engine.get_pg_pool().getconn()
        conn.set_isolation_level(0) # ISOLATION_LEVEL_AUTOCOMMIT
        cursor = conn.cursor()
        cursor.execute("VACUUM ANALYZE")
        db_engine.get_pg_pool().putconn(conn)
    else:
        conn = db_engine.get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA incremental_vacuum(1000)")
        cursor.execute("ANALYZE")
        conn.commit()
        db_engine.release_connection(conn)
    return True

# ================== DASHBOARD ANALİTİK ==================

def get_sales_analytics(category=None, brand=None, store=None, segment=None, 
                        customer_type=None, approval_status=None, region=None,
                        start_date=None, end_date=None, group_by='month',
                        month=None):
    """Dashboard KPI'ları - crmozet (Hızlı) veya satislar (Detaylı) tablosundan
       Desteklenen filtreler:
       - category: string veya list[string]
       - brand: string veya list[string]
       - store: string veya list[string]
       - segment: string veya list[string] (Müşteri segmenti)
       - customer_type: string veya list[string] (Bireysel/Kurumsal)
       - approval_status: string veya list[string] (Onaylı/Onaysız)
       - region: string veya list[string] (Bölge)
       - month: int (1-12) - year olmadan tek başına gelirse tüm yıllardaki o ay filtrelenir
    """
    import time
    start_all = time.perf_counter()
    conn = get_connection()
    if not conn:
        return None

    try:
        cursor = _get_cursor(conn)
        def resolve_ids(table, name_col, values):
            if not values: return []
            input_list = values if isinstance(values, list) else [values]
            # Detect if already IDs
            if all(isinstance(v, int) or (isinstance(v, str) and v.isdigit()) for v in input_list):
                return [int(v) for v in input_list]
            
            # Look up IDs by name
            ph = _placeholder()
            placeholders = ','.join([ph] * len(input_list))
            cursor.execute(f"SELECT id FROM {table} WHERE {name_col} IN ({placeholders})", input_list)
            return [r['id'] if isinstance(r, dict) else r[0] for r in cursor.fetchall()]

        resolved_cat_ids = resolve_ids('kategoriler', 'ana', category) if category else []
        resolved_brand_ids = resolve_ids('markalar', 'ad', brand) if brand else []
        resolved_store_ids = resolve_ids('magazalar', 'ad', store) if store else []

        # Build where clauses for different tables
        where_s = ["1=1"]
        where_g = ["1=1"]
        params_s = [] # Params for satislar/Detail
        params_g = [] # Params for gunlukozet/Summary

        if start_date:
            ph = _placeholder()
            where_s.append(f"s.tarih >= {ph}")
            where_g.append(f"tarih >= {ph}")
            params_s.append(start_date)
            params_g.append(start_date)
        if end_date:
            ph = _placeholder()
            where_s.append(f"s.tarih <= {ph}")
            where_g.append(f"tarih <= {ph}")
            params_s.append(end_date)
            params_g.append(end_date)
        
        if month and not start_date:
            ph = _placeholder()
            if db_engine.DB_BACKEND == "postgresql":
                where_s.append(f"TO_CHAR(s.tarih, 'MM') = {ph}")
                where_g.append(f"TO_CHAR(tarih, 'MM') = {ph}")
            else:
                where_s.append(f"substr(s.tarih, 6, 2) = {ph}")
                where_g.append(f"substr(tarih, 6, 2) = {ph}")
            params_s.append(str(month).zfill(2))
            params_g.append(str(month).zfill(2))
        
        if resolved_cat_ids:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(resolved_cat_ids))
            where_s.append(f"s.kategori_id IN ({placeholders})")
            where_g.append(f"kategori_id IN ({placeholders})")
            params_s.extend(resolved_cat_ids)
            params_g.extend(resolved_cat_ids)

        if resolved_brand_ids:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(resolved_brand_ids))
            where_s.append(f"s.marka_id IN ({placeholders})")
            where_g.append(f"marka_id IN ({placeholders})")
            params_s.extend(resolved_brand_ids)
            params_g.extend(resolved_brand_ids)

        if resolved_store_ids:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(resolved_store_ids))
            where_s.append(f"s.magaza_id IN ({placeholders})")
            where_g.append(f"magaza_id IN ({placeholders})")
            params_s.extend(resolved_store_ids)
            params_g.extend(resolved_store_ids)

        if segment:
            u_segments = segment if isinstance(segment, list) else [segment]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_segments))
            where_s.append(f"s.musteri_id IN (SELECT id FROM musteriler WHERE segment IN ({placeholders}))")
            params_s.extend(u_segments)

        if customer_type:
            u_types = customer_type if isinstance(customer_type, list) else [customer_type]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_types))
            where_s.append(f"s.musteri_id IN (SELECT id FROM musteriler WHERE tip IN ({placeholders}))")
            params_s.extend(u_types)

        if approval_status:
            u_status = approval_status if isinstance(approval_status, list) else [approval_status]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_status))
            where_s.append(f"s.onay_durumu IN ({placeholders})")
            params_s.extend(u_status)

        if region:
            u_regions = region if isinstance(region, list) else [region]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_regions))
            where_s.append(f"s.magaza_id IN (SELECT id FROM magazalar WHERE bolge IN ({placeholders}))")
            where_g.append(f"magaza_id IN (SELECT id FROM magazalar WHERE bolge IN ({placeholders}))")
            params_s.extend(u_regions)
            params_g.extend(u_regions)

        # Build where clauses for daily_metrics_summary
        where_d = ["1=1"]
        params_d = []

        if start_date:
            ph = _placeholder()
            where_d.append(f"d.tarih >= {ph}")
            params_d.append(start_date)
        if end_date:
            ph = _placeholder()
            where_d.append(f"d.tarih <= {ph}")
            params_d.append(end_date)
        if month and not start_date:
            ph = _placeholder()
            if db_engine.DB_BACKEND == "postgresql":
                where_d.append(f"TO_CHAR(d.tarih, 'MM') = {ph}")
            else:
                where_d.append(f"substr(d.tarih, 6, 2) = {ph}")
            params_d.append(str(month).zfill(2))
        if resolved_cat_ids:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(resolved_cat_ids))
            where_d.append(f"d.kategori_id IN ({placeholders})")
            params_d.extend(resolved_cat_ids)
        if resolved_brand_ids:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(resolved_brand_ids))
            where_d.append(f"d.marka_id IN ({placeholders})")
            params_d.extend(resolved_brand_ids)
        if resolved_store_ids:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(resolved_store_ids))
            where_d.append(f"d.magaza_id IN ({placeholders})")
            params_d.extend(resolved_store_ids)
        if region:
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_regions))
            where_d.append(f"d.magaza_id IN (SELECT id FROM magazalar WHERE bolge IN ({placeholders}))")
            params_d.extend(u_regions)
        if segment:
            u_segments = segment if isinstance(segment, list) else [segment]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_segments))
            where_d.append(f"d.rfm_segment IN ({placeholders})")
            params_d.extend(u_segments)
        if customer_type:
            u_types = customer_type if isinstance(customer_type, list) else [customer_type]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_types))
            where_d.append(f"d.customer_type IN ({placeholders})")
            params_d.extend(u_types)
        if approval_status:
            u_status = approval_status if isinstance(approval_status, list) else [approval_status]
            ph = _placeholder()
            placeholders = ','.join([ph]*len(u_status))
            where_d.append(f"d.onay_durumu IN ({placeholders})")
            params_d.extend(u_status)

        current_where = " AND ".join(where_d)
        current_params = params_d
        main_table = "daily_metrics_summary"

        where_clause_s = " AND ".join(where_s)

        # 1. KPI'lar
        start_kpi = time.perf_counter()
        
        # Kritik Fix: Dashboard'da "SUM(customer_count)" kullanmak çoklu günlerde 
        # aynı müşteriyi tekrar saydığı için (inflated) hatalı sonuç verir.
        # Eğer çoklu gün/ay seçiliyse ve satislar tablosu varsa oradan benzersiz sayım yapmalıyız.
        
        kpi_query = f"""
            SELECT 
                SUM(revenue) as total_revenue,
                SUM(receipt_count) as total_receipts,
                SUM(unit_count) as total_qty
            FROM {main_table} d
            WHERE {current_where}
        """
        logger.info(f"Executing Optimized KPI Query: {kpi_query}")
        cursor.execute(kpi_query, current_params)
        kpi = cursor.fetchone()
        
        # Müşteri Sayısı için Benzersiz Sayım
        total_customers = 0
        try:
            # OPTIMIZATION: If no filters are applied, use simple COUNT(*) on musteriler
            # If ONLY store or no filters, we can use a faster method
            is_unfiltered = where_clause_s.strip() == "1=1" or not (start_date or end_date or categories or brands or products or search_query or min_revenue or max_revenue or min_orders or max_orders)
            
            if is_unfiltered:
                cursor.execute("SELECT COUNT(*) as cnt FROM musteriler")
                total_customers = cursor.fetchone()['cnt'] or 0
            else:
                # JOIN kullanarak satislar'dan say
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT s.musteri_id) as cnt 
                    FROM satislar s
                    INNER JOIN musteriler m ON s.musteri_id = m.id
                    WHERE {where_clause_s}
                """, params_s)
                total_customers = cursor.fetchone()['cnt'] or 0
        except Exception as e:
            logger.error(f"Customer count query error: {e}")
            # Fallback (Summary table - inflated but fast)
            cursor.execute(f"SELECT SUM(customer_count) FROM {main_table} d WHERE {current_where}", current_params)
            res = cursor.fetchone()
            total_customers = (res['sum'] if isinstance(res, dict) else (res[0] if res else 0)) or 0

        logger.info(f"KPI query took {time.perf_counter() - start_kpi:.4f}s")

        total_revenue = kpi['total_revenue'] or 0 if kpi else 0
        total_receipts = kpi['total_receipts'] or 0 if kpi else 0
        # total_customers satır 291-301'de zaten hesaplandı (KPI sorgusunda bu sütun yok)
        total_quantity = kpi['total_qty'] or 0 if kpi else 0

        # ... (KPI calculations like avg_receipt) ...
        avg_receipt = total_revenue / total_receipts if total_receipts > 0 else 0
        rev_per_customer = total_revenue / total_customers if total_customers > 0 else 0

        # 2. Zaman Serisi
        start_time_series = time.perf_counter()
        if db_engine.DB_BACKEND == "postgresql":
            if group_by == 'day':
                date_group = "tarih"
            elif group_by == 'week':
                date_group = "TO_CHAR(DATE_TRUNC('week', tarih), 'YYYY-\"W\"IW')"
            else:
                date_group = "TO_CHAR(tarih, 'YYYY-MM')"
        else:
            if group_by == 'day':
                date_group = "tarih"
            elif group_by == 'week':
                date_group = "strftime('%Y-W', tarih) || printf('%02d', (strftime('%j', date(tarih, '-3 days', 'weekday 4')) - 1) / 7 + 1)"
            else:
                date_group = "strftime('%Y-%m', tarih)"
            
        time_query = f"SELECT {date_group} as date_group, SUM(revenue) as sales FROM {main_table} d WHERE {current_where} GROUP BY date_group ORDER BY date_group"
        cursor.execute(time_query, current_params)
        
        sales_by_time = [{'date': row['date_group'], 'sales': row['sales'] or 0} for row in cursor.fetchall()]
        logger.info(f"Time series query ({main_table}) took {time.perf_counter() - start_time_series:.4f}s")

        # 3. Kategori Dağılımı
        start_cat = time.perf_counter()
        cat_query = f"""
            SELECT k.ana as category, SUM(d.revenue) as revenue 
            FROM {main_table} d
            JOIN kategoriler k ON d.kategori_id = k.id 
            WHERE {current_where} 
            GROUP BY k.ana ORDER BY revenue DESC LIMIT 10
        """
        cursor.execute(cat_query, current_params)
        categories = [{'category': row['category'] or 'Diğer', 'revenue': row['revenue'] or 0} for row in cursor.fetchall()]

        # 4. Marka Dağılımı
        start_brand = time.perf_counter()
        brand_query = f"""
            SELECT m.ad as name, SUM(d.revenue) as revenue 
            FROM {main_table} d
            JOIN markalar m ON d.marka_id = m.id 
            WHERE {current_where} 
            GROUP BY m.ad ORDER BY revenue DESC LIMIT 10
        """
        cursor.execute(brand_query, current_params)
        brands = [{'name': row['name'] or 'Diğer', 'revenue': row['revenue'] or 0} for row in cursor.fetchall()]

        # 5. Top Ürünler (En çok satanlar) - Optimized using product_daily_summary
        start_prod = time.perf_counter()
        
        where_clause_s = " AND ".join(where_s)
        
        # Optimization: If no complex customer filters, use product_daily_summary
        use_pds = not (segment or customer_type or approval_status or region or store)
        
        if use_pds:
            ph = _placeholder()
            where_pds = ["1=1"]
            params_pds = []
            if start_date:
                where_pds.append(f"pds.tarih >= {ph}"); params_pds.append(start_date)
            if end_date:
                where_pds.append(f"pds.tarih <= {ph}"); params_pds.append(end_date)
            
            # Category/Brand filters - join with urunler
            join_pds = ""
            if resolved_cat_ids or resolved_brand_ids:
                join_pds = "JOIN urunler u ON pds.urun_id = u.id "
                if resolved_cat_ids:
                    ph_cat = ','.join([ph]*len(resolved_cat_ids))
                    where_pds.append(f"u.kategori_id IN ({ph_cat})")
                    params_pds.extend(resolved_cat_ids)
                if resolved_brand_ids:
                    ph_brand = ','.join([ph]*len(resolved_brand_ids))
                    where_pds.append(f"u.marka_id IN ({ph_brand})")
                    params_pds.extend(resolved_brand_ids)

            top_ids_query = f"""
                SELECT pds.urun_id, SUM(pds.revenue) as revenue, SUM(pds.unit_count) as quantity,
                       SUM(pds.customer_count) as approx_customer_count
                FROM product_daily_summary pds
                {join_pds}
                WHERE {" AND ".join(where_pds)}
                GROUP BY pds.urun_id
                ORDER BY revenue DESC
                LIMIT 20
            """
            logger.info(f"Executing Optimized Product Ranking (Summary): {top_ids_query}")
            cursor.execute(top_ids_query, params_pds)
            top_rows = cursor.fetchall()
            
            # Map for Step 2 metadata
            if top_rows:
                target_ids = [row['urun_id'] for row in top_rows]
                ph = _placeholder()
                placeholders = ', '.join([ph] * len(target_ids))
                
                cursor.execute(f"""
                    SELECT u.id, u.ad as name, m.ad as brand, k.ana as category
                    FROM urunler u
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    WHERE u.id IN ({placeholders})
                """, list(target_ids))
                meta_map = {row['id']: row for row in cursor.fetchall()}
                
                products = []
                for row in top_rows:
                    u_id = row['urun_id']
                    m = meta_map.get(u_id)
                    products.append({
                        'id': u_id,
                        'name': m['name'] if m else 'Bilinmeyen',
                        'brand': m['brand'] if m else '-',
                        'category': m['category'] if m else '-',
                        'revenue': row['revenue'] or 0,
                        'sales': row['revenue'] or 0,
                        'count': row['quantity'] or 0,
                        'quantity': row['quantity'] or 0,
                        'customer_count': row['approx_customer_count'] or 0,
                        'frequency': row['quantity'] or 0
                    })
            else:
                products = []
        else:
            # Fallback to satislar for complex segment/region filters
            top_ids_query = f"""
                SELECT s.urun_id, SUM(s.tutar) as revenue, SUM(s.miktar) as quantity
                FROM satislar s
                WHERE {where_clause_s}
                GROUP BY s.urun_id
                ORDER BY revenue DESC
                LIMIT 20
            """
            cursor.execute(top_ids_query, params_s)
            top_rows = cursor.fetchall()
            
            products = []
            if top_rows:
                target_ids = [row['urun_id'] for row in top_rows]
                ph = _placeholder()
                placeholders = ', '.join([ph] * len(target_ids))
                
                # Fetch metadata + Step 2 slow distinct count (only for 20 IDs)
                stats_query = f"""
                    SELECT 
                        s.urun_id, u.ad as name, m.ad as brand, k.ana as category,
                        COUNT(DISTINCT s.musteri_id) as customer_count
                    FROM satislar s
                    JOIN urunler u ON s.urun_id = u.id
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    WHERE s.urun_id IN ({placeholders}) AND {where_clause_s}
                    GROUP BY s.urun_id, u.ad, m.ad, k.ana
                """
                cursor.execute(stats_query, list(target_ids) + params_s)
                stats_map = {row['urun_id']: row for row in cursor.fetchall()}
                
                for row in top_rows:
                    m = stats_map.get(row['urun_id'])
                    products.append({
                        'id': row['urun_id'],
                        'name': m['name'] if m else 'Bilinmeyen',
                        'brand': m['brand'] if m else '-',
                        'category': m['category'] if m else '-',
                        'revenue': row['revenue'] or 0,
                        'sales': row['revenue'] or 0,
                        'count': row['quantity'] or 0,
                        'quantity': row['quantity'] or 0,
                        'customer_count': m['customer_count'] if m else 0,
                        'frequency': row['quantity'] or 0
                    })

        logger.info(f"Product query (Optimized) took {time.perf_counter() - start_prod:.4f}s")

        top_product = {'name': 'N/A', 'sales': 0, 'quantity': 0}
        if products:
            top_product = {'name': products[0]['name'], 'sales': products[0]['revenue'], 'quantity': products[0]['quantity']}

        # Ürün sayısı için urunler tablosu
        cursor.execute("SELECT COUNT(*) as cnt FROM urunler")
        res = cursor.fetchone()
        total_products = res['cnt'] if isinstance(res, dict) else res[0]

        # Marka sayısı için markalar tablosu
        cursor.execute("SELECT COUNT(*) as cnt FROM markalar")
        res = cursor.fetchone()
        total_brands = res['cnt'] if isinstance(res, dict) else res[0]

        # Kategori sayısı için kategoriler tablosu
        cursor.execute("SELECT COUNT(*) as cnt FROM kategoriler")
        res = cursor.fetchone()
        total_categories = res['cnt'] if isinstance(res, dict) else res[0]

        # 6. Müşteri Segmentleri (RFM Dağılımı)
        start_seg = time.perf_counter()
        
        is_unfiltered = where_clause_s.strip() == "1=1" or not (start_date or end_date or categories or brands or products or search_query or min_revenue or max_revenue or min_orders or max_orders)
        
        if is_unfiltered:
            # Use pre-calculated segmentozet table
            cursor.execute("SELECT segment, customer_count as count FROM segmentozet ORDER BY count DESC")
        else:
            # Not: Dashboard'da segment dağılımı için satislar tablosunu kullanıyoruz (daha doğru)
            seg_query = f"""
                SELECT m.segment, COUNT(DISTINCT s.musteri_id) as count
                FROM satislar s
                JOIN musteriler m ON s.musteri_id = m.id
                WHERE {where_clause_s}
                GROUP BY m.segment
                ORDER BY count DESC
            """
            cursor.execute(seg_query, params_s)
            
        customer_segments = [{'segment': row['segment'] or 'Bilinmeyen', 'count': row['count'] or 0} for row in cursor.fetchall()]
        logger.info(f"Segment query took {time.perf_counter() - start_seg:.4f}s")

        logger.info(f"Total get_sales_analytics took {time.perf_counter() - start_all:.4f}s")
        return {
            'totalRevenue': total_revenue,
            'totalCustomers': total_customers,
            'totalReceipts': total_receipts,
            'totalProducts': total_products,
            'totalBrands': total_brands,
            'totalCategories': total_categories,
            'totalQuantity': total_quantity,
            'averageOrderValue': avg_receipt,
            'salesByTime': sales_by_time,
            'productCategories': categories,
            'brandRevenue': brands,
            'topProduct': top_product,
            'topProducts': products,
            'productRevenue': products,
            'customerSegments': customer_segments
        }

    except Exception as e:
        logger.error(f"Analytics Error: {e}", exc_info=True)
        return None
    finally:
        db_engine.release_connection(conn)

# ================== KARŞILAŞTIRMA VERİLERİ ==================

def get_comparison_data(start_month=None, end_month=None):
    """CRM vs Anonim karşılaştırma verileri (genelozet tablosundan)"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = _get_cursor(conn)
        
        where = ""
        params = []
        ph = _placeholder()
        if start_month:
            where += f" AND ay >= {ph}"
            params.append(start_month)
        if end_month:
            where += f" AND ay <= {ph}"
            params.append(end_month)
        
        query = f"""
            SELECT 
                SUM(toplam_ciro) as toplam_ciro,
                SUM(crm_ciro) as crm_ciro,
                SUM(anonim_ciro) as anonim_ciro,
                SUM(toplam_fis) as toplam_fis,
                SUM(crm_fis) as crm_fis,
                SUM(anonim_fis) as anonim_fis,
                SUM(crm_musteri) as crm_musteri,
                AVG(crm_sepet_ort) as crm_sepet_ort,
                AVG(anonim_sepet_ort) as anonim_sepet_ort,
                AVG(crm_oran_ciro) as crm_oran
            FROM genelozet
            WHERE 1=1 {where}
        """
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        return {
            'toplamCiro': row['toplam_ciro'] or 0,
            'crmCiro': row['crm_ciro'] or 0,
            'anonimCiro': row['anonim_ciro'] or 0,
            'toplamFis': row['toplam_fis'] or 0,
            'crmFis': row['crm_fis'] or 0,
            'anonimFis': row['anonim_fis'] or 0,
            'crmMusteri': row['crm_musteri'] or 0,
            'crmSepetOrt': row['crm_sepet_ort'] or 0,
            'anonimSepetOrt': row['anonim_sepet_ort'] or 0,
            'crmOran': row['crm_oran'] or 0
        }
        
    except Exception as e:
        logger.error(f"Comparison Error: {e}")
        return None
    finally:
        db_engine.release_connection(conn)

# ================== MÜŞTERİ VERİLERİ ==================

def get_customer_data(limit=50, offset=0, search_query=None):
    """Müşteri listesi"""
    conn = get_connection()
    if not conn:
        return {"data": [], "total_count": 0}
    
    try:
        cursor = _get_cursor(conn)
        
        where = ""
        params = []
        ph = _placeholder()
        if search_query:
            where = f"WHERE ad LIKE {ph} OR telefon LIKE {ph}"
            params = [f"%{search_query}%", f"%{search_query}%"]
        
        # Toplam sayı
        cursor.execute(f"SELECT COUNT(*) FROM musteriler {where}", params)
        res = cursor.fetchone()
        total = res['count'] if isinstance(res, dict) else res[0]
        
        # Veri
        query = f"""
            SELECT id, ad, telefon, tip, onay_durumu, kayit_tarihi, kayit_magazasi
            FROM musteriler
            {where}
            ORDER BY id DESC
            LIMIT {ph} OFFSET {ph}
        """
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()
        
        data = [dict(row) for row in rows]
        
        return {"data": data, "total_count": total}
        
    except Exception as e:
        logger.error(f"Customer Error: {e}")
        return {"data": [], "total_count": 0}
    finally:
        db_engine.release_connection(conn)

def get_customer_transactions(customer_id, limit=50):
    """Müşteri satış geçmişi"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cursor = _get_cursor(conn)
        ph = _placeholder()
        
        query = f"""
            SELECT 
                s.fis_no, s.tarih, s.saat, s.tutar, s.miktar, s.belge_tipi,
                u.ad as urun_ad,
                m.ad as magaza_ad
            FROM satislar s
            LEFT JOIN urunler u ON s.urun_id = u.id
            LEFT JOIN magazalar m ON s.magaza_id = m.id
            WHERE s.musteri_id = {ph}
            ORDER BY s.tarih DESC, s.saat DESC
            LIMIT {ph}
        """
        cursor.execute(query, [customer_id, limit])
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Customer Transactions Error: {e}")
        return []
    finally:
        db_engine.release_connection(conn)

# ================== SYNC DURUMU ==================

def get_sync_status():
    """Senkronizasyon durumu"""
    conn = get_connection()
    if not conn:
        return {"total_records": 0, "last_sync": None, "status": "offline"}

    try:
        cursor = _get_cursor(conn)

        # Satış sayısı
        cursor.execute("SELECT COUNT(*) FROM satislar")
        res = cursor.fetchone()
        count = res['count'] if isinstance(res, dict) else res[0]

        # Sync meta
        cursor.execute("SELECT key, value FROM syncmeta")
        meta = {row['key']: row['value'] for row in cursor.fetchall()}

        # DB boyutu
        if db_engine.DB_BACKEND == "postgresql":
            db_size = 0
        else:
            try:
                db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
            except OSError:
                db_size = 0

        # Sync lock
        is_syncing = False

        # Scheduler artık harici (Task Scheduler) tarafından yönetiliyor
        # Bu yüzden boş bir scheduler durumu döndürüyoruz
        scheduler_status = {
            "running": False,
            "jobs": []
        }

        return {
            "total_records": count,
            "db_size_mb": round(db_size, 2),
            "status": "online",
            "is_syncing": is_syncing,
            "last_sync": meta.get('last_full_sync'),
            "last_delta_sync": meta.get('last_delta_sync'),
            "last_lookup_sync": meta.get('last_lookup_sync'),
            "last_lookup_sync_error": meta.get('last_lookup_sync_error'),
            "last_summary_update": meta.get('last_summary_update'),
            "last_maintenance": meta.get('last_maintenance'),
            "scheduler": scheduler_status
        }

    except Exception as e:
        logger.error(f"Sync Status Error: {e}")
        return {"total_records": 0, "last_sync": None, "status": "error"}
    finally:
        db_engine.release_connection(conn)

# ================== LEGACY UYUMLULUK ==================

def get_sales_data(limit=None, offset=0, sort_by=None, filter_column=None, filter_value=None):
    """Satış listesi - CRM Analytics için tüm veri

    Args:
        limit: Maksimum kayıt sayısı. None ise tüm kayıtlar döner.
        offset: Başlangıç offset'i
    """
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = _get_cursor(conn)
        ph = _placeholder()

        # Limit yoksa tüm veriyi çek (CRM Analytics için)
        if limit is None:
            cursor.execute("""
                SELECT
                       s.id, s.fis_no, s.musteri_id, s.tarih,
                       s.saat, s.tutar, s.miktar, s.urun_id, s.magaza_id,
                       u.ad as urun_ad,
                       m.ad as magaza_ad,
                       mrk.ad as marka,
                       k.ana as kategori
                FROM satislar s
                LEFT JOIN urunler u ON s.urun_id = u.id
                LEFT JOIN magazalar m ON s.magaza_id = m.id
                LEFT JOIN markalar mrk ON u.marka_id = mrk.id
                LEFT JOIN kategoriler k ON u.kategori_id = k.id
                ORDER BY s.tarih DESC
            """)
        else:
            cursor.execute(f"""
                SELECT
                       s.id, s.fis_no, s.musteri_id, s.tarih,
                       s.saat, s.tutar, s.miktar, s.urun_id, s.magaza_id,
                       u.ad as urun_ad,
                       m.ad as magaza_ad,
                       mrk.ad as marka,
                       k.ana as kategori
                FROM satislar s
                LEFT JOIN urunler u ON s.urun_id = u.id
                LEFT JOIN magazalar m ON s.magaza_id = m.id
                LEFT JOIN markalar mrk ON u.marka_id = mrk.id
                LEFT JOIN kategoriler k ON u.kategori_id = k.id
                ORDER BY s.tarih DESC
                LIMIT {ph} OFFSET {ph}
            """, [limit, offset])

        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"Sales Data Error: {e}")
        return []
    finally:
        db_engine.release_connection(conn)

def get_db_connection():
    """Legacy uyumluluk"""
    return get_connection()

def get_live_sql_connection():
    """Legacy - artık kullanılmıyor"""
    return None


# ================== PLATFORM DURUMU ==================

from concurrent.futures import ThreadPoolExecutor
from django.core.cache import cache

def get_platform_status():
    """Tüm platform durumları — Paralel ve Estimate bazlı yüksek performanslı versiyon"""
    import time
    import urllib.request
    import socket
    from datetime import datetime, timedelta

    # 1. Önbellek Kontrolü (15 saniye)
    cache_key = 'platform_status_data_ultra'
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    RAILWAY_BACKEND_URL = os.environ.get('RAILWAY_BACKEND_URL', 'https://backend-production-05ce.up.railway.app')
    RAILWAY_FRONTEND_URL = os.environ.get('RAILWAY_FRONTEND_URL', 'https://frontend-production-96d5.up.railway.app')

    def check_url(url, name, icon, details_prefix):
        try:
            # Optimizasyon: Eğer kendi URL'imizi kontrol ediyorsak dışarı çıkma (Hairpinning engelleme)
            # URL içinde 'backend' geçiyorsa veya mevcut host ise direkt online dön
            is_self = 'backend' in url.lower() or '127.0.0.1' in url or 'localhost' in url
            if is_self and name == 'Railway Backend':
                return {
                    'id': 'railway_backend', 'name': 'Railway Backend', 'icon': '🚂',
                    'status': 'online', 'latency_ms': 1, 'url': url,
                    'details': 'Internal — Aktif',
                    'checked_at': datetime.now().isoformat(),
                }

            t0 = time.time()
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'XPlusCRM-Monitor/1.0')
            # Timeout'u 5 saniyeye çıkaralım (Railway proxy bazen yavaş olabilir)
            with urllib.request.urlopen(req, timeout=5) as resp:
                latency = round((time.time() - t0) * 1000)
                return {
                    'id': name.lower().replace(' ', '_'), 'name': name, 'icon': icon,
                    'status': 'online', 'latency_ms': latency, 'url': url,
                    'details': f'{details_prefix} — {latency}ms yanıt',
                    'checked_at': datetime.now().isoformat(),
                }
        except Exception as e:
            return {
                'id': name.lower().replace(' ', '_'), 'name': name, 'icon': icon,
                'status': 'offline', 'latency_ms': None, 'url': url,
                'details': f'Hata: {str(e)[:40]}',
                'checked_at': datetime.now().isoformat(),
            }

    def check_postgres():
        # ... (no changes here, keeping it as is)
        try:
            t0 = time.time()
            from . import db_engine
            pg_pool = db_engine.get_pg_pool()
            if pg_pool:
                conn = pg_pool.getconn()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                latency = round((time.time() - t0) * 1000)
                db_size = 0
                table_counts = {}
                try:
                    cursor.execute("SELECT pg_database_size(current_database())")
                    db_size = round(cursor.fetchone()[0] / (1024 * 1024), 1)
                    for table in ['satislar', 'musteriler', 'urunler']:
                        cursor.execute(f"SELECT reltuples::bigint FROM pg_class WHERE relname = '{table}'")
                        row = cursor.fetchone()
                        table_counts[table] = row[0] if row else 0
                except: pass
                cursor.close()
                pg_pool.putconn(conn)
                return {
                    'id': 'railway_postgres', 'name': 'Railway PostgreSQL', 'icon': '🐘',
                    'status': 'online', 'latency_ms': latency,
                    'url': 'Internal Pool',
                    'details': f'DB: {db_size} MB — ~{table_counts.get("satislar", 0):,} kayıt',
                    'checked_at': datetime.now().isoformat(),
                    'extra': {'db_size_mb': db_size, 'tables': table_counts}
                }
            else:
                raise Exception("DB Pool bulunamadı")
        except Exception as e:
            return {'id': 'railway_postgres', 'name': 'Railway PostgreSQL', 'icon': '🐘', 'status': 'offline', 'details': f'Pool Hatası: {str(e)[:30]}'}

    def check_sync():
        """Sync Worker durumunu kontrol et - Log tabanlı"""
        try:
            from . import db_engine
            pg_pool = db_engine.get_pg_pool()
            if not pg_pool: raise Exception("No PG Pool")
            
            conn = pg_pool.getconn()
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. SyncMeta'dan son başarılı sync zamanını al
            cursor.execute("SELECT key, value FROM syncmeta WHERE key IN ('last_delta_sync', 'last_full_sync')")
            meta = {row['key']: row['value'] for row in cursor.fetchall()}
            
            # 2. worker-sales servisinin son logunu al (canlılık için)
            cursor.execute("SELECT timestamp FROM system_logs WHERE service_name = 'worker-sales' ORDER BY id DESC LIMIT 1")
            last_log = cursor.fetchone()
            
            cursor.close()
            pg_pool.putconn(conn)
            
            last_delta = meta.get('last_delta_sync')
            last_full = meta.get('last_full_sync')
            worker_status = 'offline'
            worker_details = 'Aktivite yok'
            latest_sync = None
            
            # En son başarılı data sync zamanı
            for ts_str in [last_delta, last_full]:
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.split('.')[0].replace('Z', '+00:00').replace('+00:00', ''))
                        if latest_sync is None or ts > latest_sync: latest_sync = ts
                    except: pass
            
            # Canlılık kontrolü: Son 15 dakikada herhangi bir log var mı?
            is_alive = False
            if last_log:
                log_time = last_log['timestamp']
                if datetime.now() - log_time.replace(tzinfo=None) < timedelta(minutes=15):
                    is_alive = True
            
            if latest_sync:
                age = datetime.now() - latest_sync
                if age < timedelta(hours=2): 
                    worker_status = 'online'
                    worker_details = f'Aktif — {int(age.total_seconds() // 60)} dk önce sync'
                else: 
                    worker_status = 'warning'
                    worker_details = f'Veritabanı {int(age.total_seconds() // 3600)} saat önce güncellendi'
            
            # Eğer sync eski ama servis log atıyorsa durumu 'online' ama detayda 'beklemede' yapabiliriz
            if is_alive and worker_status != 'online':
                worker_status = 'online'
                worker_details = 'Servis Aktif — Veri bekleniyor'
                    
            return {
                'id': 'sync_worker', 'name': 'Sync Worker', 'icon': '🔄',
                'status': worker_status, 'details': worker_details,
                'checked_at': datetime.now().isoformat(),
            }
        except Exception as e: 
            return {'id': 'sync_worker', 'name': 'Sync Worker', 'icon': '🔄', 'status': 'offline', 'details': f'Hata: {str(e)[:30]}'}


    def check_sql_server():
        """Tailscale + SQL durumunu kontrol et - Log tabanlı"""
        try:
            from . import db_engine
            pg_pool = db_engine.get_pg_pool()
            if not pg_pool: raise Exception("No PG Pool")
            
            conn = pg_pool.getconn()
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # tailscale-boot servisinden son logu al
            cursor.execute("""
                SELECT message, timestamp 
                FROM system_logs 
                WHERE service_name = 'tailscale-boot' 
                ORDER BY id DESC LIMIT 1
            """)
            last_boot_log = cursor.fetchone()
            
            cursor.close()
            pg_pool.putconn(conn)
            
            if last_boot_log:
                msg = last_boot_log['message']
                ts = last_boot_log['timestamp']
                
                # Eğer son log 1 saat içindeyse online (veya yeni başlayan bir işlemse)
                is_recent = (datetime.now() - ts.replace(tzinfo=None)) < timedelta(hours=1)
                
                if "successfully" in msg.lower() or "connected" in msg.lower():
                    return {
                        'id': 'tailscale_sqlserver', 'name': 'Tailscale + SQL', 'icon': '🔗',
                        'status': 'online' if is_recent else 'warning', 
                        'details': 'VPN Aktif' if is_recent else 'Pasif (Son 1 saatte boot yok)',
                        'checked_at': datetime.now().isoformat(),
                    }
                elif "failed" in msg.lower() or "error" in msg.lower():
                    return {
                        'id': 'tailscale_sqlserver', 'name': 'Tailscale + SQL', 'icon': '🔗',
                        'status': 'offline', 'details': f'Hata: {msg[:30]}...',
                        'checked_at': datetime.now().isoformat(),
                    }
                else:
                    # Tanımlanmamış tüm loglar için, en azından logun var olduğunu gösterelim
                    return {
                        'id': 'tailscale_sqlserver', 'name': 'Tailscale + SQL', 'icon': '🔗',
                        'status': 'online' if is_recent else 'warning',
                        'details': f'Bilgi: {msg[:25]}...',
                        'checked_at': datetime.now().isoformat(),
                    }
            
            return {'id': 'tailscale_sqlserver', 'name': 'Tailscale + SQL', 'icon': '🔗', 'status': 'offline', 'details': 'Log Bulunamadı'}
        except Exception as e: 
            return {'id': 'tailscale_sqlserver', 'name': 'Tailscale + SQL', 'status': 'offline', 'details': str(e)[:30]}


    # PARALEL ÇALIŞTIRMA 🚀
    with ThreadPoolExecutor(max_workers=5) as executor:
        f_backend = executor.submit(check_url, f"{RAILWAY_BACKEND_URL}/api/health/", 'Railway Backend', '🚂', 'Django API')
        f_frontend = executor.submit(check_url, RAILWAY_FRONTEND_URL, 'Railway Frontend', '🌐', 'React SPA')
        f_postgres = executor.submit(check_postgres)
        f_sync = executor.submit(check_sync)
        f_sql = executor.submit(check_sql_server)
        
        platforms = [f_backend.result(), f_frontend.result(), f_postgres.result(), f_sync.result(), f_sql.result()]

    result = {
        'platforms': platforms,
        'summary': {
            'online': sum(1 for p in platforms if p['status'] == 'online'),
            'total': len(platforms),
            'overall_status': 'healthy' if sum(1 for p in platforms if p['status'] == 'online') >= 4 else 'degraded',
            'checked_at': datetime.now().isoformat(),
        }
    }
    
    # 20 saniye önbelleğe al
    cache.set(cache_key, result, 20)
    return result


# ================== SİSTEM DURUMU (Legacy) ==================

def get_system_status():
    """Tam sistem durumu - Monitör ekranı için"""
    import pyodbc
    from datetime import datetime
    
    status = {
        'sqlite_cache': {
            'status': 'offline',
            'path': None,
            'size_mb': 0,
            'tables': {}
        },
        'sql_server': {
            'status': 'offline',
            'server': None,
            'database': None,
            'tables': {}
        },
        'sync': {
            'last_full_sync': None,
            'last_delta_sync': None,
            'is_syncing': False
        },
        'scheduler': {
            'running': False,
            'jobs': []
        }
    }
    
    # 1. SQLite Cache Durumu
    try:
        conn = get_connection()
        if conn:
            cursor = _get_cursor(conn)

            status['sqlite_cache']['status'] = 'online'
            status['sqlite_cache']['path'] = 'PostgreSQL' if db_engine.DB_BACKEND == 'postgresql' else DB_PATH
            if db_engine.DB_BACKEND != 'postgresql':
                try:
                    status['sqlite_cache']['size_mb'] = round(os.path.getsize(DB_PATH) / (1024 * 1024), 2)
                except OSError:
                    status['sqlite_cache']['size_mb'] = 0

            # Tablo kayıt sayıları
            tables = ['satislar', 'musteriler', 'urunler', 'markalar', 'kategoriler', 'magazalar',
                      'gunlukozet', 'genelozet', 'markakarsilastirma', 'kategorikarsilastirma', 'kampanyalar']
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    row = cursor.fetchone()
                    status['sqlite_cache']['tables'][table] = row['cnt'] if isinstance(row, dict) else row[0]
                except:
                    pass
            
            # Sync meta
            cursor.execute("SELECT key, value, updated_at FROM syncmeta")
            for row in cursor.fetchall():
                if row['key'] == 'last_full_sync':
                    status['sync']['last_full_sync'] = row['value']  # Fixed: was row['updated_at']
                elif row['key'] == 'last_delta_sync':
                    status['sync']['last_delta_sync'] = row['value']
                elif row['key'] == 'last_summary_update':
                    status['sync']['last_summary_update'] = row['value']
                elif row['key'] == 'last_maintenance':
                    status['sync']['last_maintenance'] = row['value']
            
            db_engine.release_connection(conn)
    except Exception as e:
        logger.error(f"SQLite status error: {e}")
    
    # 2. SQL Server Durumu
    try:
        if not pyodbc:
            status['sql_server']['status'] = 'unavailable (backend-only)'
            status['sql_server']['server'] = '100.109.143.127:14330'
            status['sql_server']['database'] = 'DerinSISShow'
            status['sql_server']['info'] = 'SQL Server access is handled via Sync Worker'
        else:
            driver = '{SQL Server}'
            available = pyodbc.drivers()
            for d in ['{ODBC Driver 18 for SQL Server}', '{ODBC Driver 17 for SQL Server}', '{SQL Server Native Client 11.0}']:
                if d.strip('{}') in available:
                    driver = d
                    break
            
            import socket
            host = '100.109.143.127'
            port = 14330
            # Fast socket check before pyodbc connect to avoid long hangs
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            if s.connect_ex((host, port)) != 0: 
                s.close()
                raise Exception("SQL Server portuna ulaşılamıyor (VPN kapalı olabilir)")
            s.close()
            
            conn_str = (
                f"DRIVER={driver};SERVER={host},{port};"
                f"DATABASE=DerinSISShow;UID=sa2;PWD=1478236950Mm..;"
                f"Network=DBMSSOCN;Encrypt=no;TrustServerCertificate=yes;"
            )
            sql_conn = pyodbc.connect(conn_str, timeout=5)
            sql_cursor = sql_conn.cursor()
            
            status['sql_server']['status'] = 'online'
            status['sql_server']['server'] = '100.109.143.127:14330'
            status['sql_server']['database'] = 'DerinSISShow'
            
            # View kayıt sayıları
            for view in ['M_Crm', 'M_PowerBimusteriler']:
                try:
                    sql_cursor.execute(f"SELECT COUNT(*) FROM {view} WITH (NOLOCK)")
                    status['sql_server']['tables'][view] = sql_cursor.fetchone()[0]
                except:
                    pass
            
            sql_conn.close()
    except Exception as e:
        logger.warning(f"SQL Server status error: {e}")
        status['sql_server']['status'] = 'offline'
        status['sql_server']['error'] = str(e)
    
    # 3. Scheduler Durumu (Moved to Sync Worker)
    status['scheduler'] = {
        'running': False,
        'info': 'Scheduler is managed by xplus-worker service on Railway'
    }
    
    return status

def get_available_years():
    """crmozet ve satislar'dan mevcut yılları getir"""
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = _get_cursor(conn)
        ph = _placeholder()
        # gunlukciroozet en hızlısıdır, tüm yılları içerir
        if db_engine.DB_BACKEND == "postgresql":
            cursor.execute("SELECT DISTINCT EXTRACT(YEAR FROM tarih)::text as pid FROM gunlukciroozet ORDER BY 1 DESC")
        else:
            cursor.execute("SELECT DISTINCT strftime('%Y', tarih) as pid FROM gunlukciroozet ORDER BY 1 DESC")
        years = [int(row['pid'] if isinstance(row, dict) else row[0]) for row in cursor.fetchall() if (row['pid'] if isinstance(row, dict) else row[0]) is not None]
        return years
    except Exception as e:
        logger.error(f"Error getting available years: {e}")
        return []
    finally:
        db_engine.release_connection(conn)

_category_hierarchy_cache = None
_category_hierarchy_cache_time = 0.0
_CATEGORY_CACHE_TTL = 600  # 10 dakika

def get_category_hierarchy():
    """SQLite'tan kategori hiyerarşisini getir (Ana -> Alt1 -> Alt2) — in-memory cached"""
    global _category_hierarchy_cache, _category_hierarchy_cache_time
    import time as _time
    if _category_hierarchy_cache is not None and _time.time() - _category_hierarchy_cache_time < _CATEGORY_CACHE_TTL:
        return _category_hierarchy_cache

    conn = get_connection()
    if not conn:
        return {}

    try:
        cursor = _get_cursor(conn)
        cursor.execute("""
            SELECT DISTINCT k.ana, k.alt1, k.alt2
            FROM kategoriler k
            WHERE k.ana IS NOT NULL
            ORDER BY k.ana, k.alt1, k.alt2
        """)

        hierarchy = {}
        for row in cursor.fetchall():
            ana = row['ana'] or 'Diğer'
            alt1 = row['alt1'] or ''
            alt2 = row['alt2'] or ''

            if ana not in hierarchy:
                hierarchy[ana] = {}
            if alt1:
                if alt1 not in hierarchy[ana]:
                    hierarchy[ana][alt1] = []
                if alt2 and alt2 not in hierarchy[ana][alt1]:
                    hierarchy[ana][alt1].append(alt2)

        _category_hierarchy_cache = hierarchy
        _category_hierarchy_cache_time = _time.time()
        return hierarchy
    except Exception as e:
        logger.error(f"Error getting category hierarchy: {e}")
        return {}
    finally:
        db_engine.release_connection(conn)

def get_brand_list():
    """SQLite'tan tüm marka listesini getir"""
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = _get_cursor(conn)
        cursor.execute("SELECT DISTINCT ad FROM markalar WHERE ad IS NOT NULL AND ad != '' ORDER BY ad")
        return [row['ad'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting brand list: {e}")
        return []
    finally:
        db_engine.release_connection(conn)

_brand_by_category_cache = None
_brand_by_category_cache_time = 0.0

def get_brand_by_category():
    """Her kategori için marka listesi — in-memory cached"""
    global _brand_by_category_cache, _brand_by_category_cache_time
    import time as _time
    if _brand_by_category_cache is not None and _time.time() - _brand_by_category_cache_time < _CATEGORY_CACHE_TTL:
        return _brand_by_category_cache

    conn = get_connection()
    if not conn:
        return {}

    try:
        cursor = _get_cursor(conn)
        cursor.execute("""
            SELECT DISTINCT k.ana as category, m.ad as brand
            FROM urunler u
            JOIN kategoriler k ON u.kategori_id = k.id
            JOIN markalar m ON u.marka_id = m.id
            WHERE k.ana IS NOT NULL AND m.ad IS NOT NULL
            ORDER BY k.ana, m.ad
        """)

        result = {}
        for row in cursor.fetchall():
            cat = row['category']
            brand = row['brand']
            if cat not in result:
                result[cat] = []
            if brand and brand not in result[cat]:
                result[cat].append(brand)

        _brand_by_category_cache = result
        _brand_by_category_cache_time = _time.time()
        return result
    except Exception as e:
        logger.error(f"Error getting brand by category: {e}")
        return {}
    finally:
        db_engine.release_connection(conn)
def get_clv_data_optimized(year=None, month=None, start_date=None, end_date=None, 
                           customer_type=None, approval_status=None, region=None):
    """
    CLV hesaplaması için optimize edilmiş SQL sorgusu.
    BG/NBD + Gamma-Gamma modeli ile hesaplanan lifetime_value_tahmini ve 
    diğer önceden hesaplanmış metrikleri (toplam_harcama, fis_sayisi) musteridetayozet'ten çeker.
    """
    conn = get_connection()
    if not conn:
        return None

    try:
        cursor = _get_cursor(conn)
        ph = _placeholder()
        
        # Filtreleri hazırlat (musteriler ve musteridetayozet üzerinde)
        where_conditions = ["1=1"]
        params = []
        
        if customer_type:
            where_conditions.append(f"mu.tip = {ph}")
            params.append(customer_type)
        if approval_status:
            where_conditions.append(f"mu.onay_durumu = {ph}")
            params.append(approval_status)
        if region:
            where_conditions.append(f"mu.kayit_magazasi LIKE {ph}")
            params.append(f"%{region}%")

        # ÖNEMLİ: Eğer tarih filtresi (yıl, ay, start_date, end_date) VARSA, 
        # mecburen satislar tablosuna gitmeliyiz çünkü musteridetayozet TÜM zamanları kapsar.
        has_date_filter = bool(year or month or start_date or end_date)
        
        if not has_date_filter:
            # SADECE Müşteri Bazlı Özetlerden Çek (Süper Hızlı)
            # SQLite'ta MusteriID, PostgreSQL'de musteri_id gibi farklılıkları val ile çözeriz 
            # ancak SQL içinde DB'ye özel field adını kullanmalıyız.
            if db_engine.DB_BACKEND == "postgresql":
                query = f"""
                    SELECT 
                        mdo.musteri_id, 
                        mu.ad as customer_name,
                        mdo.toplam_harcama as total_value, 
                        mdo.toplam_alisveris as order_count,
                        mdo.ilk_alisveris_tarihi as first_date, -- musteridetayozet'ten ilk tarih
                        mdo.son_alisveris_tarihi as last_date,
                        COALESCE(mdo.lifetime_value_tahmini, mdo.toplam_harcama) as predicted_clv
                    FROM musteridetayozet mdo
                    LEFT JOIN musteriler mu ON mdo.musteri_id = mu.id
                    WHERE {" AND ".join(where_conditions)}
                """
            else:
                query = f"""
                    SELECT 
                        mdo.MusteriID as musteri_id, 
                        mu.ad as customer_name,
                        mdo.ToplamHarcama as total_value, 
                        mdo.ToplamAlisveris as order_count,
                        mdo.IlkAlisverisTarihi as first_date,
                        mdo.SonAlisverisTarihi as last_date,
                        COALESCE(mdo.LifetimeValueTahmini, mdo.ToplamHarcama) as predicted_clv
                    FROM musteridetayozet mdo
                    LEFT JOIN musteriler mu ON mdo.MusteriID = mu.id
                    WHERE {" AND ".join(where_conditions)}
                """
            logger.info("Executing FAST CLV Summary Query (No satislar join)")
            cursor.execute(query, params)
            rows = cursor.fetchall()
        else:
            # Tarih filtresi varsa mecburen satislar ile join yapıyoruz ama musteridetayozet'ten 
            # CLV tahminini alıyoruz. satislar'dan sadece o tarih aralığındaki TUTAR ve FİŞ sayısını alıyoruz.
            
            # Tarih filtrelerini ekle
            where_s = list(where_conditions)
            params_s = list(params)
            
            if year:
                where_s.append(f"s.tarih >= {ph} AND s.tarih < {ph}")
                params_s.append(f"{year}-01-01")
                params_s.append(f"{int(year)+1}-01-01")
            if month:
                if db_engine.DB_BACKEND == "postgresql":
                    where_s.append(f"TO_CHAR(s.tarih, 'MM') = {ph}")
                else:
                    where_s.append(f"substr(s.tarih, 6, 2) = {ph}")
                params_s.append(str(month).zfill(2))
            if start_date:
                where_s.append(f"s.tarih >= {ph}")
                params_s.append(start_date)
            if end_date:
                where_s.append(f"s.tarih <= {ph}")
                params_s.append(end_date)
                
            if db_engine.DB_BACKEND == "postgresql":
                query = f"""
                    SELECT 
                        s.musteri_id, 
                        mu.ad as customer_name,
                        SUM(s.tutar) as total_value, 
                        COUNT(DISTINCT s.fis_no) as order_count,
                        MIN(s.tarih) as first_date,
                        MAX(s.tarih) as last_date,
                        COALESCE(mdo.lifetime_value_tahmini, 0) as predicted_clv
                    FROM satislar s
                    LEFT JOIN musteriler mu ON s.musteri_id = mu.id
                    LEFT JOIN musteridetayozet mdo ON s.musteri_id = mdo.musteri_id
                    WHERE {" AND ".join(where_s)}
                    GROUP BY s.musteri_id, mu.ad, mdo.lifetime_value_tahmini
                    HAVING SUM(s.tutar) > 0
                """
            else:
                query = f"""
                    SELECT 
                        s.musteri_id, 
                        mu.ad as customer_name,
                        SUM(s.tutar) as total_value, 
                        COUNT(DISTINCT s.fis_no) as order_count,
                        MIN(s.tarih) as first_date,
                        MAX(s.tarih) as last_date,
                        COALESCE(mdo.LifetimeValueTahmini, 0) as predicted_clv
                    FROM satislar s
                    LEFT JOIN musteriler mu ON s.musteri_id = mu.id
                    LEFT JOIN musteridetayozet mdo ON s.musteri_id = mdo.MusteriID
                    WHERE {" AND ".join(where_s)}
                    GROUP BY s.musteri_id, mu.ad, mdo.LifetimeValueTahmini
                    HAVING SUM(s.tutar) > 0
                """
            logger.info("Executing Filtered CLV Query (Date filtering required)")
            cursor.execute(query, params_s)
            rows = cursor.fetchall()
        
        result = []
        for row in rows:
            # BG/NBD CLV değeri varsa onu kullan, yoksa toplam harcamayı kullan (mdo'dan geliyorsa)
            # Eğer tarih filtresi varsa, predicted_clv'yi oransal olarak mı yoksa olduğu gibi mi göstermeli?
            # Genelde predicted_clv "gelecek" içindir, bu yüzden olduğu gibi dursa daha iyi.
            result.append({
                'cid': row['musteri_id'],
                'name': row['customer_name'] or str(row['musteri_id']),
                'total_value': row['predicted_clv'] if row.get('predicted_clv') and row['predicted_clv'] > 0 else row['total_value'],
                'historical_value': row['total_value'],
                'order_count': row['order_count'],
                'first_date': row.get('first_date'),
                'last_date': row['last_date']
            })
            
        return result

    except Exception as e:
        logger.error(f"Optimized CLV SQL Error: {e}")
        if db_engine.DB_BACKEND == 'postgresql':
            conn.rollback()
        return None

    finally:
        db_engine.release_connection(conn)
