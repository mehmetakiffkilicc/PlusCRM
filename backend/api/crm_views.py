"""
CRM API Views

Server-side pagination, lazy loading ve on-demand veri yükleme
destekleyen CRM API endpoint'leri.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.permissions import AllowAny

import sys
import os

# database modülünü import et
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from database import DatabaseManager, PaginationParams, SortDirection
    from database.manager import get_db_manager
    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    import_error = str(e)

logger = logging.getLogger(__name__)


class CRMBaseView(APIView):
    """CRM API base view."""
    # Uses default IsAuthenticated from settings

    def get_db(self):
        """Veritabanı bağlantısı döndürür."""
        if not DB_AVAILABLE:
            raise Exception(f"Database module not available: {import_error}")
        return get_db_manager()
    
    def get_pagination_params(self, request) -> dict:
        """Request'ten sayfalama parametrelerini çıkarır."""
        return {
            'page': int(request.query_params.get('page', 1)),
            'page_size': int(request.query_params.get('pageSize', request.query_params.get('page_size', 50))),
            'search': request.query_params.get('search', request.query_params.get('q')),
            'sort_by': request.query_params.get('sortBy', request.query_params.get('sort_by')),
            'sort_dir': request.query_params.get('sortDir', request.query_params.get('sort_dir', 'ASC')),
        }


# ==================== CUSTOMERS ====================

