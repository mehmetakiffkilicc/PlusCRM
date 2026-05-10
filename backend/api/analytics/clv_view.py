"""
CLV (Customer Lifetime Value) Analysis View - Dual Mode Optimized
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
import logging
import time
from datetime import datetime

from ..models import DataSource
from .base import (
    get_datasource_data,
    get_cached_data,
    set_cached_data,
    get_user_from_request,
    detect_columns,
    parse_date_fast
)

logger = logging.getLogger(__name__)

# Cache for calculated segments to make drill-down consistent and fast
# Key: cache_key -> Value: { 'segments': {'Platinum': [...], ...}, 'timestamp': ... }
_clv_internal_cache = {}
_clv_internal_timeout = 300 # 5 minutes

def parse_amount(value):
    if value is None: return 0.0
    if isinstance(value, (int, float)): return float(value)
    try:
        s_val = str(value)
        if ',' in s_val: return float(s_val.replace(',', '.'))
        return float(s_val)
    except (ValueError, TypeError): return 0.0

def _get_internal_stats(request, data_source_id):
    """
    Unified method to get customer stats and thresholds.
    Used by both summary and detail views.
    """
    # Filtreleri al
    year = request.GET.get('year')
    month = request.GET.get('month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    customer_type = request.GET.get('customer_type')
    approval_status = request.GET.get('approval_status')
    region = request.GET.get('region')

    # Internal cache key
    filter_hash = f"{year}_{month}_{start_date}_{end_date}_{customer_type}_{approval_status}_{region}"
    internal_key = f"{data_source_id}_{filter_hash}"
    
    if internal_key in _clv_internal_cache:
        entry = _clv_internal_cache[internal_key]
        if time.time() - entry['timestamp'] < _clv_internal_timeout:
            return entry['data']

    # DataSource load
    user = get_user_from_request(request)
    try:
        if user: ds = DataSource.objects.get(id=data_source_id, user=user)
        else: ds = DataSource.objects.get(id=data_source_id)
    except DataSource.DoesNotExist:
        return None

    data_type = getattr(ds, 'type', '')
    is_db = data_type == 'database' or 'sal' in ds.name.lower() or 'sat' in ds.name.lower()

    customer_stats = [] 

    # SQL PATH
    if is_db:
        has_filters = any([
            year and year not in ('null', 'undefined', ''),
            month and month not in ('null', 'undefined', ''),
            start_date and start_date not in ('null', 'undefined', ''),
            end_date and end_date not in ('null', 'undefined', ''),
            customer_type and customer_type not in ('null', 'undefined', ''),
            approval_status and approval_status not in ('null', 'undefined', ''),
            region and region not in ('null', 'undefined', '')
        ])

        if not has_filters:
            # Özet Tablodan Hızlı Çekim (Kullanıcı talebi ve performans için)
            from ..db_engine import get_connection, get_dict_cursor, release_connection
            conn = get_connection()
            try:
                cur = get_dict_cursor(conn)
                cur.execute('''
                    SELECT musteri_id as cid, ad_soyad as name, 
                           toplam_harcama as total_value, 
                           toplam_alisveris as order_count,
                           ilk_alisveris_tarihi as first_date,
                           son_alisveris_tarihi as last_date
                    FROM musteridetayozet
                    WHERE toplam_harcama > 0
                ''')
                customer_stats = cur.fetchall()
            except Exception as e:
                logger.error(f"Error reading CLV from musteridetayozet: {e}")
                from ..data_access import get_clv_data_optimized
                customer_stats = get_clv_data_optimized(
                    year=year, month=month, start_date=start_date, end_date=end_date,
                    customer_type=customer_type, approval_status=approval_status, region=region
                )
            finally:
                release_connection(conn)
        else:
            # Filtre var, asıl büyük sorguyu çalıştır (uzun yol)
            from ..data_access import get_clv_data_optimized
            customer_stats = get_clv_data_optimized(
                year=year, month=month, start_date=start_date, end_date=end_date,
                customer_type=customer_type, approval_status=approval_status, region=region
            )
    
    # PYTHON FALLBACK
    if not is_db or (is_db and customer_stats is None):
        data = get_datasource_data(ds)
        if not data: return None
        
        first_row = data[0]
        cols = detect_columns(list(first_row.keys()), ds.column_mapping)
        cid_col = cols.get('customer_id_col') or next((c for c in ['musteri_id', 'customer_id'] if c in first_row), 'musteri_id')
        amt_col = cols.get('revenue_col') or next((c for c in ['tutar', 'amount'] if c in first_row), 'tutar')
        dt_col = cols.get('date_col') or 'tarih'
        name_col = cols.get('customer_name_col') or next((c for c in ['ad', 'name', 'Müşteri Adı'] if c in first_row), None)
        
        keys_lower = {k.lower(): k for k in first_row.keys()}
        ctype_col = keys_lower.get('tip') or keys_lower.get('musteri_tipi')
        
        y_int = int(year) if year else None
        
        temp_stats = {}
        for row in data:
            if customer_type and ctype_col and str(row.get(ctype_col,'')).lower() != customer_type.lower(): continue
            
            cid = row.get(cid_col)
            if not cid: continue
            
            amt = parse_amount(row.get(amt_col))
            d_obj, r_y, _, _ = parse_date_fast(str(row.get(dt_col, '')))
            if y_int and r_y != y_int: continue
            
            fis_no = row.get('fis_no') or row.get('receipt_no') or row.get('id')
            
            if cid not in temp_stats:
                temp_stats[cid] = {
                    'cid': cid, 
                    'name': str(row.get(name_col, cid)) if name_col else str(cid), 
                    'total_value': 0.0, 
                    'receipts': set(), 
                    'first_date': d_obj, 
                    'last_date': d_obj
                }
            
            s = temp_stats[cid]
            s['total_value'] += amt
            if fis_no: s['receipts'].add(fis_no)
            if d_obj:
                if not s['first_date'] or d_obj < s['first_date']: s['first_date'] = d_obj
                if not s['last_date'] or d_obj > s['last_date']: s['last_date'] = d_obj
        
        for cid, stats in temp_stats.items():
            stats['order_count'] = len(stats.pop('receipts'))
        customer_stats = list(temp_stats.values())

    if not customer_stats: return None

    # Calculate Segments and Map
    clv_vals = sorted([c['total_value'] for c in customer_stats], reverse=True)
    count = len(clv_vals)
    top_val = clv_vals[0]
    
    p_th = clv_vals[int(count * 0.05)] if count > 20 else top_val * 0.8
    g_th = clv_vals[int(count * 0.15)] if count > 20 else top_val * 0.5
    s_th = clv_vals[int(count * 0.35)] if count > 20 else top_val * 0.25
    b_th = clv_vals[int(count * 0.60)] if count > 20 else top_val * 0.1
    
    segment_data = {'Platinum': [], 'Gold': [], 'Silver': [], 'Bronze': [], 'Basic': []}
    for c in customer_stats:
        v = c['total_value']
        if v >= p_th: segment_data['Platinum'].append(c)
        elif v >= g_th: segment_data['Gold'].append(c)
        elif v >= s_th: segment_data['Silver'].append(c)
        elif v >= b_th: segment_data['Bronze'].append(c)
        else: segment_data['Basic'].append(c)

    result = {
        'customer_stats': customer_stats,
        'segment_data': segment_data,
        'clv_vals': clv_vals,
        'thresholds': (p_th, g_th, s_th, b_th)
    }
    
    _clv_internal_cache[internal_key] = {'data': result, 'timestamp': time.time()}
    return result

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_clv_analysis(request, data_source_id):
    try:
        overall_start = time.time()
        
        # Check high-level cache first (formatting/summary is cached too)
        year = request.GET.get('year')
        month = request.GET.get('month')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        customer_type = request.GET.get('customer_type')
        approval_status = request.GET.get('approval_status')
        region = request.GET.get('region')
        filter_hash = f"{year}_{month}_{start_date}_{end_date}_{customer_type}_{approval_status}_{region}"
        cache_key = f"clv_sum_v3_{data_source_id}_{filter_hash}"
        
        cached = get_cached_data('clv', cache_key)
        if cached: return Response(cached)

        stats_data = _get_internal_stats(request, data_source_id)
        if not stats_data:
            return Response({'summary': {'averageCLV': 0, 'totalCLV': 0, 'customerCount': 0}, 'clvSegments': []})

        segment_data = stats_data['segment_data']
        clv_vals = stats_data['clv_vals']
        count = len(clv_vals)
        total_val = sum(clv_vals)
        avg_val = total_val / count
        top_val = clv_vals[0]
        
        # Additional summary metrics
        lifespans = []
        loyals = 0
        total_orders = 0
        for c in stats_data['customer_stats']:
            if c['order_count'] > 1: loyals += 1
            total_orders += c['order_count']
            if c['first_date'] and c['last_date']:
                try:
                    d1 = c['first_date'] if isinstance(c['first_date'], datetime) else datetime.strptime(str(c['first_date']).split(' ')[0], '%Y-%m-%d')
                    d2 = c['last_date'] if isinstance(c['last_date'], datetime) else datetime.strptime(str(c['last_date']).split(' ')[0], '%Y-%m-%d')
                    lifespans.append(max((d2 - d1).days, 1))
                except: pass

        avg_ls = sum(lifespans)/len(lifespans) if lifespans else 0
        avg_orders = total_orders / count
        avg_ord_val = avg_val / avg_orders if avg_orders > 0 else avg_val

        colors = {'Platinum': '#9333ea', 'Gold': '#f59e0b', 'Silver': '#6b7280', 'Bronze': '#cd7f32', 'Basic': '#94a3b8'}
        segments_res = []
        for name, custs in segment_data.items():
            if not custs: continue
            vals = [c['total_value'] for c in custs]
            segments_res.append({
                'segment': name, 'customers': len(custs), 
                'avgCLV': round(sum(vals)/len(vals), 2), 'totalValue': round(sum(vals), 2), 
                'color': colors[name]
            })

        result = {
            'summary': {
                'averageCLV': round(avg_val, 2), 'totalCLV': round(total_val, 2), 
                'customerCount': count, 'avgLifespan': round(avg_ls, 0), 
                'topCLV': round(top_val, 2), 'avgOrderValue': round(avg_ord_val, 2), 
                'avgOrderCount': round(avg_orders, 1)
            },
            'clvSegments': segments_res,
            'clvFactors': [
                {'factor': 'Ortalama Sipariş Değeri', 'weight': min(round(avg_ord_val / avg_val * 35), 45), 'color': '#6366f1'},
                {'factor': 'Alışveriş Sıklığı', 'weight': min(round(avg_orders * 10), 35), 'color': '#10b981'},
                {'factor': 'Müşteri Ömrü', 'weight': min(round(avg_ls / 365 * 25), 30), 'color': '#f59e0b'},
                {'factor': 'Sadakat', 'weight': min(round(loyals / count * 20), 25), 'color': '#ec4899'}
            ]
        }
        
        set_cached_data('clv', cache_key, result)
        logger.info(f"CLV Profile - Overall: {time.time() - overall_start:.4f}s")
        return Response(result)

    except Exception as e:
        logger.error(f"CLV Global Error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_clv_customer_details(request, data_source_id):
    """Segment bazlı müşteri detayı"""
    try:
        segment = request.GET.get('segment')
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        sort_by = request.GET.get('sort_by', 'totalValue')
        order = request.GET.get('order', 'desc') # 'asc' or 'desc'
        
        stats_data = _get_internal_stats(request, data_source_id)
        if not stats_data or segment not in stats_data['segment_data']:
            return Response({'customers': [], 'total': 0})
            
        customers = stats_data['segment_data'][segment]
        
        # Pre-process for sorting if needed
        # Lifespan and last_date are the tricky ones
        processed_list = []
        for c in customers:
            ls = 1
            if c['first_date'] and c['last_date']:
                try:
                    d1 = c['first_date'] if isinstance(c['first_date'], datetime) else datetime.strptime(str(c['first_date']).split(' ')[0], '%Y-%m-%d')
                    d2 = c['last_date'] if isinstance(c['last_date'], datetime) else datetime.strptime(str(c['last_date']).split(' ')[0], '%Y-%m-%d')
                    ls = max((d2 - d1).days, 1)
                except: pass
            
            last_date_str = c['last_date']
            if last_date_str and not isinstance(last_date_str, str):
                last_date_str = last_date_str.strftime('%Y-%m-%d')
            elif last_date_str and ' ' in last_date_str:
                last_date_str = last_date_str.split(' ')[0]

            first_date_str = c['first_date']
            if first_date_str and not isinstance(first_date_str, str):
                first_date_str = first_date_str.strftime('%Y-%m-%d')
            elif first_date_str and ' ' in first_date_str:
                first_date_str = first_date_str.split(' ')[0]

            frequency = round(ls / c['order_count'], 1) if c['order_count'] > 0 else 0

            processed_list.append({
                'id': c['cid'],
                'name': (c['name'] if 'name' in c.keys() else str(c['id'])) if c['id'] else 'Bilinmeyen',
                'totalValue': round(c['total_value'], 2),
                'orderCount': c['order_count'],
                'frequency': frequency,
                'firstPurchaseDate': first_date_str or '-',
                'lastPurchaseDate': last_date_str or '-',
                'raw_first_date': c['first_date'],
                'raw_last_date': c['last_date'],
                'lifespanDays': int(ls)
            })

        # Sorting logic
        reverse = (order == 'desc')
        if sort_by == 'name':
            processed_list.sort(key=lambda x: str(x['name']).lower(), reverse=reverse)
        elif sort_by == 'totalValue':
            processed_list.sort(key=lambda x: x['totalValue'], reverse=reverse)
        elif sort_by == 'orderCount':
            processed_list.sort(key=lambda x: x['orderCount'], reverse=reverse)
        elif sort_by == 'frequency':
            processed_list.sort(key=lambda x: x['frequency'], reverse=reverse)
        elif sort_by == 'firstPurchaseDate':
            processed_list.sort(key=lambda x: str(x['raw_first_date'] or ''), reverse=reverse)
        elif sort_by == 'lastPurchaseDate':
            processed_list.sort(key=lambda x: str(x['raw_last_date'] or ''), reverse=reverse)
        elif sort_by == 'lifespanDays':
            processed_list.sort(key=lambda x: x['lifespanDays'], reverse=reverse)
        else:
            processed_list.sort(key=lambda x: x['totalValue'], reverse=reverse)
        
        total = len(processed_list)
        start = (page - 1) * limit
        end = start + limit
        
        paged_customers = processed_list[start:end]
        # Clean internal raw fields
        for pc in paged_customers:
            if 'raw_last_date' in pc: del pc['raw_last_date']
            if 'raw_first_date' in pc: del pc['raw_first_date']
            
        return Response({
            'customers': paged_customers,
            'total': total,
            'page': page,
            'pageSize': limit
        })
    except Exception as e:
        logger.error(f"CLV Details Error: {e}")
        return Response({'error': str(e)}, status=500)
