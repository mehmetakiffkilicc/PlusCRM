"""
Dashboard Analytics Views
Includes: Data Source Analytics, Product Analytics, Brand Report,
Product Search, New Customers Analysis, Customer Info Analysis
"""

import sys
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_401_UNAUTHORIZED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import sys
import time
import os
import sqlite3

from ..models import DataSource
from ..auth import verify_jwt_token
from ..data_access import (
    get_sales_analytics,
    get_available_years,
    get_category_hierarchy,
    get_brand_by_category,
)  # <-- data_access'den import
from .. import db_engine
from django.contrib.auth.models import User
from .base import (
    get_datasource_data,
    filter_data_by_date,
    get_cached_data,
    set_cached_data,
    get_user_from_request,
    detect_columns,
    categorize_to_parent,
    parse_date_fast,
    _build_datasource_analytics_cache_key,
    _get_cached_datasource_analytics,
    _set_cached_datasource_analytics,
    _build_filter_cache_key,
    _get_ttl_cache,
    _set_ttl_cache,
    _brand_report_cache,
    _brand_report_cache_timeout,
    _brand_report_cache_max_entries,
    _brand_filters_cache,
    _brand_filters_cache_timeout,
    _brand_filters_cache_max_entries,
    _new_customers_filter_cache,
    _new_customers_filter_cache_timeout,
    _new_customers_filter_cache_max_entries,
)

logger = logging.getLogger(__name__)

