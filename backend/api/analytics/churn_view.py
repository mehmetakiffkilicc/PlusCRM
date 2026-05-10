"""
Churn Analysis View - Optimized for Cache DB
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from datetime import datetime, timedelta
import logging
import os
from django.conf import settings
from .. import db_engine

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_churn_analysis(request, data_source_id):
    """
    Churn analizi endpoint'i
    """
    ph = db_engine.ph()
    conn = None
    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        # Filtreleri Al
        year_param = request.GET.get('year')
        month_param = request.GET.get('month')
        end_date_param = request.GET.get('end_date') or request.GET.get('endDate')
        customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
        approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')
        region = request.GET.get('region')

        # Referans Tarihi Belirle (Analizin yapıldığı tarih)
        ref_date = datetime.now()
        
        # Filtreleme SQL'i için
        filter_sql = ""
        params = []

        if end_date_param and end_date_param != 'null' and end_date_param != 'undefined':
            try:
                ref_date = datetime.strptime(end_date_param, '%Y-%m-%d')
                filter_sql = f"WHERE tarih <= {ph}"
                params.append(end_date_param)
            except ValueError:
                pass
        elif year_param and year_param != 'null' and year_param != 'undefined':
            try:
                y = int(year_param)
                if month_param and month_param != 'null' and month_param != 'undefined':
                    m = int(month_param)
                    # Ayın son günü (yaklaşık)
                    if m == 12:
                        ref_date = datetime(y, 12, 31)
                    else:
                        ref_date = datetime(y, m + 1, 1) - timedelta(days=1)
                else:
                    ref_date = datetime(y, 12, 31)


                filter_sql = f"WHERE tarih <= {ph}"
                ref_date_str_param = ref_date.strftime('%Y-%m-%d')
                
                # Gelecek tarih kontrolü: Eğer seçilen yıl/ay şu andan ilerideyse veya yıl sonu hesaplanıyorsa,
                # ama biz henüz o tarihte değilsek, referans olarak ŞİMDİKİ zamanı almalıyız.
                # Örn: 2026 yılı seçildi (ref=2026-12-31) ama bugün 2026-01-22. 
                # Aralık ayına göre bakarsak herkes churn olur. Bugüne göre bakmalıyız.
                if ref_date > datetime.now():
                    ref_date = datetime.now()

                params.append(ref_date_str_param) # SQL filtresi yine de seçilen dönemin tavanını kullanabilir veya ref_date kullanabilir.
                # Ancak SQL "tarih <= ?" diyor. Eğer tüm yılı seçtiysek ve yıl bitmediyse, 
                # SQL'de "tarih <= 2026-12-31" demek sorun değil (zaten gelecek veri yok).
                # Ama churn hesaplarken "active_threshold" referans tarihine göre belirleniyor.
                # Bu yüzden ref_date'i güncellememiz şart.
            except:
                pass
        
        # Referans tarihi string formatında
        ref_date_str = ref_date.strftime('%Y-%m-%d')
        
        logger.info(f"Churn Analysis Params: Year={year_param}, Month={month_param}, RefDate={ref_date_str}")

        # SQL ile Müşteri Aktivitesini Çek
        has_customer_filter = bool(customer_type or approval_status or region)

        if has_customer_filter:
            # Müşteri filtresi varsa musteriler JOIN ile çek
            musteri_where = ["1=1"]
            musteri_params = []
            if customer_type:
                musteri_where.append(f"m.tip = {ph}")
                musteri_params.append(customer_type)
            if approval_status:
                musteri_where.append(f"m.onay_durumu = {ph}")
                musteri_params.append(approval_status)
            if region:
                musteri_where.append(f"m.kayit_magazasi IN (SELECT id::text FROM magazalar WHERE {db_engine.bolge_expr()} = {ph})")
                musteri_params.append(region)

            date_filter = ""
            if params:
                date_filter = f"AND md.son_alisveris_tarihi <= {ph}"
                musteri_params.extend(params)

            musteri_where_clause = " AND ".join(musteri_where)
            query = f"""
                SELECT md.musteri_id, md.son_alisveris_tarihi as last_date
                FROM musteridetayozet md
                JOIN musteriler m ON md.musteri_id = m.id
                WHERE {musteri_where_clause} {date_filter}
            """
            cursor.execute(query, musteri_params)
        else:
            filter_str = filter_sql.replace('tarih', 'son_alisveris_tarihi')
            query = f"""
                SELECT musteri_id, son_alisveris_tarihi as last_date
                FROM musteridetayozet
                {filter_str}
            """
            cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
             return Response({'summary': {'totalCustomers': 0, 'activeCustomers': 0, 'churnedCustomers': 0, 'churnRate': 0, 'atRiskCustomers': 0}, 'churnByMonth': [], 'riskFactors': [], 'atRiskCustomers': []})

        # Python tarafında sınıflandırma yap (DB fonksiyonları karmaşıklaşabilir)
        active_customers = 0
        at_risk_customers = 0
        churned_customers = 0
        
        # Eşik Değerler (Referans tarihine göre)
        # GÜNCELLEME: Churn = 120+ gün (Kayıp Müşteri ile aynı)

        # Aktif: Son 30 gün içinde işlem yapmış
        # Risk: 31-120 gün arası işlem yapmamış
        # Churn: 120 günden fazla işlem yapmamış (Kayıp Müşteri)

        active_threshold = ref_date - timedelta(days=30)
        risk_threshold_start = ref_date - timedelta(days=120)  # 120 gün = Churn sınırı
        
        # String karşılaştırma (YYYY-MM-DD formatı olduğu için string karşılaştırma çalışır ve hızlıdır)
        active_threshold_str = active_threshold.strftime('%Y-%m-%d')
        risk_threshold_str = risk_threshold_start.strftime('%Y-%m-%d')
        
        for r in rows:
            last_date_val = r['last_date'] if isinstance(r, dict) else r[1]
            last_date_str = str(last_date_val) if last_date_val else None
            if not last_date_str: continue

            if last_date_str >= active_threshold_str:
                active_customers += 1
            # 31-120 gün arası: Risk Altında
            elif last_date_str >= risk_threshold_str:
                at_risk_customers += 1
            # 120+ gün: Churn (Kayıp)
            else:
                churned_customers += 1
                
        total_customers = len(rows)
        churn_rate = (churned_customers / total_customers * 100) if total_customers > 0 else 0

        summary = {
            'totalCustomers': total_customers,
            'activeCustomers': active_customers,
            'churnedCustomers': churned_customers,
            'churnRate': round(churn_rate, 1),
            'atRiskCustomers': at_risk_customers
        }

        # Aylık churn trendi — son 12 ay için her ay churn olan müşteri sayısı
        churn_by_month = []
        try:
            one_year_ago = (ref_date - timedelta(days=365)).strftime('%Y-%m-%d')
            month_expr_md = db_engine.strftime_expr('%Y-%m', 'md.son_alisveris_tarihi')

            churn_extra = ""
            churn_extra_params = []
            if customer_type:
                churn_extra += f" AND m.tip = {ph}"
                churn_extra_params.append(customer_type)
            if approval_status:
                churn_extra += f" AND m.onay_durumu = {ph}"
                churn_extra_params.append(approval_status)
            if region:
                churn_extra += f" AND m.kayit_magazasi IN (SELECT id::text FROM magazalar WHERE {db_engine.bolge_expr()} = {ph})"
                churn_extra_params.append(region)

            if has_customer_filter:
                cursor.execute(f"""
                    SELECT {month_expr_md} as ay, COUNT(DISTINCT musteri_id) as churn_sayisi
                    FROM musteridetayozet md
                    JOIN musteriler m ON md.musteri_id = m.id
                    WHERE md.son_alisveris_tarihi < {ph}
                      AND md.son_alisveris_tarihi >= {ph}
                      {churn_extra}
                    GROUP BY ay ORDER BY ay DESC LIMIT 12
                """, [risk_threshold_str, one_year_ago] + churn_extra_params)
            else:
                month_expr_plain = db_engine.strftime_expr('%Y-%m', 'son_alisveris_tarihi')
                cursor.execute(f"""
                    SELECT {month_expr_plain} as ay, COUNT(DISTINCT musteri_id) as churn_sayisi
                    FROM musteridetayozet
                    WHERE son_alisveris_tarihi < {ph}
                      AND son_alisveris_tarihi >= {ph}
                    GROUP BY ay ORDER BY ay DESC LIMIT 12
                """, [risk_threshold_str, one_year_ago])
            churn_by_month = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"churnByMonth hesaplama hatası: {e}")

        # Risk altındaki müşteri listesi (ilk 100)
        at_risk_list = []
        try:
            at_risk_extra = churn_extra
            at_risk_extra_params = churn_extra_params

            cursor.execute(f"""
                SELECT md.musteri_id as id, m.ad as name, m.telefon,
                       md.son_alisveris_tarihi as last_date,
                       md.toplam_harcama as total_spend,
                       m.rfm_segment as segment
                FROM musteridetayozet md
                JOIN musteriler m ON md.musteri_id = m.id
                WHERE md.son_alisveris_tarihi >= {ph}
                  AND md.son_alisveris_tarihi < {ph}
                  {at_risk_extra}
                ORDER BY md.son_alisveris_tarihi ASC
                LIMIT 100
            """, [risk_threshold_str, active_threshold_str] + at_risk_extra_params)
            at_risk_list = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.warning(f"atRiskCustomers hesaplama hatası: {e}")

        result = {
            'summary': summary,
            'churnByMonth': churn_by_month,
            'riskFactors': [
                {'factor': 'Son 31-120 Gün Alışveriş Yok', 'count': at_risk_customers, 'impact': 'HIGH'},
                {'factor': 'Son 120+ Gün Alışveriş Yok', 'count': churned_customers, 'impact': 'CRITICAL'},
            ],
            'atRiskCustomers': at_risk_list
        }

        db_engine.release_connection(conn)
        return Response(result)

    except Exception as e:
        logger.error(f"Churn analysis error: {type(e).__name__}: {e}", exc_info=True)
        if conn:
            try:
                db_engine.release_connection(conn)
            except Exception:
                pass
        return Response({
            'summary': {'totalCustomers': 0, 'activeCustomers': 0, 'churnedCustomers': 0, 'churnRate': 0, 'atRiskCustomers': 0},
            'churnByMonth': [], 'riskFactors': [], 'atRiskCustomers': [],
            'error': 'Churn verisi yüklenemedi'
        }, status=200)
