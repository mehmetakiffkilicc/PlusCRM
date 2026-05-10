"""
Customer Segmentation Analysis View
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
import logging

from ..models import DataSource
from .base import (
    get_datasource_data,
    filter_data_by_date,
    get_cached_data,
    set_cached_data,
    get_user_from_request,
    detect_columns,
    _build_filter_cache_key,
    _get_ttl_cache,
    _set_ttl_cache,
    _segmentation_filter_cache,
    _segmentation_filter_cache_timeout,
    _segmentation_filter_cache_max_entries
)

logger = logging.getLogger(__name__)

_segment_detail_cache = {}
_segment_detail_cache_timeout = 300  # 5 dakika


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_segmentation_analysis(request, data_source_id):
    """Müşteri segmentasyonu analizi endpoint'i - Veritabanı Optimizasyonlu"""
    try:
        user = get_user_from_request(request)
        
        # Filtreleri al
        year = request.GET.get('year')
        month = request.GET.get('month')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
        approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')
        region = request.GET.get('region')
        has_filters = any([year, month, start_date, end_date, customer_type, approval_status, region])

        # Önbellek anahtarı oluştur ve kontrol et
        seg_cache_key = _build_filter_cache_key(data_source_id, user.id if user else None, request)
        cached = _get_ttl_cache(_segmentation_filter_cache, seg_cache_key, _segmentation_filter_cache_timeout)
        if cached is not None:
            return Response(cached)

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)

        # Veri kaynağı tipine göre strateji belirle
        is_db = getattr(data_source, 'type', '') == 'database' or \
                'sal' in getattr(data_source, 'name', '').lower() or \
                'sat' in getattr(data_source, 'name', '').lower()

        segment_data_list = []
        total_customers = 0

        if is_db:
            # === VERİTABANI OPTİMİZASYONU ===
            from .. import db_engine
            conn = db_engine.get_connection()
            cursor = db_engine.get_dict_cursor(conn)
            ph = db_engine.ph()

            if not has_filters:
                # 1. HIZLI YOL: Filtre yoksa doğrudan musteridetayozet'ten çek (Saniyeler yerine milisaniyeler)
                cursor.execute("""
                    SELECT 
                        rfm_segment as name, 
                        COUNT(DISTINCT musteri_id) as count, 
                        SUM(toplam_harcama) as revenue,
                        SUM(toplam_alisveris) as transactions
                    FROM musteridetayozet
                    WHERE rfm_segment IS NOT NULL
                    GROUP BY rfm_segment
                """)
                results = cursor.fetchall()
                # Toplam müşteri sayısı
                cursor.execute("SELECT COUNT(DISTINCT musteri_id) as cnt FROM musteridetayozet WHERE rfm_segment IS NOT NULL")
                total_customers = db_engine.val(cursor.fetchone(), 'cnt') or 0
            else:
                # 2. FİLTRELİ YOL: Satislar ve Musteriler join'i ile SQL üzerinden hesapla (Belleğe tüm satırları çekmez)
                from .base import parse_date_fast
                where_clauses = ["s.musteri_id IS NOT NULL", "m.rfm_segment IS NOT NULL"]
                params = []

                if year:
                    year_expr = db_engine.strftime_expr('%Y', 's.tarih')
                    where_clauses.append(f"{year_expr} = {ph}")
                    params.append(str(year))
                if month:
                    month_expr = db_engine.strftime_expr('%m', 's.tarih')
                    where_clauses.append(f"CAST({month_expr} AS INTEGER) = {ph}")
                    params.append(int(month))
                if start_date:
                    where_clauses.append(f"s.tarih >= {ph}")
                    params.append(start_date)
                if end_date:
                    where_clauses.append(f"s.tarih <= {ph}")
                    params.append(end_date)
                if customer_type:
                    where_clauses.append(f"m.tip = {ph}")
                    params.append(customer_type)
                if approval_status:
                    where_clauses.append(f"m.onay_durumu = {ph}")
                    params.append(approval_status)
                if region:
                    where_clauses.append(f"m.kayit_magazasi IN (SELECT id::text FROM magazalar WHERE bolge = {ph})")
                    params.append(region)

                where_sql = " AND ".join(where_clauses)
                
                query = f"""
                    SELECT 
                        m.rfm_segment as name,
                        COUNT(DISTINCT m.id) as count,
                        SUM(s.tutar) as revenue,
                        COUNT(DISTINCT s.fis_no) as transactions
                    FROM satislar s
                    JOIN musteriler m ON s.musteri_id = m.id
                    WHERE {where_sql}
                    GROUP BY m.rfm_segment
                """
                cursor.execute(query, params)
                results = cursor.fetchall()

                # Filtreli toplam müşteri sayısı
                cursor.execute(f"SELECT COUNT(DISTINCT musteri_id) as cnt FROM satislar s WHERE {where_sql}", params)
                total_customers = db_engine.val(cursor.fetchone(), 'cnt') or 0

            db_engine.release_connection(conn)

            # Renkler
            colors = {
                '01-) Şampiyonlar': '#9333ea', '02-) Potansiyel Şampiyonlar': '#3b82f6',
                '03-) Sadık Müşteriler': '#0ea5e9', '04-) Sadık Olmaya Adaylar': '#10b981',
                '05-) Yeni Müşteriler': '#22c55e', '06-) Tekrar Kazanılanlar': '#14b8a6',
                '07-) Yüksek Harcama Yapanlar': '#ec4899', '08-) İlgi Bekleyenler': '#f59e0b',
                '09-) Risk Altındakiler': '#f97316', '10-) Uyuyanlar': '#6b7280',
                '11-) Kayıp Müşteriler': '#ef4444'
            }

            for row in results:
                name = row['name']
                count = row['count']
                rev = row['revenue'] or 0
                tx = row['transactions'] or 0
                
                percentage = round((count / total_customers * 100), 1) if total_customers > 0 else 0
                avg_order = round(rev / tx, 2) if tx > 0 else 0
                
                segment_data_list.append({
                    'name': name,
                    'count': count,
                    'percentage': percentage,
                    'revenue': round(rev, 2),
                    'avgOrderValue': avg_order,
                    'color': colors.get(name, '#6366f1')
                })
        else:
            # === CSV / JSON FALLBACK (Mevcut Algoritma) ===
            data = get_datasource_data(data_source)
            if not data:
                return Response({'segments': [], 'totalCustomers': 0})
            
            data = filter_data_by_date(data, request)
            first_row_keys = list(data[0].keys()) if data else []
            columns = detect_columns(first_row_keys, data_source.column_mapping)
            customer_id_col = columns.get('customer_id_col') or 'Müşteri Kodu'
            segment_col = columns.get('segment_col') or 'Müşteri Segmenti'
            amount_col = columns.get('revenue_col') or 'Satış Tutarı'

            segment_data = {}
            customer_ids = set()
            for row in data:
                cid = row.get(customer_id_col)
                seg = row.get(segment_col, 'Tanımsız')
                if not cid: continue
                customer_ids.add(cid)
                
                try: 
                    amt = float(str(row.get(amount_col, 0)).replace(',', '.'))
                except: 
                    amt = 0

                if seg not in segment_data:
                    segment_data[seg] = {'customers': set(), 'revenue': 0, 'transactions': 0}
                segment_data[seg]['customers'].add(cid)
                segment_data[seg]['revenue'] += amt
                segment_data[seg]['transactions'] += 1

            total_customers = len(customer_ids)
            colors = {
                '01-) Şampiyonlar': '#9333ea', '02-) Potansiyel Şampiyonlar': '#3b82f6',
                '03-) Sadık Müşteriler': '#0ea5e9', '04-) Sadık Olmaya Adaylar': '#10b981',
                '05-) Yeni Müşteriler': '#22c55e', '06-) Tekrar Kazanılanlar': '#14b8a6',
                '07-) Yüksek Harcama Yapanlar': '#ec4899', '08-) İlgi Bekleyenler': '#f59e0b',
                '09-) Risk Altındakiler': '#f97316', '10-) Uyuyanlar': '#6b7280',
                '11-) Kayıp Müşteriler': '#ef4444'
            }

            for name, s_data in segment_data.items():
                c_count = len(s_data['customers'])
                percentage = round((c_count / total_customers * 100), 1) if total_customers > 0 else 0
                avg_val = round(s_data['revenue'] / s_data['transactions'], 2) if s_data['transactions'] > 0 else 0
                segment_data_list.append({
                    'name': name,
                    'count': c_count,
                    'percentage': percentage,
                    'revenue': round(s_data['revenue'], 2),
                    'avgOrderValue': avg_val,
                    'color': colors.get(name, '#6366f1')
                })

        # Sort by revenue
        segment_data_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        response_data = {
            'segments': segment_data_list,
            'totalCustomers': total_customers
        }
        
        _set_ttl_cache(_segmentation_filter_cache, seg_cache_key, response_data, _segmentation_filter_cache_max_entries)
        return Response(response_data)

    except DataSource.DoesNotExist:
        return Response({'error': 'Veri kaynağı bulunamadı'}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_segment_detailed_analysis(request, data_source_id):
    """
    Seçili segment/etiket için detaylı davranışsal analiz özeti.
    Ortalama sepet, en çok alınan kategoriler, risk durumu vb.
    Tarih filtresi ile dönemsel hesaplama destekler.
    """
    try:
        user = get_user_from_request(request)
        etiket = request.GET.get('etiketler')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not etiket:
            return Response({'error': 'Etiket parametresi gerekli'}, status=400)
        
        # Cache kontrolü (sadece filtresiz ise)
        import time as _time
        cache_key = f"seg_detail_{data_source_id}_{etiket}"
        if not (start_date or end_date):
            cached = _segment_detail_cache.get(cache_key)
            if cached and (_time.time() - cached['ts']) < _segment_detail_cache_timeout:
                return Response(cached['data'])
        
        from .. import db_engine
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()
        
        # Etiket whitelist kontrolü (customer_portal_view.py ile aynı)
        SKOR_LABELS = {
            'hane_bekar_skoru', 'hane_cift_skoru', 'hane_aile_skoru', 'hane_cocuklu_skoru',
            'hane_bebek_skoru', 'hane_yasli_skoru', 'hane_evcil_hayvan_skoru',
            'hane_araba_skoru', 'hane_toplu_alim_skoru'
        }
        
        # Tarih filtresi varsa satislar tablosundan hesapla, yoksa özet tablodan al
        if start_date or end_date:
            # Dönemsel hesaplama - satislar tablosundan
            filter_condition_sql = f"el.{etiket} > 0.5" if etiket in SKOR_LABELS else f"el.{etiket} = TRUE"
            where_clauses = ["el.musteri_id = s.musteri_id", filter_condition_sql]
            params = []
            
            if start_date:
                where_clauses.append("s.tarih >= %s")
                params.append(start_date)
            if end_date:
                where_clauses.append("s.tarih <= %s")
                params.append(end_date)
            
            where_sql = " AND ".join(where_clauses)
            
            # Toplam metrikler
            cursor.execute(f"""
                SELECT
                    COUNT(DISTINCT el.musteri_id) as total_count,
                    AVG(s.tutar) as avg_spend,
                    COUNT(DISTINCT s.fis_no) * 1.0 / COUNT(DISTINCT el.musteri_id) as avg_visits,
                    AVG(o.churn_risk_skoru) as avg_churn_risk,
                    CASE 
                        WHEN COUNT(DISTINCT s.fis_no) > 0 
                        THEN SUM(s.tutar) * 1.0 / COUNT(DISTINCT s.fis_no)
                        ELSE 0 
                    END as avg_basket
                FROM musterietiketler el
                JOIN satislar s ON el.musteri_id = s.musteri_id
                LEFT JOIN musteridetayozet o ON el.musteri_id = o.musteri_id
                WHERE {where_sql}
            """, params)
        else:
            # Özet tablodan hızlı okuma
            filter_condition = f"el.{etiket} > 0.5" if etiket in SKOR_LABELS else f"el.{etiket} = TRUE"
            cursor.execute(f"""
                SELECT
                    COUNT(DISTINCT el.musteri_id) as total_count,
                    AVG(o.toplam_harcama) as avg_spend,
                    AVG(o.toplam_alisveris) as avg_visits,
                    AVG(o.churn_risk_skoru) as avg_churn_risk,
                    AVG(o.ortalama_sepet_tutari) as avg_basket
                FROM musterietiketler el
                JOIN musteridetayozet o ON el.musteri_id = o.musteri_id
                WHERE {filter_condition}
            """)
        general_metrics = cursor.fetchone()

        cursor.execute(f"""
            SELECT rfm_segment, COUNT(DISTINCT musteri_id) as musteri_sayisi
            FROM musteridetayozet
            WHERE rfm_segment IS NOT NULL
            GROUP BY rfm_segment
            ORDER BY musteri_sayisi DESC
        """)
        top_categories = [dict(row) for row in cursor.fetchall()]

        cursor.execute(f"""
            SELECT o.aktivite_durumu as status, COUNT(DISTINCT el.musteri_id) as count
            FROM musterietiketler el
            JOIN musteridetayozet o ON el.musteri_id = o.musteri_id
            WHERE {filter_condition} AND o.aktivite_durumu IS NOT NULL
            GROUP BY o.aktivite_durumu
        """)
        activity_dist = [dict(row) for row in cursor.fetchall()]

        db_engine.release_connection(conn)

        result = {
            'metrics': {
                'total_count': general_metrics['total_count'],
                'avg_spend': round(general_metrics['avg_spend'] or 0, 2),
                'avg_visits': round(general_metrics['avg_visits'] or 0, 2),
                'avg_churn_risk': round(general_metrics['avg_churn_risk'] or 0, 1),
                'avg_basket': round(general_metrics['avg_basket'] or 0, 2)
            },
            'top_categories': top_categories,
            'activity_dist': activity_dist,
            'label': etiket
        }
        _segment_detail_cache[cache_key] = {'data': result, 'ts': _time.time()}
        return Response(result)

    except Exception as e:
        logger.error(f"Detailed analysis error: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_beklenen_musteriler(request, data_source_id):
    """
    Bu hafta ziyaret etmesi beklenen veya geciken düzenli müşteriler.

    ?tip=beklenen (default): tahmini ziyaret bu hafta içinde
    ?tip=geciken: tahmini ziyaret geçmiş (son 30 gün) ama gelmemiş

    Güven skoru: std/ort oranı (CV) düşükse → düzenli ziyaretçi → yüksek güven
    """
    try:
        from .. import db_engine
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        page_size = min(int(request.GET.get('limit', 50)), 200)
        page = max(int(request.GET.get('page', 1)), 1)
        offset = (page - 1) * page_size
        tip = request.GET.get('tip', 'beklenen')
        # filtre: 'bugun' | 'bu_hafta' | 'bu_ay' | '7_gun' | '30_gun'
        filtre = request.GET.get('filtre', '30_gun' if tip == 'geciken' else 'bu_hafta')
        magaza_id = request.GET.get('magaza_id', '').strip()

        tahmini = db_engine.col_date_add_expr('v.son_ziyaret_tarihi', 'v.ort_ziyaret_araligi')
        today = "CURRENT_DATE" if db_engine.DB_BACKEND == 'postgresql' else "date('now')"
        yesterday = db_engine.date_offset_expr(-1)
        last7 = db_engine.date_offset_expr(-7)
        last30 = db_engine.date_offset_expr(-30)
        tomorrow = db_engine.date_offset_expr(1)
        next7 = db_engine.date_offset_expr(7)
        
        week_start = db_engine.date_trunc_expr('week', today)
        week_end = db_engine.date_offset_expr(6, week_start)
        
        month_start = db_engine.date_trunc_expr('month', today)
        if db_engine.DB_BACKEND == 'postgresql':
            month_end = "(date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::date"
        else:
            month_end = "date('now', 'start of month', '+1 month', '-1 day')"

        if tip == 'geciken':
            # Tahmini ziyaret tarihi geçmiş ama gelmemiş
            if filtre == 'bugun':
                # Bugün beklenen ama henüz gelmedi (aslında tahmini < bugün olmalı geciken diyebilmek için)
                date_filter = f"{tahmini} < {today} AND v.son_ziyaret_tarihi < {today}"
            elif filtre == 'bu_hafta':
                date_filter = f"{tahmini} BETWEEN {week_start} AND {yesterday}"
            elif filtre == 'bu_ay':
                date_filter = f"{tahmini} BETWEEN {month_start} AND {yesterday}"
            elif filtre == '7_gun':
                date_filter = f"{tahmini} BETWEEN {last7} AND {yesterday}"
            else:
                date_filter = f"{tahmini} BETWEEN {last30} AND {yesterday}"
            order_sql = "tahmini_ziyaret_tarihi DESC"
        else:
            # Beklenen: sadece ileriye dönük
            if filtre == 'bugun':
                date_filter = f"{tahmini} = {today}"
            elif filtre == 'bu_hafta':
                date_filter = f"{tahmini} BETWEEN {today} AND {week_end}"
            elif filtre == 'yarin':
                date_filter = f"{tahmini} = {tomorrow}"
            elif filtre == '7_gun':
                date_filter = f"{tahmini} BETWEEN {today} AND {next7}"
            else:
                date_filter = f"{tahmini} BETWEEN {today} AND {month_end}"
            order_sql = "tahmini_ziyaret_tarihi ASC"

        sort_by = request.GET.get('sort_by')
        sort_order = request.GET.get('sort_order', 'desc').lower()
        if sort_order not in ('asc', 'desc'):
            sort_order = 'desc'

        sort_mapping = {
            'ad_soyad': 'o.ad_soyad',
            'son_ziyaret_tarihi': 'v.son_ziyaret_tarihi',
            'tahmini_ziyaret_tarihi': 'tahmini_ziyaret_tarihi',
            'gecikme_gun': 'gecikme_gun',
            'ort_aralik_gun': 'ROUND(v.ort_ziyaret_araligi::numeric, 1)',
            'toplam_ziyaret': 'v.toplam_ziyaret',
            'rfm_segment': 'o.rfm_segment',
            'guven_skoru': 'guven_skoru'
        }

        if sort_by in sort_mapping:
            order_sql = f"{sort_mapping[sort_by]} {sort_order.upper()}"


        select_cols = f"""
                v.musteri_id,
                o.ad_soyad,
                m.telefon,
                o.rfm_segment,
                v.son_ziyaret_tarihi AS son_ziyaret_tarihi,
                {tahmini} AS tahmini_ziyaret_tarihi,
                ROUND(CAST(v.ort_ziyaret_araligi AS REAL), 1) AS ort_aralik_gun,
                CAST(v.toplam_ziyaret AS INTEGER) AS toplam_ziyaret,
                {db_engine.date_diff_days_expr(today, tahmini)} AS gecikme_gun,
                COALESCE(o.toplam_harcama, 0) AS toplam_harcama,
                COALESCE(o.ortalama_sepet_tutari, 0) AS ortalama_sepet_tutari,
                COALESCE(o.ortalama_sepet_tutari, 0) AS tahmini_alisveris_tutari,
                CASE
                    WHEN v.std_ziyaret_araligi / NULLIF(v.ort_ziyaret_araligi, 0) < 0.3
                         AND v.toplam_ziyaret >= 10 THEN 'Yuksek'
                    WHEN v.std_ziyaret_araligi / NULLIF(v.ort_ziyaret_araligi, 0) < 0.5
                         AND v.toplam_ziyaret >= 5  THEN 'Orta'
                    ELSE 'Dusuk'
                END AS guven_skoru,
                CASE
                    WHEN {tahmini} < {today} THEN 'Gecti'
                    WHEN {tahmini} = {today} THEN 'Bugun'
                    ELSE 'Yaklasan'
                END AS durum,
                m.kayit_magazasi as magaza_id,
                mg.ad as magaza_adi
        """

        base_where = f"""
            v.ort_ziyaret_araligi IS NOT NULL
              AND v.toplam_ziyaret >= 3
              AND COALESCE(e.tamamen_kaybedilmis, FALSE) = FALSE
              AND {date_filter}
        """
        
        # Mağaza filtresi
        magaza_filter = ""
        magaza_params = []
        if magaza_id:
            magaza_filter = f" AND m.kayit_magazasi = {db_engine.ph()}"
            magaza_params.append(magaza_id)

        mg_id_cast = "mg.id::text" if db_engine.DB_BACKEND == 'postgresql' else "mg.id"

        cursor.execute(f"""
            SELECT {select_cols}
            FROM musteriziyaretfeatures v
            JOIN musteriler m ON v.musteri_id = m.id
            JOIN musteridetayozet o ON v.musteri_id = o.musteri_id
            LEFT JOIN musterietiketler e ON v.musteri_id = e.musteri_id
            LEFT JOIN magazalar mg ON m.kayit_magazasi = {mg_id_cast}
            WHERE {base_where} {magaza_filter}
            ORDER BY {order_sql}
            LIMIT {db_engine.ph()} OFFSET {db_engine.ph()}
        """, magaza_params + [page_size, offset])
        rows = cursor.fetchall()

        if page == 1:
            cursor.execute(f"""
                SELECT COUNT(DISTINCT v.musteri_id) AS cnt
                FROM musteriziyaretfeatures v
                JOIN musteriler m ON v.musteri_id = m.id
                LEFT JOIN musterietiketler e ON v.musteri_id = e.musteri_id
                WHERE {base_where} {magaza_filter}
            """, magaza_params)
            toplam = cursor.fetchone()['cnt']
        else:
            toplam = -1

        db_engine.release_connection(conn)

        musteriler = []
        for r in rows:
            row = dict(r)
            row['ort_aralik_gun'] = round(float(row.get('ort_aralik_gun') or 0), 1)
            row['toplam_ziyaret'] = int(row.get('toplam_ziyaret') or 0)
            row['gecikme_gun'] = int(row.get('gecikme_gun') or 0)
            row['toplam_harcama'] = round(float(row.get('toplam_harcama') or 0), 2)
            row['ortalama_sepet_tutari'] = round(float(row.get('ortalama_sepet_tutari') or 0), 2)
            row['tahmini_alisveris_tutari'] = round(float(row.get('tahmini_alisveris_tutari') or 0), 2)
            if row.get('son_ziyaret_tarihi'):
                row['son_ziyaret_tarihi'] = str(row['son_ziyaret_tarihi'])
            if row.get('tahmini_ziyaret_tarihi'):
                row['tahmini_ziyaret_tarihi'] = str(row['tahmini_ziyaret_tarihi'])
            musteriler.append(row)

        return Response({'toplam': toplam, 'musteriler': musteriler})

    except Exception as e:
        import traceback
        logger.error(f"Beklenen musteriler error: {traceback.format_exc()}")
        return Response({'error': str(e)}, status=500)
