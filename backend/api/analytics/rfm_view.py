"""
RFM (Recency, Frequency, Monetary) Analysis View
11 Segmentli Dinamik RFM Analizi
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from datetime import datetime
import logging
import sqlite3

from ..models import DataSource
from .. import db_engine
from .base import (
    get_datasource_data,
    filter_data_by_date,
    get_cached_data,
    set_cached_data,
    get_user_from_request,
    detect_columns,
    validate_data_source,
)

logger = logging.getLogger(__name__)

# 11 Segment tanimlari (Database naming: '01-) Şampiyonlar')
SEGMENT_CONFIG = {
    '01-) Şampiyonlar': {
        'color': '#10b981',
        'description': 'En değerli müşteriler, çok sık ve yüksek harcama yapanlar',
        'action': 'Özel ayrıcalıklar sunun, VIP programına davet edin'
    },
    '02-) Potansiyel Şampiyonlar': {
        'color': '#22c55e',
        'description': 'Şampiyon olmaya yakın, yüksek potansiyelli müşteriler',
        'action': 'Sadakat programı önerisi, özel teklifler'
    },
    '03-) Sadık Müşteriler': {
        'color': '#3b82f6',
        'description': 'Düzenli gelen, orta-yüksek harcama yapan müşteriler',
        'action': 'Teşekkür kampanyaları, referans programı'
    },
    '05-) Yeni Müşteriler': {
        'color': '#06b6d4',
        'description': 'İlk alışverişini yapmış yeni müşteriler',
        'action': 'Hosgeldin mesajı, ikinci alışveriş teşvigi'
    },
    '06-) Tekrar Kazanılanlar': {
        'color': '#14b8a6',
        'description': 'Uzun aradan sonra geri dönen müşteriler',
        'action': 'Hosgeldin kampanyası, geri dönüş özel indirimi'
    },
    '07-) Yüksek Harcama Yapanlar': {
        'color': '#a855f7',
        'description': 'Az gelir ama çok harcar',
        'action': 'Ziyaret sıklığını artırmak için özel davetler'
    },
    '04-) Sadık Olmaya Adaylar': {
        'color': '#8b5cf6',
        'description': 'Yeni ama potansiyeli olan musteriler',
        'action': 'Engagement artırıcı kampanyalar'
    },
    '08-) İlgi Bekleyenler': {
        'color': '#f59e0b',
        'description': 'Orta seviye, dikkat gerektiren musteriler',
        'action': 'Hatırlatma kampanyaları, özel fırsatlar'
    },
    '09-) Risk Altındakiler': {
        'color': '#ef4444',
        'description': 'Onceden aktifti, şimdi kaybediliyor',
        'action': 'Acil geri kazanım kampanyası, anket'
    },
    '10-) Uyuyanlar': {
        'color': '#6b7280',
        'description': 'Uzun süredir gelmemiş, az işlem yapan musteriler',
        'action': 'Reaktivasyon kampanyası'
    },
    '11-) Kayıp Müşteriler': {
        'color': '#1f2937',
        'description': '6 aydan fazladır yok, muhtemelen kaybedildi',
        'action': 'Son şans kampanyası veya listeden çıkar'
    }
}

# RFM puanlama fonksiyonlari (rfm_segmentation.py ile senkronize)
def calculate_r_score(days):
    """Recency puani (1-5)"""
    if days <= 30: return 5
    elif days <= 60: return 4
    elif days <= 90: return 3
    elif days <= 150: return 2  # Relaxed from 120
    else: return 1

def calculate_f_score(monthly_freq):
    """Frequency puani (1-5) - aylik normalize edilmis islem sayisi"""
    if monthly_freq >= 3.0: return 5
    elif monthly_freq >= 2.0: return 4
    elif monthly_freq >= 1.0: return 3
    elif monthly_freq >= 0.5: return 2
    else: return 1

def calculate_m_score(monthly_amount):
    """Monetary puani (1-5) - aylik ortalama harcama"""
    if monthly_amount >= 15000: return 5
    elif monthly_amount >= 7500: return 4
    elif monthly_amount >= 3000: return 3
    elif monthly_amount >= 1000: return 2
    else: return 1

def determine_segment(r, f, m, days_since_prev=None, first_purchase_days=None, recency_days=None, freq=None):
    """11 segmentten birini belirle (rfm_segmentation.py ile senkronize)"""
    # 0. YENİ MÜŞTERİ KONTROLÜ (Kayıp kontrolünden ÖNCE yapılmalı)
    # Yeni müşteri: İlk alışveriş son 30 gün içinde VE toplam ziyaret < 3
    if first_purchase_days is not None and first_purchase_days <= 30 and freq is not None and freq < 3:
        return '05-) Yeni Müşteriler'
    
    # 1. Kayıp Müşteriler (Yeni müşteri olmayanlar için)
    if recency_days is not None and recency_days > 180:
        return '11-) Kayıp Müşteriler'
    
    # 2. Şampiyonlar
    if r >= 4 and f >= 4 and m >= 4:
        return '01-) Şampiyonlar'
    
    # 3. Sadık Müşteriler
    if r >= 3 and f >= 3 and m >= 3:
        return '03-) Sadık Müşteriler'
    
    # 4. Yüksek Harcama Yapanlar
    if m >= 3 and f == 1:
        return '07-) Yüksek Harcama Yapanlar'
    
    # 5. Potansiyel Şampiyonlar
    if r >= 4 and f >= 2 and m >= 2:
        return '02-) Potansiyel Şampiyonlar'
    
    # 6. Tekrar Kazanılanlar
    if r >= 4 and days_since_prev is not None and days_since_prev >= 90:
        return '06-) Tekrar Kazanılanlar'
    
    # 7. Sadık Olmaya Adaylar
    if r >= 4 and f >= 2:
        return '04-) Sadık Olmaya Adaylar'
    
    # 8. Risk Altındakiler
    if r == 2 and f >= 3:
        return '09-) Risk Altındakiler'
    
    # 9. Uyuyanlar
    if r <= 2 and f <= 2:
        return '10-) Uyuyanlar'
    
    # 10. Default - İlgi Bekleyenler
    return '08-) İlgi Bekleyenler'


# Eski segment isimlerini yeni formata eslestir
OLD_TO_NEW_SEGMENT_MAP = {
    'Sampiyonlar': '01-) Şampiyonlar',
    'Şampiyonlar': '01-) Şampiyonlar',
    'Potansiyel Sampiyonlar': '02-) Potansiyel Şampiyonlar',
    'Potansiyel Şampiyonlar': '02-) Potansiyel Şampiyonlar',
    'Sadiklar': '03-) Sadık Müşteriler',
    'Sadık Müşteriler': '03-) Sadık Müşteriler',
    'Sadik Olmaya Adaylar': '04-) Sadık Olmaya Adaylar',
    'Sadık Olmaya Adaylar': '04-) Sadık Olmaya Adaylar',
    'Yeni Musteriler': '05-) Yeni Müşteriler',
    'Yeni Müşteriler': '05-) Yeni Müşteriler',
    'Ilgi Bekleyenler': '08-) İlgi Bekleyenler',
    'İlgi Bekleyenler': '08-) İlgi Bekleyenler',
    'Risk Altindakiler': '09-) Risk Altındakiler',
    'Risk Altındakiler': '09-) Risk Altındakiler',
    'Uyuyanlar': '10-) Uyuyanlar',
    'Kayip Musteriler': '11-) Kayıp Müşteriler',
    'Kayıp Müşteriler': '11-) Kayıp Müşteriler',
    'Tekrar Kazanilanlar': '06-) Tekrar Kazanılanlar',
    'Tekrar Kazanılanlar': '06-) Tekrar Kazanılanlar',
    'Yuksek Harcama Yapanlar': '07-) Yüksek Harcama Yapanlar',
    'Yüksek Harcama Yapanlar': '07-) Yüksek Harcama Yapanlar',
}

def _normalize_segment_name(raw_name):
    """Eski veya yeni formattaki segment ismini standart yeni formata cevir"""
    if not raw_name:
        return None
    raw_name = raw_name.strip()
    # Zaten yeni formatta mi? (XX-) seklinde basliyor)
    if raw_name and len(raw_name) > 3 and raw_name[2:4] == '-)':
        return raw_name
    # Eski format mapping
    return OLD_TO_NEW_SEGMENT_MAP.get(raw_name, raw_name)


from django.core.cache import cache

def get_rfm_from_database():
    """Veritabanindan onceden hesaplanmis RFM verilerini getir (eski+yeni segment isimlerini birlestirir)"""
    cache_key = 'global_rfm_database_summary'
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info("RFM data loaded from cache.")
        return cached_data

    try:
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        # musteriler tablosundan tum kayitli musteri sayisi (satisi olan+olmayan)
        cursor.execute("SELECT COUNT(DISTINCT musteri_id) as cnt FROM musteriler")
        total_unique_customers = db_engine.val(cursor.fetchone(), 'cnt')

        # Segment bazli ozet - tum segment isimlerini normalize ederek birlestir
        cursor.execute("""
            SELECT
                rfm_segment,
                COUNT(DISTINCT m.id) as count,
                AVG(CASE WHEN rfm_r_score > 0 THEN rfm_r_score END) as avg_r,
                AVG(CASE WHEN rfm_f_score > 0 THEN rfm_f_score END) as avg_f,
                AVG(CASE WHEN rfm_m_score > 0 THEN rfm_m_score END) as avg_m
            FROM musteriler
            WHERE rfm_segment IS NOT NULL
            GROUP BY rfm_segment
        """)

        # Eski ve yeni isimleri birlestir
        merged_data = {}
        for row in cursor.fetchall():
            raw_segment = row['rfm_segment']
            normalized = _normalize_segment_name(raw_segment)
            if not normalized:
                continue
            
            count = row['count']
            avg_r = row['avg_r'] or 0
            avg_f = row['avg_f'] or 0
            avg_m = row['avg_m'] or 0
            
            if normalized in merged_data:
                # Weighted average ile birlestir
                existing = merged_data[normalized]
                total_count = existing['count'] + count
                existing['avg_r'] = round((existing['avg_r'] * existing['count'] + avg_r * count) / total_count, 1)
                existing['avg_f'] = round((existing['avg_f'] * existing['count'] + avg_f * count) / total_count, 1)
                existing['avg_m'] = round((existing['avg_m'] * existing['count'] + avg_m * count) / total_count, 1)
                existing['count'] = total_count
            else:
                merged_data[normalized] = {
                    'count': count,
                    'avg_r': round(avg_r, 1),
                    'avg_f': round(avg_f, 1),
                    'avg_m': round(avg_m, 1)
                }

        # R, F, M dagilimi
        cursor.execute("""
            SELECT
                rfm_r_score, COUNT(DISTINCT musteri_id) as count
            FROM musteriler
            WHERE rfm_r_score IS NOT NULL
            GROUP BY rfm_r_score
            ORDER BY rfm_r_score
        """)
        r_dist = {row['rfm_r_score']: row['count'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT
                rfm_f_score, COUNT(DISTINCT musteri_id) as count
            FROM musteriler
            WHERE rfm_f_score IS NOT NULL
            GROUP BY rfm_f_score
            ORDER BY rfm_f_score
        """)
        f_dist = {row['rfm_f_score']: row['count'] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT
                rfm_m_score, COUNT(DISTINCT musteri_id) as count
            FROM musteriler
            WHERE rfm_m_score IS NOT NULL
            GROUP BY rfm_m_score
            ORDER BY rfm_m_score
        """)
        m_dist = {row['rfm_m_score']: row['count'] for row in cursor.fetchall()}

        # Top musteriler (en yuksek M puanina sahip)
        cursor.execute("""
            SELECT
                m.id,
                m.ad,
                m.rfm_segment,
                m.rfm_r_score,
                m.rfm_f_score,
                m.rfm_m_score
            FROM musteriler m
            WHERE m.rfm_segment LIKE '%Şampiyonlar%' OR m.rfm_segment LIKE '%Sampiyonlar%'
            ORDER BY m.rfm_m_score DESC, m.rfm_f_score DESC
            LIMIT 10
        """)

        top_customers = []
        for row in cursor.fetchall():
            top_customers.append({
                'customer_id': str(row['id']),
                'name': row['ad'] or 'Isimsiz',
                'segment': _normalize_segment_name(row['rfm_segment']),
                'r_score': row['rfm_r_score'],
                'f_score': row['rfm_f_score'],
                'm_score': row['rfm_m_score']
            })

        db_engine.release_connection(conn)

        result = {
            'segment_data': merged_data,
            'r_distribution': r_dist,
            'f_distribution': f_dist,
            'm_distribution': m_dist,
            'top_customers': top_customers,
            'total_unique_customers': total_unique_customers
        }
        cache.set(cache_key, result, timeout=300)
        return result

    except Exception as e:
        logger.error(f"Database RFM query error: {e}")
        return None



def calculate_rfm_sql(filters):
    """
    SQL tabanli hizli RFM hesaplama (Filtreli durumlar icin)
    """
    conn = db_engine.get_connection()
    if db_engine.DB_BACKEND != 'postgresql':
        import sqlite3 as _sqlite3
        conn.row_factory = _sqlite3.Row
        # SQLite-specific optimizations
        try:
            conn.execute("PRAGMA mmap_size = 30000000000")
            conn.execute("PRAGMA query_only = 1")
        except:
            pass

    cursor = db_engine.get_dict_cursor(conn)
    ph = db_engine.ph()

    # Base Query
    base_query = f"""
        SELECT
            musteri_id,
            COUNT(DISTINCT fis_no) as frequency,
            SUM(tutar) as monetary,
            MAX(tarih) as last_date,
            MIN(tarih) as first_date
        FROM satislar
        WHERE musteri_id IS NOT NULL
    """
    params = []

    # Tarih filtreleri
    if filters.get('start_date') and filters.get('end_date'):
        base_query += f" AND tarih BETWEEN {ph} AND {ph}"
        params.extend([filters['start_date'], filters['end_date']])
    elif filters.get('year') and filters.get('month'):
        col_expr = "tarih::text" if db_engine.DB_BACKEND == 'postgresql' else "tarih"
        base_query += f" AND {col_expr} LIKE {ph}"
        params.append(f"{filters['year']}-{int(filters['month']):02d}%")
    elif filters.get('year'):
        col_expr = "tarih::text" if db_engine.DB_BACKEND == 'postgresql' else "tarih"
        base_query += f" AND {col_expr} LIKE {ph}"
        params.append(f"{filters['year']}%")

    # Müşteri filtreleri
    if filters.get('customer_type'):
        base_query += f" AND musteri_id IN (SELECT id FROM musteriler WHERE tip = {ph})"
        params.append(filters['customer_type'])
    if filters.get('approval_status'):
        base_query += f" AND musteri_id IN (SELECT id FROM musteriler WHERE onay_durumu = {ph})"
        params.append(filters['approval_status'])
    if filters.get('region'):
        base_query += f" AND magaza_id IN (SELECT id FROM magazalar WHERE bolge = {ph})"
        params.append(filters['region'])

    base_query += " GROUP BY musteri_id"

    try:
        cursor.execute(base_query, params)
        rows = cursor.fetchall()

        # Tekrar Kazanılanlar segmenti için önceki alışveriş aralığı
        # musteridetayozet tablosundan çek (zaten hesaplanmış — satislar self-join'den çok daha hızlı)
        days_since_prev_map = {}
        try:
            cursor.execute("""
                SELECT musteri_id, ortalama_alisveris_araligi
                FROM musteridetayozet
                WHERE ortalama_alisveris_araligi IS NOT NULL
            """)
            for gap_row in cursor.fetchall():
                g_cid = gap_row['musteri_id']
                g_val = gap_row['ortalama_alisveris_araligi']
                if g_val is not None:
                    days_since_prev_map[g_cid] = int(g_val) if not isinstance(g_val, int) else g_val
        except Exception as gap_err:
            logger.warning(f"Gap map alınamadı (non-fatal): {gap_err}")

        # Bellek verimli işleme: dict listesi yerine sadece sayaçlar ve aggregated değerler tutulur
        # segment_agg: {name: {'count': int, 'r_sum': float, 'f_sum': float, 'm_sum': float}}
        segment_agg = {name: {'count': 0, 'r_sum': 0.0, 'f_sum': 0.0, 'm_sum': 0.0} for name in SEGMENT_CONFIG}
        dist_recency = [0]*5
        dist_frequency = [0]*5
        dist_monetary = [0]*5
        # Top 10 şampiyon için sadece en yüksek monetary'li 10 kişiyi tut (min-heap yerine basit liste, max 10 eleman)
        top_champ = []
        total_count = 0

        now = datetime.now()

        for row in rows:
            cust_id = str(row['musteri_id'])
            freq = row['frequency']
            monetary = row['monetary']
            last_date_str = row['last_date']
            first_date_str = row['first_date']

            try:
                if isinstance(last_date_str, str):
                    last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                else:
                    last_date = datetime.combine(last_date_str, datetime.min.time()) if last_date_str else None
                if isinstance(first_date_str, str):
                    first_date = datetime.strptime(first_date_str, '%Y-%m-%d')
                else:
                    first_date = datetime.combine(first_date_str, datetime.min.time()) if first_date_str else None
                if not last_date or not first_date:
                    continue
            except:
                continue

            recency = (now - last_date).days
            first_purchase_days = (now - first_date).days
            tenure_months = max(1, first_purchase_days / 30.0)
            monthly_freq = freq / tenure_months
            monetary_monthly = monetary / tenure_months

            r_score = calculate_r_score(recency)
            f_score = calculate_f_score(monthly_freq)
            m_score = calculate_m_score(monetary_monthly)

            dist_recency[5 - r_score] += 1
            dist_frequency[5 - f_score] += 1
            dist_monetary[5 - m_score] += 1

            days_since_prev = days_since_prev_map.get(row['musteri_id'])
            segment = determine_segment(r_score, f_score, m_score, days_since_prev, first_purchase_days, recency, freq)

            agg = segment_agg[segment]
            agg['count'] += 1
            agg['r_sum'] += r_score
            agg['f_sum'] += f_score
            agg['m_sum'] += monetary_monthly
            total_count += 1

            # Şampiyon ise top 10 listesinde tut
            if 'Şampiyonlar' in segment or 'Sampiyonlar' in segment:
                top_champ.append({
                    'customer_id': cust_id,
                    'recency': recency,
                    'frequency': freq,
                    'monetary': monetary_monthly,
                    'r_score': r_score,
                    'f_score': f_score,
                    'm_score': m_score,
                    'segment': segment
                })

        db_engine.release_connection(conn)

        segment_summary = []
        for name, config in SEGMENT_CONFIG.items():
            agg = segment_agg[name]
            cnt = agg['count']
            if cnt > 0:
                segment_summary.append({
                    'name': name,
                    'count': cnt,
                    'avg_r': round(agg['r_sum'] / cnt, 1),
                    'avg_f': round(agg['f_sum'] / cnt, 1),
                    'avg_m': round(agg['m_sum'] / cnt, 1),
                    'color': config['color'],
                    'description': config['description'],
                    'action': config['action']
                })

        distribution = {
            'recency': [
                {'range': '0-30 gun (R=5)', 'count': dist_recency[0]},
                {'range': '31-60 gun (R=4)', 'count': dist_recency[1]},
                {'range': '61-90 gun (R=3)', 'count': dist_recency[2]},
                {'range': '91-180 gun (R=2)', 'count': dist_recency[3]},
                {'range': '180+ gun (R=1)', 'count': dist_recency[4]}
            ],
            'frequency': [
                {'range': 'Ayda 5+ (F=5)', 'count': dist_frequency[0]},
                {'range': 'Ayda 4-5 (F=4)', 'count': dist_frequency[1]},
                {'range': 'Ayda 3-4 (F=3)', 'count': dist_frequency[2]},
                {'range': 'Ayda 2-3 (F=2)', 'count': dist_frequency[3]},
                {'range': 'Ayda <2 (F=1)', 'count': dist_frequency[4]}
            ],
            'monetary': [
                {'range': '30K+ TL (M=5)', 'count': dist_monetary[0]},
                {'range': '20-30K TL (M=4)', 'count': dist_monetary[1]},
                {'range': '10-20K TL (M=3)', 'count': dist_monetary[2]},
                {'range': '3-10K TL (M=2)', 'count': dist_monetary[3]},
                {'range': '<3K TL (M=1)', 'count': dist_monetary[4]}
            ]
        }

        top_customers = sorted(top_champ, key=lambda x: x['monetary'], reverse=True)[:10]

        return {
            'segments': segment_summary,
            'distribution': distribution,
            'topCustomers': top_customers,
            'source': 'calculated_sql_fast',
            'segment_count': 11,
            'totalCustomers': total_count
        }

    except Exception as e:
        logger.error(f"SQL RFM Error: {e}")
        if conn:
            db_engine.release_connection(conn)
        return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_rfm_analysis(request, data_source_id):
    """RFM analizi endpoint'i - 11 Segment"""
    try:
        user = get_user_from_request(request)
        if not validate_data_source(user, data_source_id):
            return Response({'error': 'Veri kaynağı bulunamadı veya erişim izni yok'}, status=404)

        customer_type = request.GET.get('customer_type') or request.GET.get('customerType')
        approval_status = request.GET.get('approval_status') or request.GET.get('approvalStatus')
        region = request.GET.get('region')
        has_customer_filter = bool(customer_type or approval_status or region)

        # Müşteri filtresi varsa DB cache'i atla, live SQL hesapla
        if not has_customer_filter:
            db_rfm = get_rfm_from_database()

            if db_rfm and db_rfm['segment_data']:
                segments = []

                for segment_name, config in SEGMENT_CONFIG.items():
                    data = db_rfm['segment_data'].get(segment_name, {})
                    count = data.get('count', 0)

                    segments.append({
                        'name': segment_name,
                        'count': count,
                        'avg_r': data.get('avg_r', 0),
                        'avg_f': data.get('avg_f', 0),
                        'avg_m': data.get('avg_m', 0),
                        'color': config['color'],
                        'description': config['description'],
                        'action': config['action']
                    })

                segment_order = list(SEGMENT_CONFIG.keys())
                segments.sort(key=lambda x: segment_order.index(x['name']) if x['name'] in segment_order else 999)

                distribution = {
                    'recency': [
                        {'range': '0-30 gun (R=5)', 'count': db_rfm['r_distribution'].get(5, 0)},
                        {'range': '31-60 gun (R=4)', 'count': db_rfm['r_distribution'].get(4, 0)},
                        {'range': '61-90 gun (R=3)', 'count': db_rfm['r_distribution'].get(3, 0)},
                        {'range': '91-180 gun (R=2)', 'count': db_rfm['r_distribution'].get(2, 0)},
                        {'range': '180+ gun (R=1)', 'count': db_rfm['r_distribution'].get(1, 0)}
                    ],
                    'frequency': [
                        {'range': 'Ayda 5+ (F=5)', 'count': db_rfm['f_distribution'].get(5, 0)},
                        {'range': 'Ayda 4-5 (F=4)', 'count': db_rfm['f_distribution'].get(4, 0)},
                        {'range': 'Ayda 3-4 (F=3)', 'count': db_rfm['f_distribution'].get(3, 0)},
                        {'range': 'Ayda 2-3 (F=2)', 'count': db_rfm['f_distribution'].get(2, 0)},
                        {'range': 'Ayda <2 (F=1)', 'count': db_rfm['f_distribution'].get(1, 0)}
                    ],
                    'monetary': [
                        {'range': '30K+ TL (M=5)', 'count': db_rfm['m_distribution'].get(5, 0)},
                        {'range': '20-30K TL (M=4)', 'count': db_rfm['m_distribution'].get(4, 0)},
                        {'range': '10-20K TL (M=3)', 'count': db_rfm['m_distribution'].get(3, 0)},
                        {'range': '3-10K TL (M=2)', 'count': db_rfm['m_distribution'].get(2, 0)},
                        {'range': '<3K TL (M=1)', 'count': db_rfm['m_distribution'].get(1, 0)}
                    ]
                }

                result = {
                    'segments': segments,
                    'distribution': distribution,
                    'topCustomers': db_rfm['top_customers'],
                    'source': 'database',
                    'segment_count': 11,
                    'totalCustomers': db_rfm.get('total_unique_customers', 0)
                }

                return Response(result)

        # Filtre varsa veya DB cache boşsa SQL hesapla
        has_filters = any([request.GET.get('year'), request.GET.get('month'),
                          request.GET.get('start_date'), request.GET.get('end_date'),
                          has_customer_filter])

        if not has_filters:
            cached = get_cached_data('rfm', data_source_id)
            if cached:
                return Response(cached)

        # Optimized SQL Path
        filters = {
            'year': request.GET.get('year'),
            'month': request.GET.get('month'),
            'start_date': request.GET.get('start_date'),
            'end_date': request.GET.get('end_date'),
            'customer_type': customer_type,
            'approval_status': approval_status,
            'region': region,
        }

        sql_result = calculate_rfm_sql(filters)
        if sql_result:
            return Response(sql_result)

        user = get_user_from_request(request)

        if user:
            data_source = DataSource.objects.get(id=data_source_id, user=user)
        else:
            data_source = DataSource.objects.get(id=data_source_id)

        data = get_datasource_data(data_source)

        if not data or len(data) == 0:
            return Response({'segments': [], 'distribution': {}, 'topCustomers': []})

        # Tarih filtreleme uygula
        data = filter_data_by_date(data, request)

        # Sutun tespiti
        first_row_keys = list(data[0].keys()) if data else []
        columns = detect_columns(first_row_keys, data_source.column_mapping)

        customer_id_col = columns.get('customer_id_col') or 'Musteri Kodu'
        date_col = columns.get('date_col') or 'TARIH'
        amount_col = columns.get('revenue_col') or 'Satis Tutari'

        now = datetime.now()

        # Tarih parse fonksiyonu
        date_cache = {}
        def parse_date(d):
            if not d:
                return None
            if d in date_cache:
                return date_cache[d]
            try:
                result = datetime.strptime(str(d), '%d.%m.%Y')
                date_cache[d] = result
                return result
            except (ValueError, TypeError):
                try:
                    result = datetime.strptime(str(d), '%Y-%m-%d')
                    date_cache[d] = result
                    return result
                except (ValueError, TypeError):
                    date_cache[d] = None
                    return None

        # Musteri verilerini topla
        customer_data = {}
        customer_dates = {}  # Her musterinin tum tarihlerini tut

        for row in data:
            customer_id = row.get(customer_id_col)
            if not customer_id:
                continue

            try:
                amount = float(str(row.get(amount_col, 0)).replace(',', '.'))
            except (ValueError, TypeError, AttributeError):
                amount = 0

            if customer_id not in customer_data:
                customer_data[customer_id] = {
                    'last_date': None,
                    'first_date': None,
                    'frequency': 0,
                    'monetary': 0
                }
                customer_dates[customer_id] = []

            customer_data[customer_id]['frequency'] += 1
            customer_data[customer_id]['monetary'] += amount

            date_val = parse_date(row.get(date_col))
            if date_val:
                customer_dates[customer_id].append(date_val)
                if customer_data[customer_id]['last_date'] is None or date_val > customer_data[customer_id]['last_date']:
                    customer_data[customer_id]['last_date'] = date_val
                if customer_data[customer_id]['first_date'] is None or date_val < customer_data[customer_id]['first_date']:
                    customer_data[customer_id]['first_date'] = date_val

        if not customer_data:
            return Response({'segments': [], 'distribution': {}, 'topCustomers': []})

        # 11 segment icin dict
        segments = {name: [] for name in SEGMENT_CONFIG.keys()}

        # Distribution sayaclari
        dist_recency = [0, 0, 0, 0, 0]  # R=5,4,3,2,1
        dist_frequency = [0, 0, 0, 0, 0]  # F=5,4,3,2,1
        dist_monetary = [0, 0, 0, 0, 0]  # M=5,4,3,2,1

        rfm_list = []
        for customer_id, info in customer_data.items():
            recency = (now - info['last_date']).days if info['last_date'] else 365
            first_purchase_days = (now - info['first_date']).days if info['first_date'] else 365

            # Tenure bazli aylik frekans
            tenure_days = max(1, first_purchase_days)
            tenure_months = max(1, tenure_days / 30.0)
            monthly_freq = info['frequency'] / tenure_months

            # Aylik ortalama harcama
            monetary_monthly = round(info['monetary'] / tenure_months, 0)

            # Tekrar kazanilanlar icin: son 2 tarih arasindaki fark
            dates = sorted(customer_dates.get(customer_id, []), reverse=True)
            days_since_prev = None
            if len(dates) >= 2:
                days_since_prev = (dates[0] - dates[1]).days

            # RFM skorlari
            r_score = calculate_r_score(recency)
            f_score = calculate_f_score(monthly_freq)
            m_score = calculate_m_score(monetary_monthly)

            # Distribution sayaclari
            dist_recency[5 - r_score] += 1
            dist_frequency[5 - f_score] += 1
            dist_monetary[5 - m_score] += 1

            # Segment belirle
            segment = determine_segment(r_score, f_score, m_score, days_since_prev, first_purchase_days, recency, info['frequency'])

            customer_rfm = {
                'customer_id': str(customer_id),
                'recency': recency,
                'frequency': info['frequency'],
                'monetary': monetary_monthly,
                'r_score': r_score,
                'f_score': f_score,
                'm_score': m_score,
                'segment': segment
            }
            rfm_list.append(customer_rfm)
            segments[segment].append(customer_rfm)

        # Segment ozeti
        segment_summary = []
        for name, config in SEGMENT_CONFIG.items():
            customers = segments[name]
            if customers:
                segment_summary.append({
                    'name': name,
                    'count': len(customers),
                    'avg_r': round(sum(c['r_score'] for c in customers) / len(customers), 1),
                    'avg_f': round(sum(c['f_score'] for c in customers) / len(customers), 1),
                    'avg_m': round(sum(c['m_score'] for c in customers) / len(customers), 1),
                    'color': config['color'],
                    'description': config['description'],
                    'action': config['action']
                })

        distribution = {
            'recency': [
                {'range': '0-30 gun (R=5)', 'count': dist_recency[0]},
                {'range': '31-60 gun (R=4)', 'count': dist_recency[1]},
                {'range': '61-90 gun (R=3)', 'count': dist_recency[2]},
                {'range': '91-180 gun (R=2)', 'count': dist_recency[3]},
                {'range': '180+ gun (R=1)', 'count': dist_recency[4]}
            ],
            'frequency': [
                {'range': 'Ayda 5+ (F=5)', 'count': dist_frequency[0]},
                {'range': 'Ayda 4-5 (F=4)', 'count': dist_frequency[1]},
                {'range': 'Ayda 3-4 (F=3)', 'count': dist_frequency[2]},
                {'range': 'Ayda 2-3 (F=2)', 'count': dist_frequency[3]},
                {'range': 'Ayda <2 (F=1)', 'count': dist_frequency[4]}
            ],
            'monetary': [
                {'range': '30K+/ay TL (M=5)', 'count': dist_monetary[0]},
                {'range': '20-30K/ay TL (M=4)', 'count': dist_monetary[1]},
                {'range': '10-20K/ay TL (M=3)', 'count': dist_monetary[2]},
                {'range': '3-10K/ay TL (M=2)', 'count': dist_monetary[3]},
                {'range': '<3K/ay TL (M=1)', 'count': dist_monetary[4]}
            ]
        }

        # Top musteriler (Sampiyonlar)
        top_customers = sorted(
            [c for c in rfm_list if 'Şampiyonlar' in c['segment'] or 'Sampiyonlar' in c['segment']],
            key=lambda x: x['monetary'],
            reverse=True
        )[:10]

        result = {
            'segments': segment_summary,
            'distribution': distribution,
            'topCustomers': top_customers,
            'source': 'calculated',
            'segment_count': 11
        }

        if not has_filters:
            set_cached_data('rfm', data_source_id, result)

        return Response(result)

    except DataSource.DoesNotExist:
        return Response({'error': 'Veri kaynagi bulunamadi'}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"RFM analysis error: {e}")
        return Response({'error': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_segment_customers(request, segment_name):
    """Belirli bir segmentteki musterileri getir"""
    try:
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))

        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)
        ph = db_engine.ph()

        cursor.execute(db_engine.adapt_query("""
            SELECT
                m.id,
                m.ad,
                m.telefon,
                m.rfm_segment,
                m.rfm_r_score,
                m.rfm_f_score,
                m.rfm_m_score,
                m.rfm_updated_at
            FROM musteriler m
            WHERE m.rfm_segment = ?
            ORDER BY m.rfm_m_score DESC, m.rfm_f_score DESC
            LIMIT ? OFFSET ?
        """), (segment_name, limit, offset))

        customers = []
        for row in cursor.fetchall():
            customers.append({
                'id': row['id'],
                'name': row['ad'] or 'Isimsiz',
                'phone': row['telefon'],
                'segment': row['rfm_segment'],
                'r_score': row['rfm_r_score'],
                'f_score': row['rfm_f_score'],
                'm_score': row['rfm_m_score'],
                'updated_at': row['rfm_updated_at']
            })

        # Toplam sayiyi al
        cursor.execute(db_engine.adapt_query("""
            SELECT COUNT(DISTINCT musteri_id) as cnt FROM musteriler WHERE rfm_segment = ?
        """), (segment_name,))
        total = db_engine.val(cursor.fetchone(), 'cnt')

        db_engine.release_connection(conn)

        segment_config = SEGMENT_CONFIG.get(segment_name, {})

        return Response({
            'segment': segment_name,
            'description': segment_config.get('description', ''),
            'action': segment_config.get('action', ''),
            'color': segment_config.get('color', '#gray'),
            'total': total,
            'customers': customers
        })

    except Exception as e:
        logger.error(f"Segment customers error: {e}")
        return Response({'error': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_rfm_update(request):
    """Manuel RFM guncelleme tetikle"""
    try:
        from ...rfm_segmentation import run_rfm_update

        result = run_rfm_update()

        if result['success']:
            return Response({
                'success': True,
                'message': f"{result['customers_updated']} musteri guncellendi",
                'segment_distribution': result['segment_distribution'],
                'updated_at': result['updated_at']
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Bilinmeyen hata')
            }, status=HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"RFM update trigger error: {e}")
        return Response({'error': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