class CustomerListView(CRMBaseView):
    """
    Sayfalanmış müşteri listesi.
    
    GET /api/crm/customers/
    
    Query Parameters:
        - page: Sayfa numarası (default: 1)
        - pageSize: Sayfa boyutu (default: 50, max: 500)
        - search: Arama metni
        - sortBy: Sıralama sütunu
        - sortDir: Sıralama yönü (ASC/DESC)
    
    Response:
        {
            "data": [...],
            "pagination": {
                "totalCount": 200000,
                "page": 1,
                "pageSize": 50,
                "totalPages": 4000,
                "hasNext": true,
                "hasPrevious": false
            }
        }
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            params = self.get_pagination_params(request)
            
            result = db.get_customers(
                page=params['page'],
                page_size=params['page_size'],
                search=params['search'],
                sort_by=params['sort_by'],
                sort_dir=params['sort_dir'],
            )
            
            return Response(result, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CustomerListView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class CustomerDetailView(CRMBaseView):
    """
    Müşteri detayları (Lazy Loading).
    
    GET /api/crm/customers/<customer_code>/
    
    Response:
        {
            "customer": {...},
            "salesSummary": {
                "summary": {...},
                "recentSales": [...]
            }
        }
    """
    
    def get(self, request, customer_code):
        try:
            db = self.get_db()
            
            # Müşteri detayları
            customer = db.get_customer_detail(customer_code)
            if not customer:
                return Response(
                    {'error': 'Müşteri bulunamadı'},
                    status=HTTP_404_NOT_FOUND
                )
            
            # Satış özeti (on-demand)
            include_sales = request.query_params.get('includeSales', 'true').lower() == 'true'
            sales_summary = None
            if include_sales:
                sales_summary = db.get_customer_sales_summary(customer_code)
            
            return Response({
                'customer': customer,
                'salesSummary': sales_summary,
            }, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CustomerDetailView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class CustomerSalesView(CRMBaseView):
    """
    Müşteri satış geçmişi (Paginated).
    
    GET /api/crm/customers/<customer_code>/sales/
    
    Query Parameters:
        - page: Sayfa numarası
        - pageSize: Sayfa boyutu
    """
    
    def get(self, request, customer_code):
        try:
            db = self.get_db()
            params = self.get_pagination_params(request)
            
            result = db.get_customer_sales(
                customer_code=customer_code,
                page=params['page'],
                page_size=params['page_size'],
            )
            
            return Response(result, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CustomerSalesView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class CustomerSearchView(CRMBaseView):
    """
    Hızlı müşteri araması (Autocomplete).
    
    GET /api/crm/customers/search/
    
    Query Parameters:
        - q: Arama metni
        - limit: Maksimum sonuç sayısı (default: 20)
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            query = request.query_params.get('q', '')
            limit = int(request.query_params.get('limit', 20))
            
            if len(query) < 2:
                return Response({'results': []}, status=HTTP_200_OK)
            
            results = db.search_customers(query, limit)
            
            return Response({'results': results}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CustomerSearchView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class CustomerSegmentsView(CRMBaseView):
    """
    Müşteri segmentleri.
    
    GET /api/crm/customers/segments/
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            segments = db.get_customer_segments()
            return Response({'segments': segments}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"CustomerSegmentsView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


# ==================== SALES ====================

class SalesListView(CRMBaseView):
    """
    Sayfalanmış satış listesi.
    
    GET /api/crm/sales/
    
    Query Parameters:
        - page, pageSize: Sayfalama
        - search: Arama
        - startDate, endDate: Tarih filtresi (YYYY-MM-DD)
        - store: Mağaza filtresi
        - category: Kategori filtresi
        - brand: Marka filtresi
        - sortBy, sortDir: Sıralama
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            params = self.get_pagination_params(request)
            
            result = db.get_sales(
                page=params['page'],
                page_size=params['page_size'],
                search=params['search'],
                start_date=request.query_params.get('startDate', request.query_params.get('start_date')),
                end_date=request.query_params.get('endDate', request.query_params.get('end_date')),
                store=request.query_params.get('store'),
                category=request.query_params.get('category'),
                brand=request.query_params.get('brand'),
                sort_by=params['sort_by'] or 'ZAMAN',
                sort_dir=params['sort_dir'],
            )
            
            return Response(result, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"SalesListView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class SalesSummaryView(CRMBaseView):
    """
    Satış özeti (günlük/haftalık/aylık).
    
    GET /api/crm/sales/summary/
    
    Query Parameters:
        - startDate: Başlangıç tarihi (zorunlu)
        - endDate: Bitiş tarihi (zorunlu)
        - groupBy: 'day', 'week', 'month' (default: 'day')
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            start_date = request.query_params.get('startDate', request.query_params.get('start_date'))
            end_date = request.query_params.get('endDate', request.query_params.get('end_date'))
            group_by = request.query_params.get('groupBy', request.query_params.get('group_by', 'day'))
            
            if not start_date or not end_date:
                return Response(
                    {'error': 'startDate ve endDate parametreleri zorunludur'},
                    status=HTTP_400_BAD_REQUEST
                )
            
            result = db.get_sales_summary(start_date, end_date, group_by)
            
            return Response({'data': result}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"SalesSummaryView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class TopProductsView(CRMBaseView):
    """
    En çok satan ürünler.
    
    GET /api/crm/sales/top-products/
    
    Query Parameters:
        - limit: Maksimum ürün sayısı (default: 20)
        - startDate, endDate: Tarih filtresi
        - by: 'revenue' veya 'quantity' (default: 'revenue')
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            limit = int(request.query_params.get('limit', 20))
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            by = request.query_params.get('by', 'revenue')
            
            result = db.get_top_products(limit, start_date, end_date, by)
            
            return Response({'data': result}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"TopProductsView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class TopCategoriesView(CRMBaseView):
    """
    En çok satan kategoriler.
    
    GET /api/crm/sales/top-categories/
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            limit = int(request.query_params.get('limit', 20))
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            
            result = db.get_top_categories(limit, start_date, end_date)
            
            return Response({'data': result}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"TopCategoriesView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class TopBrandsView(CRMBaseView):
    """
    En çok satan markalar.
    
    GET /api/crm/sales/top-brands/
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            limit = int(request.query_params.get('limit', 20))
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            
            result = db.get_top_brands(limit, start_date, end_date)
            
            return Response({'data': result}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"TopBrandsView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class StoreSummaryView(CRMBaseView):
    """
    Mağaza bazlı özet.
    
    GET /api/crm/sales/stores/
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            
            result = db.get_store_summary(start_date, end_date)
            
            return Response({'data': result}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"StoreSummaryView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class OverallStatsView(CRMBaseView):
    """
    Genel istatistikler.
    
    GET /api/crm/stats/
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            start_date = request.query_params.get('startDate')
            end_date = request.query_params.get('endDate')
            
            result = db.get_overall_stats(start_date, end_date)
            
            return Response(result, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"OverallStatsView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class FilterOptionsView(CRMBaseView):
    """
    Filtre seçenekleri.
    
    GET /api/crm/filters/
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            result = db.get_filter_options()
            return Response(result, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"FilterOptionsView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class ProductSearchView(CRMBaseView):
    """
    Hızlı ürün araması.
    
    GET /api/crm/products/search/
    
    Query Parameters:
        - q: Arama metni
        - limit: Maksimum sonuç sayısı
    """
    
    def get(self, request):
        try:
            db = self.get_db()
            
            query = request.query_params.get('q', '')
            limit = int(request.query_params.get('limit', 20))
            
            if len(query) < 2:
                return Response({'results': []}, status=HTTP_200_OK)
            
            results = db.search_products(query, limit)
            
            return Response({'results': results}, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"ProductSearchView error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)


class ConnectionTestView(CRMBaseView):
    """
    Veritabanı bağlantı testi.
    
    GET /api/crm/test-connection/
    """
    
    def get(self, request):
        try:
            if not DB_AVAILABLE:
                return Response({
                    'connected': False,
                    'error': f'Database module not available: {import_error}'
                }, status=HTTP_200_OK)
            
            db = self.get_db()
            connected = db.test_connection()
            stats = db.get_stats() if connected else {}
            
            return Response({
                'connected': connected,
                'stats': stats,
            }, status=HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"ConnectionTestView error: {e}")
            return Response({
                'connected': False,
                'error': str(e)
            }, status=HTTP_200_OK)
