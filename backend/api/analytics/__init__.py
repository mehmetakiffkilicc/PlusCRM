"""
Analytics Module
Provides modular analytics views for CRM, segmentation, dashboard and category analytics.
"""
from .rfm_view import get_rfm_analysis
from .churn_view import get_churn_analysis
from .clv_view import get_clv_analysis, get_clv_customer_details
from .segmentation_view import get_segmentation_analysis, get_segment_detailed_analysis, get_beklenen_musteriler
from .campaigns_view import get_campaigns_analysis
from .dashboard_view import (
    get_data_source_analytics,
    get_product_analytics,
    get_brand_report,
    search_products,
    get_new_customers_analysis_backend,
    get_customer_info_analysis,
    get_brand_suggestions,
    get_brand_detail,
    dashboard_sqlite_direct,
    get_dashboard_kpis,
    get_dashboard_trend,
    get_dashboard_comparison,
    get_dashboard_segments,
    get_dashboard_filters
)
from .product_portal_view import get_product_portal
from .category_report_view import get_category_report_details, handle_category_tags, get_category_tree, export_category_report_excel
from .customer_portal_view import get_customer_list, get_customer_detail, musteri_birlestir, get_musteri_etiket_ozeti, get_musteri_zaman_cizelgesi, get_segment_gecis_matrisi, get_kategori_terk_listesi, get_kategori_terk_by_kategori
from .campaign_view import (
    get_campaign_recommendations,
    update_recommendation_status,
    bulk_update_recommendation_status,
    get_ai_campaign_summary,
    get_category_hierarchy,
    get_category_top_products,
    get_campaign_counts,
    get_campaign_filter_counts,
    get_campaign_source_categories,
    get_kategori_yoneticileri,
    get_brands,
    regenerate_campaigns,
    enrich_urun_fiyatlari
)
from .export_view import export_campaign_customers_excel, export_brand_customers, export_beklenen_musteriler_excel
from .kohort_view import get_kohort_analizi, get_urun_birliktelik, get_marka_sadakati, export_cohort_analysis_excel, export_brand_loyalty_excel
from .sprint4_view import (get_enflasyon_dayaniklilik, get_rakip_riski, musteri_notlari, musteri_not_sil,
                           kampanya_gonder, kampanya_gonderim_ozeti, get_hane_analizi)
from .llm.llm_view import (
    ai_chat_stream, ai_new_session, ai_session_history,
    ai_delete_session, ai_quick_summary, ai_customer_profile, ai_usage_stats,
    ai_generate_variants, ai_detect_anomalies, ai_customer_nba, ai_weekly_brief
)
from .llm.campaign_view import (
    get_scheduled_campaigns, schedule_campaign_view, delete_scheduled_campaign, run_scheduled_campaign
)
from .llm.notification_view import (
    list_notifications, mark_notification_as_read, sync_ai_notifications
)
from .llm.aidashboard_view import (
    list_ai_dashboards, get_ai_dashboard, delete_ai_dashboard,
    toggle_ai_dashboard_favorite
)
from .store_view import get_store_analysis, export_store_analysis_excel, get_store_list

__all__ = [
    'get_rfm_analysis',
    'get_churn_analysis',
    'get_clv_analysis',
    'get_clv_customer_details',
    'get_segmentation_analysis',
    'get_segment_detailed_analysis',
    'get_beklenen_musteriler',
    'get_campaigns_analysis',
    'get_data_source_analytics',
    'get_product_analytics',
    'get_brand_report',
    'search_products',
    'get_new_customers_analysis_backend',
    'get_customer_info_analysis',
    'get_brand_suggestions',
    'get_brand_detail',
    'dashboard_sqlite_direct',
    'get_dashboard_kpis',
    'get_dashboard_trend',
    'get_dashboard_comparison',
    'get_dashboard_segments',
    'get_dashboard_filters',
    'get_product_portal',
    'get_category_report_details',
    'handle_category_tags',
    'get_category_tree',
    'get_customer_list',
    'get_customer_detail',
    'get_musteri_etiket_ozeti',
    'get_musteri_zaman_cizelgesi',
    'get_segment_gecis_matrisi',
    'get_kategori_terk_listesi',
    'get_kategori_terk_by_kategori',
    'get_campaign_recommendations',
    'get_campaign_counts',
    'get_campaign_filter_counts',
    'get_campaign_source_categories',
    'update_recommendation_status',
    'bulk_update_recommendation_status',
    'get_ai_campaign_summary',
    'get_category_hierarchy',
    'get_category_top_products',
    'get_kategori_yoneticileri',
    'get_brands',
    'regenerate_campaigns',
    'enrich_urun_fiyatlari',
    'export_campaign_customers_excel',
    'export_brand_customers',
    'export_beklenen_musteriler_excel',
    'get_kohort_analizi',
    'get_urun_birliktelik',
    'get_marka_sadakati',
    'get_enflasyon_dayaniklilik',
    'get_rakip_riski',
    'musteri_notlari',
    'musteri_not_sil',
    'kampanya_gonder',
    'kampanya_gonderim_ozeti',
    'get_hane_analizi',
    'ai_chat_stream',
    'ai_new_session',
    'ai_session_history',
    'ai_delete_session',
    'ai_quick_summary',
    'ai_customer_profile',
    'ai_usage_stats',
    'ai_generate_variants',
    'ai_detect_anomalies',
    'ai_customer_nba',
    'ai_weekly_brief',
    'list_notifications',
    'mark_notification_as_read',
    'sync_ai_notifications',
    'get_scheduled_campaigns',
    'schedule_campaign_view',
    'delete_scheduled_campaign',
    'run_scheduled_campaign',
    'list_ai_dashboards',
    'get_ai_dashboard',
    'delete_ai_dashboard',
    'toggle_ai_dashboard_favorite',
    'get_store_analysis',
    'export_store_analysis_excel',
    'musteri_birlestir',
    'export_category_report_excel',
    'export_cohort_analysis_excel',
    'export_brand_loyalty_excel',
]
