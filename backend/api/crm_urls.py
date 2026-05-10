"""
CRM API URL Configuration

Server-side pagination destekleyen CRM endpoint'leri.
"""

from django.urls import path
from .crm_views import (
    # Customers
    CustomerListView,
    CustomerDetailView,
    CustomerSalesView,
    CustomerSearchView,
    CustomerSegmentsView,
    
    # Sales
    SalesListView,
    SalesSummaryView,
    TopProductsView,
    TopCategoriesView,
    TopBrandsView,
    StoreSummaryView,
    
    # General
    OverallStatsView,
    FilterOptionsView,
    ProductSearchView,
    ConnectionTestView,
)

urlpatterns = [
    # ==================== CUSTOMERS ====================
    # Sayfalanmış müşteri listesi
    path('customers/', CustomerListView.as_view(), name='crm-customer-list'),
    
    # Hızlı müşteri araması (autocomplete)
    path('customers/search/', CustomerSearchView.as_view(), name='crm-customer-search'),
    
    # Müşteri segmentleri
    path('customers/segments/', CustomerSegmentsView.as_view(), name='crm-customer-segments'),
    
    # Müşteri detayı (lazy loading)
    path('customers/<str:customer_code>/', CustomerDetailView.as_view(), name='crm-customer-detail'),
    
    # Müşteri satış geçmişi (paginated)
    path('customers/<str:customer_code>/sales/', CustomerSalesView.as_view(), name='crm-customer-sales'),
    
    # ==================== SALES ====================
    # Sayfalanmış satış listesi
    path('sales/', SalesListView.as_view(), name='crm-sales-list'),
    
    # Satış özeti (günlük/haftalık/aylık)
    path('sales/summary/', SalesSummaryView.as_view(), name='crm-sales-summary'),
    
    # En çok satan ürünler
    path('sales/top-products/', TopProductsView.as_view(), name='crm-top-products'),
    
    # En çok satan kategoriler
    path('sales/top-categories/', TopCategoriesView.as_view(), name='crm-top-categories'),
    
    # En çok satan markalar
    path('sales/top-brands/', TopBrandsView.as_view(), name='crm-top-brands'),
    
    # Mağaza bazlı özet
    path('sales/stores/', StoreSummaryView.as_view(), name='crm-store-summary'),
    
    # ==================== GENERAL ====================
    # Genel istatistikler
    path('stats/', OverallStatsView.as_view(), name='crm-stats'),
    
    # Filtre seçenekleri
    path('filters/', FilterOptionsView.as_view(), name='crm-filters'),
    
    # Ürün araması
    path('products/search/', ProductSearchView.as_view(), name='crm-product-search'),
    
    # Bağlantı testi
    path('test-connection/', ConnectionTestView.as_view(), name='crm-test-connection'),
]
