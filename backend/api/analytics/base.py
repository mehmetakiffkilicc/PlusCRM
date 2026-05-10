"""
Shared utilities, cache logic, and helpers for analytics views.
"""
from django.contrib.auth.models import User
from datetime import datetime
from ..models import DataSource
from ..auth import verify_jwt_token
from ..data_access import get_sales_data
from .. import db_engine
import time
import logging

logger = logging.getLogger(__name__)

# Global cache for CRM analytics - improves page load speed
_crm_cache = {
    'rfm': {},
    'churn': {},
    'clv': {},
    'segmentation': {},
    'campaigns': {},
    'new_customers': {},
    'customer_info': {}
}
_cache_timeout = 300  # 5 dakika cache süresi

# Filter-keyed caches (avoid cache pollution while speeding up filtered requests)
_brand_report_cache = {}
_brand_report_cache_timeout = 600  # 10 dk — daha az sorgu, aynı hız
_brand_report_cache_max_entries = 50  # 300 → 50: RAM tasarrufu

_brand_filters_cache = {}
_brand_filters_cache_timeout = 3600  # 1 saat - filtreler nadiren değişir
_brand_filters_cache_max_entries = 30  # 100 → 30

_segmentation_filter_cache = {}
_segmentation_filter_cache_timeout = 600
_segmentation_filter_cache_max_entries = 50  # 300 → 50

_new_customers_filter_cache = {}
_new_customers_filter_cache_timeout = 600
_new_customers_filter_cache_max_entries = 50  # 300 → 50

# Cache for datasource analytics endpoint (filter-keyed). Keeps drilldowns fast without overwriting baseline.
_datasource_analytics_cache = {}
_datasource_analytics_cache_timeout = 600  # 120s → 600s: 5x daha az yeniden sorgu
_datasource_analytics_cache_max_entries = 60  # 250 → 60: RAM baskısını kır

# Cache for Dashboard Full Summary endpoint - filter-keyed
_dashboard_full_summary_cache = {}
_dashboard_full_summary_cache_timeout = 120  # 2 dakika - dashboard verisi gerçek zamanlı değil
_dashboard_full_summary_cache_max_entries = 50


def get_datasource_data(data_source):
    """Helper to switch between JSON field and Local DB"""
    # FIX: CSV/JSON dosyaları için önce type kontrolü yap
    # CSV/JSON dosyaları için direkt data field'ından döndür
    data_type = getattr(data_source, 'type', '')

    # CSV veya JSON dosyası ise SQLite cache'e bakma, direkt döndür
    if data_type in ('csv', 'json'):
        return data_source.data

    # Database tipi ise veya adı SQL Server kaynaklıysa yerel SQLite cache'den oku
    # "Silent Worker" optimizasyonu için veriyi sales_cache.db'den çekiyoruz
    if data_type == 'database' or \
       'sal' in getattr(data_source, 'name', '').lower() or \
       'sat' in getattr(data_source, 'name', '').lower():

        # Önce sync_worker veritabanını kontrol et
        local_data = get_sales_data()
        if local_data:
            return local_data

    # Fallback: DataSource modelindeki data field'ını döndür
    return data_source.data


def _build_datasource_analytics_cache_key(pk, user_id, selected_segments, selected_categories, selected_brands,
                                         selected_year, selected_month, start_date_str, end_date_str):
    """Build cache key for datasource analytics"""
    def norm_list(values):
        return tuple(sorted([str(v).strip().rstrip('/') for v in (values or []) if str(v).strip()]))

    return (
        int(pk),
        int(user_id),
        norm_list(selected_segments),
        norm_list(selected_categories),
        norm_list(selected_brands),
        int(selected_year) if selected_year else None,
        int(selected_month) if selected_month else None,
        str(start_date_str or ''),
        str(end_date_str or ''),
    )


def _get_cached_datasource_analytics(cache_key):
    """Get cached datasource analytics data"""
    cached = _datasource_analytics_cache.get(cache_key)
    if not cached:
        return None
    if time.time() - cached['timestamp'] < _datasource_analytics_cache_timeout:
        return cached['data']
    try:
        del _datasource_analytics_cache[cache_key]
    except KeyError:
        pass
    return None


