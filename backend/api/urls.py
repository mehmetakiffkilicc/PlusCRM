from django.urls import path
from django.http import JsonResponse
from rest_framework.response import Response
from . import db_engine
from .views import (
    RegisterView, LoginView, ProfileView,
    DataSourceListView, DataSourceDetailView,
    DashboardListView, DashboardDetailView,
    WidgetCreateView, WidgetDeleteView,
    QueryView, SyncStatusView
)
from .views.datasource_views import SystemStatusView, PlatformStatusView
from .views.system_views import get_system_logs, clear_system_logs, rebuild_kpi_cache
from .views.settings_views import SettingsView


from .analytics import (
    get_data_source_analytics,
    get_product_analytics,
    get_rfm_analysis,
    get_churn_analysis,
    get_clv_analysis,
    get_clv_customer_details,
    get_brand_report,
    get_brand_detail,
    get_brand_suggestions,
    get_segmentation_analysis,
    get_segment_detailed_analysis,
    get_beklenen_musteriler,
    search_products,
    get_product_portal,
    get_campaigns_analysis,
    get_new_customers_analysis_backend,
    get_customer_info_analysis,
    get_category_report_details, handle_category_tags, get_category_tree, export_category_report_excel,
    get_kohort_analizi, export_cohort_analysis_excel, get_urun_birliktelik, get_marka_sadakati,
    export_brand_loyalty_excel,
    get_customer_list,
    get_customer_detail,
    musteri_birlestir,
    get_musteri_etiket_ozeti,
    get_musteri_zaman_cizelgesi,
    get_segment_gecis_matrisi,
    get_kategori_terk_listesi,
    get_kategori_terk_by_kategori,
    get_enflasyon_dayaniklilik,
    get_rakip_riski,
    get_campaign_recommendations,
    get_campaign_counts,
    get_campaign_filter_counts,
    get_campaign_source_categories,
    update_recommendation_status,
    bulk_update_recommendation_status,
    get_ai_campaign_summary,
    get_category_hierarchy,
    get_category_top_products,
    get_kategori_yoneticileri,
    get_brands,
    regenerate_campaigns,
    enrich_urun_fiyatlari,
    get_dashboard_kpis,
    get_dashboard_trend,
    get_dashboard_comparison,
    get_dashboard_segments,
    get_dashboard_filters,
    dashboard_sqlite_direct,
    export_campaign_customers_excel,
    export_brand_customers,
    export_beklenen_musteriler_excel,
    musteri_notlari,
    musteri_not_sil,
    kampanya_gonder,
    kampanya_gonderim_ozeti,
    get_hane_analizi,
    ai_chat_stream,
    ai_new_session,
    ai_session_history,
    ai_delete_session,
    ai_quick_summary,
    ai_customer_profile,
    ai_usage_stats,
    ai_customer_nba,
    ai_generate_variants,
    ai_detect_anomalies,
    ai_weekly_brief,
    list_notifications,
    mark_notification_as_read,
    sync_ai_notifications,
    get_scheduled_campaigns,
    schedule_campaign_view,
    delete_scheduled_campaign,
    run_scheduled_campaign,
    list_ai_dashboards,
    get_ai_dashboard,
    delete_ai_dashboard,
    toggle_ai_dashboard_favorite,
    export_store_analysis_excel,
    get_store_analysis,
    get_store_list
)