# Global cache for product search data
_product_cache = {}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_data_source_analytics(request, pk):
    """
    Veri kaynağı için analytics hesapla - Frontend'e sadece özet gönder
    Bu sayede 130K satır yerine sadece özet veriler (KPI'lar) gönderilir
    """
    import time

    start_ep = time.perf_counter()

    # JWT token authentication
    user = get_user_from_request(request)
    if not user:
        return Response(
            {"error": "Geçersiz kullanıcı veya oturum"}, status=HTTP_401_UNAUTHORIZED
        )

    # Filtre parametrelerini al (çoklu seçim)
    selected_segments = request.GET.getlist("segments")  # Array olarak gelecek
    selected_categories = request.GET.getlist("categories")  # Array olarak gelecek
    selected_brands = request.GET.getlist("brands")  # Array olarak gelecek

    # Geriye uyumluluk için tekli parametreleri de kontrol et
    if not selected_segments and request.GET.get("segment"):
        selected_segments = [request.GET.get("segment")]
    if not selected_categories and request.GET.get("category"):
        selected_categories = [request.GET.get("category")]
    if not selected_brands and request.GET.get("brand"):
        selected_brands = [request.GET.get("brand")]

    # URL'den gelen değerlerdeki gereksiz karakterleri temizle (boşluk, /, vb.)
    selected_segments = [s.strip().rstrip("/") for s in selected_segments if s.strip()]
    selected_categories = [
        c.strip().rstrip("/") for c in selected_categories if c.strip()
    ]
    selected_brands = [b.strip().rstrip("/") for b in selected_brands if b.strip()]

    # Ay ve yıl filtrelerini al
    selected_year = request.GET.get("year")
    selected_month = request.GET.get("month")
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    # Fast path: filter-keyed cache for this endpoint
    cache_key = _build_datasource_analytics_cache_key(
        pk,
        user.id,
        selected_segments,
        selected_categories,
        selected_brands,
        selected_year,
        selected_month,
        start_date_str,
        end_date_str,
    )
    cached_payload = _get_cached_datasource_analytics(cache_key)
    if cached_payload is not None:
        return Response(cached_payload, status=HTTP_200_OK)

    try:
        selected_year = int(selected_year) if selected_year else None
        selected_month = int(selected_month) if selected_month else None
    except ValueError:
        selected_year = None
        selected_month = None

    # Tarih aralığı parse
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse start_date '{start_date_str}': {e}")
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse end_date '{end_date_str}': {e}")
            pass
    # --- SQL AGGREGATION / CACHE MODE ---
    try:
        # Önce Aggregated veriyi (Cache DB) dene.
        logger.info(f"Attempting SQL Aggregation for DS {pk}...")

        # Filtreleri hazırla (fonksiyon imzasına uygun)
        cat_filter = selected_categories[0] if selected_categories else None
        brand_filter = selected_brands[0] if selected_brands else None

        # Eğer start/end date yoksa ama Yıl/Ay seçiliyse, tarih aralığını hesapla
        calc_start = start_date
        calc_end = end_date

        if not calc_start and selected_year:
            try:
                if selected_month:
                    # Belirli bir ay: 2026-02-01 to 2026-02-28
                    import calendar

                    last_day = calendar.monthrange(selected_year, selected_month)[1]
                    calc_start = datetime(selected_year, selected_month, 1)
                    calc_end = datetime(selected_year, selected_month, last_day)
                else:
                    # Tüm yıl: 2026-01-01 to 2026-12-31
                    calc_start = datetime(selected_year, 1, 1)
                    calc_end = datetime(selected_year, 12, 31)
            except Exception as e:
                logger.warning(f"Date calculation error: {e}")

        # Gelecek tarih kontrolü: Analiz bitiş tarihi bugünden ilerideyse bugüne çek
        # Bu sayede "Mevcut Yıl" seçildiğinde süre 365 gün değil, geçen süre (örn: 22 gün) olarak hesaplanır
        # ve Smart Granularity (Günlük Çizim) devreye girer.
        if calc_end and calc_end > datetime.now():
            calc_end = datetime.now()

        start_str = calc_start.strftime("%Y-%m-%d") if calc_start else None
        end_str = calc_end.strftime("%Y-%m-%d") if calc_end else None

        # Akıllı Granülerite: 92 günden (3 ay) az veri varsa GÜNLÜK, yoksa AYLIK detay göster
        group_by = "month"
        if calc_start and calc_end:
            delta = calc_end - calc_start
            if delta.days < 92:
                group_by = "day"
        elif selected_month and selected_year:
            group_by = "day"

        agg_result = get_sales_analytics(
            category=selected_categories if selected_categories else None,
            brand=selected_brands if selected_brands else None,
            segment=selected_segments if selected_segments else None,
            customer_type=request.GET.get("customer_type")
            or request.GET.get("customerType"),
            approval_status=request.GET.get("approval_status")
            or request.GET.get("approvalStatus"),
            region=request.GET.get("region"),
            end_date=end_str,
            start_date=start_str,
            group_by=group_by,
            month=selected_month if not selected_year else None,
        )

        if agg_result:
            # FIX: If it's a database source and revenue is 0, DON'T fallback to 404.
            # Just return 200 with zeroed data.
            logger.info(
                f"SQL Aggregation for DS {pk}: Revenue={agg_result.get('totalRevenue', 0)}"
            )

            # Dashboard formatına dönüştür
            dashboard_payload = {
                "analytics": {
                    "totalRevenue": agg_result.get("totalRevenue", 0),
                    "totalCustomers": agg_result.get("totalCustomers", 0),
                    "totalReceipts": agg_result.get("totalReceipts", 0),
                    "totalProducts": agg_result.get("totalProducts", 0),
                    "totalBrands": agg_result.get("totalBrands", 0),
                    "topProduct": agg_result.get(
                        "topProduct", {"name": "N/A", "sales": 0}
                    ),
                    "topProducts": agg_result.get("topProducts", []),
                    "productRevenue": agg_result.get("productRevenue", []),
                    "salesByMonth": (
                        lambda data: (
                            # Eğer yıl seçiliyse ve veri aylık ise 12 ayı tamamla (0 ile doldur)
                            (
                                lambda full_year_data: sorted(
                                    full_year_data, key=lambda x: str(x["month"])
                                )
                            )(
                                data
                                + [
                                    {"month": f"{selected_year}-{m:02d}", "sales": 0}
                                    for m in range(1, 13)
                                    if selected_year
                                    and not any(
                                        d["month"] == f"{selected_year}-{m:02d}"
                                        for d in data
                                    )
                                    and (
                                        int(selected_year) < datetime.now().year
                                        or (
                                            int(selected_year) == datetime.now().year
                                            and m <= datetime.now().month
                                        )
                                    )
                                ]
                            )
                            if selected_year and not selected_month
                            else data
                        )
                    )(
                        [
                            {"month": str(s.get("date") or s.get("month") or ""), "sales": s.get("sales", 0)}
                            for s in agg_result.get("salesByTime", [])
                        ]
                    ),
                    "productCategories": agg_result.get("productCategories", []),
                    "brandRevenue": agg_result.get("brandRevenue", []),
                    # Super Category Logic - Basitleştirilmiş
                    "superCategoryRevenue": [],  # Şimdilik boş bırak, gerekirse sonra ekle
                    "customerSegments": agg_result.get("customerSegments", []),
                    "hasProductColumn": True,
                },
                "categoryHierarchy": get_category_hierarchy(),
                "brandByCategory": get_brand_by_category(),
                "columns": [],
                "rowCount": agg_result.get("totalReceipts", 0),
                "availableMonths": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "availableYears": get_available_years(),
                "availableRegions": [],
                "availableCustomerTypes": [],
                "availableApprovalStatuses": [],
            }

            # -------------------------------------------------------------
            # Populate Available Filters — cached 6 saat (filtreler nadiren değişir)
            # Bu 3 sorgu 130K+ satır tarayarak full table scan yapıyordu, artık cache'den gelir.
            _FILTER_CACHE_KEY = "dashboard_available_filters"
            _FILTER_CACHE_TTL = 6 * 3600  # 6 saat
            try:
                from django.core.cache import cache as django_cache
                cached_filters = django_cache.get(_FILTER_CACHE_KEY)
                if cached_filters:
                    dashboard_payload["availableRegions"] = cached_filters.get("regions", [])
                    dashboard_payload["availableCustomerTypes"] = cached_filters.get("types", [])
                    dashboard_payload["availableApprovalStatuses"] = cached_filters.get("statuses", [])
                else:
                    conn_lite = db_engine.get_connection()
                    try:
                        if db_engine.DB_BACKEND == "postgresql":
                            from psycopg2.extras import RealDictCursor
                            cursor_lite = conn_lite.cursor(cursor_factory=RealDictCursor)
                        else:
                            cursor_lite = conn_lite.cursor()

                        regions, types, statuses = [], [], []

                        try:
                            cursor_lite.execute(
                        "SELECT DISTINCT " + db_engine.bolge_expr() + " as bolge FROM magazalar WHERE bolge IS NOT NULL ORDER BY bolge"
                            )
                            rows = cursor_lite.fetchall()
                            regions = [r[0] if isinstance(r, tuple) else r["bolge"] for r in rows if (r[0] if isinstance(r, tuple) else r.get("bolge"))]
                        except Exception:
                            pass

                        try:
                            cursor_lite.execute(
                                "SELECT DISTINCT tip FROM musteriler WHERE tip IS NOT NULL ORDER BY tip"
                            )
                            rows = cursor_lite.fetchall()
                            types = [r[0] if isinstance(r, tuple) else r["tip"] for r in rows if (r[0] if isinstance(r, tuple) else r.get("tip"))]
                        except Exception:
                            pass

                        try:
                            cursor_lite.execute(
                                "SELECT DISTINCT onay_durumu FROM musteriler WHERE onay_durumu IS NOT NULL ORDER BY onay_durumu"
                            )
                            rows = cursor_lite.fetchall()
                            statuses = [r[0] if isinstance(r, tuple) else r["onay_durumu"] for r in rows if (r[0] if isinstance(r, tuple) else r.get("onay_durumu"))]
                        except Exception:
                            pass

                        django_cache.set(_FILTER_CACHE_KEY, {"regions": regions, "types": types, "statuses": statuses}, _FILTER_CACHE_TTL)
                        dashboard_payload["availableRegions"] = regions
                        dashboard_payload["availableCustomerTypes"] = types
                        dashboard_payload["availableApprovalStatuses"] = statuses
                    finally:
                        db_engine.release_connection(conn_lite)
            except Exception as e:
                logger.warning(f"Failed to populate available filters: {e}")
            # -------------------------------------------------------------

            _set_cached_datasource_analytics(cache_key, dashboard_payload)
            logger.info(
                f"get_data_source_analytics (SQL path) took {time.perf_counter() - start_ep:.4f}s"
            )
            return Response(dashboard_payload, status=HTTP_200_OK)

    except Exception as e:
        logger.error(f"SQL Aggregation Failed: {e}", exc_info=True)
        # Hata durumunda Fallback (aşağıdaki koda devam et)

    try:
        data_source = DataSource.objects.get(id=pk, user_id=user.id)
        data = get_datasource_data(data_source)

        # Handle paginated response from get_sales_data
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        if not data or len(data) == 0:
            return Response({"error": "Veri kaynağı boş"}, status=HTTP_404_NOT_FOUND)

        first_row = data[0]
        columns = list(first_row.keys())

        # Tüm kolonları tek seferde tespit et (column_mapping varsa kullan)
        cols = detect_columns(columns, data_source.column_mapping)
        revenue_col = cols["revenue_col"]
        date_col = cols["date_col"]
        product_col = cols["product_col"]
        customer_id_col = cols["customer_id_col"]
        receipt_id_col = cols["receipt_id_col"]
        quantity_col = cols["quantity_col"]
        unit_price_col = cols["unit_price_col"]
        segment_col = cols["segment_col"]
        brand_col = cols["brand_col"]
        ust_kategori_col = cols["ust_kategori_col"]
        category_col = cols["category_col"]
        alt_kategori_1_col = cols["alt_kategori_1_col"]
        alt_kategori_2_col = cols["alt_kategori_2_col"]
        hour_col = cols["hour_col"]

        # Ay/Yıl ve tarih aralığı filtresini uygula - optimize edilmiş versiyon
        date_filtered_data = data
        has_date_filter = selected_year or selected_month or start_date or end_date
        if has_date_filter and date_col:
            date_filtered_data = []
            for row in data:
                date_value = row.get(date_col)
                if date_value:
                    row_date, row_year, row_month, _ = parse_date_fast(date_value)

                    if row_year is not None and row_month is not None:
                        match = True
                        if selected_year and row_year != selected_year:
                            match = False
                        if selected_month and row_month != selected_month:
                            match = False
                        # Tarih aralığı kontrolü
                        if start_date and row_date and row_date < start_date:
                            match = False
                        if end_date and row_date and row_date > end_date:
                            match = False

                        if match:
                            date_filtered_data.append(row)

        # Veriyi filtrele (çoklu seçim) - KPI'lar için her iki filtre de uygulanır
        # Set kullanarak lookup hızını O(1) yap
        filtered_data = date_filtered_data
        if selected_segments and segment_col:
            segments_set = set(selected_segments)
            filtered_data = [
                row
                for row in filtered_data
                if str(row.get(segment_col, "")).strip().rstrip("/") in segments_set
            ]

        if selected_categories:
            categories_set = set(selected_categories)
            # Kategori Üst_Kategori (dinamik), Ana_Kategori, Alt_Kategori1 veya Alt_Kategori2'de olabilir
            new_filtered = []
            for row in filtered_data:
                # Üst kategori kolonu varsa direkt kontrol et
                if (
                    ust_kategori_col
                    and str(row.get(ust_kategori_col, "")).strip().rstrip("/")
                    in categories_set
                ):
                    new_filtered.append(row)
                    continue
                # Ana kategori kontrol et
                ana_kat = (
                    str(row.get(category_col, "")).strip().rstrip("/")
                    if category_col
                    else ""
                )
                if ana_kat in categories_set:
                    new_filtered.append(row)
                    continue
                # Ana kategoriden türetilen üst kategoriyi kontrol et
                if ana_kat and categorize_to_parent(ana_kat) in categories_set:
                    new_filtered.append(row)
                    continue
                # Alt kategori 1 kontrol et
                if (
                    alt_kategori_1_col
                    and str(row.get(alt_kategori_1_col, "")).strip().rstrip("/")
                    in categories_set
                ):
                    new_filtered.append(row)
                    continue
                # Alt kategori 2 kontrol et
                if (
                    alt_kategori_2_col
                    and str(row.get(alt_kategori_2_col, "")).strip().rstrip("/")
                    in categories_set
                ):
                    new_filtered.append(row)
                    continue
            filtered_data = new_filtered

        if selected_brands and brand_col:
            brands_set = set(selected_brands)
            filtered_data = [
                row
                for row in filtered_data
                if str(row.get(brand_col, "")).strip().rstrip("/") in brands_set
            ]

        # Analytics hesapla
        analytics = {
            "totalRevenue": 0,
            "topProduct": {"name": "N/A", "sales": 0},
            "totalCustomers": 0,
            "totalReceipts": 0,
            "totalProducts": 0,
            "customerSegments": [],
            "salesByMonth": [],
            "productCategories": [],
        }

        # === TÜM METRİKLERİ TEK DÖNGÜDE HESAPLA (PERFORMANS OPTİMİZASYONU) ===
        total_revenue = 0.0
        unique_customers = set()
        unique_receipts = set()
        unique_products = set()
        product_sales = defaultdict(float)
        product_quantities = defaultdict(int)

        for row in filtered_data:
            # Ciro
            if revenue_col:
                try:
                    total_revenue += float(
                        str(row.get(revenue_col, "0")).replace(",", ".")
                    )
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Failed to parse revenue value: {e}")
                    pass

            # Müşteri
            if customer_id_col:
                customer_id = row.get(customer_id_col)
                if customer_id and str(customer_id).strip():
                    unique_customers.add(str(customer_id).strip())

            # Fiş
            if receipt_id_col:
                receipt_id = row.get(receipt_id_col)
                if receipt_id and str(receipt_id).strip():
                    unique_receipts.add(str(receipt_id).strip())

            # Ürün
            if product_col:
                product = row.get(product_col)
                if product and str(product).strip():
                    product_clean = str(product).strip()
                    unique_products.add(product_clean)
                    if revenue_col:
                        try:
                            sales = float(
                                str(row.get(revenue_col, "0")).replace(",", ".")
                            )
                            product_sales[product_clean] += sales
                            product_quantities[product_clean] += 1
                        except (ValueError, TypeError, AttributeError) as e:
                            logger.debug(f"Failed to parse product sales value: {e}")
                            pass

        analytics["totalRevenue"] = total_revenue
        analytics["totalCustomers"] = len(unique_customers)
        analytics["totalReceipts"] = len(unique_receipts)
        analytics["totalProducts"] = len(unique_products) if product_col else 0
        analytics["hasProductColumn"] = bool(product_col)

        # En çok satan ürün (Özet Tablosundan veya RAM'den)
        # Önce pre-calculated table'a bak (Pre-calculated table is faster and handles filtered Best Seller)
        top_product_found = False
        try:
            conn_lite = db_engine.get_connection()
            try:
                if db_engine.DB_BACKEND == "postgresql":
                    from psycopg2.extras import RealDictCursor

                    cursor_lite = conn_lite.cursor(cursor_factory=RealDictCursor)
                else:
                    cursor_lite = conn_lite.cursor()

                # Determine Period
                p_type = None
                p_val = None
                if selected_year and selected_month:
                    p_type = "AY"
                    p_val = f"{int(selected_year)}-{int(selected_month):02d}"
                elif selected_year:
                    p_type = "YIL"
                    p_val = str(int(selected_year))
                elif not start_date_str and not end_date_str:
                    p_type = "GLOBAL"
                    p_val = "ALL"

                # Determine Group
                g_type = "GENEL"
                g_vals = ["ALL"]

                if selected_categories:
                    g_type = "KATEGORI"
                    g_vals = selected_categories
                elif selected_brands:
                    g_type = "MARKA"
                    g_vals = selected_brands

                if p_type:
                    placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
                    query = f"SELECT urun_ad, toplam_ciro, toplam_adet FROM encoksatanlar WHERE donem_tipi={placeholder} AND donem_degeri={placeholder}"
                    params = [p_type, p_val]

                    if g_type != "GENEL":
                        placeholders = ",".join([placeholder] * len(g_vals))
                        query += f" AND grup_tipi={placeholder} AND grup_degeri IN ({placeholders})"
                        params.append(g_type)
                        params.extend(g_vals)
                    else:
                        query += " AND grup_tipi='GENEL'"

                    query += " ORDER BY toplam_ciro DESC LIMIT 1"

                    cursor_lite.execute(query, params)
                    row = cursor_lite.fetchone()
                    if row:
                        analytics["topProduct"] = {
                            "name": row[0]
                            if isinstance(row, tuple)
                            else row["urun_ad"],
                            "sales": row[1]
                            if isinstance(row, tuple)
                            else row["toplam_ciro"],
                            "quantity": row[2]
                            if isinstance(row, tuple)
                            else row["toplam_adet"],
                        }
                        top_product_found = True
            finally:
                db_engine.release_connection(conn_lite)
        except Exception as e:
            logger.warning(f"Failed to fetch best seller from database: {e}")

        # Fallback to RAM calculation if not found in table
        if not top_product_found and product_sales:
            top_product = max(product_sales.items(), key=lambda x: x[1])
            analytics["topProduct"] = {
                "name": top_product[0],
                "sales": top_product[1],
                "quantity": product_quantities[top_product[0]],
            }

        # Önceki ay için müşteri değişim yüzdesi (sadece ay seçiliyse)
        analytics["customersChangePercent"] = 0
        if customer_id_col and selected_year and selected_month and date_col:
            # Önceki ayı hesapla
            prev_month = selected_month - 1
            prev_year = selected_year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1

            # Önceki ay için müşteri sayısını hızlıca hesapla
            prev_customers = set()
            for row in data:
                date_value = row.get(date_col)
                if date_value:
                    _, row_year, row_month, _ = parse_date_fast(date_value)
                    if row_year == prev_year and row_month == prev_month:
                        customer_id = row.get(customer_id_col)
                        if customer_id and str(customer_id).strip():
                            prev_customers.add(str(customer_id).strip())

            prev_count = len(prev_customers)
            if prev_count > 0:
                change_percent = (
                    (len(unique_customers) - prev_count) / prev_count
                ) * 100
                analytics["customersChangePercent"] = round(change_percent, 1)

        # Aylara göre benzersiz müşteri/fiş sayısı (Müşteri Elde Tutma için)
        # Not: Kullanıcı talebine göre öncelik müşteri sayısıdır; müşteri kolonu yoksa fiş sayısı gösterilir.
        if date_col and (customer_id_col or receipt_id_col):
            monthly_customers = defaultdict(set) if customer_id_col else None
            monthly_receipts = defaultdict(set) if receipt_id_col else None

            for row in data:  # Tüm veriyi kullan
                date_value = row.get(date_col)
                if not date_value:
                    continue

                _, row_year, row_month, _ = parse_date_fast(date_value)
                if not row_year or not row_month:
                    continue

                # Yıl seçimi varsa sadece o yılı al, yoksa tüm yılları al
                if selected_year and row_year != selected_year:
                    continue

                month_key = f"{row_year}-{row_month:02d}"

                if monthly_customers is not None:
                    customer_id = row.get(customer_id_col)
                    if customer_id and str(customer_id).strip():
                        monthly_customers[month_key].add(str(customer_id).strip())

                if monthly_receipts is not None:
                    receipt_id = row.get(receipt_id_col)
                    if receipt_id and str(receipt_id).strip():
                        monthly_receipts[month_key].add(str(receipt_id).strip())

            keys = set()
            if monthly_customers is not None:
                keys.update(monthly_customers.keys())
            if monthly_receipts is not None:
                keys.update(monthly_receipts.keys())

            retention_data = []
            for month_key in sorted(keys):
                year_month = month_key.split("-")
                payload = {
                    "month": month_key,
                    "year": int(year_month[0]),
                    "monthNum": int(year_month[1]),
                }
                if monthly_customers is not None:
                    payload["uniqueCustomers"] = len(
                        monthly_customers.get(month_key, set())
                    )
                if monthly_receipts is not None:
                    payload["uniqueReceipts"] = len(
                        monthly_receipts.get(month_key, set())
                    )
                retention_data.append(payload)

            analytics["retentionByMonth"] = retention_data
        else:
            analytics["retentionByMonth"] = []

        # Müşteri segmentleri - SADECE kategori filtresinden etkilenir
        if segment_col:
            segments = defaultdict(int)
            # Sadece kategori filtresi varsa onu uygula, segment filtresi uygulama
            segment_filter_data = data
            if selected_categories and category_col:
                categories_set = set(selected_categories)
                segment_filter_data = [
                    row
                    for row in data
                    if str(row.get(category_col, "")).strip().rstrip("/")
                    in categories_set
                ]

            for row in segment_filter_data:
                seg = row.get(segment_col)
                # Boş değerleri atla
                if seg and str(seg).strip():
                    seg_clean = str(seg).strip().rstrip("/")
                    segments[seg_clean] += 1

            # Segmentleri numaraya göre sırala (01-) Şampiyonlar, 02-) Potansiyel...)
            def get_segment_number(segment_name):
                try:
                    # "07-) Yüksek Harcama Yapanlar" -> 7
                    if "-" in segment_name:
                        return int(segment_name.split("-")[0].strip())
                    return 999  # Numara yoksa sona koy
                except (ValueError, IndexError, AttributeError):
                    return 999

            sorted_segments = sorted(
                segments.items(), key=lambda x: get_segment_number(x[0])
            )
            analytics["customerSegments"] = [
                {"segment": k, "count": v} for k, v in sorted_segments
            ]

        # Satışlar - Eğer ay seçiliyse günlük (yıllar birleştirilebilir), değilse aylık
        if date_col and revenue_col:
            if selected_month:
                # Günlük ve saatlik satışlar (seçili ay için)
                # Key: (day, hour)
                hourly_sales = defaultdict(float)
                has_hourly_data = False

                for row in filtered_data:
                    date_value = row.get(date_col)
                    if date_value:
                        try:
                            date_str = str(date_value).strip()
                            day_num = None
                            hour_num = 0

                            # Tarih ve saat ayrıştırma
                            # Örn: "17.09.2025 14:30" veya "2025-09-17 14:30:00"
                            date_part = date_str
                            time_part = None

                            if " " in date_str:
                                parts = date_str.split(" ")
                                date_part = parts[0]
                                if len(parts) > 1:
                                    time_part = parts[1]
                            elif "T" in date_str:  # ISO format with T
                                parts = date_str.split("T")
                                date_part = parts[0]
                                if len(parts) > 1:
                                    time_part = parts[1]

                            # Tarih formatı: dd.mm.yyyy
                            if "." in date_part:
                                parts = date_part.split(".")
                                if len(parts) == 3:
                                    day_num = int(parts[0])
                            # ISO formatı: yyyy-mm-dd
                            elif "-" in date_part:
                                parts = date_part.split("-")
                                if len(parts) == 3:
                                    day_num = int(parts[2])

                            # Saat formatı: HH:MM veya HH:MM:SS veya SAAT kolonundan
                            if hour_col:
                                try:
                                    hour_val = str(row.get(hour_col, "0")).strip()
                                    if hour_val:
                                        # "15" veya "15:30" formatı
                                        if ":" in hour_val:
                                            hour_num = int(hour_val.split(":")[0])
                                        else:
                                            hour_num = int(float(hour_val))
                                        has_hourly_data = True
                                except (
                                    ValueError,
                                    IndexError,
                                    TypeError,
                                    AttributeError,
                                ) as e:
                                    logger.debug(f"Failed to parse hour value: {e}")
                                    pass
                            elif time_part:
                                try:
                                    if ":" in time_part:
                                        time_parts = time_part.split(":")
                                        hour_num = int(time_parts[0])
                                        if hour_num > 0:
                                            has_hourly_data = True
                                except (ValueError, IndexError, TypeError) as e:
                                    logger.debug(f"Failed to parse time part: {e}")
                                    pass

                            if day_num:
                                # Satış Tutarı kolonunu kullan
                                revenue_value = row.get(revenue_col, "0")
                                try:
                                    sales = float(
                                        str(revenue_value)
                                        .replace(",", ".")
                                        .replace(" ", "")
                                    )
                                    hourly_sales[(day_num, hour_num)] += sales
                                except (ValueError, TypeError, AttributeError) as e:
                                    logger.debug(f"Failed to parse sales value: {e}")
                                    pass
                        except (ValueError, IndexError, TypeError, AttributeError) as e:
                            logger.debug(f"Failed to parse hourly sales data: {e}")
                            pass

                # Veriyi formatla
                year_prefix = selected_year if selected_year else "0000"

                # Eğer saatlik veri varsa saatlik formatta döndür, yoksa günlük (00:00)
                analytics["salesByMonth"] = [
                    {
                        "month": f"{year_prefix}-{selected_month:02d}-{day:02d} {hour:02d}:00",
                        "sales": sales,
                    }
                    for (day, hour), sales in sorted(hourly_sales.items())
                ]
            else:
                # Aylık satışlar yerine GÜNLÜK satışlar (Zoom için)
                # Key: YYYY-MM-DD
                daily_sales = defaultdict(float)

                for row in filtered_data:
                    date_value = row.get(date_col)
                    if date_value:
                        try:
                            date_str = str(date_value).strip()

                            # Tarih formatı: dd.mm.yyyy (örn: 17.09.2025)
                            if "." in date_str:
                                parts = date_str.split(".")
                                if len(parts) == 3:
                                    day = int(parts[0])
                                    month = int(parts[1])
                                    year = int(parts[2])
                                    date_obj = datetime(year, month, day)
                                else:
                                    continue
                            # ISO formatı: yyyy-mm-dd
                            elif "-" in date_str:
                                date_obj = datetime.fromisoformat(date_str)
                            # Diğer formatlar
                            else:
                                continue

                            date_key = date_obj.strftime("%Y-%m-%d")

                            # Satış Tutarı kolonunu kullan (örn: "1950,00")
                            revenue_value = row.get(revenue_col, "0")
                            try:
                                # Virgülü noktaya çevir ve float'a parse et
                                sales = float(
                                    str(revenue_value)
                                    .replace(",", ".")
                                    .replace(" ", "")
                                )
                                daily_sales[date_key] += sales
                            except (ValueError, TypeError, AttributeError) as e:
                                logger.debug(f"Failed to parse daily sales value: {e}")
                                pass
                        except (ValueError, TypeError, AttributeError) as e:
                            logger.debug(f"Failed to parse daily sales date: {e}")
                            pass

                analytics["salesByMonth"] = [
                    {"month": k, "sales": v} for k, v in sorted(daily_sales.items())
                ]

        # Aylık müşteri sayısı ve değişim oranı hesapla
        if date_col and customer_id_col:
            monthly_customers = defaultdict(set)

            for row in filtered_data:
                date_value = row.get(date_col)
                customer_id = row.get(customer_id_col)

                if date_value and customer_id and str(customer_id).strip():
                    try:
                        date_str = str(date_value).strip()

                        # Tarih formatı: dd.mm.yyyy
                        if "." in date_str:
                            parts = date_str.split(".")
                            if len(parts) == 3:
                                month = int(parts[1])
                                year = int(parts[2])
                                date_obj = datetime(year, month, 1)
                            else:
                                continue
                        # ISO formatı: yyyy-mm-dd
                        elif "-" in date_str:
                            date_obj = datetime.fromisoformat(date_str)
                        else:
                            continue

                        month_key = date_obj.strftime("%Y-%m")
                        monthly_customers[month_key].add(str(customer_id).strip())
                    except (ValueError, IndexError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse monthly customer date: {e}")
                        pass

            # Aylık müşteri sayılarını liste olarak hazırla
            monthly_customer_counts = []
            sorted_months = sorted(monthly_customers.keys())

            for i, month_key in enumerate(sorted_months):
                customer_count = len(monthly_customers[month_key])
                change_percent = 0

                # Önceki ay varsa değişim oranını hesapla
                if i > 0:
                    prev_month_key = sorted_months[i - 1]
                    prev_count = len(monthly_customers[prev_month_key])
                    if prev_count > 0:
                        change_percent = (
                            (customer_count - prev_count) / prev_count
                        ) * 100

                monthly_customer_counts.append(
                    {
                        "month": month_key,
                        "customers": customer_count,
                        "changePercent": round(change_percent, 1),
                    }
                )

            analytics["customersByMonth"] = monthly_customer_counts

        # Kategori bazlı gelir - Pasta grafiği için (filtered_data kullan - kategori filtresi YOK ama segment/ay/yıl var)
        if category_col and revenue_col:
            category_revenue = defaultdict(float)
            # Sadece segment ve tarih filtresini uygula, kategori filtresini UYGULAMA (çünkü kategori dağılımını göstermek istiyoruz)
            category_filter_data = date_filtered_data
            if selected_segments and segment_col:
                segments_set = set(selected_segments)
                category_filter_data = [
                    row
                    for row in category_filter_data
                    if str(row.get(segment_col, "")).strip().rstrip("/") in segments_set
                ]

            for row in category_filter_data:
                cat = row.get(category_col, "Unknown")
                if cat:
                    cat_clean = str(cat).strip().rstrip("/")
                    try:
                        revenue = float(
                            str(row.get(revenue_col, "0")).replace(",", ".")
                        )
                        category_revenue[cat_clean] += revenue
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse category revenue: {e}")
                        pass

            analytics["productCategories"] = [
                {"category": k, "revenue": v} for k, v in category_revenue.items()
            ]

        # Marka bazlı gelir - filtered_data'yı kullan (kategori/segment/ay/yıl filtreleri zaten uygulandı)
        brand_revenue = defaultdict(float)
        brand_count = defaultdict(int)
        if brand_col and revenue_col:
            # Zaten filtrelenmiş veriyi kullan, sadece markaya göre grupla
            brand_filter_data = filtered_data
            # Marka filtresi yoksa tüm markaları göster, varsa sadece seçili markaları
            if selected_brands:
                brands_set = set(selected_brands)
                brand_filter_data = [
                    row
                    for row in brand_filter_data
                    if str(row.get(brand_col, "")).strip().rstrip("/") in brands_set
                ]

            for row in brand_filter_data:
                brand = row.get(brand_col, "")
                if brand:
                    brand_clean = str(brand).strip().rstrip("/")
                    try:
                        revenue = float(
                            str(row.get(revenue_col, "0")).replace(",", ".")
                        )
                        brand_revenue[brand_clean] += revenue
                        brand_count[brand_clean] += 1
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse brand revenue: {e}")
                        pass

            analytics["brandRevenue"] = [
                {"name": k, "revenue": v, "count": brand_count[k]}
                for k, v in sorted(
                    brand_revenue.items(), key=lambda x: x[1], reverse=True
                )
            ]

        # Alt Kategori 1 bazlı gelir
        alt_kat_1_revenue = defaultdict(float)
        if alt_kategori_1_col and revenue_col:
            for row in filtered_data:
                alt_kat_1 = row.get(alt_kategori_1_col, "")
                if alt_kat_1:
                    alt_kat_1_clean = str(alt_kat_1).strip().rstrip("/")
                    try:
                        revenue = float(
                            str(row.get(revenue_col, "0")).replace(",", ".")
                        )
                        alt_kat_1_revenue[alt_kat_1_clean] += revenue
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse alt kategori 1 revenue: {e}")
                        pass

            analytics["altKategori1Revenue"] = [
                {"name": k, "revenue": v}
                for k, v in sorted(
                    alt_kat_1_revenue.items(), key=lambda x: x[1], reverse=True
                )
            ]

        # Alt Kategori 2 bazlı gelir
        alt_kat_2_revenue = defaultdict(float)
        if alt_kategori_2_col and revenue_col:
            for row in filtered_data:
                alt_kat_2 = row.get(alt_kategori_2_col, "")
                if alt_kat_2:
                    alt_kat_2_clean = str(alt_kat_2).strip().rstrip("/")
                    try:
                        revenue = float(
                            str(row.get(revenue_col, "0")).replace(",", ".")
                        )
                        alt_kat_2_revenue[alt_kat_2_clean] += revenue
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse alt kategori 2 revenue: {e}")
                        pass

            analytics["altKategori2Revenue"] = [
                {"name": k, "revenue": v}
                for k, v in sorted(
                    alt_kat_2_revenue.items(), key=lambda x: x[1], reverse=True
                )
            ]

        # Ürün bazlı gelir - filtered_data'yı kullan (tüm filtreler zaten uygulandı)
        product_revenue = defaultdict(float)
        product_count = defaultdict(int)
        product_brand = {}
        product_category = {}
        if product_col and revenue_col:
            # Zaten filtrelenmiş veriyi kullan
            product_filter_data = filtered_data

            for row in product_filter_data:
                product = row.get(product_col, "")
                if product:
                    product_clean = str(product).strip()
                    try:
                        revenue = float(
                            str(row.get(revenue_col, "0")).replace(",", ".")
                        )
                        product_revenue[product_clean] += revenue
                        product_count[product_clean] += 1
                        # İlk karşılaşılan marka ve kategoriyi sakla
                        if product_clean not in product_brand:
                            product_brand[product_clean] = (
                                str(row.get(brand_col, "")).strip().rstrip("/")
                                if brand_col
                                else ""
                            )
                            product_category[product_clean] = (
                                str(row.get(category_col, "")).strip().rstrip("/")
                                if category_col
                                else ""
                            )
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse product revenue: {e}")
                        pass

            analytics["productRevenue"] = [
                {
                    "name": k,
                    "revenue": v,
                    "count": product_count[k],
                    "brand": product_brand.get(k, ""),
                    "category": product_category.get(k, ""),
                }
                for k, v in sorted(
                    product_revenue.items(), key=lambda x: x[1], reverse=True
                )[:50]  # Top 50 ürün
            ]

        # Kategori hiyerarşisi oluştur - 4 seviye: Üst → Ana → Alt1 → Alt2
        category_hierarchy = {}
        if category_col:
            for row in data:
                ana_kat = str(row.get(category_col, "")).strip().rstrip("/")
                ust_kat_direct = (
                    str(row.get(ust_kategori_col, "")).strip().rstrip("/")
                    if ust_kategori_col
                    else ""
                )
                alt_kat_1 = (
                    str(row.get(alt_kategori_1_col, "")).strip().rstrip("/")
                    if alt_kategori_1_col
                    else ""
                )
                alt_kat_2 = (
                    str(row.get(alt_kategori_2_col, "")).strip().rstrip("/")
                    if alt_kategori_2_col
                    else ""
                )

                if ana_kat:
                    # Üst kategori varsa onu kullan, yoksa ana kategoriden türet
                    ust_kat = ust_kat_direct or categorize_to_parent(ana_kat)

                    # Üst kategori yoksa oluştur
                    if ust_kat not in category_hierarchy:
                        category_hierarchy[ust_kat] = {}

                    # Ana kategori yoksa oluştur
                    if ana_kat not in category_hierarchy[ust_kat]:
                        category_hierarchy[ust_kat][ana_kat] = {}

                    # Alt kategori 1 varsa ekle
                    if alt_kat_1:
                        if alt_kat_1 not in category_hierarchy[ust_kat][ana_kat]:
                            category_hierarchy[ust_kat][ana_kat][alt_kat_1] = set()

                        # Alt kategori 2 varsa ekle
                        if alt_kat_2:
                            category_hierarchy[ust_kat][ana_kat][alt_kat_1].add(
                                alt_kat_2
                            )

        # Set'leri listeye çevir (JSON serialization için)
        for ust_kat in category_hierarchy:
            for ana_kat in category_hierarchy[ust_kat]:
                for alt_kat_1 in category_hierarchy[ust_kat][ana_kat]:
                    category_hierarchy[ust_kat][ana_kat][alt_kat_1] = list(
                        category_hierarchy[ust_kat][ana_kat][alt_kat_1]
                    )

        # Kategori bazlı marka listesi oluştur
        brand_by_category = {}
        if brand_col and category_col:
            for row in data:
                ana_kat = str(row.get(category_col, "")).strip().rstrip("/")
                brand = str(row.get(brand_col, "")).strip().rstrip("/")

                if ana_kat and brand:
                    if ana_kat not in brand_by_category:
                        brand_by_category[ana_kat] = set()
                    brand_by_category[ana_kat].add(brand)

            # Set'leri listeye çevir ve alfabetik sırala
            for cat in brand_by_category:
                brand_by_category[cat] = sorted(list(brand_by_category[cat]))

        # Maksimum değerleri hesapla
        max_values = {
            "maxSegmentCount": max(
                [s["count"] for s in analytics["customerSegments"]], default=1
            ),
            "maxSales": max([s["sales"] for s in analytics["salesByMonth"]], default=1),
            "maxRevenue": max(
                [c["revenue"] for c in analytics["productCategories"]], default=1
            ),
        }
        analytics["maxValues"] = max_values

        # Verideki tüm ay ve yılları bul
        available_months = set()
        available_years = set()
        if date_col:
            for row in data:
                date_value = row.get(date_col)
                if date_value:
                    try:
                        date_str = str(date_value).strip()
                        # Tarih formatı: dd.mm.yyyy
                        if "." in date_str:
                            parts = date_str.split(".")
                            if len(parts) == 3:
                                month = int(parts[1])
                                year = int(parts[2])
                                available_months.add(month)
                                available_years.add(year)
                        # ISO formatı: yyyy-mm-dd
                        elif "-" in date_str:
                            parts = date_str.split("-")
                            if len(parts) == 3:
                                year = int(parts[0])
                                month = int(parts[1])
                                available_months.add(month)
                                available_years.add(year)
                    except (ValueError, IndexError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse available date: {e}")
                        pass

        payload = {
            "analytics": analytics,
            "categoryHierarchy": category_hierarchy,
            "brandByCategory": brand_by_category,
            "columns": columns,
            "rowCount": len(data),
            "availableMonths": sorted(list(available_months)),
            "availableYears": sorted(list(available_years)),
        }
        _set_cached_datasource_analytics(cache_key, payload)
        return Response(payload, status=HTTP_200_OK)

    except DataSource.DoesNotExist:
        return Response({"error": "Veri kaynağı bulunamadı"}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_product_analytics(request, pk):
    """
    Ürünler sayfası için hiyerarşik veri ve analizler döndürür.
    Hiyerarşi: Ana Kategori -> Marka -> Alt Kategori -> Ürün (Gramaj/İsim)
    Filtreler: categories (list), brands (list), product_name (str)
    """
    # JWT token authentication
    user = get_user_from_request(request)
    if not user:
        return Response(
            {"error": "Geçersiz kullanıcı veya oturum"}, status=HTTP_401_UNAUTHORIZED
        )

    try:
        data_source = DataSource.objects.get(id=pk, user_id=user.id)
    except DataSource.DoesNotExist:
        return Response({"error": "Kaynak bulunamadı"}, status=HTTP_401_UNAUTHORIZED)

    # Parametreleri al
    filter_categories = request.GET.getlist("categories")
    filter_brands = request.GET.getlist("brands")
    filter_product = request.GET.get("product_name", "").strip()
    filter_product_names = request.GET.getlist("product_names")

    # Tarih filtreleri
    selected_year = request.GET.get("year", "")
    selected_month = request.GET.get("month", "")
    start_date_str = request.GET.get("start_date") or request.GET.get("startDate")
    end_date_str = request.GET.get("end_date") or request.GET.get("endDate")

    # Yeni Filtreler
    filter_customer_type = request.GET.get("customer_type", "").strip()
    filter_approval_status = request.GET.get("approval_status", "").strip()
    filter_region = request.GET.get("region", "").strip()

    import sqlite3
    import os
    import calendar
    from datetime import datetime

    # Database connection (use configured backend)
    try:
        conn = db_engine.get_connection()
        try:
            if db_engine.DB_BACKEND == "postgresql":
                from psycopg2.extras import RealDictCursor

                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()

            # Tarih aralığı belirleme
            calc_start = None
            calc_end = None

            if start_date_str:
                try:
                    calc_start = datetime.strptime(start_date_str, "%Y-%m-%d")
                except:
                    pass
            if end_date_str:
                try:
                    calc_end = datetime.strptime(end_date_str, "%Y-%m-%d")
                except:
                    pass

            if not calc_start and selected_year:
                y = int(selected_year)
                if selected_month:
                    m = int(selected_month)
                    last_day = calendar.monthrange(y, m)[1]
                    calc_start = datetime(y, m, 1)
                    calc_end = datetime(y, m, last_day)
                else:
                    calc_start = datetime(y, 1, 1)
                    calc_end = datetime(y, 12, 31)
            elif not calc_start and selected_month and not selected_year:
                # Sadece ay seçildiğinde tüm yıllardaki o ay filtrelemesi için
                # calc_start/calc_end hesaplama, WHERE'de month filter kullanılacak
                pass

            # Bugün sınırını kontrol et
            if calc_end and calc_end > datetime.now():
                calc_end = datetime.now()

            # SQL WHERE oluşturma
            placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
            where_conditions = ["1=1"]
            params = []

            if calc_start:
                where_conditions.append(f"s.tarih >= {placeholder}")
                params.append(calc_start.strftime("%Y-%m-%d"))
            if calc_end:
                where_conditions.append(f"s.tarih <= {placeholder}")
                params.append(calc_end.strftime("%Y-%m-%d"))

            # Sadece ay seçildiğinde tüm yıllardaki o ayı filtrele
            if selected_month and not selected_year:
                if db_engine.DB_BACKEND == "postgresql":
                    where_conditions.append(f"TO_CHAR(s.tarih, 'MM') = {placeholder}")
                else:
                    where_conditions.append(f"substr(s.tarih, 6, 2) = {placeholder}")
                params.append(f"{int(selected_month):02d}")

            if filter_categories:
                # kategoriler ana, alt1 veya alt2 olabilir - hepsini kontrol et
                placeholders = ",".join([placeholder] * len(filter_categories))
                where_conditions.append(
                    f"(k.ana IN ({placeholders}) OR k.alt1 IN ({placeholders}) OR k.alt2 IN ({placeholders}))"
                )
                params.extend(filter_categories)  # ana için
                params.extend(filter_categories)  # alt1 için
                params.extend(filter_categories)  # alt2 için

            if filter_brands:
                placeholders = ",".join([placeholder] * len(filter_brands))
                where_conditions.append(f"m.ad IN ({placeholders})")
                params.extend(filter_brands)

            if filter_product:
                col_expr = db_engine.normalize_turkish_sql("u.ad")
                # Normalize parameter in SQL as well
                param_expr = placeholder
                if db_engine.DB_BACKEND == "postgresql":
                    param_expr = f"translate(lower({placeholder}), 'çğışıöü', 'cgisiou')"
                where_conditions.append(f"{col_expr} LIKE {param_expr}")
                params.append(f"%{filter_product}%")

            if filter_product_names:
                placeholders = ",".join([placeholder] * len(filter_product_names))
                where_conditions.append(f"u.ad IN ({placeholders})")
                params.extend(filter_product_names)

            # --- YENİ FİLTRELER ---
            if filter_customer_type:
                where_conditions.append(f"mus.tip = {placeholder}")
                params.append(filter_customer_type)

            if filter_approval_status:
                where_conditions.append(f"mus.onay_durumu = {placeholder}")
                # Handle 'Onaysız' mapping if needed, based on DB values
                # DB: 'ONAYSIZ', 'Onaylı'. Frontend: 'Onaysız', 'Onaylı'
                val = filter_approval_status
                if val == "Onaysız":
                    val = "ONAYSIZ"
                elif val == "ONAYSIZ":
                    val = "ONAYSIZ"
                params.append(val)

            if filter_region:
                where_conditions.append(f"{db_engine.bolge_expr('mag.bolge')} = {placeholder}")
                params.append(filter_region)
            # ----------------------

            # Check if we can use summary tables (Fast Path)
            # Only if NO customer-level filters are applied
            use_pds = not any([filter_customer_type, filter_approval_status, filter_region])
            
            where_clause = " AND ".join(where_conditions)

            # Base JOINs for all queries
            # LEFT JOIN musteriler to support customer_type filtering
            # LEFT JOIN magazalar to support region filtering
            base_joins = """
                LEFT JOIN urunler u ON s.urun_id = u.id
                LEFT JOIN kategoriler k ON u.kategori_id = k.id
                LEFT JOIN markalar m ON u.marka_id = m.id
                LEFT JOIN musteriler mus ON s.musteri_id = mus.id
                LEFT JOIN magazalar mag ON s.magaza_id = mag.id
            """

            # 1+2. KPI + Counts — tek sorguda (round-trip azalt)
            if use_pds:
                # Fast path using product_daily_summary
                cursor.execute(
                    f"""
                    SELECT 
                        SUM(pds.revenue) as total_revenue,
                        SUM(pds.unit_count) as total_units,
                        COUNT(DISTINCT pds.urun_id) as prod_count,
                        COUNT(DISTINCT u.marka_id) as brand_count,
                        COUNT(DISTINCT u.kategori_id) as cat_count
                    FROM product_daily_summary pds
                    JOIN urunler u ON pds.urun_id = u.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    WHERE {where_clause.replace('s.', 'pds.')}
                """,
                    params,
                )
                res = cursor.fetchone()
                
                # total_customers optimization
                is_unfiltered = where_clause.strip() == "1=1" or not (filter_start_date or filter_end_date or filter_categories or filter_brands or filter_products)
                
                kpi_row = {
                    "total_revenue": res["total_revenue"] or 0,
                    "total_quantity": res["total_units"] or 0,
                    "total_receipts": 0,
                    "total_customers": 0,
                    "prod_count": res["prod_count"] or 0,
                    "brand_count": res["brand_count"] or 0,
                    "cat_count": res["cat_count"] or 0
                }
                
                if is_unfiltered:
                    cursor.execute("SELECT COUNT(*) as cnt FROM musteriler")
                    kpi_row["total_customers"] = cursor.fetchone()['cnt'] or 0
                
                # Receipts fallback from gunlukciroozet if possible
                if not filter_categories and not filter_brands:
                    cursor.execute(f"SELECT SUM(toplam_ciro) as rev, SUM(toplam_fis) as fis FROM gunlukciroozet WHERE {where_clause.replace('s.tarih', 'tarih')}", params[:2])
                    ciro_res = cursor.fetchone()
                    kpi_row["total_receipts"] = ciro_res["fis"] or 0
            else:
                # Slow path using satislar
                cursor.execute(
                    f"""
                    SELECT 
                        SUM(s.tutar) as total_revenue,
                        SUM(s.miktar) as total_quantity,
                        COUNT(DISTINCT s.fis_no) as total_receipts,
                        COUNT(DISTINCT s.musteri_id) as total_customers,
                        COUNT(DISTINCT s.urun_id) as prod_count,
                        COUNT(DISTINCT u.marka_id) as brand_count,
                        COUNT(DISTINCT u.kategori_id) as cat_count
                    FROM satislar s
                    {base_joins}
                    WHERE {where_clause}
                """,
                    params,
                )
                kpi_row = cursor.fetchone()
            
            combined_row = kpi_row
            kpi_row = combined_row  # backward compat
            counts = [
                combined_row["prod_count"] or 0,
                combined_row["brand_count"] or 0,
                combined_row["cat_count"] or 0,
            ]

            # 3. Top Products (Optimized: Two-Step)
            if use_pds:
                cursor.execute(
                    f"""
                    SELECT pds.urun_id, SUM(pds.revenue) as sales, SUM(pds.unit_count) as count
                    FROM product_daily_summary pds
                    JOIN urunler u ON pds.urun_id = u.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    WHERE {where_clause.replace('s.', 'pds.')}
                    GROUP BY pds.urun_id
                    ORDER BY sales DESC
                    LIMIT 50
                """,
                    params,
                )
            else:
                cursor.execute(
                    f"""
                    SELECT s.urun_id, SUM(s.tutar) as sales, SUM(s.miktar) as count
                    FROM satislar s
                    {base_joins}
                    WHERE {where_clause}
                    GROUP BY s.urun_id
                    ORDER BY sales DESC
                    LIMIT 50
                """,
                    params,
                )
            top_rows = cursor.fetchall()
            
            top_products = []
            if top_rows:
                target_ids = [r["urun_id"] for r in top_rows]
                placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
                placeholders = ",".join([placeholder] * len(target_ids))
                
                # Step 2: Get metadata only for top products
                # No complex joins on 'satislar' here!
                cursor.execute(
                    f"""
                    SELECT u.id as id, u.ad as name, m.ad as brand, k.ana as category,
                           upd.performanskategori as perf_kat, upd.hiztrendi as trend,
                           upd.stokdurumu as stok_durumu, upd.uyaridurumu as uyari,
                           kpo.pazar_payi as kat_payi, kpo.performans_kategori as kat_perf
                    FROM urunler u
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    LEFT JOIN urunperformansdetay upd ON u.id = upd.urunid
                    LEFT JOIN kategoriperformansozet kpo ON u.kategori_id = kpo.kategori_id
                    WHERE u.id IN ({placeholders})
                """,
                    target_ids,
                )
                stats_map = {r["id"]: r for r in cursor.fetchall()}
                
                # Optimization: Avoid satislar for customerCount in the list
                is_unfiltered_date = not (filter_start_date or filter_end_date)
                placeholders_ids = ",".join([placeholder] * len(target_ids))
                
                if is_unfiltered_date:
                    # Use life-time customer counts from urunperformansdetay
                    cursor.execute(
                        f"""
                        SELECT urunid as urun_id, toplammusterisayisi as musteri_sayisi
                        FROM urunperformansdetay
                        WHERE urunid IN ({placeholders_ids})
                        """,
                        target_ids
                    )
                else:
                    # Use product_daily_summary as an approximation (sum of daily unique)
                    # This is much faster than satislar and close enough for a dashboard list
                    cursor.execute(
                        f"""
                        SELECT urun_id, SUM(customer_count) as musteri_sayisi
                        FROM product_daily_summary
                        WHERE urun_id IN ({placeholders_ids})
                          AND {where_clause.replace('s.', 'pds.')}
                        GROUP BY urun_id
                        """,
                        target_ids + params,
                    )
                musteri_map = {r["urun_id"]: r["musteri_sayisi"] for r in cursor.fetchall()}

                for r in top_rows:
                    m = stats_map.get(r["urun_id"])
                    if not m: continue
                    top_products.append({
                        "id": r["urun_id"],
                        "name": m["name"],
                        "brand": m["brand"] or "-",
                        "category": m["category"] or "-",
                        "sales": r["sales"] or 0,
                        "count": r["count"] or 0,
                        "customerCount": musteri_map.get(r["urun_id"], 0),
                        "perf_kat": m["perf_kat"] or "Orta",
                        "trend": m["trend"] or "Stabil",
                        "stok_durumu": m["stok_durumu"] or "Normal",
                        "uyari": m["uyari"] or "Normal",
                        "kat_payi": m["kat_payi"] or 0,
                        "kat_perf": m["kat_perf"] or "Stabil",
                    })

            # 4. Sales trend — aylık bazda topla
            if use_pds:
                month_expr_pds = db_engine.strftime_expr('%Y-%m', 'pds.tarih')
                trend_sql = f"""
                    SELECT {month_expr_pds} as sale_month, SUM(pds.revenue) as monthly_sales
                    FROM product_daily_summary pds
                    JOIN urunler u ON pds.urun_id = u.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    WHERE {where_clause.replace('s.', 'pds.')}
                    GROUP BY {month_expr_pds}
                    ORDER BY sale_month
                """
            else:
                month_expr = db_engine.strftime_expr('%Y-%m', 's.tarih')
                trend_sql = f"""
                    SELECT {month_expr} as sale_month, SUM(s.tutar) as monthly_sales
                    FROM satislar s
                    {base_joins}
                    WHERE {where_clause}
                    GROUP BY {month_expr}
                    ORDER BY sale_month
                """
            cursor.execute(trend_sql, params)
            sales_by_month = [
                {"month": r["sale_month"], "sales": r["monthly_sales"] or 0}
                for r in cursor.fetchall()
            ]

            # 5. Top Brands
            if use_pds:
                cursor.execute(
                    f"""
                    SELECT m.ad as brand_name, SUM(pds.revenue) as brand_sales
                    FROM product_daily_summary pds
                    JOIN urunler u ON pds.urun_id = u.id
                    LEFT JOIN markalar m ON u.marka_id = m.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    WHERE {where_clause.replace('s.', 'pds.')}
                    GROUP BY m.id, m.ad
                    ORDER BY brand_sales DESC
                    LIMIT 10
                """,
                    params,
                )
            else:
                cursor.execute(
                    f"""
                    SELECT m.ad as brand_name, SUM(s.tutar) as brand_sales
                    FROM satislar s
                    {base_joins}
                    WHERE {where_clause}
                    GROUP BY m.id, m.ad
                    ORDER BY brand_sales DESC
                    LIMIT 10
                """,
                    params,
                )
            top_brands = [
                {"name": r["brand_name"] or "Diğer", "sales": r["brand_sales"] or 0}
                for r in cursor.fetchall()
            ]

            total_revenue = kpi_row["total_revenue"] or 0
            total_quantity = kpi_row.get("total_quantity") or 0
            total_receipts = kpi_row["total_receipts"] or 0
            avg_order_value = round(total_revenue / total_receipts, 2) if total_receipts > 0 else 0
            avg_product_price = round(total_revenue / total_quantity, 2) if total_quantity > 0 else 0

            analytics = {
                "totalRevenue": total_revenue,
                "totalQuantity": total_quantity,
                "totalProducts": counts[0],
                "totalBrands": counts[1],
                "totalCategories": counts[2],
                "totalReceipts": total_receipts,
                "averageOrderValue": avg_order_value,
                "averageProductPrice": avg_product_price,
                "hasProductColumn": True,
                "priceRanges": [],
                "topBrands": top_brands,
                "topProducts": top_products,
                "salesByMonth": sales_by_month,
            }

            return Response(
                {"analytics": analytics, "availableYears": get_available_years()},
                status=HTTP_200_OK,
            )
        finally:
            db_engine.release_connection(conn)
    except Exception as e:
        logger.error(f"Product Analytics SQL Error: {e}")
        # Fallback to legacy is intentionally removed for DB sources to avoid slow/incomplete results

    # ========== LEGACY YOL (CSV/JSON için) ==========
    try:
        data = get_datasource_data(data_source)
        if not data:
            return Response({"error": "Veri boş"}, status=404)

        first_row = data[0]
        columns = list(first_row.keys())
        cols = detect_columns(columns, data_source.column_mapping)
        revenue_col, date_col, product_col, brand_col = (
            cols["revenue_col"],
            cols["date_col"],
            cols["product_col"],
            cols["brand_col"],
        )
        category_col = cols["category_col"]

        # Filtreleme ve hiyerarşi oluşturma (Eski yöntem)
        # (NOT: Bu kısım sadece CSV yüklemeleri için çalışır ve yavaştır)
        unique_products = set()
        total_revenue = 0
        filtered_data = []  # ... filters applied ...
        # (Implementation omitted for brevity as User focus is SQLite)
        return Response(
            {
                "message": "CSV/JSON analytics not fully optimized, please use Database source"
            },
            status=200,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# STUB: get_rfm_analysis - Real implementation is in rfm_view.py:541
# TODO: Remove this stub when all callers are migrated
# RFM Analysis Endpoint
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_rfm_analysis(request, data_source_id):
    """RFM analizi endpoint'i - Tarih filtreleme destekli"""
    try:
        # Filtre varsa cache'i atla
        has_filters = any(
            [
                request.GET.get("year"),
                request.GET.get("month"),
                request.GET.get("start_date"),
                request.GET.get("end_date"),
            ]
        )

        if not has_filters:
            cached = get_cached_data("rfm", data_source_id)
            if cached:
                return Response(cached)

        user = get_user_from_request(request)

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)

        data = get_datasource_data(data_source)

        if not data or len(data) == 0:
            return Response({"segments": [], "distribution": {}, "topCustomers": []})

        # Tarih filtreleme uygula
        data = filter_data_by_date(data, request)

        # Sütun tespiti
        first_row_keys = list(data[0].keys()) if data else []
        columns = detect_columns(first_row_keys, data_source.column_mapping)

        customer_id_col = columns.get("customer_id_col") or "Müşteri Kodu"
        date_col = columns.get("date_col") or "TARİH"
        amount_col = columns.get("revenue_col") or "Satış Tutarı"

        from datetime import datetime

        now = datetime.now()

        # Tarih parse fonksiyonu - cache ile optimize
        date_cache = {}

        def parse_date(d):
            if not d:
                return None
            if d in date_cache:
                return date_cache[d]
            try:
                result = datetime.strptime(str(d), "%d.%m.%Y")
                date_cache[d] = result
                return result
            except (ValueError, TypeError):
                try:
                    result = datetime.strptime(str(d), "%Y-%m-%d")
                    date_cache[d] = result
                    return result
                except (ValueError, TypeError):
                    date_cache[d] = None
                    return None

        # Tek döngüde tüm hesaplamaları yap
        customer_data = {}
        for row in data:
            customer_id = row.get(customer_id_col)
            if not customer_id:
                continue

            try:
                amount = float(str(row.get(amount_col, 0)).replace(",", "."))
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"Failed to parse amount value: {e}")
                amount = 0

            if customer_id not in customer_data:
                customer_data[customer_id] = {
                    "last_date": None,
                    "frequency": 0,
                    "monetary": 0,
                }

            customer_data[customer_id]["frequency"] += 1
            customer_data[customer_id]["monetary"] += amount

            # Sadece en son tarihi tut
            date_val = parse_date(row.get(date_col))
            if date_val:
                if (
                    customer_data[customer_id]["last_date"] is None
                    or date_val > customer_data[customer_id]["last_date"]
                ):
                    customer_data[customer_id]["last_date"] = date_val

        if not customer_data:
            return Response({"segments": [], "distribution": {}, "topCustomers": []})

        # RFM skorları ve segmentasyon - tek döngüde
        segments = {
            "Şampiyonlar": [],
            "Sadık Müşteriler": [],
            "Potansiyel Sadıklar": [],
            "Risk Altında": [],
            "Kayıp": [],
        }
        colors = {
            "Şampiyonlar": "#10b981",
            "Sadık Müşteriler": "#3b82f6",
            "Potansiyel Sadıklar": "#8b5cf6",
            "Risk Altında": "#f59e0b",
            "Kayıp": "#ef4444",
        }

        # Distribution sayaçları
        dist_recency = [0, 0, 0, 0]  # 0-30, 31-60, 61-90, 90+
        dist_frequency = [0, 0, 0, 0]  # 1-2, 3-5, 6-10, 10+
        dist_monetary = [0, 0, 0, 0]  # 0-1000, 1001-5000, 5001-10000, 10000+

        rfm_list = []
        for customer_id, info in customer_data.items():
            recency = (now - info["last_date"]).days if info["last_date"] else 365
            frequency = info["frequency"]
            monetary = round(info["monetary"], 0)

            # Distribution sayaçları
            if recency <= 30:
                dist_recency[0] += 1
            elif recency <= 60:
                dist_recency[1] += 1
            elif recency <= 90:
                dist_recency[2] += 1
            else:
                dist_recency[3] += 1

            if frequency <= 2:
                dist_frequency[0] += 1
            elif frequency <= 5:
                dist_frequency[1] += 1
            elif frequency <= 10:
                dist_frequency[2] += 1
            else:
                dist_frequency[3] += 1

            if monetary <= 1000:
                dist_monetary[0] += 1
            elif monetary <= 5000:
                dist_monetary[1] += 1
            elif monetary <= 10000:
                dist_monetary[2] += 1
            else:
                dist_monetary[3] += 1

            # RFM skorları
            r_score = (
                5
                if recency <= 30
                else 4
                if recency <= 60
                else 3
                if recency <= 90
                else 2
                if recency <= 180
                else 1
            )
            f_score = (
                5
                if frequency >= 10
                else 4
                if frequency >= 6
                else 3
                if frequency >= 3
                else 2
                if frequency >= 2
                else 1
            )
            m_score = (
                5
                if monetary >= 10000
                else 4
                if monetary >= 5000
                else 3
                if monetary >= 1000
                else 2
                if monetary >= 500
                else 1
            )

            avg_score = (r_score + f_score + m_score) / 3

            customer_rfm = {
                "customer_id": str(customer_id),
                "recency": recency,
                "frequency": frequency,
                "monetary": monetary,
            }
            rfm_list.append(customer_rfm)

            if avg_score >= 4.5:
                segments["Şampiyonlar"].append(customer_rfm)
            elif avg_score >= 3.5:
                segments["Sadık Müşteriler"].append(customer_rfm)
            elif avg_score >= 2.5:
                segments["Potansiyel Sadıklar"].append(customer_rfm)
            elif avg_score >= 1.5:
                segments["Risk Altında"].append(customer_rfm)
            else:
                segments["Kayıp"].append(customer_rfm)

        # Segment özeti
        segment_summary = []
        for name, customers in segments.items():
            if customers:
                segment_summary.append(
                    {
                        "name": name,
                        "count": len(customers),
                        "recency": round(
                            sum(c["recency"] for c in customers) / len(customers), 0
                        ),
                        "frequency": round(
                            sum(c["frequency"] for c in customers) / len(customers), 1
                        ),
                        "monetary": round(
                            sum(c["monetary"] for c in customers) / len(customers), 0
                        ),
                        "color": colors[name],
                    }
                )

        distribution = {
            "recency": [
                {"range": "0-30 gün", "count": dist_recency[0]},
                {"range": "31-60 gün", "count": dist_recency[1]},
                {"range": "61-90 gün", "count": dist_recency[2]},
                {"range": "90+ gün", "count": dist_recency[3]},
            ],
            "frequency": [
                {"range": "1-2", "count": dist_frequency[0]},
                {"range": "3-5", "count": dist_frequency[1]},
                {"range": "6-10", "count": dist_frequency[2]},
                {"range": "10+", "count": dist_frequency[3]},
            ],
            "monetary": [
                {"range": "0-1.000", "count": dist_monetary[0]},
                {"range": "1.001-5.000", "count": dist_monetary[1]},
                {"range": "5.001-10.000", "count": dist_monetary[2]},
                {"range": "10.000+", "count": dist_monetary[3]},
            ],
        }

        # Top müşteriler
        top_customers = sorted(rfm_list, key=lambda x: x["monetary"], reverse=True)[:10]

        result = {
            "segments": segment_summary,
            "distribution": distribution,
            "topCustomers": top_customers,
        }

        # Cache'e kaydet (SADECE filtresiz isteklerde)
        # Aksi halde filtreli sonuçlar cache'i ezip "Filtreleri Temizle" sonrası
        # yanlış (hala filtreli) veri dönmesine sebep olur.
        if not has_filters:
            set_cached_data("rfm", data_source_id, result)

        return Response(result)

    except DataSource.DoesNotExist:
        return Response({"error": "Veri kaynağı bulunamadı"}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# STUB: get_churn_analysis - Real implementation is in churn_view.py:18
# TODO: Remove this stub when all callers are migrated
# Churn Analysis Endpoint
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_churn_analysis(request, data_source_id):
    """Churn analizi endpoint'i - Tarih filtreleme destekli"""
    try:
        # Filtre varsa cache'i atla
        has_filters = any(
            [
                request.GET.get("year"),
                request.GET.get("month"),
                request.GET.get("start_date"),
                request.GET.get("end_date"),
            ]
        )

        if not has_filters:
            cached = get_cached_data("churn", data_source_id)
            if cached:
                return Response(cached)

        user = get_user_from_request(request)

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)
        data = get_datasource_data(data_source)

        if not data or len(data) == 0:
            return Response(
                {
                    "summary": {
                        "totalCustomers": 0,
                        "activeCustomers": 0,
                        "churnedCustomers": 0,
                        "churnRate": 0,
                        "atRiskCustomers": 0,
                    },
                    "churnByMonth": [],
                    "riskFactors": [],
                    "atRiskCustomers": [],
                }
            )

        # Tarih filtreleme uygula
        data = filter_data_by_date(data, request)

        # Sütun isimlerini detect et
        first_row_keys = list(data[0].keys()) if data else []
        columns = detect_columns(first_row_keys, data_source.column_mapping)

        customer_id_col = columns.get("customer_id_col") or "Müşteri Kodu"
        date_col = columns.get("date_col") or "TARİH"

        def parse_date(d):
            if not d:
                return None
            if isinstance(d, datetime):
                return d
            try:
                for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
                    try:
                        return datetime.strptime(str(d), fmt)
                    except (ValueError, TypeError):
                        continue
            except (ValueError, TypeError, AttributeError):
                pass
            return None

        # Customer activity tracking
        customer_activity = {}
        for row in data:
            customer_id = row.get(customer_id_col)
            if not customer_id:
                continue

            date_val = row.get(date_col)
            parsed_date = parse_date(date_val)
            if customer_id not in customer_activity:
                customer_activity[customer_id] = []
            if parsed_date:
                customer_activity[customer_id].append(parsed_date)

        if not customer_activity:
            return Response(
                {
                    "summary": {
                        "totalCustomers": 0,
                        "activeCustomers": 0,
                        "churnedCustomers": 0,
                        "churnRate": 0,
                        "atRiskCustomers": 0,
                    },
                    "churnByMonth": [],
                    "riskFactors": [],
                    "atRiskCustomers": [],
                }
            )

        now = datetime.now()
        churn_threshold_days = 90

        active_customers = 0
        churned_customers = 0
        at_risk_customers = 0

        for customer_id, dates in customer_activity.items():
            if not dates:
                churned_customers += 1
                continue

            last_date = max(dates)
            days_since = (now - last_date).days

            if days_since <= 30:
                active_customers += 1
            elif days_since <= churn_threshold_days:
                at_risk_customers += 1
            else:
                churned_customers += 1

        total_customers = len(customer_activity)
        churn_rate = (
            (churned_customers / total_customers * 100) if total_customers > 0 else 0
        )

        summary = {
            "totalCustomers": total_customers,
            "activeCustomers": active_customers,
            "churnedCustomers": churned_customers,
            "churnRate": round(churn_rate, 1),
            "atRiskCustomers": at_risk_customers,
        }

        result = {
            "summary": summary,
            "churnByMonth": [],
            "riskFactors": [],
            "atRiskCustomers": [],
        }

        # Cache'e kaydet (SADECE filtresiz isteklerde)
        # Aksi halde filtreli sonuçlar cache'i ezip "Filtreleri Temizle" sonrası
        # yanlış (hala filtreli) veri dönmesine sebep olur.
        if not has_filters:
            set_cached_data("churn", data_source_id, result)

        return Response(result)

    except DataSource.DoesNotExist:
        return Response({"error": "Veri kaynağı bulunamadı"}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# STUB: get_clv_analysis - Real implementation is in clv_view.py:203
# TODO: Remove this stub when all callers are migrated
# Customer Lifetime Value Endpoint
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_clv_analysis(request, data_source_id):
    """CLV analizi endpoint'i - Tarih filtreleme destekli"""
    try:
        # Filtre varsa cache'i atla
        has_filters = any(
            [
                request.GET.get("year"),
                request.GET.get("month"),
                request.GET.get("start_date"),
                request.GET.get("end_date"),
            ]
        )

        if not has_filters:
            cached = get_cached_data("clv", data_source_id)
            if cached:
                return Response(cached)

        user = get_user_from_request(request)

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)
        data = get_datasource_data(data_source)

        if not data or len(data) == 0:
            return Response(
                {
                    "summary": {
                        "averageCLV": 0,
                        "totalCLV": 0,
                        "customerCount": 0,
                        "avgLifespan": 0,
                        "topCLV": 0,
                    },
                    "clvSegments": [],
                    "predictedGrowth": [],
                }
            )

        # Tarih filtreleme uygula
        data = filter_data_by_date(data, request)

        # Sütun isimlerini detect et
        first_row_keys = list(data[0].keys()) if data else []
        columns = detect_columns(first_row_keys, data_source.column_mapping)

        customer_id_col = columns.get("customer_id_col") or "Müşteri Kodu"
        amount_col = columns.get("revenue_col") or "Satış Tutarı"

        # Customer CLV hesaplama
        customer_clv = {}
        for row in data:
            customer_id = row.get(customer_id_col)
            if not customer_id:
                continue

            try:
                amount = float(str(row.get(amount_col, 0)).replace(",", "."))
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug(f"Failed to parse amount value: {e}")
                amount = 0

            if customer_id not in customer_clv:
                customer_clv[customer_id] = 0
            customer_clv[customer_id] += amount

        if not customer_clv:
            return Response(
                {
                    "summary": {
                        "averageCLV": 0,
                        "totalCLV": 0,
                        "customerCount": 0,
                        "avgLifespan": 0,
                        "topCLV": 0,
                    },
                    "clvSegments": [],
                    "predictedGrowth": [],
                }
            )

        avg_clv = sum(customer_clv.values()) / len(customer_clv)
        total_clv = sum(customer_clv.values())
        top_clv = max(customer_clv.values())

        # CLV Segmentlerini hesapla
        clv_values = sorted(customer_clv.values(), reverse=True)
        segments = []

        n = len(clv_values)
        platinum_threshold = clv_values[int(n * 0.05)] if n > 20 else (top_clv * 0.8 if top_clv > 0 else 1)
        gold_threshold     = clv_values[int(n * 0.15)] if n > 20 else (top_clv * 0.5 if top_clv > 0 else 1)
        silver_threshold   = clv_values[int(n * 0.35)] if n > 20 else (top_clv * 0.25 if top_clv > 0 else 1)
        bronze_threshold   = clv_values[int(n * 0.60)] if n > 20 else (top_clv * 0.1 if top_clv > 0 else 1)

        platinum = [v for v in customer_clv.values() if v >= platinum_threshold]
        gold = [
            v for v in customer_clv.values() if gold_threshold <= v < platinum_threshold
        ]
        silver = [
            v for v in customer_clv.values() if silver_threshold <= v < gold_threshold
        ]
        bronze = [
            v for v in customer_clv.values() if bronze_threshold <= v < silver_threshold
        ]
        basic = [v for v in customer_clv.values() if v < bronze_threshold]

        if platinum:
            segments.append(
                {
                    "segment": "Platinum",
                    "customers": len(platinum),
                    "avgCLV": round(sum(platinum) / len(platinum), 2),
                    "totalValue": round(sum(platinum), 2),
                    "color": "#9333ea",
                }
            )
        if gold:
            segments.append(
                {
                    "segment": "Gold",
                    "customers": len(gold),
                    "avgCLV": round(sum(gold) / len(gold), 2),
                    "totalValue": round(sum(gold), 2),
                    "color": "#f59e0b",
                }
            )
        if silver:
            segments.append(
                {
                    "segment": "Silver",
                    "customers": len(silver),
                    "avgCLV": round(sum(silver) / len(silver), 2),
                    "totalValue": round(sum(silver), 2),
                    "color": "#6b7280",
                }
            )
        if bronze:
            segments.append(
                {
                    "segment": "Bronze",
                    "customers": len(bronze),
                    "avgCLV": round(sum(bronze) / len(bronze), 2),
                    "totalValue": round(sum(bronze), 2),
                    "color": "#cd7f32",
                }
            )
        if basic:
            segments.append(
                {
                    "segment": "Basic",
                    "customers": len(basic),
                    "avgCLV": round(sum(basic) / len(basic), 2),
                    "totalValue": round(sum(basic), 2),
                    "color": "#94a3b8",
                }
            )

        # Müşteri başına sipariş sayısı ve ortalama hesapla
        customer_orders = {}
        customer_first_purchase = {}
        customer_last_purchase = {}
        date_col = columns.get("date_col") or "Tarih"

        for row in data:
            customer_id = row.get(customer_id_col)
            if not customer_id:
                continue
            if customer_id not in customer_orders:
                customer_orders[customer_id] = 0
            customer_orders[customer_id] += 1

            # Tarih hesaplama
            date_str = row.get(date_col)
            if date_str:
                try:
                    if isinstance(date_str, str):
                        parsed_result = parse_date_fast(date_str)
                        parsed_date = parsed_result[0] if parsed_result else None
                        if parsed_date:
                            if (
                                customer_id not in customer_first_purchase
                                or parsed_date < customer_first_purchase[customer_id]
                            ):
                                customer_first_purchase[customer_id] = parsed_date
                            if (
                                customer_id not in customer_last_purchase
                                or parsed_date > customer_last_purchase[customer_id]
                            ):
                                customer_last_purchase[customer_id] = parsed_date
                except (ValueError, TypeError, AttributeError, IndexError) as e:
                    logger.debug(f"Failed to parse customer purchase date: {e}")
                    pass

        # Faktörleri hesapla
        total_orders = sum(customer_orders.values())
        avg_order_count = total_orders / len(customer_orders) if customer_orders else 0
        avg_order_value = avg_clv / avg_order_count if avg_order_count > 0 else avg_clv

        # Müşteri ömrü hesapla (ay cinsinden)
        lifespans = []
        for cid in customer_first_purchase:
            if cid in customer_last_purchase:
                diff = (customer_last_purchase[cid] - customer_first_purchase[cid]).days
                lifespans.append(max(diff / 30, 1))  # En az 1 ay
        avg_lifespan = sum(lifespans) / len(lifespans) if lifespans else 12

        # Faktör ağırlıklarını dinamik hesapla
        # Normalize edilmiş değerler (0-100 arası)
        factors = []
        if avg_order_value > 0:
            factors.append(
                {
                    "factor": "Ortalama Sipariş Değeri",
                    "weight": min(
                        round(avg_order_value / (total_clv / len(customer_clv)) * 35),
                        40,
                    ),
                    "color": "#6366f1",
                }
            )
        if avg_order_count > 0:
            factors.append(
                {
                    "factor": "Alışveriş Sıklığı",
                    "weight": min(round(avg_order_count * 10), 35),
                    "color": "#10b981",
                }
            )
        if avg_lifespan > 0:
            factors.append(
                {
                    "factor": "Müşteri Ömrü",
                    "weight": min(round(avg_lifespan / 12 * 25), 30),
                    "color": "#f59e0b",
                }
            )
        factors.append(
            {
                "factor": "Sadakat",
                "weight": min(
                    round(
                        len([v for v in customer_orders.values() if v > 1])
                        / len(customer_orders)
                        * 20
                    )
                    if customer_orders
                    else 10,
                    25,
                ),
                "color": "#ec4899",
            }
        )

        summary = {
            "averageCLV": round(avg_clv, 2),
            "totalCLV": round(total_clv, 2),
            "customerCount": len(customer_clv),
            "avgLifespan": round(avg_lifespan, 1),
            "topCLV": round(top_clv, 2),
            "avgOrderValue": round(avg_order_value, 2),
            "avgOrderCount": round(avg_order_count, 1),
        }

        result = {
            "summary": summary,
            "clvSegments": segments,
            "clvFactors": factors,
            "predictedGrowth": [],
        }

        # Cache'e kaydet (SADECE filtresiz isteklerde)
        # Aksi halde filtreli sonuçlar cache'i ezip "Filtreleri Temizle" sonrası
        # yanlış (hala filtreli) veri dönmesine sebep olur.
        if not has_filters:
            set_cached_data("clv", data_source_id, result)

        return Response(result)

    except DataSource.DoesNotExist:
        return Response({"error": "Veri kaynağı bulunamadı"}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# Brand Report Endpoint


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_brand_report(request, data_source_id):
    """Marka raporu endpoint'i - Tarih filtreleme destekli"""
    try:
        # Filter-aware cache (keeps BrandReport fast without polluting baseline)
        has_filters = any(
            [
                request.GET.get("year"),
                request.GET.get("month"),
                request.GET.get("start_date"),
                request.GET.get("end_date"),
            ]
        )

        user = get_user_from_request(request)

        cache_key = _build_filter_cache_key(
            data_source_id, user.id if user else None, request
        )
        cached = _get_ttl_cache(
            _brand_report_cache, cache_key, _brand_report_cache_timeout
        )
        if cached is not None:
            return Response(cached)

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)

        import sqlite3
        import os
        from datetime import datetime

        is_database_source = (
            getattr(data_source, "type", "") == "database"
            or "sal" in getattr(data_source, "name", "").lower()
            or "sat" in getattr(data_source, "name", "").lower()
        )

        if is_database_source:
            try:
                conn = db_engine.get_connection()
                if db_engine.DB_BACKEND == "postgresql":
                    from psycopg2.extras import RealDictCursor

                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                else:
                    cursor = conn.cursor()

                # Parametreleri al
                year = request.GET.get("year")
                month = request.GET.get("month")
                start_date_str = request.GET.get("start_date") or request.GET.get(
                    "startDate"
                )
                end_date_str = request.GET.get("end_date") or request.GET.get("endDate")
                page = int(request.GET.get("page", 1))
                limit = int(request.GET.get("limit", 10))
                offset = (page - 1) * limit

                # Yeni filtreler
                placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
                segment = request.GET.get("segment")
                customer_type = request.GET.get("customer_type") or request.GET.get(
                    "customerType"
                )
                approval_status = request.GET.get("approval_status") or request.GET.get(
                    "approvalStatus"
                )
                region = request.GET.get("region")

                where_conditions = ["1=1"]
                params = []

                if start_date_str:
                    where_conditions.append(f"s.tarih >= {placeholder}")
                    params.append(start_date_str)
                if end_date_str:
                    where_conditions.append(f"s.tarih <= {placeholder}")
                    params.append(end_date_str)
                if year:
                    # Performans optimizasyonu: strftime yerine range-based filtreleme
                    # Index kullanımı için tarih aralığı olarak yıl filtresi
                    where_conditions.append(
                        f"s.tarih >= {placeholder} AND s.tarih < {placeholder}"
                    )
                    params.append(f"{year}-01-01")
                    params.append(f"{int(year) + 1}-01-01")
                if month:
                    if db_engine.DB_BACKEND == "postgresql":
                        where_conditions.append(f"EXTRACT(MONTH FROM s.tarih) = {placeholder}")
                        params.append(int(month))
                    else:
                        where_conditions.append(f"substr(s.tarih, 6, 2) = {placeholder}")
                        params.append(f"{int(month):02d}")

                if segment:
                    where_conditions.append(f"mu.rfm_segment = {placeholder}")
                    params.append(segment)
                if customer_type:
                    where_conditions.append(f"mu.tip = {placeholder}")
                    params.append(customer_type)
                if approval_status:
                    where_conditions.append(f"mu.onay_durumu = {placeholder}")
                    params.append(approval_status)
                if region:
                    where_conditions.append(f"{db_engine.bolge_expr('mg.bolge')} = {placeholder}")
                    params.append(region)

                # Kategori ve Marka Arama (Hem özet hem detay için)
                categories = (
                    request.GET.getlist("category")
                    or request.GET.getlist("category[]")
                    or request.GET.getlist("categories")
                    or request.GET.getlist("categories[]")
                )
                brand_search_term = request.GET.get("brand_search")

                # Helper for turkish lower
                def tr_lower(s):
                    if s is None:
                        return ""
                    if not isinstance(s, str):
                        s = str(s)
                    s = s.strip().replace("\xa0", " ")
                    s = s.replace("İ", "i").replace("I", "ı")
                    s = s.lower()
                    replacements = {
                        "ç": "c",
                        "ğ": "g",
                        "ö": "o",
                        "ş": "s",
                        "ü": "u",
                        "ı": "i",
                    }
                    for search, replace in replacements.items():
                        s = s.replace(search, replace)
                    return s

                # Legacy Path Filtreleri (satislar Tablosu İçin)
                if brand_search_term and len(brand_search_term) > 1:
                    where_conditions.append(f"m.ad LIKE {placeholder}")
                    params.append(f"%{brand_search_term}%")
                if categories:
                    cat_conds = []
                    for c in categories:
                        if not c:
                            continue
                        cat_conds.append(
                            f"(k.ana = {placeholder} OR k.alt1 = {placeholder} OR k.alt2 = {placeholder})"
                        )
                        params.extend([c, c, c])
                    if cat_conds:
                        where_conditions.append(f"({' OR '.join(cat_conds)})")

                where_clause = " AND ".join(where_conditions)

                # Base Join Clause - Use LEFT JOINs for safety
                base_joins = """
                    FROM satislar s
                    LEFT JOIN urunler u ON s.urun_id = u.id
                    LEFT JOIN musteriler mu ON s.musteri_id = mu.id
                    LEFT JOIN magazalar mg ON s.magaza_id = mg.id
                    LEFT JOIN kategoriler k ON u.kategori_id = k.id
                    LEFT JOIN markalar m ON u.marka_id = m.id
                """

                import time

                start_time = time.time()

                # Check if brandsummary exists (PostgreSQL / SQLite uyumlu)
                if db_engine.DB_BACKEND == "postgresql":
                    cursor.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename ILIKE 'brandsummary'"
                    )
                else:
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND lower(name)='brandsummary'"
                    )
                has_summary = cursor.fetchone()

                logger.info(
                    f"Brand Report Request - HasSummary: {bool(has_summary)} | Search: {brand_search_term} | Cats: {categories}"
                )

                t_brands_dur = 0
                kpi_dur = 0
                list_dur = 0

                # Card 1: Total Brands (Always fast from markalar)
                t_brands_start = time.time()
                cursor.execute("SELECT COUNT(*) as total FROM markalar")
                total_brands_abs = cursor.fetchone()["total"] or 0
                t_brands_dur = time.time() - t_brands_start

                brand_list = []

                if has_summary:
                    # USE OPTIMIZED SUMMARY TABLE

                    # Build WHERE clause for Summary
                    sum_conditions = ["1=1"]
                    sum_params = []

                    # Helper for turkish lower

                    if start_date_str:
                        # Approximation: filter by year/month if start_date aligns
                        pass

                    if year:
                        sum_conditions.append(f"year = {placeholder}")
                        sum_params.append(int(year))
                    if month:
                        sum_conditions.append(f"month = {placeholder}")
                        sum_params.append(int(month))
                    if region:
                        sum_conditions.append(f"region_norm = {placeholder}")
                        sum_params.append(tr_lower(region))
                    if customer_type:
                        sum_conditions.append(f"customer_type_norm = {placeholder}")
                        sum_params.append(tr_lower(customer_type))
                    if segment:
                        sum_conditions.append(f"segment_norm = {placeholder}")
                        sum_params.append(tr_lower(segment))
                    if approval_status:
                        sum_conditions.append(f"approval_status_norm = {placeholder}")
                        sum_params.append(tr_lower(approval_status))

                    if brand_search_term and len(brand_search_term) > 1:
                        sum_conditions.append(f"brand_name_norm LIKE {placeholder}")
                        sum_params.append(f"%{tr_lower(brand_search_term)}%")

                    if categories:
                        # Handle hierarchical category filtering
                        # Check if any level matches any of the selected categories
                        cat_conditions = []
                        for c in categories:
                            if not c:
                                continue
                            c_norm = tr_lower(c)
                            cat_conditions.append(
                                f"(category_norm = {placeholder} OR category_sub1_norm = {placeholder} OR category_sub2_norm = {placeholder})"
                            )
                            sum_params.extend([c_norm, c_norm, c_norm])

                        if cat_conditions:
                            sum_conditions.append(f"({' OR '.join(cat_conditions)})")

                    sum_where = " AND ".join(sum_conditions)

                    # KPIs
                    kpi_start = time.time()
                    cursor.execute(
                        f"""
                        SELECT 
                            SUM(total_sales) as total_sales,
                            COUNT(DISTINCT brand_id) as active_brands
                        FROM brandsummary
                        WHERE {sum_where}
                    """,
                        sum_params,
                    )
                    row = cursor.fetchone()
                    true_total_sales = row["total_sales"] or 0
                    true_active_brands = row["active_brands"] or 0
                    kpi_dur = time.time() - kpi_start

                    # List
                    list_start = time.time()
                    cursor.execute(
                        f"""
                        SELECT
                            brand_id,
                            MAX(brand_name) as name,
                            SUM(total_sales) as sales,
                            SUM(total_units) as units,
                            SUM(customer_count) as customers
                        FROM brandsummary
                        WHERE {sum_where}
                        GROUP BY brand_id
                        ORDER BY sales DESC
                        LIMIT {placeholder} OFFSET {placeholder}
                    """,
                        sum_params + [limit, offset],
                    )
                    rows = cursor.fetchall()
                    list_dur = time.time() - list_start

                    # Get available categories and other filters from cache if possible
                    filters_cache_key = f"filters_{data_source_id}"
                    cached_filters = _get_ttl_cache(_brand_filters_cache, filters_cache_key, _brand_filters_cache_timeout)
                    
                    if cached_filters:
                        result_hierarchy = cached_filters['hierarchy']
                        available_regions = cached_filters['regions']
                        available_customer_types = cached_filters['customer_types']
                        available_approval_statuses = cached_filters['approval_statuses']
                    else:
                        # Get available categories for filter (Hierarchical)
                        cursor.execute(
                            "SELECT DISTINCT ana as category_main, alt1 as category_sub1, alt2 as category_sub2 FROM kategoriler WHERE ana IS NOT NULL ORDER BY 1, 2, 3"
                        )
                        categories_rows = cursor.fetchall()
                        
                        hierarchy_map = {}
                        for r in categories_rows:
                            main = r["category_main"]
                            sub1 = r["category_sub1"]
                            sub2 = r["category_sub2"]
                            if main:
                                if main not in hierarchy_map:
                                    hierarchy_map[main] = {}
                                if sub1:
                                    if sub1 not in hierarchy_map[main]:
                                        hierarchy_map[main][sub1] = []
                                    if sub2 and sub2 not in hierarchy_map[main][sub1]:
                                        hierarchy_map[main][sub1].append(sub2)

                        result_hierarchy = hierarchy_map

                        # Get other filter options — shared cache ile (6 saat TTL, full table scan engellenir)
                        try:
                            from django.core.cache import cache as django_cache
                            _cached_f = django_cache.get("dashboard_available_filters")
                        except Exception:
                            _cached_f = None
                        if _cached_f:
                            available_regions = _cached_f.get("regions", [])
                            available_customer_types = _cached_f.get("types", [])
                            available_approval_statuses = _cached_f.get("statuses", [])
                        else:
                            cursor.execute(
                                "SELECT DISTINCT " + db_engine.bolge_expr() + " as region FROM magazalar WHERE bolge IS NOT NULL ORDER BY 1"
                            )
                            available_regions = [r['region'] for r in cursor.fetchall() if r['region']]

                            cursor.execute(
                                "SELECT DISTINCT tip as customer_type FROM musteriler WHERE tip IS NOT NULL ORDER BY 1"
                            )
                            available_customer_types = [r['customer_type'] for r in cursor.fetchall() if r['customer_type']]

                            cursor.execute(
                                "SELECT DISTINCT onay_durumu as approval_status FROM musteriler WHERE onay_durumu IS NOT NULL ORDER BY 1"
                            )
                            available_approval_statuses = [r['approval_status'] for r in cursor.fetchall() if r['approval_status']]
                        
                        # Store in cache
                        _set_ttl_cache(_brand_filters_cache, filters_cache_key, {
                            'hierarchy': result_hierarchy,
                            'regions': available_regions,
                            'customer_types': available_customer_types,
                            'approval_statuses': available_approval_statuses
                        }, _brand_filters_cache_max_entries)

                else:
                    # FALLBACK TO LEGACY (SLOW) IF SUMMARY MISSING
                    kpi_start = time.time()
                    cursor.execute(
                        f"""
                        SELECT 
                            SUM(s.tutar) as total_sales,
                            COUNT(DISTINCT u.marka_id) as active_brands
                        {base_joins}
                        WHERE {where_clause}
                    """,
                        params,
                    )
                    summary_row = cursor.fetchone()
                    true_total_sales = summary_row["total_sales"] or 0
                    true_active_brands = summary_row["active_brands"] or 0
                    kpi_dur = time.time() - kpi_start

                    list_start = time.time()
                    cursor.execute(
                        f"""
                        SELECT 
                            m.ad as name, 
                            SUM(s.tutar) as sales, 
                            SUM(s.miktar) as units,
                            COUNT(DISTINCT s.musteri_id) as customers
                        {base_joins}
                        WHERE {where_clause} AND m.ad IS NOT NULL
                        GROUP BY m.id, m.ad
                        ORDER BY sales DESC
                        LIMIT {placeholder} OFFSET {placeholder}
                    """,
                        params + [limit, offset],
                    )
                    rows = cursor.fetchall()
                    list_dur = time.time() - list_start

                    categories_list = []  # Fallback empty if no summary
                    result_hierarchy = {}
                    available_regions = []
                    available_customer_types = []
                    available_approval_statuses = []

                logger.info(
                    f"Brand Report OPTIMIZED Timings (Summary={bool(has_summary)}) - Total: {t_brands_dur:.4f}s, KPIs: {kpi_dur:.4f}s, List: {list_dur:.4f}s"
                )

                brand_list = []
                colors = [
                    "#6366f1",
                    "#8b5cf6",
                    "#a855f7",
                    "#d946ef",
                    "#ec4899",
                    "#f43f5e",
                    "#ef4444",
                    "#f97316",
                    "#f59e0b",
                    "#eab308",
                ]

                for idx, r in enumerate(rows):
                    s = r["sales"] or 0
                    if idx < 10:
                        brand_list.append(
                            {
                                "name": r["name"] or "Bilinmiyor",
                                "sales": round(s, 2),
                                "units": int(r["units"] or 0),
                                "customers": r["customers"],
                                "avgPrice": round(s / r["units"], 2)
                                if r["units"] and r["units"] > 0
                                else 0,
                                "growth": 0,
                                "marketShare": round((s / true_total_sales * 100), 1)
                                if true_total_sales > 0
                                else 0,
                                "color": colors[idx % len(colors)],
                            }
                        )

                result = {
                    "topBrands": brand_list,
                    "categoryHierarchy": result_hierarchy if has_summary else {},
                    "availableRegions": available_regions,
                    "availableCustomerTypes": available_customer_types,
                    "availableApprovalStatuses": available_approval_statuses,
                    "brandPerformance": {
                        "totalBrands": total_brands_abs,
                        "activeBrands": true_active_brands,
                        "topPerformers": min(10, len(rows)),
                        "declining": 0,
                        "totalSales": round(true_total_sales, 2),
                    },
                    "categoryDistribution": [],
                }

                _set_ttl_cache(
                    _brand_report_cache,
                    cache_key,
                    result,
                    _brand_report_cache_max_entries,
                )
                return Response(result)
            except Exception as e:
                logger.error(f"Brand Report SQL Error: {e}", exc_info=True)
            finally:
                db_engine.release_connection(conn)
                # Fallback to legacy if SQL fails

        data = get_datasource_data(data_source)

        if not data or len(data) == 0:
            return Response(
                {
                    "topBrands": [],
                    "brandPerformance": {
                        "totalBrands": 0,
                        "activeBrands": 0,
                        "topPerformers": 0,
                        "declining": 0,
                        "totalSales": 0,
                    },
                    "categoryDistribution": [],
                }
            )

        # Tarih filtreleme uygula
        data = filter_data_by_date(data, request)

        # Sütun isimlerini detect et
        first_row_keys = list(data[0].keys()) if data else []
        columns = detect_columns(first_row_keys, data_source.column_mapping)

        brand_col = columns.get("brand_col") or "MarkaAdi"
        amount_col = columns.get("revenue_col") or "Satış Tutarı"
        quantity_col = columns.get("quantity_col") or "Miktar"
        customer_id_col = columns.get("customer_id_col") or "Müşteri Kodu"

        # Brand satış analizi
        brand_sales = {}
        total_global_sales = 0
        for row in data:
            brand = (
                row.get(brand_col)
                or row.get("MarkaAdi")
                or row.get("marka")
                or "Bilinmiyor"
            )
            if not brand or brand == "":
                brand = "Bilinmiyor"

            try:
                amount = float(str(row.get(amount_col, 0)).replace(",", "."))
            except (ValueError, TypeError, AttributeError):
                amount = 0

            try:
                quantity = float(str(row.get(quantity_col, 1)).replace(",", "."))
            except (ValueError, TypeError, AttributeError):
                quantity = 1

            total_global_sales += amount
            if brand not in brand_sales:
                brand_sales[brand] = {"sales": 0, "units": 0, "customers": set()}

            brand_sales[brand]["sales"] += amount
            brand_sales[brand]["units"] += quantity

            customer_id = row.get(customer_id_col)
            if customer_id:
                brand_sales[brand]["customers"].add(customer_id)

        if not brand_sales:
            return Response(
                {
                    "topBrands": [],
                    "brandPerformance": {
                        "totalBrands": 0,
                        "activeBrands": 0,
                        "topPerformers": 0,
                        "declining": 0,
                        "totalSales": 0,
                    },
                    "categoryDistribution": [],
                }
            )

        # Top brands
        colors = [
            "#6366f1",
            "#8b5cf6",
            "#a855f7",
            "#d946ef",
            "#ec4899",
            "#f43f5e",
            "#ef4444",
            "#f97316",
            "#f59e0b",
            "#eab308",
        ]
        top_brands = []
        for idx, (brand, brand_data) in enumerate(
            sorted(brand_sales.items(), key=lambda x: x[1]["sales"], reverse=True)[:10]
        ):
            avg_price = (
                brand_data["sales"] / brand_data["units"]
                if brand_data["units"] > 0
                else 0
            )
            top_brands.append(
                {
                    "name": brand,
                    "sales": round(brand_data["sales"], 2),
                    "units": int(brand_data["units"]),
                    "customers": len(brand_data["customers"]),
                    "avgPrice": round(avg_price, 2),
                    "growth": 0,
                    "marketShare": round(
                        (brand_data["sales"] / total_global_sales * 100), 1
                    )
                    if total_global_sales > 0
                    else 0,
                    "color": colors[idx % len(colors)],
                }
            )

        brand_performance = {
            "totalBrands": len(brand_sales),
            "activeBrands": len(brand_sales),
            "topPerformers": min(10, len(brand_sales)),
            "declining": 0,
            "totalSales": round(total_global_sales, 2),
        }

        result = {
            "topBrands": top_brands,
            "brandPerformance": brand_performance,
            "categoryDistribution": [],
        }

        _set_ttl_cache(
            _brand_report_cache, cache_key, result, _brand_report_cache_max_entries
        )
        return Response(result)

        _set_ttl_cache(
            _brand_report_cache, cache_key, result, _brand_report_cache_max_entries
        )
        return Response(result)

    except DataSource.DoesNotExist:
        return Response({"error": "Veri kaynağı bulunamadı"}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_brand_suggestions(request, data_source_id):
    """Marka önerileri getir (Autocomplete için)"""
    try:
        q = request.GET.get("q", "")
        if len(q) < 1:
            return Response([])

        def tr_lower(s):
            if s is None:
                return ""
            if not isinstance(s, str):
                s = str(s)
            s = s.strip().replace("\xa0", " ")
            s = s.replace("İ", "i").replace("I", "ı")
            s = s.lower()
            replacements = {"ç": "c", "ğ": "g", "ö": "o", "ş": "s", "ü": "u", "ı": "i"}
            for search, replace in replacements.items():
                s = s.replace(search, replace)
            return s

        search_term = tr_lower(q)

        conn = db_engine.get_connection()
        try:
            if db_engine.DB_BACKEND == "postgresql":
                from psycopg2.extras import RealDictCursor

                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()

            placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
            cursor.execute(
                f"""
                SELECT DISTINCT brand_name
                FROM brandsummary
                WHERE brand_name_norm LIKE {placeholder}
                ORDER BY brand_name
                LIMIT 10
            """,
                [f"%{search_term}%"],
            )

            suggestions = [
                row["brand_name"] if isinstance(row, dict) else row[0]
                for row in cursor.fetchall()
            ]
            return Response(suggestions)
        finally:
            db_engine.release_connection(conn)

    except Exception as e:
        logger.error(f"Brand suggestions error: {e}")
        return Response([])


# Segmentation Endpoint


@api_view(["GET"])
def search_products(request, data_source_id):
    """Tüm ürünler içinde arama yap - Optimized with caching"""
    global _product_cache

    try:
        user = get_user_from_request(request)
        if not user:
            return Response(
                {"error": "Yetkilendirme gerekli"}, status=HTTP_401_UNAUTHORIZED
            )

        # Arama sorgusu
        search_query = request.GET.get("q", "").strip().lower()
        if len(search_query) < 2:
            return Response({"results": []})

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)

        # SQL Branch
        is_database_source = (
            getattr(data_source, "type", "") == "database"
            or "sal" in getattr(data_source, "name", "").lower()
            or "sat" in getattr(data_source, "name", "").lower()
        )

        if is_database_source:
            try:
                conn = db_engine.get_connection()
                if db_engine.DB_BACKEND == "postgresql":
                    from psycopg2.extras import RealDictCursor
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                else:
                    cursor = conn.cursor()

                placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
                like_op = "ILIKE" if db_engine.DB_BACKEND == "postgresql" else "LIKE"
                
                # Turkish-insensitive search using translate in SQL
                column_expr = db_engine.normalize_turkish_sql("u.ad")
                param_expr = db_engine.placeholder()
                if db_engine.DB_BACKEND == "postgresql":
                    param_expr = f"translate(lower({param_expr}), 'çğışıöü', 'cgisiou')"
                
                cursor.execute(
                    f"""
                        SELECT
                            u.id as id,
                            u.ad as name,
                            m.ad as brand,
                            k.ana as category,
                            upd.toplamtutar as revenue,
                            upd.toplammiktar as count
                        FROM urunler u
                        LEFT JOIN urunperformansdetay upd ON upd.urunid = u.id
                        LEFT JOIN markalar m ON u.marka_id = m.id
                        LEFT JOIN kategoriler k ON u.kategori_id = k.id
                        WHERE {column_expr} {like_op} {param_expr}
                        ORDER BY revenue DESC NULLS LAST
                        LIMIT 100
                    """,
                        [f"%{search_query}%"],
                    )

                results = [
                    {
                        "id": r["id"] if isinstance(r, dict) else r[0],
                        "name": r["name"] if isinstance(r, dict) else r[1],
                        "brand": (r["brand"] if isinstance(r, dict) else r[2])
                        or "-",
                        "category": (r["category"] if isinstance(r, dict) else r[3]) or "-",
                        "revenue": round((r["revenue"] if isinstance(r, dict) else r[4]) or 0, 2),
                        "count": int((r["count"] if isinstance(r, dict) else r[5]) or 0),
                    }
                    for r in cursor.fetchall()
                ]

                return Response({"results": results})
            except Exception as e:
                logger.error(f"Search Products SQL Error: {e}")
            finally:
                db_engine.release_connection(conn)

        # --- LEGACY FALLBACK (Memory Cache) ---
        cache_key = f"{user.id}_{data_source_id}"

        # Cache kontrolü - önceden işlenmiş ürün verileri var mı?
        if cache_key not in _product_cache:
            data = data_source.data
            if not data:
                return Response({"results": []})

            # Kolon tespiti
            column_names = list(data[0].keys()) if data else []
            columns = detect_columns(column_names)
            product_col = columns.get("product_col")
            brand_col = columns.get("brand_col")
            category_col = columns.get("category_col")
            revenue_col = columns.get("revenue_col")

            if not product_col:
                return Response({"results": []})

            # Türkçe karakter normalizasyonu
            def normalize_turkish(text):
                if not isinstance(text, str):
                    return ""
                return (
                    text.lower()
                    .replace("ğ", "g")
                    .replace("ü", "u")
                    .replace("ş", "s")
                    .replace("ı", "i")
                    .replace("ö", "o")
                    .replace("ç", "c")
                    .replace("Ğ", "g")
                    .replace("Ü", "u")
                    .replace("Ş", "s")
                    .replace("İ", "i")
                    .replace("Ö", "o")
                    .replace("Ç", "c")
                )

            # Tüm ürün verilerini önceden işle ve cache'le
            product_data = {}
            for row in data:
                product = row.get(product_col, "")
                if product:
                    product_name = str(product).strip()
                    normalized_name = normalize_turkish(product_name)

                    if product_name not in product_data:
                        product_data[product_name] = {
                            "name": product_name,
                            "normalized": normalized_name,
                            "brand": str(row.get(brand_col, "")).strip().rstrip("/")
                            if brand_col
                            else "-",
                            "category": str(row.get(category_col, ""))
                            .strip()
                            .rstrip("/")
                            if category_col
                            else "-",
                            "revenue": 0,
                            "count": 0,
                        }

                    try:
                        revenue = float(
                            str(row.get(revenue_col, "0")).replace(",", ".")
                        )
                        product_data[product_name]["revenue"] += revenue
                        product_data[product_name]["count"] += 1
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse product revenue: {e}")
                        pass

            # Cache'e kaydet (liste olarak, hızlı filtreleme için)
            _product_cache[cache_key] = list(product_data.values())

        # Cache'den hızlı arama
        cached_products = _product_cache[cache_key]

        # Türkçe karakter normalizasyonu (query için)
        normalized_query = (
            search_query.replace("ğ", "g")
            .replace("ü", "u")
            .replace("ş", "s")
            .replace("ı", "i")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace("Ğ", "g")
            .replace("Ü", "u")
            .replace("Ş", "s")
            .replace("İ", "i")
            .replace("Ö", "o")
            .replace("Ç", "c")
        )

        # Filtreleme ve sıralama
        results = [
            {
                "name": p["name"],
                "brand": p["brand"],
                "category": p["category"],
                "revenue": p["revenue"],
                "count": p["count"],
            }
            for p in cached_products
            if normalized_query in p["normalized"]
        ]
        results.sort(key=lambda x: x["revenue"], reverse=True)

        return Response({"results": results[:50]})

    except DataSource.DoesNotExist:
        return Response({"error": "Veri kaynağı bulunamadı"}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_new_customers_analysis_backend(request, data_source_id):
    """Yeni müşteri analizi - Database tabanlı ve filtre uyumlu"""
    import sqlite3
    import os
    from datetime import datetime, timedelta

    # Parametreler
    year = request.GET.get("year")
    month = request.GET.get("month")
    start_date_str = request.GET.get("start_date") or request.GET.get("startDate")
    end_date_str = request.GET.get("end_date") or request.GET.get("endDate")

    # Çoklu seçim filtreleri
    def get_list_param(name):
        val = request.GET.get(name) or request.GET.get(f"{name}[]")
        if not val:
            return request.GET.getlist(name) or request.GET.getlist(f"{name}[]")
        if "," in val:
            return [v.strip() for v in val.split(",") if v.strip()]
        return [val]

    categories = get_list_param("categories") or get_list_param("category")
    brands = get_list_param("brands") or get_list_param("brand")
    regions = get_list_param("regions") or get_list_param("region")
    customer_types = (
        get_list_param("customerTypes")
        or get_list_param("customer_type")
        or get_list_param("customerType")
    )
    approval_statuses = (
        get_list_param("approvalStatuses")
        or get_list_param("approval_status")
        or get_list_param("approvalStatus")
    )

    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        # Temel WHERE koşulları (İlk alışveriş tarihi belirlendikten sonra uygulanacak)
        placeholder = db_engine.ph()
        where_clauses = ["1=1"]
        params = []

        # Tarih Aralığı Belirleme
        now = datetime.now()
        if start_date_str and end_date_str:
            where_clauses.append(
                f"FirstPurchaseDate BETWEEN {placeholder} AND {placeholder}"
            )
            params.extend([start_date_str, end_date_str])
            filter_start = start_date_str
            filter_end = end_date_str
        elif year:
            if month:
                filter_start = f"{year}-{int(month):02d}-01"
                import calendar

                last_day = calendar.monthrange(int(year), int(month))[1]
                filter_end = f"{year}-{int(month):02d}-{last_day}"
            else:
                filter_start = f"{year}-01-01"
                filter_end = f"{year}-12-31"
            where_clauses.append(
                f"FirstPurchaseDate BETWEEN {placeholder} AND {placeholder}"
            )
            params.extend([filter_start, filter_end])
        else:
            # Varsayılan: Daha geniş bir kapsam (Son 5 yıl) - Toplam kitleyi daha iyi yansıtmak için
            filter_end = now.strftime("%Y-%m-%d")
            filter_start = (now - timedelta(days=1825)).strftime("%Y-%m-%d")
            where_clauses.append(
                f"FirstPurchaseDate BETWEEN {placeholder} AND {placeholder}"
            )
            params.extend([filter_start, filter_end])

        # Ek Filtreler
        if categories:
            placeholders = ", ".join([placeholder] * len(categories))
            where_clauses.append(
                f" (k.ana IN ({placeholders}) OR k.alt1 IN ({placeholders}) OR k.alt2 IN ({placeholders}))"
            )
            params.extend(categories * 3)
        if brands:
            placeholders = ", ".join([placeholder] * len(brands))
            where_clauses.append(f" m.ad IN ({placeholders})")
            params.extend(brands)
        if regions:
            placeholders = ", ".join([placeholder] * len(regions))
            where_clauses.append(f" mg.bolge IN ({placeholders})")
            params.extend(regions)
        if customer_types:
            placeholders = ", ".join([placeholder] * len(customer_types))
            where_clauses.append(f" mu.tip IN ({placeholders})")
            params.extend(customer_types)
        if approval_statuses:
            placeholders = ", ".join([placeholder] * len(approval_statuses))
            where_clauses.append(f" mu.onay_durumu IN ({placeholders})")
            params.extend(approval_statuses)

        where_stmt = " AND ".join(where_clauses)

        # 1. Yeni müşterileri 'musteridetayozet' tablosundaki 'ilk_alisveris_tarihi' üzerinden bul
        # Bu yaklaşım 'satislar' tablosuna yapılan devasa CTE/GROUP BY işlemini engeller.
        query = f"""
            SELECT 
                mdo.musteri_id,
                mdo.ilk_alisveris_tarihi as FirstPurchaseDate,
                mdo.ortalama_sepet_tutari as first_order_amount, -- Yaklaşık değer veya ilk gün toplamı
                mdo.rfm_segment as segment,
                mdo.favori_magaza as store_name,
                mdo.toplam_alisveris as total_orders,
                mdo.lifetime_value_tahmini as lifetime_revenue
            FROM musteridetayozet mdo
            JOIN musteriler mu ON mu.id = mdo.musteri_id
            WHERE mdo.ilk_alisveris_tarihi BETWEEN {placeholder} AND {placeholder}
        """
        params = [filter_start, filter_end]
        
        # Ek Filtreler (Eğer varsa mdo üzerinden veya JOIN ile uygulanır)
        # Not: Categories/Brands filtreleri mdo'da favori_kategori/favori_marka olarak var
        if categories:
            placeholders = ", ".join([placeholder] * len(categories))
            query += f" AND mdo.favori_kategori IN ({placeholders})"
            params.extend(categories)
        if brands:
            placeholders = ", ".join([placeholder] * len(brands))
            query += f" AND mdo.favori_marka IN ({placeholders})"
            params.extend(brands)
        if regions:
            placeholders = ", ".join([placeholder] * len(regions))
            query += f" AND mdo.favori_magaza IN ({placeholders})"
            params.extend(regions)
        if customer_types:
            placeholders = ", ".join([placeholder] * len(customer_types))
            query += f" AND mu.tip IN ({placeholders})"
            params.extend(customer_types)
        if approval_statuses:
            placeholders = ", ".join([placeholder] * len(approval_statuses))
            query += f" AND mu.onay_durumu IN ({placeholders})"
            params.extend(approval_statuses)

        cursor.execute(query, params)
        new_customers = cursor.fetchall()

        if not new_customers:
            return Response(
                {
                    "summary": {
                        "newCustomersThisMonth": 0,
                        "growthRate": 0,
                        "avgFirstOrder": 0,
                        "retentionRate": 0,
                    },
                    "monthlyTrend": [],
                    "acquisitionChannels": [],
                    "recentCustomers": [],
                }
            )

                # --- HESAPLAMALAR ---
        now = datetime.now()

        # trend ve Özet için Gruplama
        monthly_distribution = {}
        total_first_order_value = 0
        retained_count = 0

        # Son katılan 10 müşteri
        recent_list = sorted(
            new_customers, key=lambda x: db_engine.val(x, "FirstPurchaseDate", ""), reverse=True
        )[:10]

        for row in new_customers:
            fpd = db_engine.val(row, "FirstPurchaseDate", "")
            if not fpd:
                continue
            
            # Tip kontrolü: fpd zaten datetime veya date ise strptime atla
            from datetime import date
            if isinstance(fpd, datetime):
                date_obj = fpd
            elif isinstance(fpd, date):
                date_obj = datetime.combine(fpd, datetime.min.time())
            elif isinstance(fpd, str):
                try:
                    date_obj = datetime.strptime(fpd, "%Y-%m-%d")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(fpd, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        date_obj = now
            else:
                date_obj = now
            
            month_key = date_obj.strftime("%Y-%m")

            monthly_distribution[month_key] = monthly_distribution.get(month_key, 0) + 1
            total_first_order_value += db_engine.val(row, "first_order_amount", 0)

            # Retention: En az 2 sipariş vermişse
            if db_engine.val(row, "total_orders", 0) >= 2:
                retained_count += 1

        # trend Listesi
        trend_list = []
        for m_key in sorted(monthly_distribution.keys()):
            trend_list.append({"month": m_key, "count": monthly_distribution[m_key]})

        # Özet Veriler
        total_new = len(new_customers)
        avg_first_order = total_first_order_value / total_new if total_new > 0 else 0
        retention_rate = (retained_count / total_new * 100) if total_new > 0 else 0

        # Büyüme Oranı (Son ay vs Önceki ay)
        growth_rate = 0
        if len(trend_list) >= 2:
            last_val = trend_list[-1]["count"]
            prev_val = trend_list[-2]["count"]
            if prev_val > 0:
                growth_rate = round(((last_val - prev_val) / prev_val) * 100, 1)

        # Kazanım Kanalları (Mağaza bazlı)
        channel_map = {}  # {store_name: {'count': 0, 'total': 0}}
        for row in new_customers:
            ch = db_engine.val(row, "store_name", None) or "Bilinmiyor"
            if ch not in channel_map:
                channel_map[ch] = {"count": 0, "total": 0}
            channel_map[ch]["count"] += 1
            channel_map[ch]["total"] += db_engine.val(row, "lifetime_revenue", 0)

        acquisition_channels = []
        for ch, stats in sorted(
            channel_map.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            count = stats["count"]
            acquisition_channels.append(
                {
                    "channel": ch,
                    "count": count,
                    "percentage": round((count / total_new * 100), 1)
                    if total_new > 0
                    else 0,
                    "avg_first_order": round(stats["total"] / count, 2)
                    if count > 0
                    else 0,
                    "total_revenue": round(stats["total"], 2),
                }
            )

                # Son Katılanlar Formatla
        recent_customers = []
        for rc in recent_list:
            fpd = db_engine.val(rc, "FirstPurchaseDate", "")
            if fpd:
                from datetime import date
                if isinstance(fpd, datetime):
                    jd_obj = fpd
                elif isinstance(fpd, date):
                    jd_obj = datetime.combine(fpd, datetime.min.time())
                elif isinstance(fpd, str):
                    try:
                        jd_obj = datetime.strptime(fpd, "%Y-%m-%d")
                    except ValueError:
                        try:
                            jd_obj = datetime.strptime(fpd, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            jd_obj = now
                else:
                    jd_obj = now
                join_date = jd_obj.strftime("%d.%m.%Y")
            else:
                join_date = ""
            
            recent_customers.append(
                {
                    "id": db_engine.val(rc, "musteri_id", None),
                    "joinDate": join_date,
                    "firstOrder": round(db_engine.val(rc, "first_order_amount", 0), 2),
                    "status": "Aktif" if db_engine.val(rc, "total_orders", 0) >= 2 else "Yeni",
                    "segment": db_engine.val(rc, "segment", None) or "Yeni Müşteri",
                }
            )

        return Response(
            {
                "summary": {
                    "totalNewCustomers": total_new,
                    "newCustomersThisMonth": trend_list[-1]["count"]
                    if trend_list
                    else 0,
                    "growthRate": growth_rate,
                    "avgFirstOrder": round(avg_first_order, 2),
                    "retentionRate": round(retention_rate, 1),
                },
                "monthlyTrend": trend_list,
                "acquisitionChannels": acquisition_channels,
                "acquisitionSource": "store",  # Changed from region to store
                "recentCustomers": recent_customers,
            }
        )

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return Response({"error": str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if conn:
            db_engine.release_connection(conn)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_customer_info_analysis(request, data_source_id):
    """Müşteri bilgi analizi — SQL aggregation ile hızlandırılmış versiyon."""
    conn = None
    try:
        ph = db_engine.ph()
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        # ── 1. Özet sayılar (tek SQL, satır çekmeden) ──────────────────────
        cursor.execute(f"""
            SELECT
                COUNT(m.id)                                             AS total,
                COUNT(m.id) FILTER (WHERE md.rfm_segment NOT ILIKE '%kaybed%'
                                    AND md.rfm_segment NOT ILIKE '%riskli%')          AS active,
                COUNT(m.id) FILTER (WHERE m.telefon IS NOT NULL
                                    AND LENGTH(CAST(m.telefon AS TEXT)) > 5)         AS filled_phone,
                COUNT(m.id) FILTER (WHERE m.tip IS NOT NULL)                           AS filled_type,
                COUNT(m.id) FILTER (WHERE md.rfm_segment IS NOT NULL)                   AS filled_segment,
                COUNT(m.id) FILTER (WHERE m.onay_durumu IS NOT NULL)                   AS filled_approval
            FROM musteriler m
            LEFT JOIN musteridetayozet md ON m.id = md.musteri_id
        """)
        row = cursor.fetchone()
        total        = row["total"]        or 0
        active       = row["active"]       or 0
        filled_phone = row["filled_phone"] or 0
        filled_type  = row["filled_type"]  or 0
        filled_segment  = row["filled_segment"]  or 0
        filled_approval = row["filled_approval"] or 0
        inactive = total - active

        if total == 0:
            return Response({
                "summary": {"totalCustomers": 0, "activeCustomers": 0, "inactiveCustomers": 0, "avgCustomerAge": 0},
                "dataQuality": [], "contactPreferences": [],
                "customerActivity": {k: {"count": 0, "percentage": 0} for k in ["highlyActive","active","moderate","lowActivity","inactive"]},
                "topInterests": [],
            })

        def pct(n): return round(n / total * 100, 1) if total else 0

        # ── 2. Müşteri başına sipariş sayısı dağılımı (SQL GROUP BY) ───────
        cursor.execute("""
            SELECT
                SUM(CASE WHEN cnt >= 8 THEN 1 ELSE 0 END) AS high,
                SUM(CASE WHEN cnt BETWEEN 4 AND 7 THEN 1 ELSE 0 END) AS med,
                SUM(CASE WHEN cnt BETWEEN 2 AND 3 THEN 1 ELSE 0 END) AS moderate,
                SUM(CASE WHEN cnt = 1 THEN 1 ELSE 0 END) AS low_act
            FROM (
                SELECT musteri_id, COUNT(DISTINCT fis_no) AS cnt
                FROM satislar
                WHERE musteri_id IS NOT NULL
                GROUP BY musteri_id
            ) sub
        """)
        act = cursor.fetchone()
        high     = act["high"]     or 0
        med      = act["med"]      or 0
        moderate = act["moderate"] or 0
        low      = act["low_act"]  or 0

        # ── 3. Kategori ilgi odakları ───────────────────────────────────────
        cursor.execute("""
            SELECT k.ana AS category, COUNT(DISTINCT s.musteri_id) AS customers
            FROM satislar s
            JOIN urunler u ON u.id = s.urun_id
            JOIN kategoriler k ON k.id = u.kategori_id
            WHERE k.ana IS NOT NULL
            GROUP BY k.ana
            ORDER BY customers DESC
            LIMIT 10
        """)
        top_interests = [
            {"category": r["category"], "customers": r["customers"],
             "engagement": round(r["customers"] / total * 100, 1)}
            for r in cursor.fetchall()
        ]

        # ── Ortalama müşteri yaşı (kayıt tarihinden) ───────────────────────
        if db_engine.DB_BACKEND == "postgresql":
            cursor.execute("""
                SELECT AVG(EXTRACT(YEAR FROM AGE(NOW(), kayit_tarihi))) AS avg_age
                FROM musteriler
                WHERE kayit_tarihi IS NOT NULL
            """)
        else:
            cursor.execute("""
                SELECT AVG(strftime('%Y', 'now') - strftime('%Y', kayit_tarihi)) AS avg_age
                FROM musteriler
                WHERE kayit_tarihi IS NOT NULL
            """)
        age_row = cursor.fetchone()
        avg_age = round(float(age_row["avg_age"] or 39), 1)

        def quality(p):
            if p >= 95: return "Mükemmel"
            if p >= 80: return "Çok İyi"
            if p >= 60: return "İyi"
            if p >= 40: return "Orta"
            return "Düşük"

        return Response({
            "summary": {
                "totalCustomers": total,
                "activeCustomers": active,
                "inactiveCustomers": inactive,
                "avgCustomerAge": avg_age,
            },
            "dataQuality": [
                {"field": "telefon",       "filled": filled_phone,    "missing": total - filled_phone,    "percentage": pct(filled_phone),    "quality": quality(pct(filled_phone))},
                {"field": "Müşteri Tipi",  "filled": filled_type,     "missing": total - filled_type,     "percentage": pct(filled_type),     "quality": quality(pct(filled_type))},
                {"field": "Segmentasyon",  "filled": filled_segment,  "missing": total - filled_segment,  "percentage": pct(filled_segment),  "quality": quality(pct(filled_segment))},
                {"field": "Onay Durumu",   "filled": filled_approval, "missing": total - filled_approval, "percentage": pct(filled_approval), "quality": quality(pct(filled_approval))},
            ],
            "contactPreferences": [
                {"method": "SMS / telefon",     "count": filled_phone,    "percentage": pct(filled_phone)},
                {"method": "Onaylı Pazarlama",  "count": filled_approval, "percentage": pct(filled_approval)},
                {"method": "Diğer Kanallar",    "count": int(total * 0.35), "percentage": 35},
            ],
            "customerActivity": {
                "highlyActive": {"count": high,     "percentage": pct(high)},
                "active":       {"count": med,      "percentage": pct(med)},
                "moderate":     {"count": moderate, "percentage": pct(moderate)},
                "lowActivity":  {"count": low,      "percentage": pct(low)},
                "inactive":     {"count": 0,        "percentage": 0},
            },
            "topInterests": top_interests,
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({"error": str(e)}, status=500)
    finally:
        if conn:
            db_engine.release_connection(conn)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_brand_detail(request, data_source_id):
    """Marka detay analizi - Belirli bir marka için trend, kategori ve ürün dağılımı"""
    import sqlite3
    import os
    from datetime import datetime

    try:
        brand_name = request.GET.get("brand")
        if not brand_name:
            return Response({"error": "Marka ismi gerekli"}, status=400)

        conn = db_engine.get_connection()
        try:
            if db_engine.DB_BACKEND == "postgresql":
                from psycopg2.extras import RealDictCursor
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()

            # 0. Marka ID'sini bul
            placeholder = db_engine.ph()
            cursor.execute(f"SELECT id FROM markalar WHERE ad = {placeholder}", [brand_name])
            brand_row = cursor.fetchone()
            if not brand_row:
                return Response({"error": "Marka bulunamadı"}, status=404)
            brand_id = brand_row['id'] if isinstance(brand_row, dict) else brand_row[0]

            # Filtreleri al
            year = request.GET.get("year")
            month = request.GET.get("month")
            start_date = request.GET.get("start_date") or request.GET.get("startDate")
            end_date = request.GET.get("end_date") or request.GET.get("endDate")
            region = request.GET.get("region")
            customer_type = request.GET.get("customer_type") or request.GET.get("customerType")
            approval_status = request.GET.get("approval_status") or request.GET.get("approvalStatus")

            # WHERE ve Params (Özet Tablolar İçin)
            where_clauses = [f"marka_id = {placeholder}"]
            params = [brand_id]

            if start_date:
                where_clauses.append(f"tarih >= {placeholder}")
                params.append(start_date)
            if end_date:
                where_clauses.append(f"tarih <= {placeholder}")
                params.append(end_date)
            if year:
                # PostgreSQL'de TO_CHAR(tarih, 'YYYY') kullanılabilir ama summary tabloda tarih genelde string değilse BETWEEN daha iyi
                where_clauses.append(f"tarih >= {placeholder} AND tarih < {placeholder}")
                params.extend([f"{year}-01-01", f"{int(year) + 1}-01-01"])
            if month:
                # Postgres vs SQLite uyumlu month extraction
                month_expr = db_engine.strftime_expr("%m", "tarih")
                where_clauses.append(f"{month_expr} = {placeholder}")
                params.append(f"{int(month):02d}")
            if region:
                where_clauses.append(f"magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})")
                params.append(region)
            if customer_type:
                where_clauses.append(f"customer_type = {placeholder}")
                params.append(customer_type)
            if approval_status:
                where_clauses.append(f"onay_durumu = {placeholder}")
                params.append(approval_status)

            # category filtresini al
            category_list = request.GET.getlist("category") or request.GET.getlist("category[]")
            if not category_list and request.GET.get("category"):
                category_list = [request.GET.get("category")]
            
            # Kategori araması varsa ekle (JOIN ile kategoriler tablosundan bul)
            if category_list:
                cat_placeholders = ",".join([placeholder] * len(category_list))
                # Not: daily_metrics_summary'deki kategori_id üzerinden kategoriler tablosuna join yapıyoruz
                category_subquery = f"SELECT id FROM kategoriler WHERE ana IN ({cat_placeholders}) OR alt1 IN ({cat_placeholders}) OR alt2 IN ({cat_placeholders})"
                where_clauses.append(f"kategori_id IN ({category_subquery})")
                # params listesine 3 kez (ana, alt1, alt2) kopyasını ekle
                params.extend(category_list)
                params.extend(category_list)
                params.extend(category_list)

            where_stmt = " AND ".join(where_clauses)
            logger.info(f"DEBUG: get_brand_detail - all GET params: {dict(request.GET)}")
            logger.info(f"DEBUG: get_brand_detail - brand: {brand_name}, categories: {category_list}")
            logger.info(f"DEBUG: get_brand_detail - where_stmt: {where_stmt}")
            logger.info(f"DEBUG: get_brand_detail - params: {params}")

            # 1. Özet Veriler (Summary Table Kullanılarak)
            cursor.execute(
                f"""
                SELECT 
                    SUM(revenue) as total_sales,
                    SUM(unit_count) as total_units,
                    SUM(receipt_count) as total_receipts,
                    SUM(customer_count) as total_customers
                FROM daily_metrics_summary
                WHERE {where_stmt}
                """,
                params,
            )
            summary_row = cursor.fetchone()
            
            if not summary_row:
                return Response({
                    "brand": brand_name,
                    "summary": {"sales": 0, "units": 0, "receipts": 0, "customers": 0, "avgTicket": 0},
                    "monthlyTrend": [],
                    "categoryHierarchy": [],
                    "topProducts": []
                })

            is_dict = isinstance(summary_row, dict)
            total_sales = (summary_row["total_sales"] or 0) if is_dict else (summary_row[0] or 0)
            total_units = (summary_row["total_units"] or 0) if is_dict else (summary_row[1] or 0)
            total_receipts = (summary_row["total_receipts"] or 0) if is_dict else (summary_row[2] or 0)
            total_customers = (summary_row["total_customers"] or 0) if is_dict else (summary_row[3] or 0)

            summary = {
                "sales": round(float(total_sales), 2),
                "units": int(total_units),
                "receipts": int(total_receipts),
                "customers": int(total_customers),
                "avgTicket": round(float(total_sales) / float(total_receipts), 2) if total_receipts > 0 else 0,
            }

            # 2. Aylık trend (Summary Table Kullanılarak)
            month_expr = db_engine.strftime_expr("%Y-%m", "tarih")
            cursor.execute(
                f"""
            SELECT {month_expr} as month, SUM(revenue) as sales, SUM(unit_count) as units
            FROM daily_metrics_summary
            WHERE {where_stmt}
            GROUP BY month
            ORDER BY month
            """,
                params,
            )
            monthly_trend = [dict(row) if isinstance(row, dict) else {"month": row[0], "sales": row[1], "units": row[2]} for row in cursor.fetchall()]

            # 3. Hiyerarşik Kategori Dağılımı (Summary Table JOIN Kategoriler)
            # where_stmt'deki marka_id, magaza_id vb. kolonları d. aliası ile güncelliyoruz
            hierarchy_where = where_stmt.replace('marka_id', 'd.marka_id') \
                                       .replace('magaza_id', 'd.magaza_id') \
                                       .replace('tarih', 'd.tarih') \
                                       .replace('customer_type', 'd.customer_type') \
                                       .replace('onay_durumu', 'd.onay_durumu') \
                                       .replace('kategori_id', 'd.kategori_id')
            
            logger.info(f"DEBUG: get_brand_detail hierarchy_where: {hierarchy_where}")

            cursor.execute(
                f"""
            SELECT k.ana, k.alt1, k.alt2, SUM(d.revenue) as sales
            FROM daily_metrics_summary d
            JOIN kategoriler k ON d.kategori_id = k.id
            WHERE {hierarchy_where}
            GROUP BY k.ana, k.alt1, k.alt2
            ORDER BY sales DESC
            """,
                params,
            )

            category_tree = {}
            for row in cursor.fetchall():
                ana = (row["ana"] if isinstance(row, dict) else row[0]) or "Bilinmiyor"
                alt1 = row["alt1"] if isinstance(row, dict) else row[1]
                alt2 = row["alt2"] if isinstance(row, dict) else row[2]
                sales = round(float(row["sales"] if isinstance(row, dict) else row[3]) or 0, 2)

                if ana not in category_tree:
                    category_tree[ana] = {"sales": 0, "children": {}}
                category_tree[ana]["sales"] += sales

                if alt1:
                    if alt1 not in category_tree[ana]["children"]:
                        category_tree[ana]["children"][alt1] = {
                            "sales": 0,
                            "children": {},
                        }
                    category_tree[ana]["children"][alt1]["sales"] += sales

                    if alt2:
                        if alt2 not in category_tree[ana]["children"][alt1]["children"]:
                            category_tree[ana]["children"][alt1]["children"][alt2] = {
                                "sales": 0
                            }
                        category_tree[ana]["children"][alt1]["children"][alt2][
                            "sales"
                        ] += sales

            # Sorted listeler haline getir
            def sort_tree(node):
                if "children" in node:
                    children_list = []
                    for name, child in node["children"].items():
                        children_list.append({"name": name, **sort_tree(child)})
                    node["children"] = sorted(
                        children_list, key=lambda x: x["sales"], reverse=True
                    )
                node["sales"] = round(node["sales"], 2)
                return node

            final_hierarchy = []
            sorted_cat_tree = sorted(
                category_tree.items(), key=lambda x: x[1]["sales"], reverse=True
            )

            for name, data in sorted_cat_tree:
                final_hierarchy.append({"name": name, **sort_tree(data)})

            # 4. En Çok Satan Ürünler (Top 10) - Product Daily Summary Kullanılarak
            # Product Summary'de magaza filtresi olmadığı için urun_id bazlı filtreleme yapıyoruz
            # Eğer magaza/bölge filtresi varsa mecburen satislar'dan çekilmeli VEYA product_daily_summary'ye magaza_id eklenmeliydi.
            # Şu anki platformda PDS magaza_id içermiyor, bu yüzden bu kısım genel trendi yansıtır.
            pds_where = [f"p.id = {placeholder}"]
            pds_params = [brand_id]
            if start_date:
                pds_where.append(f"pd.tarih >= {placeholder}"); pds_params.append(start_date)
            if end_date:
                pds_where.append(f"pd.tarih <= {placeholder}"); pds_params.append(end_date)
            
            # PDS için de kategori filtresini ekle (urunler tablosundaki kategori_id üzerinden)
            if category_list:
                cat_placeholders = ",".join([placeholder] * len(category_list))
                category_subquery = f"SELECT id FROM kategoriler WHERE ana IN ({cat_placeholders}) OR alt1 IN ({cat_placeholders}) OR alt2 IN ({cat_placeholders})"
                pds_where.append(f"u.kategori_id IN ({category_subquery})")
                pds_params.extend(category_list)
                pds_params.extend(category_list)
                pds_params.extend(category_list)
            
            pds_where_stmt = " AND ".join(pds_where)

            cursor.execute(
                f"""
            SELECT u.ad as name, SUM(pd.revenue) as sales, SUM(pd.unit_count) as units
            FROM product_daily_summary pd
            JOIN urunler u ON pd.urun_id = u.id
            JOIN markalar p ON u.marka_id = p.id
            WHERE {pds_where_stmt}
            GROUP BY u.id, u.ad
            ORDER BY sales DESC
            LIMIT 10
            """,
                pds_params,
            )
            top_products = [dict(row) if isinstance(row, dict) else {"name": row[0], "sales": row[1], "units": row[2]} for row in cursor.fetchall()]

            return Response(
                {
                    "brand": brand_name,
                    "summary": summary,
                    "monthlyTrend": monthly_trend,
                    "categoryHierarchy": final_hierarchy,
                    "topProducts": top_products,
                }
            )

            return Response(
                {
                    "brand": brand_name,
                    "summary": summary,
                    "monthlyTrend": monthly_trend,
                    "categoryHierarchy": final_hierarchy,
                    "topProducts": top_products,
                }
            )
        finally:
            db_engine.release_connection(conn)
    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_kpis(request):
    """Dashboard KPIs: Ciro, Fiş, Müşteri, Kayıtlı Müşteri, Ürün, Marka"""
    import time
    import traceback
    from datetime import datetime
    
    start_time = time.perf_counter()
    conn = db_engine.get_connection()
    try:
        cursor = db_engine.get_dict_cursor(conn)
        
        # Filtreleri al
        year = request.GET.get("year")
        month = request.GET.get("month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        categories = request.GET.get("categories", "").split(",") if request.GET.get("categories") else None
        brands = request.GET.get("brands", "").split(",") if request.GET.get("brands") else None
        customer_type = request.GET.get("customer_type") or request.GET.get("customerType")
        region = request.GET.get("region")
        approval_status = request.GET.get("approval_status") or request.GET.get("approvalStatus")

        if categories: categories = [c for c in categories if c.strip()]
        if brands: brands = [b for b in brands if b.strip()]

        # year/month parametrelerini start_date/end_date'e dönüştür
        if not start_date and year:
            try:
                import calendar as _cal
                y = int(year)
                if month:
                    m = int(month)
                    last_day = _cal.monthrange(y, m)[1]
                    start_date = f"{y}-{m:02d}-01"
                    end_date = end_date or f"{y}-{m:02d}-{last_day}"
                else:
                    start_date = f"{y}-01-01"
                    end_date = end_date or f"{y}-12-31"
            except (ValueError, TypeError):
                pass

        placeholder = db_engine.ph()
        is_fast_path = not (categories or brands or customer_type or region or approval_status)

        where_parts = ["1=1"]
        params = []
        if start_date:
            where_parts.append(f"tarih >= {placeholder}")
            params.append(start_date)
        if end_date:
            where_parts.append(f"tarih <= {placeholder}")
            params.append(end_date)
        
        # Sadece ay seçildiğinde (year olmadan) tüm yıllardaki o ayı filtrele
        if month and not year:
            if db_engine.DB_BACKEND == "postgresql":
                where_parts.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
            else:
                where_parts.append(f"substr(tarih, 6, 2) = {placeholder}")
            params.append(f"{int(month):02d}")
            
        # Gelişmiş filtreleri where_clause'a dahil et (Kritik: Aktif müşteri sayısını doğru filtrelemek için)
        if region:
            where_parts.append(f"magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})")
            params.append(region)
        if customer_type:
            where_parts.append(f"musteri_id IN (SELECT id FROM musteriler WHERE tip = {placeholder})")
            params.append(customer_type)
        if approval_status:
            where_parts.append(f"musteri_id IN (SELECT id FROM musteriler WHERE onay_durumu = {placeholder})")
            params.append(approval_status)
        
        where_clause = " AND ".join(where_parts)

        # 1. Tüm Cache'i tek seferde çek (Performance Optimization)
        cursor.execute("SELECT key, value FROM cache_kpi LIMIT 500")
        cache_data = {r['key']: r['value'] for r in cursor.fetchall()}

        # Hızlı yol veya satislar fallback tespiti
        # Müşteri filtresi varsa gunlukciroozet kullanılamaz (musteri_id/tip kolonu yok)
        has_customer_filter = bool(customer_type or approval_status or region)
        use_satislar_fallback = has_customer_filter
        if is_fast_path and not use_satislar_fallback:
            ozet_ts = int(float(cache_data.get('ozet_max_tarih_ts', 0) or 0))
            satis_ts = int(float(cache_data.get('satislar_max_tarih_ts', 0) or 0))

            if ozet_ts == 0:
                use_satislar_fallback = True
            elif satis_ts > 0 and (satis_ts - ozet_ts) > 30:
                use_satislar_fallback = True

        total_revenue = 0
        total_receipts = 0
        total_customers = 0
        total_registered = 0
        total_prods = int(float(cache_data.get('total_products_count', 0) or 0))
        total_brands = int(float(cache_data.get('total_brands_count', 0) or 0))

        if is_fast_path and not use_satislar_fallback:
            cursor.execute(f"SELECT SUM(toplam_ciro) as rev, SUM(toplam_fis) as fis FROM gunlukciroozet WHERE {where_clause}", params)
            res = cursor.fetchone()
            total_revenue = float(res["rev"] or 0)
            total_receipts = int(res["fis"] or 0)
        elif not (categories or brands):
            # Kategori/Marka filtresi yoksa ama diğerleri (tip, bölge, onay) varsa daily_metrics_summary kullanabiliriz
            # Çünkü daily_metrics_summary bu boyutları destekliyor.
            d_where = ["1=1"]
            d_params = []
            if start_date: d_where.append(f"tarih >= {placeholder}"); d_params.append(start_date)
            if end_date: d_where.append(f"tarih <= {placeholder}"); d_params.append(end_date)
            if region: d_where.append(f"magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})"); d_params.append(region)
            if customer_type: d_where.append(f"customer_type = {placeholder}"); d_params.append(customer_type)
            if approval_status: d_where.append(f"onay_durumu = {placeholder}"); d_params.append(approval_status)
            
            d_where_clause = " AND ".join(d_where)
            cursor.execute(f"SELECT SUM(revenue) as rev, SUM(receipt_count) as fis FROM daily_metrics_summary WHERE {d_where_clause}", d_params)
            res = cursor.fetchone()
            total_revenue = float(res["rev"] or 0)
            total_receipts = int(res["fis"] or 0)
        else:
            if is_fast_path:
                 cursor.execute(f"SELECT SUM(tutar) as rev, COUNT(DISTINCT fis_no) as fis FROM satislar WHERE {where_clause}", params)
                 res = cursor.fetchone()
                 total_revenue = res["rev"] or 0
                 total_receipts = res["fis"] or 0
            else:
                 agg_result = get_sales_analytics(
                    category=categories, brand=brands, customer_type=customer_type, 
                    region=region, start_date=start_date, end_date=end_date
                 )
                 total_revenue = agg_result.get("totalRevenue", 0) or 0
                 total_receipts = agg_result.get("totalReceipts", 0) or 0
                 total_customers = agg_result.get("totalCustomers", 0) or 0
                 total_prods = agg_result.get("totalProducts", 0) or 0
                 total_brands = agg_result.get("totalBrands", 0) or 0

        # Tarih filtresi var mı? Varsa cache kullanma, live sorgula
        has_date_filter = bool(start_date or end_date)

        # total_registered: Sistemdeki toplam kayıtlı müşteri sayısı (Tarih filtresinden bağımsız)
        total_registered = int(float(cache_data.get('total_registered_count', 0) or 0))
        if not total_registered or region or customer_type:
            m_where = ["1=1"]
            m_params = []
            if region:
                # Bölge filtresi varsa kayıt mağazasına göre filtrele
                m_where.append(f"kayit_magazasi IN (SELECT id::text FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})")
                m_params.append(region)
            if customer_type:
                m_where.append(f"tip = {placeholder}")
                m_params.append(customer_type)
            
            m_where_clause = " AND ".join(m_where)
            cursor.execute(f"SELECT COUNT(DISTINCT musteri_id) as cnt FROM musteriler WHERE {m_where_clause}", m_params)
            total_registered = cursor.fetchone()["cnt"] or 0

        # total_customers (Aktif): Seçili tarih ve filtrelerde işlem yapan benzersiz müşteri sayısı
        if not total_customers:
            if is_fast_path and not has_date_filter:
                total_customers = int(float(cache_data.get('active_customer_count', 0) or 0))
            
            if not total_customers:
                # Optimized Path: Eğer çok geniş bir tarih aralığı değilse veya summary table varsa oradan al
                # Şimdilik tutarlılık için satislar'dan JOIN ile alıyoruz ama subquery'den JOIN'e geçiyoruz (Daha hızlı)
                m_join_where = where_clause.replace("musteri_id IN (SELECT id FROM musteriler", "m.id IN (SELECT id FROM musteriler")
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT s.musteri_id) as cnt 
                    FROM satislar s
                    INNER JOIN musteriler m ON s.musteri_id = m.id
                    WHERE {where_clause}
                """, params)
                total_customers = cursor.fetchone()["cnt"] or 0

        # Güvenlik Kontrolü: Aktif müşteri sayısı toplam kayıtlı müşteri sayısından büyükse,
        # bu durum genellikle yetim kayıtlardan kaynaklanır. Tutarlılık için Aktif'i Toplam ile sınırla.
        # (Önceki mantık Toplam'ı artırarak Pasif'i yok ediyordu, artık Pasif korunacak şekilde Aktif'i kırpıyoruz)
        if total_customers > total_registered:
            total_customers = total_registered

        # ============================================================
        # TOPLAM MÜŞTERİ DURUMU — Aktif/Pasif tanımı (DEĞİŞTİRMEYİN)
        # ------------------------------------------------------------
        # "Aktif" = Tüm zamanlar içinde en az 1 satın alma yapmış müşteri
        # "Pasif" = Sistemde kayıtlı ama hiç satın alma yapmamış müşteri
        # Bu tanım DÖNEMSEL DEĞİLDİR — tarih filtresi uygulanmaz.
        # Dönemde alışveriş yapan/yapmayan sayısı bu kartın konusu DEĞİLDİR.
        # (totalCustomers değişkeni dönemsel aktif sayısı olup farklı amaçla kullanılır)
        # ============================================================
        ever_purchased_count = 0
        is_pg = db_engine.DB_BACKEND == "postgresql"
        mdo_toplam_alisveris = "toplam_alisveris" if is_pg else "ToplamAlisveris"
        
        # OPTIMIZATION: satislar tablosu yerine musteridetayozet kullan
        m_ever_where = [f"mdo.{mdo_toplam_alisveris} > 0"]
        m_ever_params = []
        if region:
            m_ever_where.append(f"m.kayit_magazasi IN (SELECT id::text FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})")
            m_ever_params.append(region)
        if customer_type:
            m_ever_where.append(f"m.tip = {placeholder}")
            m_ever_params.append(customer_type)
        m_ever_clause = " AND ".join(m_ever_where)
        cursor.execute(f"""
            SELECT COUNT(DISTINCT musteri_id) as cnt 
            FROM musteriler m
            INNER JOIN musteridetayozet mdo ON m.id = mdo.musteri_id
            WHERE {m_ever_clause}
        """, m_ever_params)
        ever_purchased_count = cursor.fetchone()["cnt"] or 0
        never_purchased_count = max(0, total_registered - ever_purchased_count)

        # approved/unapproved: tarih filtreli ise satislar JOIN musteriler
        approved_count = 0
        unapproved_count = 0
        if has_date_filter:
            cursor.execute(f"""
                SELECT mu.onay_durumu, COUNT(DISTINCT s.musteri_id) as cnt
                FROM satislar s
                JOIN musteriler mu ON s.musteri_id = mu.id
                WHERE {where_clause}
                GROUP BY mu.onay_durumu
            """, params)
            for r in cursor.fetchall():
                if str(r['onay_durumu'] or '').upper() == 'ONAYLI':
                    approved_count += r['cnt']
                else:
                    unapproved_count += r['cnt']
        else:
            approved_count = int(float(cache_data.get('approved_count', 0) or 0))
            unapproved_count = int(float(cache_data.get('unapproved_count', 0) or 0))
            if not (approved_count or unapproved_count):
                cursor.execute("SELECT onay_durumu, COUNT(DISTINCT musteri_id) as cnt FROM musteriler GROUP BY onay_durumu")
                for r in cursor.fetchall():
                    if str(r['onay_durumu'] or '').upper() == 'ONAYLI':
                        approved_count += r['cnt']
                    else:
                        unapproved_count += r['cnt']

        # churn_rate: tarih filtreli ise o dönemde alışveriş yapıp son 120 günde yapmayan müşteriler
        if has_date_filter:
            from datetime import timedelta
            # Dönem sonu tarihinden 120 gün önce
            if end_date:
                period_end = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                period_end = datetime.now()
            churn_thresh = (period_end - timedelta(days=120)).strftime("%Y-%m-%d")
            period_end_str = period_end.strftime("%Y-%m-%d")
            # O dönemde alışveriş yapıp son 120 günde (dönem sonu baz alarak) yapmayan müşteriler
            cursor.execute(f"""
                SELECT COUNT(DISTINCT musteri_id) as cnt
                FROM satislar
                WHERE {where_clause}
                AND musteri_id NOT IN (
                    SELECT DISTINCT musteri_id FROM satislar
                    WHERE tarih > {placeholder} AND tarih <= {placeholder}
                )
            """, params + [churn_thresh, period_end_str])
            churned_count = cursor.fetchone()['cnt'] or 0
            churn_rate = round((churned_count / total_registered * 100), 1) if total_registered > 0 else 0
        else:
            churn_rate = float(cache_data.get('churn_rate', -1) or -1)
            if churn_rate < 0:
                from datetime import timedelta
                churn_thresh = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
                if db_engine.DB_BACKEND == "postgresql":
                    cursor.execute(f"SELECT COUNT(DISTINCT musteri_id) as cnt FROM musteridetayozet WHERE son_alisveris_tarihi < {placeholder}", [churn_thresh])
                else:
                    cursor.execute(f"SELECT COUNT(DISTINCT musteri_id) as cnt FROM musteridetayozet WHERE SonAlisverisTarihi < {placeholder}", [churn_thresh])
                churn_row = cursor.fetchone()
                churned_count = (churn_row[0] if not isinstance(churn_row, dict) else churn_row['cnt']) or 0
                churn_rate = round((churned_count / total_registered * 100), 1) if total_registered > 0 else 0

        # loyalty_share: tarih filtreli ise o dönemdeki sadık müşteri cirosu / toplam ciro
        if has_date_filter:
            loyal_segments = ('01-) Şampiyonlar', '02-) Potansiyel Şampiyonlar', '03-) Sadık Müşteriler', '07-) Yüksek Harcama Yapanlar')
            seg_ph = ','.join([placeholder] * len(loyal_segments))
            cursor.execute(f"""
                SELECT SUM(s.tutar) as loyal_rev
                FROM satislar s
                JOIN musteridetayozet mu ON s.musteri_id = mu.musteri_id
                WHERE {where_clause}
                AND mu.rfm_segment IN ({seg_ph})
            """, params + list(loyal_segments))
            loyal_rev = cursor.fetchone()["loyal_rev"] or 0
            loyalty_share = round((loyal_rev / total_revenue * 100), 1) if total_revenue > 0 else 0
        else:
            loyalty_share = float(cache_data.get('loyalty_revenue_share', -1) or -1)
            if loyalty_share < 0:
                loyal_segments = ('01-) Şampiyonlar', '02-) Potansiyel Şampiyonlar', '03-) Sadık Müşteriler', '07-) Yüksek Harcama Yapanlar')
                if db_engine.DB_BACKEND == "postgresql":
                    cursor.execute(f"""
                        SELECT SUM(toplam_harcama) as loyal_rev
                        FROM musteridetayozet
                        WHERE rfm_segment IN ({','.join([placeholder]*len(loyal_segments))})
                    """, list(loyal_segments))
                else:
                    cursor.execute(f"""
                        SELECT SUM(ToplamHarcama) as loyal_rev
                        FROM musteridetayozet
                        WHERE RFM_Segment IN ({','.join([placeholder]*len(loyal_segments))})
                    """, list(loyal_segments))
                loyal_rev = cursor.fetchone()["loyal_rev"] or 0
                loyalty_share = round((loyal_rev / total_revenue * 100), 1) if total_revenue > 0 else 0

        return Response({
            "totalRevenue": total_revenue,
            "totalReceipts": total_receipts,
            "totalCustomers": total_customers,
            "totalRegisteredCustomers": total_registered,
            "everPurchasedCount": ever_purchased_count,
            "neverPurchasedCount": never_purchased_count,
            "totalProducts": total_prods,
            "totalBrands": total_brands,
            "averageOrderValue": round(total_revenue / total_receipts, 0) if total_receipts > 0 else 0,
            "avgTransactionsPerCustomer": round(total_receipts / total_customers, 2) if total_customers > 0 else 0,
            "avgRevenuePerCustomer": round(total_revenue / total_customers, 0) if total_customers > 0 else 0,
            "approvedCustomerCount": approved_count,
            "unapprovedCustomerCount": unapproved_count,
            "churnRate": churn_rate,
            "loyaltyShare": loyalty_share,
        })
    except Exception as e:
        logger.error(f"KPI Error: {e}", exc_info=True)
        try:
            with open("dashboard_error_dump.txt", "w") as f:
                f.write(traceback.format_exc())
        except: pass
        return Response({"error": str(e), "traceback": traceback.format_exc()}, status=500)
    finally:
        db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_trend(request, pk=None):
    """Dashboard Trend: Aylık/Günlük Satış Grafiği"""
    conn = db_engine.get_connection()
    try:
        cursor = db_engine.get_dict_cursor(conn)
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        customer_type = request.GET.get("customer_type") or request.GET.get("customerType")
        approval_status = request.GET.get("approval_status") or request.GET.get("approvalStatus")
        region = request.GET.get("region")
        year = request.GET.get("year")
        month = request.GET.get("month")

        placeholder = db_engine.ph()
        has_customer_filter = bool(customer_type or approval_status or region)

        # Tarih filtresi oluştur
        if not start_date and year:
            start_date = f"{year}-01-01"
            end_date = end_date or f"{year}-12-31"
        if not start_date and month and year:
            import calendar
            last_day = calendar.monthrange(int(year), int(month))[1]
            start_date = f"{year}-{int(month):02d}-01"
            end_date = f"{year}-{int(month):02d}-{last_day}"

        granularity = request.GET.get("granularity", "monthly")
        if granularity == "daily":
            date_expr = db_engine.strftime_expr('%Y-%m-%d', 'tarih')
        elif granularity == "weekly":
            date_expr = db_engine.strftime_expr('%Y-%W', 'tarih')
        else:
            date_expr = db_engine.strftime_expr('%Y-%m', 'tarih')

        if has_customer_filter:
            # Optimized Path: Use daily_metrics_summary
            where_parts = ["1=1"]
            params = []
            if start_date:
                where_parts.append(f"tarih >= {placeholder}")
                params.append(start_date)
            if end_date:
                where_parts.append(f"tarih <= {placeholder}")
                params.append(end_date)
            if month and not year and not start_date:
                if db_engine.DB_BACKEND == "postgresql":
                    where_parts.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
                else:
                    where_parts.append(f"substr(tarih, 6, 2) = {placeholder}")
                params.append(f"{int(month):02d}")
            if customer_type:
                where_parts.append(f"customer_type = {placeholder}")
                params.append(customer_type)
            if approval_status:
                where_parts.append(f"onay_durumu = {placeholder}")
                params.append(approval_status)
            if region:
                where_parts.append(f"magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})")
                params.append(region)
            
            where_clause = " AND ".join(where_parts)
            cursor.execute(f"""
                SELECT {date_expr} as month, SUM(revenue) as sales
                FROM daily_metrics_summary
                WHERE {where_clause}
                GROUP BY month ORDER BY month
            """, params)
            sales_by_month = [{"month": r["month"], "date": r["month"], "sales": r["sales"] or 0, "value": r["sales"] or 0} for r in cursor.fetchall()]
            
            # Fallback to slow path if no data in summary
            if not sales_by_month:
                s_date_expr = db_engine.strftime_expr('%Y-%m-%d', 's.tarih') if granularity == "daily" else db_engine.strftime_expr('%Y-%m', 's.tarih')
                where_parts_s = ["s.musteri_id IS NOT NULL"]
                params_s = []
                if start_date: where_parts_s.append(f"s.tarih >= {placeholder}"); params_s.append(start_date)
                if end_date: where_parts_s.append(f"s.tarih <= {placeholder}"); params_s.append(end_date)
                if month and not year and not start_date:
                    if db_engine.DB_BACKEND == "postgresql":
                        where_parts_s.append(f"TO_CHAR(s.tarih, 'MM') = {placeholder}")
                    else:
                        where_parts_s.append(f"substr(s.tarih, 6, 2) = {placeholder}")
                    params_s.append(f"{int(month):02d}")
                if customer_type: where_parts_s.append(f"s.musteri_id IN (SELECT id FROM musteriler WHERE tip = {placeholder})"); params_s.append(customer_type)
                cursor.execute(f"""
                    SELECT {s_date_expr} as month, SUM(s.tutar) as sales
                    FROM satislar s
                    WHERE {" AND ".join(where_parts_s)}
                    GROUP BY month ORDER BY month
                """, params_s)
                sales_by_month = [{"month": r["month"], "date": r["month"], "sales": r["sales"] or 0, "value": r["sales"] or 0} for r in cursor.fetchall()]
        else:
            where_parts = ["1=1"]
            params = []
            if start_date:
                where_parts.append(f"tarih >= {placeholder}")
                params.append(start_date)
            if end_date:
                where_parts.append(f"tarih <= {placeholder}")
                params.append(end_date)
            if month and not year and not start_date:
                if db_engine.DB_BACKEND == "postgresql":
                    where_parts.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
                else:
                    where_parts.append(f"substr(tarih, 6, 2) = {placeholder}")
                params.append(f"{int(month):02d}")
            where_clause = " AND ".join(where_parts)

            cursor.execute(f"""
                SELECT {date_expr} as month, SUM(toplam_ciro) as sales
                FROM gunlukciroozet WHERE {where_clause}
                GROUP BY month ORDER BY month
            """, params)
            sales_by_month = [{"month": r["month"], "date": r["month"], "sales": r["sales"] or 0, "value": r["sales"] or 0} for r in cursor.fetchall()]

            if not sales_by_month:
                cursor.execute(f"""
                    SELECT {date_expr} as month, SUM(tutar) as sales
                    FROM satislar WHERE {where_clause}
                    GROUP BY month ORDER BY month
                """, params)
                sales_by_month = [{"month": r["month"], "date": r["month"], "sales": r["sales"] or 0, "value": r["sales"] or 0} for r in cursor.fetchall()]

        return Response({"trend": sales_by_month, "salesByMonth": sales_by_month})
    finally:
        db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_comparison(request, pk=None):
    """Dashboard Comparison: 3 Yıllık Karşılaştırma (Tarih filtresi destekli)"""
    conn = db_engine.get_connection()
    try:
        cursor = db_engine.get_dict_cursor(conn)
        customer_type = request.GET.get("customer_type") or request.GET.get("customerType")
        approval_status = request.GET.get("approval_status") or request.GET.get("approvalStatus")
        region = request.GET.get("region")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        year = request.GET.get("year")
        month = request.GET.get("month")

        # Year/month parametrelerini tarih aralığına dönüştür
        if not start_date and year:
            try:
                import calendar
                y = int(year)
                if month:
                    m = int(month)
                    last_day = calendar.monthrange(y, m)[1]
                    start_date = f"{y}-{m:02d}-01"
                    end_date = end_date or f"{y}-{m:02d}-{last_day}"
                else:
                    start_date = f"{y}-01-01"
                    end_date = end_date or f"{y}-12-31"
            except (ValueError, TypeError):
                pass

        # Mevcut yıldan geriye 3 yıl hesapla (hardcoded 2024-2026 yerine dinamik)
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 2, current_year + 1)]
        comp_revenue = {y: [0] * 12 for y in years}
        comp_receipts = {y: [0] * 12 for y in years}
        comp_customers = {y: [0] * 12 for y in years}

        year_expr = db_engine.strftime_expr('%Y', 'tarih')
        month_expr = db_engine.strftime_expr('%m', 'tarih')
        placeholder = db_engine.ph()
        has_customer_filter = bool(customer_type or approval_status or region)
        has_date_filter = bool(start_date or end_date)

        # Tarih filtresi varsa onu kullan, yoksa son 3 yıl
        if has_date_filter:
            start_year = start_date[:4]
            end_year = end_date[:4] if end_date else str(current_year)
        else:
            start_year = years[0]
            end_year = years[-1]

        if has_customer_filter:
            # OPTIMIZED: 3 yıllık veri için daily_metrics_summary kullan
            d_where = []
            d_params = []
            if start_date: d_where.append(f"tarih >= {placeholder}"); d_params.append(start_date)
            if end_date: d_where.append(f"tarih <= {placeholder}"); d_params.append(end_date)
            if month and not year and not start_date:
                if db_engine.DB_BACKEND == "postgresql":
                    d_where.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
                else:
                    d_where.append(f"substr(tarih, 6, 2) = {placeholder}")
                d_params.append(f"{int(month):02d}")
            if customer_type: d_where.append(f"customer_type = {placeholder}"); d_params.append(customer_type)
            if approval_status: d_where.append(f"onay_durumu = {placeholder}"); d_params.append(approval_status)
            if region: d_where.append(f"magaza_id IN (SELECT id FROM magazalar WHERE bolge = {placeholder})"); d_params.append(region)
            
            d_where_clause = " AND ".join(d_where) if d_where else "1=1"
            d_year_expr = db_engine.strftime_expr('%Y', 'tarih')
            d_month_expr = db_engine.strftime_expr('%m', 'tarih')
            
            cursor.execute(f"""
                SELECT {d_year_expr} as year, {d_month_expr} as month,
                       SUM(revenue) as rev, SUM(receipt_count) as fis, SUM(customer_count) as cust
                FROM daily_metrics_summary
                WHERE {d_where_clause}
                GROUP BY year, month
            """, d_params)
            rows = cursor.fetchall()
            
            if not rows:
                # Fallback to satislar (Old slow way)
                where_parts = []
                params = []
                if start_date: where_parts.append(f"s.tarih >= {placeholder}"); params.append(start_date)
                if end_date: where_parts.append(f"s.tarih <= {placeholder}"); params.append(end_date)
                if month and not year and not start_date:
                    if db_engine.DB_BACKEND == "postgresql":
                        where_parts.append(f"TO_CHAR(s.tarih, 'MM') = {placeholder}")
                    else:
                        where_parts.append(f"substr(s.tarih, 6, 2) = {placeholder}")
                    params.append(f"{int(month):02d}")
                if customer_type: where_parts.append(f"s.musteri_id IN (SELECT id FROM musteriler WHERE tip = {placeholder})"); params.append(customer_type)
                if approval_status: where_parts.append(f"s.onay_durumu IN ({placeholder})"); params.append(approval_status)
                if region: where_parts.append(f"s.magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})"); params.append(region)
                where_clause = " AND ".join(where_parts) if where_parts else "1=1"
                s_year_expr = db_engine.strftime_expr('%Y', 's.tarih')
                s_month_expr = db_engine.strftime_expr('%m', 's.tarih')
                cursor.execute(f"""
                    SELECT {s_year_expr} as year, {s_month_expr} as month,
                           SUM(s.tutar) as rev, COUNT(DISTINCT s.fis_no) as fis, COUNT(DISTINCT s.musteri_id) as cust
                    FROM satislar s
                    WHERE {where_clause}
                    GROUP BY year, month
                """, params)
                rows = cursor.fetchall()
        else:
            where_parts = []
            params = []
            if start_date: where_parts.append(f"tarih >= {placeholder}"); params.append(start_date)
            if end_date: where_parts.append(f"tarih <= {placeholder}"); params.append(end_date)
            if month and not year and not start_date:
                if db_engine.DB_BACKEND == "postgresql":
                    where_parts.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
                else:
                    where_parts.append(f"substr(tarih, 6, 2) = {placeholder}")
                params.append(f"{int(month):02d}")
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"

            cursor.execute(f"""
                SELECT {year_expr} as year, {month_expr} as month,
                       SUM(toplam_ciro) as rev, SUM(toplam_fis) as fis, SUM(toplam_musteri) as cust
                FROM gunlukciroozet
                WHERE {where_clause}
                GROUP BY year, month
            """, params)
            rows = cursor.fetchall()

            if not rows:
                cursor.execute(f"""
                    SELECT {year_expr} as year, {month_expr} as month,
                           SUM(tutar) as rev, COUNT(DISTINCT fis_no) as fis, COUNT(DISTINCT musteri_id) as cust
                    FROM satislar
                    WHERE {where_clause}
                    GROUP BY year, month
                """, params)
                rows = cursor.fetchall()

        for row in rows:
            y = str(row["year"])
            m_idx = int(row["month"]) - 1
            if y in comp_revenue and 0 <= m_idx <= 11:
                comp_revenue[y][m_idx] = float(row["rev"] or 0)
                comp_receipts[y][m_idx] = int(row["fis"] or 0)
                comp_customers[y][m_idx] = int(row["cust"] or 0)

        return Response({
            "comparisonStats": {
                "revenue": comp_revenue,
                "receipts": comp_receipts,
                "customers": comp_customers,
            }
        })
    finally:
        db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_segments(request, pk=None):
    """Dashboard Segments: RFM Segment Dağılımı"""
    conn = db_engine.get_connection()
    try:
        cursor = db_engine.get_dict_cursor(conn)
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        customer_type = request.GET.get("customer_type") or request.GET.get("customerType")
        approval_status = request.GET.get("approval_status") or request.GET.get("approvalStatus")
        region = request.GET.get("region")
        placeholder = db_engine.ph()
        has_date_filter = bool(start_date or end_date)
        has_customer_filter = bool(customer_type or approval_status or region)

        if has_date_filter or has_customer_filter:
            # Optimized Path: Use daily_metrics_summary for revenue and musteridetayozet for count
            where_parts = ["1=1"]
            params = []
            if start_date:
                where_parts.append(f"tarih >= {placeholder}")
                params.append(start_date)
            if end_date:
                where_parts.append(f"tarih <= {placeholder}")
                params.append(end_date)
            if customer_type:
                where_parts.append(f"customer_type = {placeholder}")
                params.append(customer_type)
            if approval_status:
                where_parts.append(f"onay_durumu = {placeholder}")
                params.append(approval_status)
            if region:
                where_parts.append(f"magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})")
                params.append(region)
            
            where_clause = " AND ".join(where_parts)
            
            # Get Revenue from Summary (Fast) — rfm_segment NULL olsa bile group by yap
            cursor.execute(f"""
                SELECT COALESCE(rfm_segment, 'Belirsiz') as rfm_segment, SUM(revenue) as revenue, SUM(customer_count) as approx_count
                FROM daily_metrics_summary
                WHERE {where_clause}
                GROUP BY rfm_segment
            """, params)
            seg_rows = cursor.fetchall()
            
            # If we need accurate counts and it's not too large, or as a fallback
            if not seg_rows:
                 # Fallback to slow path only if absolutely necessary
                 cursor.execute(f"""
                    SELECT mu.rfm_segment, COUNT(DISTINCT s.musteri_id) as count, SUM(s.tutar) as revenue
                    FROM satislar s
                    JOIN musteridetayozet mu ON s.musteri_id = mu.musteri_id
                    WHERE {where_clause.replace('customer_type', 'mu.tip').replace('tarih', 's.tarih')}
                    GROUP BY mu.rfm_segment
                """, params)
                 seg_rows = cursor.fetchall()
            else:
                # Rename approx_count to count for compatibility
                for r in seg_rows:
                    r['count'] = r['approx_count']
        elif db_engine.DB_BACKEND == "postgresql":
            cursor.execute("""
                SELECT rfm_segment, COUNT(DISTINCT musteri_id) as count, SUM(toplam_harcama) as revenue
                FROM musteridetayozet
                WHERE rfm_segment IS NOT NULL
                GROUP BY rfm_segment
            """)
            seg_rows = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT RFM_Segment as rfm_segment, COUNT(DISTINCT musteri_id) as count, SUM(ToplamHarcama) as revenue
                FROM musteridetayozet
                WHERE RFM_Segment IS NOT NULL
                GROUP BY RFM_Segment
            """)
            seg_rows = cursor.fetchall()

        if not seg_rows:
            cursor.execute("SELECT rfm_segment, COUNT(DISTINCT musteri_id) as count, 0 as revenue FROM musteriler WHERE rfm_segment IS NOT NULL GROUP BY rfm_segment")
            seg_rows = cursor.fetchall()

        OLD_TO_NEW = {
            'Sampiyonlar': '01-) Şampiyonlar', 'Şampiyonlar': '01-) Şampiyonlar',
            'Potansiyel Sampiyonlar': '02-) Potansiyel Şampiyonlar', 'Potansiyel Şampiyonlar': '02-) Potansiyel Şampiyonlar',
            'Sadiklar': '03-) Sadık Müşteriler', 'Sadık Müşteriler': '03-) Sadık Müşteriler',
            'Sadik Olmaya Adaylar': '04-) Sadık Olmaya Adaylar', 'Sadık Olmaya Adaylar': '04-) Sadık Olmaya Adaylar',
            'Yeni Musteriler': '05-) Yeni Müşteriler', 'Yeni Müşteriler': '05-) Yeni Müşteriler',
            'Tekrar Kazanilanlar': '06-) Tekrar Kazanılanlar', 'Tekrar Kazanılanlar': '06-) Tekrar Kazanılanlar',
            'Yuksek Harcama Yapanlar': '07-) Yüksek Harcama Yapanlar', 'Yüksek Harcama Yapanlar': '07-) Yüksek Harcama Yapanlar',
            'Ilgi Bekleyenler': '08-) İlgi Bekleyenler', 'İlgi Bekleyenler': '08-) İlgi Bekleyenler',
            'Risk Altindakiler': '09-) Risk Altındakiler', 'Risk Altındakiler': '09-) Risk Altındakiler',
            'Uyuyanlar': '10-) Uyuyanlar',
            'Kayip Musteriler': '11-) Kayıp Müşteriler', 'Kayıp Müşteriler': '11-) Kayıp Müşteriler',
        }

        merged_segments = {}
        for r in seg_rows:
            raw_name = str(r["rfm_segment"]).strip()
            normalized = raw_name if (len(raw_name) > 3 and raw_name[2:4] == '-)') else OLD_TO_NEW.get(raw_name, raw_name)
            
            if normalized in merged_segments:
                merged_segments[normalized]['count'] += r["count"]
                merged_segments[normalized]['revenue'] += (r["revenue"] or 0)
            else:
                merged_segments[normalized] = {'count': r["count"], 'revenue': (r["revenue"] or 0)}
        
        total_seg_cust = sum(s['count'] for s in merged_segments.values())
        total_seg_rev = sum(s['revenue'] for s in merged_segments.values())
        
        segments = []
        for seg_name, seg_data in sorted(merged_segments.items()):
            segments.append({
                "segment": seg_name,
                "count": seg_data['count'],
                "revenue": round(seg_data['revenue'], 0),
                "customerPercent": round((seg_data['count'] / total_seg_cust * 100), 1) if total_seg_cust > 0 else 0,
                "revenuePercent": round((seg_data['revenue'] / total_seg_rev * 100), 1) if total_seg_rev > 0 else 0,
            })
        return Response({"customerSegments": segments})
    finally:
        db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_filters(request):
    """Dashboard Filters: Sadece filtre dropdown'ları için hafif veri"""
    conn = db_engine.get_connection()
    try:
        cursor = db_engine.get_dict_cursor(conn)
        
        # Available Years — PostgreSQL uyumlu
        if db_engine.DB_BACKEND == "postgresql":
            cursor.execute("SELECT DISTINCT EXTRACT(YEAR FROM tarih)::int as year FROM gunlukciroozet ORDER BY year DESC")
        else:
            cursor.execute("SELECT DISTINCT strftime('%Y', tarih) as year FROM gunlukciroozet ORDER BY year DESC")
        years = [int(r["year"]) for r in cursor.fetchall() if r["year"]]
        if not years: years = [2024, 2025, 2026]

        # Regions (magazalar is a small lookup table, this is fine)
        if db_engine.DB_BACKEND == "postgresql":
            cursor.execute("SELECT DISTINCT REPLACE(bolge, CHR(65533), 'ö') as bolge FROM magazalar WHERE bolge IS NOT NULL ORDER BY bolge")
        else:
            cursor.execute("SELECT DISTINCT REPLACE(bolge, char(65533), 'ö') as bolge FROM magazalar WHERE bolge IS NOT NULL ORDER BY bolge")
        regions = [r["bolge"] for r in cursor.fetchall() if r["bolge"]]

        # Customer Types & Approval Status (Using summary table instead of 3M+ musteriler table)
        cursor.execute("SELECT DISTINCT customer_type FROM daily_metrics_summary WHERE customer_type IS NOT NULL ORDER BY customer_type")
        customer_types = [r["customer_type"] for r in cursor.fetchall() if r["customer_type"]]

        cursor.execute("SELECT DISTINCT onay_durumu FROM daily_metrics_summary WHERE onay_durumu IS NOT NULL ORDER BY onay_durumu")
        approval_statuses = [r["onay_durumu"] for r in cursor.fetchall() if r["onay_durumu"]]

        return Response({
            "availableYears": years,
            "availableRegions": regions,
            "availableCustomerTypes": customer_types,
            "availableApprovalStatuses": approval_statuses
        })
    except Exception as e:
        logger.error(f"Filters Error: {e}", exc_info=True)
        return Response({"error": str(e)}, status=500)
    finally:
        db_engine.release_connection(conn)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_sqlite_direct(request):
    """
    Dashboard Ana Sayfa için doğrudan SQLite/PostgreSQL optimizasyonu.
    Tek bir request'te tüm dashboard verilerini (KPI, Trend, Karşılaştırma, Segmentler) döndürür.
    Tüm alt sorgularda global filtreleri (Bölge, Müşteri Tipi, Onay Durumu) uygular.
    """
    import time
    from datetime import datetime, timedelta
    from .base import _build_dashboard_cache_key, _get_cached_dashboard, _set_cached_dashboard
    
    start_time = time.perf_counter()

    # Helper function for robust row value extraction
    def get_val(row, key, default=0):
        if not row: return default
        if isinstance(row, dict): return row.get(key) or default
        try: return row[key] or default
        except: return default

    # 1. Filtreleri al
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    year = request.GET.get("year")
    month = request.GET.get("month")
    
    # Tarih aralığını normalize et
    if not start_date and year:
        start_date = f"{year}-01-01"
        end_date = end_date or f"{year}-12-31"
        if month:
            import calendar
            last_day = calendar.monthrange(int(year), int(month))[1]
            start_date = f"{year}-{int(month):02d}-01"
            end_date = f"{year}-{int(month):02d}-{last_day}"

    # Sadece ay seçildiğinde (year olmadan) işaretle
    only_month = month and not year and not start_date

    categories = [c for c in request.GET.get("categories", "").split(",") if c.strip()] or None
    brands = [b for b in request.GET.get("brands", "").split(",") if b.strip()] or None
    customer_type = request.GET.get("customer_type") or request.GET.get("customerType")
    approval_status = request.GET.get("approval_status") or request.GET.get("approvalStatus")
    region = request.GET.get("region")

    # Cache kontrolü
    cache_key = _build_dashboard_cache_key(start_date, end_date, year, month, categories, brands, customer_type, approval_status, region)
    cached = _get_cached_dashboard(cache_key)
    if cached is not None:
        logger.info(f"Dashboard Full Summary (CACHED) took {time.perf_counter() - start_time:.4f}s")
        return Response(cached)

    conn = db_engine.get_connection()
    try:
        cursor = db_engine.get_dict_cursor(conn)
        placeholder = db_engine.ph()
        
        # WHERE clause builder
        where_parts = ["1=1"]
        params = []
        if start_date: where_parts.append(f"tarih >= {placeholder}"); params.append(start_date)
        if end_date: where_parts.append(f"tarih <= {placeholder}"); params.append(end_date)
        if only_month:
            if db_engine.DB_BACKEND == "postgresql":
                where_parts.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
            else:
                where_parts.append(f"substr(tarih, 6, 2) = {placeholder}")
            params.append(f"{int(month):02d}")
        
        # Base filters for all metrics
        where_clause = " AND ".join(where_parts)

        # Gelişmiş Filtreler (Subqueries)
        adv_where = ["1=1"]
        adv_params = []
        if region: adv_where.append(f"magaza_id IN (SELECT id FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})"); adv_params.append(region)
        if customer_type: adv_where.append(f"customer_type = {placeholder}"); adv_params.append(customer_type)
        if approval_status: adv_where.append(f"onay_durumu = {placeholder}"); adv_params.append(approval_status)
        if only_month:
            if db_engine.DB_BACKEND == "postgresql":
                adv_where.append(f"TO_CHAR(tarih, 'MM') = {placeholder}")
            else:
                adv_where.append(f"substr(tarih, 6, 2) = {placeholder}")
            adv_params.append(f"{int(month):02d}")
        
        # 1. KPIs (Revenue, Receipts) - daily_metrics_summary üzerinden HIZLI
        kpi_query = f"""
            SELECT SUM(revenue) as rev, SUM(receipt_count) as fis, SUM(customer_count) as cust 
            FROM daily_metrics_summary 
            WHERE {where_clause} AND {" AND ".join(adv_where)}
        """
        cursor.execute(kpi_query, params + adv_params)
        kpi_res = cursor.fetchone()
        total_revenue = get_val(kpi_res, "rev")
        total_receipts = get_val(kpi_res, "fis")
        total_customers = get_val(kpi_res, "cust")

        # 2. Total Registered & Ever Purchased (Tarih filtresinden bağımsız, ama diğer filtrelere bağlı)
        # MUSTERILER tablosu üzerinden
        m_where = ["1=1"]
        m_params = []
        if region: m_where.append(f"kayit_magazasi IN (SELECT id::text FROM magazalar WHERE {db_engine.bolge_expr('bolge')} = {placeholder})"); m_params.append(region)
        if customer_type: m_where.append(f"tip = {placeholder}"); m_params.append(customer_type)
        
        cursor.execute(f"SELECT COUNT(id) as cnt FROM musteriler WHERE {" AND ".join(m_where)}", m_params)
        total_registered = cursor.fetchone()["cnt"] or 0

        # Ever Purchased (Müşteri Detay Özet üzerinden HIZLI)
        mdo_alisveris_col = "toplam_alisveris" if db_engine.DB_BACKEND == "postgresql" else "ToplamAlisveris"
        cursor.execute(f"""
            SELECT COUNT(m.id) as cnt 
            FROM musteriler m
            INNER JOIN musteridetayozet mdo ON m.id = mdo.musteri_id
            WHERE {" AND ".join(m_where)} AND mdo.{mdo_alisveris_col} > 0
        """, m_params)
        ever_purchased_count = cursor.fetchone()["cnt"] or 0
        never_purchased_count = max(0, total_registered - ever_purchased_count)

        # 3. Sales By Month (Trend)
        month_expr = db_engine.strftime_expr('%Y-%m', 'tarih')
        cursor.execute(f"""
            SELECT {month_expr} as month, SUM(revenue) as sales
            FROM daily_metrics_summary
            WHERE {where_clause} AND {" AND ".join(adv_where)}
            GROUP BY month ORDER BY month
        """, params + adv_params)
        sales_by_month = [{"month": r["month"], "sales": r["sales"] or 0} for r in cursor.fetchall()]

        # 4. Comparison Stats (3 Yıllık - Filtrelerle uyumlu!)
        current_year = datetime.now().year
        comp_years = [str(y) for y in range(current_year - 2, current_year + 1)]
        comp_revenue = {y: [0] * 12 for y in comp_years}
        comp_receipts = {y: [0] * 12 for y in comp_years}
        comp_customers = {y: [0] * 12 for y in comp_years}

        year_expr = db_engine.strftime_expr('%Y', 'tarih')
        month_expr_num = db_engine.strftime_expr('%m', 'tarih')
        
        cursor.execute(f"""
            SELECT {year_expr} as year, {month_expr_num} as month,
                   SUM(revenue) as rev, SUM(receipt_count) as fis, SUM(customer_count) as cust
            FROM daily_metrics_summary
            WHERE {year_expr} IN ({placeholder}, {placeholder}, {placeholder})
            AND {" AND ".join(adv_where)}
            GROUP BY year, month
        """, comp_years + adv_params)
        
        for r in cursor.fetchall():
            y = str(r["year"])
            m_idx = int(r["month"]) - 1
            if y in comp_revenue and 0 <= m_idx <= 11:
                comp_revenue[y][m_idx] = float(r["rev"] or 0)
                comp_receipts[y][m_idx] = int(r["fis"] or 0)
                comp_customers[y][m_idx] = int(r["cust"] or 0)

        # 5. Segments (Filtrelerle uyumlu)
        cursor.execute(f"""
            SELECT COALESCE(rfm_segment, 'Belirsiz') as rfm_segment, SUM(revenue) as revenue, SUM(customer_count) as cnt
            FROM daily_metrics_summary
            WHERE {where_clause} AND {" AND ".join(adv_where)}
            GROUP BY rfm_segment
        """, params + adv_params)
        seg_rows = cursor.fetchall()
        
        # Segment Normalizasyonu (Existing Logic)
        OLD_TO_NEW = {
            'Sampiyonlar': '01-) Şampiyonlar', 'Şampiyonlar': '01-) Şampiyonlar',
            'Potansiyel Sampiyonlar': '02-) Potansiyel Şampiyonlar', 'Potansiyel Şampiyonlar': '02-) Potansiyel Şampiyonlar',
            'Sadiklar': '03-) Sadık Müşteriler', 'Sadık Müşteriler': '03-) Sadık Müşteriler',
            'Sadik Olmaya Adaylar': '04-) Sadık Olmaya Adaylar', 'Sadık Olmaya Adaylar': '04-) Sadık Olmaya Adaylar',
            'Yeni Musteriler': '05-) Yeni Müşteriler', 'Yeni Müşteriler': '05-) Yeni Müşteriler',
            'Tekrar Kazanilanlar': '06-) Tekrar Kazanılanlar', 'Tekrar Kazanılanlar': '06-) Tekrar Kazanılanlar',
            'Yuksek Harcama Yapanlar': '07-) Yüksek Harcama Yapanlar', 'Yüksek Harcama Yapanlar': '07-) Yüksek Harcama Yapanlar',
            'Ilgi Bekleyenler': '08-) İlgi Bekleyenler', 'İlgi Bekleyenler': '08-) İlgi Bekleyenler',
            'Risk Altindakiler': '09-) Risk Altındakiler', 'Risk Altındakiler': '09-) Risk Altındakiler',
            'Uyuyanlar': '10-) Uyuyanlar', 'Kayip Musteriler': '11-) Kayıp Müşteriler', 'Kayıp Müşteriler': '11-) Kayıp Müşteriler',
        }
        
        merged_segments = {}
        for r in seg_rows:
            raw_name = str(r["rfm_segment"]).strip()
            normalized = raw_name if (len(raw_name) > 3 and raw_name[2:4] == '-)') else OLD_TO_NEW.get(raw_name, raw_name)
            if normalized in merged_segments:
                merged_segments[normalized]['count'] += r["cnt"]
                merged_segments[normalized]['revenue'] += (r["revenue"] or 0)
            else:
                merged_segments[normalized] = {'count': r["cnt"], 'revenue': (r["revenue"] or 0)}
        
        total_seg_cust = sum(s['count'] for s in merged_segments.values())
        total_seg_rev = sum(s['revenue'] for s in merged_segments.values())
        
        segments = []
        for seg_name, seg_data in sorted(merged_segments.items()):
            segments.append({
                "segment": seg_name, "count": seg_data['count'], "revenue": round(seg_data['revenue'], 0),
                "customerPercent": round((seg_data['count'] / total_seg_cust * 100), 1) if total_seg_cust > 0 else 0,
                "revenuePercent": round((seg_data['revenue'] / total_seg_rev * 100), 1) if total_seg_rev > 0 else 0,
            })

        # 6. Churn Rate & Loyalty (Simplified for speed)
        # Churn: Max date in musteridetayozet < today - 120 days
        churn_thresh = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")
        son_alisveris_col = "son_alisveris_tarihi" if db_engine.DB_BACKEND == "postgresql" else "SonAlisverisTarihi"
        cursor.execute(f"""
            SELECT COUNT(*) as cnt FROM musteridetayozet 
            WHERE {son_alisveris_col} < {placeholder}
            AND musteri_id IN (SELECT id FROM musteriler WHERE {" AND ".join(m_where)})
        """, [churn_thresh] + m_params)
        churned_count = cursor.fetchone()["cnt"] or 0
        churn_rate = round((churned_count / total_registered * 100), 1) if total_registered > 0 else 0

        # Approval Counts
        cursor.execute(f"SELECT COUNT(id) as cnt FROM musteriler WHERE {" AND ".join(m_where)} AND onay_durumu = 'ONAYLI'", m_params)
        approved_count = cursor.fetchone()["cnt"] or 0
        cursor.execute(f"SELECT COUNT(id) as cnt FROM musteriler WHERE {" AND ".join(m_where)} AND onay_durumu = 'ONAYSIZ'", m_params)
        unapproved_count = cursor.fetchone()["cnt"] or 0

        # Loyalty: Şampiyon/Sadık/Yüksek Harcama segmentlerinin ciro payı
        loyal_segments = ('01-) Şampiyonlar', '02-) Potansiyel Şampiyonlar', '03-) Sadık Müşteriler', '07-) Yüksek Harcama Yapanlar')
        total_loyal_rev = sum(s['revenue'] for n, s in merged_segments.items() if n in loyal_segments)
        loyalty_share = round((total_loyal_rev / total_revenue * 100), 1) if total_revenue > 0 else 0

        # Additional counts from cache/lookups
        cursor.execute("SELECT COUNT(id) as cnt FROM urunler")
        total_prods = cursor.fetchone()["cnt"] or 0
        cursor.execute("SELECT COUNT(id) as cnt FROM markalar")
        total_brands = cursor.fetchone()["cnt"] or 0

        # Fetch regions
        cursor.execute(f"SELECT DISTINCT {db_engine.bolge_expr('bolge')} as bolge FROM magazalar WHERE bolge IS NOT NULL")
        available_regions = [r["bolge"] for r in cursor.fetchall() if r["bolge"]]

        response_data = {
            "totalRevenue": total_revenue,
            "totalReceipts": total_receipts,
            "totalCustomers": total_customers,
            "totalRegisteredCustomers": total_registered,
            "approvedCustomerCount": approved_count,
            "unapprovedCustomerCount": unapproved_count,
            "everPurchasedCount": ever_purchased_count,
            "neverPurchasedCount": never_purchased_count,
            "totalProducts": total_prods,
            "totalBrands": total_brands,
            "averageOrderValue": round(total_revenue / total_receipts, 0) if total_receipts > 0 else 0,
            "avgTransactionsPerCustomer": round(total_receipts / total_customers, 2) if total_customers > 0 else 0,
            "avgRevenuePerCustomer": round(total_revenue / total_customers, 0) if total_customers > 0 else 0,
            "loyaltyShare": loyalty_share,
            "churnRate": churn_rate,
            "salesByMonth": sales_by_month,
            "customerSegments": segments,
            "comparisonStats": {
                "revenue": comp_revenue,
                "receipts": comp_receipts,
                "customers": comp_customers,
            },
            "breakdown": {
                "registered": never_purchased_count,
                "showPlus": ever_purchased_count,
            },
            "availableYears": comp_years,
            "availableCustomerTypes": ["BİREYSEL", "KURUMSAL"],
            "availableApprovalStatuses": ["ONAYLI", "ONAYSIZ"],
            "availableRegions": available_regions,
        }

        _set_cached_dashboard(cache_key, response_data)
        logger.info(f"Dashboard Full Summary took {time.perf_counter() - start_time:.4f}s")
        return Response(response_data)

    except Exception as e:
        logger.error(f"Dashboard Full Summary Error: {e}", exc_info=True)
        return Response({"error": str(e)}, status=500)
    finally:
        db_engine.release_connection(conn)