def _set_cached_datasource_analytics(cache_key, data):
    """Set cached datasource analytics data"""
    _datasource_analytics_cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }
    # Evict ~25% oldest entries when limit reached (more aggressive = lower RAM ceiling)
    if len(_datasource_analytics_cache) > _datasource_analytics_cache_max_entries:
        try:
            oldest = sorted(_datasource_analytics_cache.items(), key=lambda kv: kv[1].get('timestamp', 0))
            for k, _ in oldest[:max(1, _datasource_analytics_cache_max_entries // 4)]:
                _datasource_analytics_cache.pop(k, None)
        except Exception:
            pass


def _build_dashboard_cache_key(start_date, end_date, year, month, categories, brands, customer_type, approval_status, region):
    key = (
        str(start_date or ''),
        str(end_date or ''),
        str(year or ''),
        str(month or ''),
        tuple(sorted([c for c in (categories or []) if c])),
        tuple(sorted([b for b in (brands or []) if b])),
        str(customer_type or ''),
        str(approval_status or ''),
        str(region or ''),
    )
    return key

def _get_cached_dashboard(data_key):
    cached = _dashboard_full_summary_cache.get(data_key)
    if not cached:
        return None
    if time.time() - cached['timestamp'] < _dashboard_full_summary_cache_timeout:
        return cached['data']
    try:
        del _dashboard_full_summary_cache[data_key]
    except KeyError:
        pass
    return None

def _set_cached_dashboard(data_key, data):
    _dashboard_full_summary_cache[data_key] = {
        'data': data,
        'timestamp': time.time()
    }
    if len(_dashboard_full_summary_cache) > _dashboard_full_summary_cache_max_entries:
        try:
            oldest = sorted(_dashboard_full_summary_cache.items(), key=lambda kv: kv[1].get('timestamp', 0))
            for k, _ in oldest[:max(1, _dashboard_full_summary_cache_max_entries // 4)]:
                _dashboard_full_summary_cache.pop(k, None)
        except Exception:
            pass


def parse_date_fast(date_str):
    """Tarih string'ini hızlıca parse et - cache friendly"""
    if not date_str:
        return None, None, None, None
    date_str = str(date_str).strip()

    try:
        date_part = date_str.split(' ')[0].split('T')[0]

        if '.' in date_part:
            parts = date_part.split('.')
            if len(parts) == 3:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2])
                return datetime(year, month, day), year, month, day
        elif '-' in date_part:
            parts = date_part.split('-')
            if len(parts) == 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return datetime(year, month, day), year, month, day
    except (ValueError, IndexError, TypeError, AttributeError) as e:
        # Date parsing failed - invalid format or values
        pass
    return None, None, None, None


def filter_data_by_date(data, request, date_col_name=None):
    """
    Veriyi tarih parametrelerine göre filtreler.
    request.GET'ten year, month, start_date, end_date parametrelerini alır.
    Optimize edilmiş versiyon - tek geçişte format tespiti ve filtreleme
    """
    year = request.GET.get('year')
    month = request.GET.get('month')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Eğer hiçbir filtre yoksa, tüm veriyi döndür
    if not any([year, month, start_date_str, end_date_str]):
        return data

    if not data:
        return data

    # Tarih sütununu bul
    date_col = date_col_name
    if not date_col:
        for col in ['Tarih', 'tarih', 'Siparis_Tarihi', 'siparis_tarihi', 'TARİH', 'date', 'Date', 'İşlem_Tarihi']:
            if col in data[0].keys():
                date_col = col
                break

    if not date_col:
        return data  # Tarih sütunu bulunamadı, tüm veriyi döndür

    # Filtreleri integer'a çevir - bir kere yap
    year_int = int(year) if year else None
    month_int = int(month) if month else None
    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse start_date '{start_date_str}': {e}")
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse end_date '{end_date_str}': {e}")
            pass

    # Tarih formatını ilk satırdan tespit et
    detected_format = None
    formats = ['%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']
    sample_date = str(data[0].get(date_col, '')).split()[0] if data[0].get(date_col) else ''

    for fmt in formats:
        try:
            datetime.strptime(sample_date, fmt)
            detected_format = fmt
            break
        except (ValueError, TypeError):
            continue

    if not detected_format:
        return data

    # Hızlı filtreleme - parse_date_fast kullan
    filtered = []
    for row in data:
        date_str = str(row.get(date_col, ''))
        if not date_str:
            continue

        date_obj, row_year, row_month, _ = parse_date_fast(date_str)
        if not date_obj:
            continue

        # Filtre kontrolleri
        if year_int and row_year != year_int:
            continue
        if month_int and row_month != month_int:
            continue
        if start_date and date_obj < start_date:
            continue
        if end_date and date_obj > end_date:
            continue

        filtered.append(row)

    return filtered if filtered else data  # Filtreleme sonucu boşsa tüm veriyi döndür


def get_cached_data(cache_type, data_source_id):
    """Cache'den veri al"""
    cache_key = str(data_source_id)
    if cache_key in _crm_cache[cache_type]:
        cached = _crm_cache[cache_type][cache_key]
        if time.time() - cached['timestamp'] < _cache_timeout:
            return cached['data']
    return None


def set_cached_data(cache_type, data_source_id, data):
    """Cache'e veri kaydet"""
    cache_key = str(data_source_id)
    _crm_cache[cache_type][cache_key] = {
        'data': data,
        'timestamp': time.time()
    }


def _build_filter_cache_key(data_source_id, user_id, request):
    """Build cache key for filtered queries"""
    year = request.GET.get('year')
    month = request.GET.get('month')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # New filters (Essential for Brand Report)
    segment = request.GET.get('segment')
    customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
    approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')
    region = request.GET.get('region')
    brand_search = request.GET.get('brand_search')
    categories = tuple(sorted(request.GET.getlist('category') or request.GET.getlist('categories[]') or request.GET.getlist('category[]')))
    page = request.GET.get('page', '1')
    limit = request.GET.get('limit', '10')
    
    return (
        int(data_source_id),
        int(user_id) if user_id is not None else None,
        int(year) if year else None,
        int(month) if month else None,
        str(start_date_str or ''),
        str(end_date_str or ''),
        str(segment or ''),
        str(customer_type or ''),
        str(approval_status or ''),
        str(region or ''),
        str(brand_search or ''),
        categories,
        str(page),
        str(limit)
    )


def _get_ttl_cache(cache, key, timeout_seconds):
    """Get data from TTL cache"""
    cached = cache.get(key)
    if not cached:
        return None
    if time.time() - cached.get('timestamp', 0) < timeout_seconds:
        return cached.get('data')
    cache.pop(key, None)
    return None


def _set_ttl_cache(cache, key, data, max_entries):
    """Set data in TTL cache with eviction"""
    cache[key] = {'data': data, 'timestamp': time.time()}
    if len(cache) > max_entries:
        try:
            oldest = sorted(cache.items(), key=lambda kv: kv[1].get('timestamp', 0))
            for k, _ in oldest[:max(1, max_entries // 4)]:  # 25% eviction
                cache.pop(k, None)
        except Exception:
            pass


def _read_cache(cursor, tablo: str):
    """Cache tablosundan JSON veriyi oku. Tablo yoksa veya boşsa None döner."""
    try:
        cursor.execute(
            f"SELECT veri, hesaplama_tarihi FROM {tablo} ORDER BY hesaplama_tarihi DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            import json
            veri = db_engine.val(row, 'veri')
            tarih = db_engine.val(row, 'hesaplama_tarihi')
            if isinstance(veri, str):
                veri = json.loads(veri)
            if veri is not None:
                veri['_cache_tarihi'] = str(tarih)[:19] if tarih else None
            return veri
    except Exception:
        pass
    return None


def get_user_from_request(request):
    """Extract and verify JWT token from request header. Also respects already authenticated users for internal calls."""
    # Debug
    # print(f"DEBUG AUTH: hasattr(user)={hasattr(request, 'user')} | user={getattr(request, 'user', 'N/A')} | authenticated={getattr(request.user, 'is_authenticated', 'N/A') if hasattr(request, 'user') else 'N/A'}")
    
    # Internal veya middleware tarafından zaten set edilmiş user'ı destekle
    if hasattr(request, 'user') and request.user and getattr(request.user, 'is_authenticated', False):
        return request.user

    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]
    payload = verify_jwt_token(token)

    if not payload:
        return None

    try:
        user = User.objects.get(id=payload['user_id'])
        return user
    except User.DoesNotExist:
        return None


def validate_data_source(user, data_source_id) -> bool:
    """Kullanıcının bu data source'a erişim izni olup olmadığını doğrula."""
    try:
        return DataSource.objects.filter(id=data_source_id, user=user).exists()
    except Exception:
        return False


def detect_columns(columns, column_mapping=None):
    """Tüm kolon tespitlerini tek fonksiyonda yap. column_mapping varsa önce onu kullan."""
    result = {}

    # Eğer column_mapping varsa, önce onları kullan
    if column_mapping:
        for key in ['revenue_col', 'date_col', 'product_col', 'customer_id_col', 'receipt_id_col',
                    'quantity_col', 'unit_price_col', 'segment_col', 'brand_col', 'ust_kategori_col',
                    'category_col', 'alt_kategori_1_col', 'alt_kategori_2_col', 'hour_col',
                    'store_col', 'customer_name_col', 'stock_code_col', 'document_total_col']:
            result[key] = column_mapping.get(key)
    else:
        # Otomatik tespit için boş başlat
        for key in ['revenue_col', 'date_col', 'product_col', 'customer_id_col', 'receipt_id_col',
                    'quantity_col', 'unit_price_col', 'segment_col', 'brand_col', 'ust_kategori_col',
                    'category_col', 'alt_kategori_1_col', 'alt_kategori_2_col', 'hour_col',
                    'store_col', 'customer_name_col', 'stock_code_col', 'document_total_col']:
            result[key] = None

    # === SQLITE CACHE MAPPING ENFORCEMENT ===
    # Eğer kolonlar arasında 'urun_ad' varsa, bu bizim satislar+urunler join'imizdir.
    if 'urun_ad' in columns:
        return {
            'revenue_col': 'tutar', 'date_col': 'tarih', 'product_col': 'urun_ad',
            'customer_id_col': 'musteri_id', 'receipt_id_col': 'fis_no',
            'quantity_col': 'miktar', 'unit_price_col': None, 'segment_col': None,
            'brand_col': 'marka', 'ust_kategori_col': None, 'category_col': 'kategori',
            'alt_kategori_1_col': None, 'alt_kategori_2_col': None, 'hour_col': 'saat',
            'store_col': 'magaza_ad', 'customer_name_col': None, 'stock_code_col': 'urun_id',
            'document_total_col': 'tutar'
        }

    # === SQL SERVER MAPPING ENFORCEMENT ===
    # Eğer kolonlar arasında 'PosDocumentId' varsa, bu SQL Server'dan gelen veridir.
    if 'PosDocumentId' in columns:
        return {
            'revenue_col': 'Satış Tutarı', 'date_col': 'TARİH', 'product_col': 'stkAd',
            'customer_id_col': 'Müşteri Kodu', 'receipt_id_col': 'PosDocumentId',
            'quantity_col': 'Miktar', 'unit_price_col': None, 'segment_col': None,
            'brand_col': 'MarkaAdi', 'ust_kategori_col': 'ktgrGrupAd', 'category_col': 'Ana_Kategori',
            'alt_kategori_1_col': 'Alt_Kategori1', 'alt_kategori_2_col': 'Alt_Kategori2',
            'hour_col': 'SAAT', 'store_col': 'Magaza', 'customer_name_col': 'Musteri',
            'stock_code_col': 'stkKod', 'document_total_col': 'BelgeToplami'
        }

    # === GENEL TESPİT (CSV/EXCEL) ===
    # Standart isimlendirmeler için tek tek tanımlama
    cols_hash = {c.lower(): c for c in columns}
    
    mapping = {k: None for k in ['revenue_col', 'date_col', 'product_col', 'customer_id_col', 'receipt_id_col',
                                'quantity_col', 'brand_col', 'category_col', 'store_col']}
    
    # Revenue
    for opt in ['satış tutarı', 'tutar', 'amount', 'ciro', 'revenue', 'toplam', 'net tutar']:
        if opt in cols_hash: 
            mapping['revenue_col'] = cols_hash[opt]
            break
            
    # Date
    for opt in ['tarih', 'date', 'siparis_tarihi', 'işlem tarihi']:
        if opt in cols_hash:
            mapping['date_col'] = cols_hash[opt]
            break
            
    # Product
    for opt in ['stkad', 'ürün', 'ürün adı', 'product', 'stok', 'name', 'stk_ad', 'urun_ad']:
        if opt in cols_hash:
            mapping['product_col'] = cols_hash[opt]
            break
            
    # Brand
    for opt in ['markaadi', 'marka', 'brand']:
        if opt in cols_hash:
            mapping['brand_col'] = cols_hash[opt]
            break

    # Category
    for opt in ['ana_kategori', 'kategori', 'category', 'grup']:
        if opt in cols_hash:
            mapping['category_col'] = cols_hash[opt]
            break

    return mapping


def categorize_to_parent(category_name):
    """Ana kategoriden üst kategori belirle - CSV içeriğine özel"""
    if not category_name:
        return 'Diğer'

    cat = str(category_name).strip()

    # Tam eşleşme ile kontrol (CSV'deki Ana_Kategori değerlerine göre)

    # Bebek & Çocuk
    if cat == 'Bebek Bakım Ürünleri':
        return 'Bebek & Çocuk'

    # Gıda & İçecek
    if cat in [
        'Atıştırmalık & Bisküvi',
        'Baharat & Tuz',
        'Bakliyat, Makarna',
        'Çay & Kahve & Şeker',
        'Çorba & Bulyon & Harç',
        'Dondurma Ürünleri',
        'Dondurulmuş Ürünler',
        'Hazır Toz Grup',
        'İçecek',
        'İşlenmiş Et Ürünleri',
        'Kahvaltılık Ürünler & Süt',
        'Konserve & Salça & Hazır Yemek',
        'Sıvı Yağlar & Soslar',
        'Şarküteri & Sütlük'
    ]:
        return 'Gıda & İçecek'

    # Temizlik & Kağıt
    if cat == 'Temizlik & Kağıt Ürünler':
        return 'Temizlik & Kağıt'

    # Kozmetik & Kişisel Bakım
    if cat == 'Kozmetik & Kişisel Bakım':
        return 'Kozmetik & Kişisel Bakım'

    # Ev & Pet
    if cat == 'Ev & Pet':
        return 'Ev & Pet'

    return 'Diğer'


# Export cache dictionaries for views that need direct access
__all__ = [
    'get_datasource_data',
    'parse_date_fast',
    'filter_data_by_date',
    'get_cached_data',
    'set_cached_data',
    'get_user_from_request',
    'detect_columns',
    'categorize_to_parent',
    '_build_datasource_analytics_cache_key',
    '_get_cached_datasource_analytics',
    '_set_cached_datasource_analytics',
    '_build_filter_cache_key',
    '_get_ttl_cache',
    '_set_ttl_cache',
    '_brand_report_cache',
    '_brand_report_cache_timeout',
    '_brand_report_cache_max_entries',
    '_brand_filters_cache',
    '_brand_filters_cache_timeout',
    '_brand_filters_cache_max_entries',
    '_segmentation_filter_cache',
    '_segmentation_filter_cache_timeout',
    '_segmentation_filter_cache_max_entries',
    '_new_customers_filter_cache',
    '_new_customers_filter_cache_timeout',
    '_new_customers_filter_cache_max_entries',
]