urlpatterns = [
    # Auth
    path('auth/kayit/', RegisterView.as_view(), name='register'),
    path('auth/giris/', LoginView.as_view(), name='login'),
    path('auth/profil/', ProfileView.as_view(), name='profile'),
    
    # DataSources
    path('veri-kaynaklari/', DataSourceListView.as_view(), name='datasources-list'),
    path('veri-kaynaklari/<int:pk>/', DataSourceDetailView.as_view(), name='datasource-detail'),
    path('veri-kaynaklari/<int:pk>/analiz/', get_data_source_analytics, name='datasource-analytics'),
    path('veri-kaynaklari/<int:pk>/urunler/', get_product_analytics, name='datasource-products'),
    
    # CRM Analytics
    path('veri-kaynaklari/<int:data_source_id>/rfm-analizi/', get_rfm_analysis, name='rfm-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/churn-analizi/', get_churn_analysis, name='churn-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/clv-analizi/', get_clv_analysis, name='clv-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/clv-analizi/detaylar/', get_clv_customer_details, name='clv-details'),
    path('veri-kaynaklari/<int:data_source_id>/markalar/', get_brand_report, name='brand-report'),
    path('veri-kaynaklari/<int:data_source_id>/markalar/detay/', get_brand_detail, name='brand-detail'),
    path('veri-kaynaklari/<int:data_source_id>/markalar/oneriler/', get_brand_suggestions, name='brand-suggestions'),
    path('veri-kaynaklari/<int:data_source_id>/segmentasyon/', get_segmentation_analysis, name='segmentation-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/segmentasyon/detay/', get_segment_detailed_analysis, name='segmentation-detail-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/beklenen-musteriler/', get_beklenen_musteriler, name='beklenen-musteriler'),
    path('veri-kaynaklari/<int:data_source_id>/urun-ara/', search_products, name='search-products'),
    path('veri-kaynaklari/<int:data_source_id>/urun-portali/<int:product_id>/', get_product_portal, name='product-portal'),
    path('veri-kaynaklari/<int:data_source_id>/kampanyalar/', get_campaigns_analysis, name='campaigns-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/yeni-musteriler/', get_new_customers_analysis_backend, name='new-customers-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/musteri-bilgisi/', get_customer_info_analysis, name='customer-info-analysis'),
    path('veri-kaynaklari/<int:data_source_id>/kategori-raporu/', get_category_report_details, name='category-report'),
    path('veri-kaynaklari/<int:data_source_id>/kategori-raporu/etiketler/', handle_category_tags, name='category-report-tags'),
    path('veri-kaynaklari/<int:data_source_id>/kategori-raporu/agac/', get_category_tree, name='category-tree'),
    path('veri-kaynaklari/<int:data_source_id>/musteriler/', get_customer_list, name='customer-list'),
    path('veri-kaynaklari/<int:data_source_id>/musteriler/<int:customer_id>/', get_customer_detail, name='customer-detail'),
    path('veri-kaynaklari/<int:data_source_id>/musteri-birlestir/', musteri_birlestir, name='customer-merge'),
    path('veri-kaynaklari/<int:data_source_id>/musteriler/<int:customer_id>/zaman-cizelgesi/', get_musteri_zaman_cizelgesi, name='musteri-zaman-cizelgesi'),
    path('veri-kaynaklari/<int:data_source_id>/segment-gecis-matrisi/', get_segment_gecis_matrisi, name='segment-gecis-matrisi'),
    path('veri-kaynaklari/<int:data_source_id>/kategori-terk-listesi/', get_kategori_terk_listesi, name='kategori-terk-listesi'),
    path('veri-kaynaklari/<int:data_source_id>/kategori-terk-by-kategori/', get_kategori_terk_by_kategori, name='kategori-terk-by-kategori'),
    path('veri-kaynaklari/<int:data_source_id>/kohort-analizi/', get_kohort_analizi, name='kohort-analizi'),
    path('veri-kaynaklari/<int:data_source_id>/urun-birliktelik/', get_urun_birliktelik, name='urun-birliktelik'),
    path('veri-kaynaklari/<int:data_source_id>/marka-sadakati/', get_marka_sadakati, name='marka-sadakati'),
    path('veri-kaynaklari/<int:data_source_id>/enflasyon-dayaniklilik/', get_enflasyon_dayaniklilik, name='enflasyon-dayaniklilik'),
    path('veri-kaynaklari/<int:data_source_id>/rakip-riski/', get_rakip_riski, name='rakip-riski'),
    path('veri-kaynaklari/<int:data_source_id>/musteriler/<int:customer_id>/notlar/', musteri_notlari, name='musteri-notlari'),
    path('veri-kaynaklari/<int:data_source_id>/musteriler/<int:customer_id>/notlar/<int:not_id>/', musteri_not_sil, name='musteri-not-sil'),
    path('veri-kaynaklari/<int:data_source_id>/kampanya-onerileri/<int:oneri_id>/gonder/', kampanya_gonder, name='kampanya-gonder'),
    path('veri-kaynaklari/<int:data_source_id>/kampanya-onerileri/<int:oneri_id>/gonderim-ozeti/', kampanya_gonderim_ozeti, name='kampanya-gonderim-ozeti'),
    path('veri-kaynaklari/<int:data_source_id>/hane-analizi/', get_hane_analizi, name='hane-analizi'),
    path('veri-kaynaklari/<int:data_source_id>/musteri-etiket-ozeti/', get_musteri_etiket_ozeti, name='musteri-etiket-ozeti'),
    
    # Campaign Recommendations
    path('kampanya-onerileri/', get_campaign_recommendations, name='campaign-recommendations'),
    path('kampanya-onerileri/disa-aktar/', export_campaign_customers_excel, name='campaign-export'),
    path('marka-musteri-listesi/', export_brand_customers, name='brand-customer-export'),
    path('beklenen-musteriler-excel/', export_beklenen_musteriler_excel, name='beklenen-export'),
    path('campaign-recommendations/export/', export_campaign_customers_excel, name='campaign-export-alias'),
    path('kampanya-onerileri/sayilar/', get_campaign_counts, name='campaign-counts'),
    path('kampanya-sayilari/', get_campaign_counts, name='campaign-counts-alias'),
    path('kampanya-onerileri/filtre-sayilari/', get_campaign_filter_counts, name='campaign-filter-counts'),
    path('kampanya-onerileri/kategoriler/', get_campaign_source_categories, name='campaign-source-categories'),
    path('kampanya-onerileri/<int:pk>/durum/', update_recommendation_status, name='update-recommendation-status'),
    path('kampanya-onerileri/toplu-durum/', bulk_update_recommendation_status, name='bulk-update-status'),
    path('kampanya-onerileri/<int:pk>/ai-ozet/', get_ai_campaign_summary, name='campaign-ai-summary'),
    path('kampanya-onerileri/kategori-hiyerarsisi/', get_category_hierarchy, name='category-hierarchy'),
    path('kampanya-onerileri/kategori-urunleri/', get_category_top_products, name='category-top-products'),
    path('filters/kategori-yoneticileri/', get_kategori_yoneticileri, name='filters-kategori-yoneticileri'),
    path('filters/markalar/', get_brands, name='filters-markalar'),
    path('kampanya-onerileri/yeniden-uret/', regenerate_campaigns, name='regenerate-campaigns'),
    path('kampanya-onerileri/urun-fiyatlari-guncelle/', enrich_urun_fiyatlari, name='enrich-urun-fiyatlari'),
    
    # Dashboards
    path('paneller/', DashboardListView.as_view(), name='dashboards-list'),
    path('paneller/<int:pk>/', DashboardDetailView.as_view(), name='dashboard-detail'),
    
    # Widgets
    path('paneller/<int:dashboard_id>/widgetlar/', WidgetCreateView.as_view(), name='widget-create'),
    path('paneller/<int:dashboard_id>/widgetlar/<int:widget_id>/', WidgetDeleteView.as_view(), name='widget-delete'),
    
    # Query
    path('sorgu/', QueryView.as_view(), name='query'),
    
    # Sync Status
    path('senkronizasyon-durumu/', SyncStatusView.as_view(), name='sync-status'),
    
    # System Status (Monitör)
    path('sistem-durumu/', SystemStatusView.as_view(), name='system-status'),
    
    # Platform Status (All services)
    path('platform-durumu/', PlatformStatusView.as_view(), name='platform-status'),
    
    # Dashboard SQLite Direct & Progressive Endpoints
    path('panel-sqlite/', dashboard_sqlite_direct, name='dashboard-sqlite'),
    path('panel/kpiler/', get_dashboard_kpis, name='dashboard-kpis'),
    path('panel/trend/', get_dashboard_trend, name='dashboard-trend'),
    path('panel/karsilastirma/', get_dashboard_comparison, name='dashboard-comparison'),
    path('panel/segmentler/', get_dashboard_segments, name='dashboard-segments'),
    path('panel/filtreler/', get_dashboard_filters, name='dashboard-filters'),
    
    # Store Analysis
    path('kategori-raporu/<int:data_source_id>/disa-aktar/', export_category_report_excel, name='category-report-export'),
    path('kohort-analizi/<int:data_source_id>/disa-aktar/', export_cohort_analysis_excel, name='cohort-analysis-export'),
    path('marka-sadakati/<int:data_source_id>/disa-aktar/', export_brand_loyalty_excel, name='brand-loyalty-export'),
    path('magaza-analizi/', get_store_analysis, name='store-analysis'),
    path('magaza-analizi/disa-aktar/', export_store_analysis_excel, name='store-analysis-export'),
    path('magazalar/', get_store_list, name='store-list'),
    
    # System Logs
    path('sistem-loglari/', get_system_logs, name='system-logs'),
    path('sistem-loglari/temizle/', clear_system_logs, name='clear-system-logs'),
    path('sistem/cache-yenile/', rebuild_kpi_cache, name='rebuild-kpi-cache'),
    
    # Settings (Uygulama Ayarları)
    path('ayarlar/', SettingsView.as_view(), name='app-settings'),
    
    # AI Assistant Endpoints
    path('ai/sohbet/', ai_chat_stream, name='ai-chat'),
    path('ai/sohbet/yeni/', ai_new_session, name='ai-new-session'),
    path('ai/sohbet/gecmis/', ai_session_history, name='ai-history'),
    path('ai/sohbet/<int:session_id>/', ai_delete_session, name='ai-delete-session'),
    path('ai/ozet/', ai_quick_summary, name='ai-summary'),
    path('ai/musteri-profili/<int:customer_id>/', ai_customer_profile, name='ai-customer-profile'),
    path('ai/kullanim/', ai_usage_stats, name='ai-usage'),
    path('ai/customer-nba/<int:customer_id>/', ai_customer_nba, name='ai-customer-nba'),
    path('ai/varyant-uret/', ai_generate_variants, name='ai-variant-producer'),
    path('ai/anomaliler/', ai_detect_anomalies, name='ai-anomaliler'),
    path('ai/haftalik-brifing/', ai_weekly_brief, name='ai-weekly-brief'),
    path('ai/bildirimler/', list_notifications, name='ai-notifications-list'),
    path('ai/bildirimler/sync/', sync_ai_notifications, name='ai-notifications-sync'),
    path('ai/bildirimler/<int:pk>/okundu/', mark_notification_as_read, name='ai-notifications-read'),
    path('ai/kampanya/listele/', get_scheduled_campaigns, name='get-scheduled-campaigns'),
    path('ai/kampanya/planla/', schedule_campaign_view, name='ai-campaign-create'),
    path('ai/kampanya/<int:pk>/sil/', delete_scheduled_campaign, name='ai-campaign-delete'),
    path('ai/kampanya/<int:pk>/calistir/', run_scheduled_campaign, name='ai-campaign-run'),
    path('ai/paneller/', list_ai_dashboards, name='ai-dashboards-list'),
    path('ai/paneller/<int:dashboard_id>/', get_ai_dashboard, name='ai-dashboard-detail'),
    path('ai/paneller/<int:dashboard_id>/sil/', delete_ai_dashboard, name='ai-dashboard-delete'),
    path('ai/paneller/<int:dashboard_id>/favori/', toggle_ai_dashboard_favorite, name='ai-dashboard-favorite'),
    
    # Debug DB Status
    path('debug-db/', lambda r: Response({
        "DB_BACKEND": db_engine.DB_BACKEND,
        "POSTGRES_URL_SET": bool(db_engine.POSTGRES_URL),
        "TestQuery": (db_engine.execute_query("SELECT 1 as connected") or [{"status": "failed"}])[0],
    }), name='debug-db'),

    # Lightweight health check - no DB query, just confirms backend is alive
    path('health/', lambda r: JsonResponse({"status": "ok"}), name='health-check'),
]
