import json
import decimal
import logging
from datetime import datetime, date
from .guards import mask_pii
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from .client import get_llm_client
from .prompt_templates import SYSTEM_PROMPT

class CrmJsonEncoder(json.JSONEncoder):
    """Decimal ve Tarih objelerini JSON dostu stringlere çevirir."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(CrmJsonEncoder, self).default(obj)

def safe_json_dumps(data, **kwargs):
    """Hata almadan JSON serileştirmesi yapar."""
    kwargs.setdefault('cls', CrmJsonEncoder)
    kwargs.setdefault('ensure_ascii', False)
    return json.dumps(data, **kwargs)


def get_rfm_summary(data_source_id, filters=None, user=None):
    """Veritabanından hazır RFM özeti getirir."""
    from ..rfm_view import get_rfm_from_database
    data = get_rfm_from_database()
    if not data:
        return json.dumps({"status": "error", "message": "RFM verisi bulunamadı."})
    
    # LLM için veriyi sadeleştir (özellikle trend ve dağılım)
    summary = {
        "status": "success",
        "segment_counts": {k: v['count'] for k, v in data['segment_data'].items()},
        "top_customers": data['top_customers'][:5],
        "total_customers": data['total_unique_customers']
    }
    return safe_json_dumps(summary)

def get_customer_profile(customer_id, data_source_id=0, user=None):
    """Müşteri detay bilgilerini, harcama alışkanlıklarını ve etiketlerini döner."""
    from ..customer_portal_view import get_customer_detail
    from rest_framework.test import force_authenticate
    from rest_framework.test import APIRequestFactory
    factory = APIRequestFactory()
    request = factory.get('/')
    # Force authentication to satisfy [IsAuthenticated] decorator and get_user_from_request
    if not user or user.is_anonymous:
        from django.contrib.auth.models import User
        user = User.objects.filter(is_superuser=True).first()
    
    request.user = user
    request._force_auth_user = user # For DRF
    
    response = get_customer_detail(request, data_source_id, customer_id)
    if response.status_code != 200:
        return safe_json_dumps({"status": "error", "message": f"Müşteri (ID: {customer_id}) bulunamadı veya profil verisi yüklenemedi. (Hata: {response.status_code})"})
    
    data = response.data or {}
    # Kısıtlı veri gönder (token tasarrufu) + Key check
    try:
        # Robust access to prevent NoneType errors
        info_data = data.get('info') or {}
        rfm_data = data.get('rfm_scores') or {}
        kpis_data = data.get('kpis') or {}
        
        # Flatten labels for easier LLM/Rule-Engine consumption
        all_labels = []
        labels_raw = data.get('labels') or {}
        for group_name, group_data in labels_raw.items():
            if isinstance(group_data, dict):
                for label_key, label_val in group_data.items():
                    if label_val: # True or > 0.5
                        all_labels.append(label_key)
        
        profile = {
            "info": {
                "ad": info_data.get('ad', 'Bilinmiyor'),
                "rfm_segment": rfm_data.get('segment', 'Bilinmiyor'),
                "churn_risk": kpis_data.get('churn_risk', 0),
                "trend": kpis_data.get('trend', 'Stabil')
            },
            "kpis": kpis_data,
            "labels": all_labels,
            "fav_categories": [c.get('name') for c in (data.get('fav_categories') or []) if c.get('name')]
        }
        return safe_json_dumps(profile)
    except Exception as e:
        return safe_json_dumps({"status": "error", "message": f"Profil verisi işlenirken hata oluştu: {str(e)}"})

def get_customer_nba(customer_id, data_source_id=0, user=None):
    """
    Müşteri için AI tabanlı Next Best Action (NBA) önerileri üretir.
    Haiku modelini kullanarak veriden aksiyon çıkarır.
    """
    profile_json = get_customer_profile(customer_id, data_source_id=data_source_id, user=user)
    profile = json.loads(profile_json)
    
    if profile.get("status") == "error":
        return profile_json

    # Akıllı Kural Motoru (Gelecekte LLM ile de beslenebilir)
    # Şimdilik Haiku modeline gitmek yerine hızlı yanıt için rule-engine kullanıyoruz
    actions = []
    churn_risk = profile['info'].get('churn_risk', 0)
    
    if churn_risk > 50:
        actions.append({
            "title": "Geri Kazanım Araması",
            "description": f"Müşterinin churn riski %{churn_risk}. {profile['fav_categories'][0] if profile['fav_categories'] else 'Genel'} kategorisinde özel bir teklif ile iletişime geçin.",
            "priority": "high",
            "type": "call"
        })
    
    if "indirim_avcisi" in profile['labels']:
        actions.append({
            "title": "Kupon Tanımla",
            "description": "Müşteri indirimleri takip ediyor. ₺500 üzeri alışverişe ₺50 indirim tanımlayarak sepet büyüklüğünü artırın.",
            "priority": "medium",
            "type": "discount"
        })
    else:
        actions.append({
            "title": "Yeni Koleksiyon Bilgilendirmesi",
            "description": f"İlgi duyduğu {profile['fav_categories'][0] if profile['fav_categories'] else 'kategoriler'} için yeni gelen ürünleri e-posta ile bildirin.",
            "priority": "low",
            "type": "email"
        })
        
    return safe_json_dumps({"status": "success", "actions": actions})

def list_segment_customers(segment_name, data_source_id=0, limit=10, user=None):
    """Belirli bir segmentteki müşterileri listeler."""
    from ..customer_portal_view import get_customer_list
    factory = RequestFactory()
    request = factory.get(f"/?segments={segment_name}")
    request.user = user or AnonymousUser()
    
    response = get_customer_list(request, data_source_id)
    if response.status_code != 200:
        return json.dumps({"status": "error", "message": "Liste alınamadı."})
    
    data = response.data
    customers = data['customers'][:limit]
    result = {
        "status": "success",
        "segment": segment_name,
        "count": data['total'],
        "customers": [{"id": c['id'], "ad": c['ad'], "spend": c['total_spend']} for c in customers]
    }
    return safe_json_dumps(result)

def get_campaign_recommendations(filters=None, user=None):
    return json.dumps({"status": "success", "data": "Kampanya öneri sistemi entegrasyonu aşamasında."})

def get_cohort_analysis(data_source_id=0, user=None):
    """Kohort retansiyon analizini döner."""
    from ..kohort_view import get_kohort_analizi
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user or AnonymousUser()
    
    response = get_kohort_analizi(request, data_source_id)
    if response.status_code != 200:
        return json.dumps({"status": "error", "message": "Kohort verisi alınamadı."})
    
    # AI için veriyi biraz sadeleştir (son 12 kohort)
    data = response.data
    return json.dumps({
        "status": "success",
        "cohorts": data.get('kohortlar', [])[-12:],
        "cache_date": data.get('_cache_tarihi')
    }, ensure_ascii=False)

def get_product_analysis(query, user=None):
    """
    Belirli bir ürünü (örn: 'yarım yağlı süt') arar ve o ürünün:
    - Müşteri segment dağılımını
    - Çapraz satış (cross-sell) potansiyelini
    - Genel performansını döner.
    """
    from ... import db_engine
    from ..product_portal_view import get_product_portal
    
    # 1. Ürünü bul
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    ph = db_engine.ph()
    
    # PostgreSQL için ILIKE, SQLite için LIKE (db_engine genellikle PostgreSQL kullanıyor)
    like_op = "ILIKE" if db_engine.DB_BACKEND == "postgresql" else "LIKE"
    cursor.execute(f"SELECT id, ad FROM urunler WHERE ad {like_op} {ph} ORDER BY id LIMIT 1", [f"%{query}%"])
    prod = cursor.fetchone()
    
    if not prod:
        db_engine.release_connection(conn)
        return json.dumps({"status": "error", "message": f"'{query}' isminde bir ürün bulunamadı."})
    
    product_id = db_engine.val(prod, 'id')
    db_engine.release_connection(conn)

    # 2. Ürün portal verisini çek
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user or AnonymousUser()
    
    # Not: Ürün portalı şu an data_source_id=0 üzerinden çalışıyor olabilir, 
    # ancak tutarlılık için 0 geçiyoruz (ileride parametrik yapılabilir).
    response = get_product_portal(request, 0, product_id)
    if response.status_code != 200:
        return safe_json_dumps({"status": "error", "message": "Ürün detayları alınamadı."})
    
    data = response.data
    # AI için anlamlı bir özet oluştur
    analysis = {
        "product_info": data['product'],
        "summary": data['summary'],
        "customer_segments": [
            {"segment": s['segment'], "revenue": s['revenue']} 
            for s in data['customerProfile'].get('bySegment', [])[:5]
        ],
        "cross_sell_hot": [
            {"product": p['productName'], "lift": p['lift']} 
            for p in data['crossSell'].get('PRODUCT', [])[:5]
        ],
        "performance_tags": data['performance'].get('PerformansKategori', 'Bilinmiyor')
    }
    
    return safe_json_dumps({
        "status": "success",
        "analysis": analysis
    })

def get_churn_risk_customers(threshold=70, city=None, segment=None, limit=20, user=None):
    """Churn riski yüksek müşterileri getirir. city ve segment ile filtrelenebilir."""
    from ... import db_engine
    ph = db_engine.ph()
    conn = None
    try:
        from datetime import datetime, timedelta
        conn = db_engine.get_connection()
        cursor = db_engine.get_dict_cursor(conn)

        ref_date = datetime.now()
        risk_threshold = (ref_date - timedelta(days=90)).strftime('%Y-%m-%d')

        conditions = [f"son_alisveris_tarihi < {ph}"]
        params = [risk_threshold]

        if city:
            conditions.append(f"sehir = {ph}")
            params.append(city)
        if segment:
            conditions.append(f"rfm_segment = {ph}")
            params.append(segment)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT musteri_id, ad, soyad, sehir, rfm_segment, son_alisveris_tarihi
            FROM musteridetayozet
            WHERE {where_clause}
            ORDER BY son_alisveris_tarihi ASC
            LIMIT {int(limit)}
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        db_engine.release_connection(conn)

        customers = []
        for r in rows:
            if isinstance(r, dict):
                customers.append({
                    "id": r.get("musteri_id"),
                    "ad": f"{r.get('ad', '')} {r.get('soyad', '')}".strip(),
                    "sehir": r.get("sehir"),
                    "segment": r.get("rfm_segment"),
                    "son_alisveris": str(r.get("son_alisveris_tarihi"))
                })
            else:
                customers.append({
                    "id": r[0], "ad": f"{r[1]} {r[2]}".strip(),
                    "sehir": r[3], "segment": r[4], "son_alisveris": str(r[5])
                })

        return safe_json_dumps({
            "status": "success",
            "filters": {"threshold_days": 90, "city": city, "segment": segment},
            "count": len(customers),
            "customers": customers
        })

    except Exception as e:
        if conn:
            db_engine.release_connection(conn)
        return safe_json_dumps({"status": "error", "message": f"Churn Risk Sorgu Hatası: {str(e)}"})

def detect_anomalies(data_source_id, user=None):

    """Sistemdeki anormallikleri (ani düşüş/yükseliş) tespit eder ve AI ile yorumlar."""
    from ..dashboard_view import get_dashboard_kpis, get_dashboard_trend
    from ..category_report_view import get_category_report_details
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user or AnonymousUser()
    
    anomalies = []
    try:
        # 1. Genel KPI Anomalileri
        kpis_res = get_dashboard_kpis(request, data_source_id)
        if kpis_res.status_code == 200 and hasattr(kpis_res, 'data'):
            kpis = kpis_res.data
            for key, val in kpis.items():
                if isinstance(val, dict) and 'change' in val:
                    change = val['change']
                    if abs(change) > 15: # Kritiklik eşiğini %15'e indirdik
                        anomalies.append({
                            "metric": key,
                            "scope": "Global",
                            "type": "spike" if change > 0 else "drop",
                            "value": val['value'],
                            "change": change,
                            "severity": "critical" if abs(change) > 30 else "warning"
                        })
        
        # 2. Kategori Bazlı Anomaliler
        cat_req = factory.get('/?category_name=all&level=primary')
        cat_req.user = request.user
        cat_res = get_category_report_details(cat_req, data_source_id)
        if cat_res.status_code == 200:
            for cat in cat_res.data.get('category_stats', [])[:10]:
                if abs(cat.get('trend', 0)) > 20:
                    anomalies.append({
                        "metric": cat['category'],
                        "scope": "Kategori",
                        "type": "spike" if cat['trend'] > 0 else "drop",
                        "value": cat['revenue'],
                        "change": cat['trend'],
                        "severity": "critical" if abs(cat['trend']) > 35 else "warning"
                    })
                    
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Anomali hesaplama hatası: {str(e)}"}, ensure_ascii=False)
    
    # AI Narrative (Zeka Artırımı)
    narrative = ""
    if anomalies:
        client = get_llm_client()
        if client.is_configured():
            prompt = f"""
Saptanan şu anomalileri profesyonel bir İş Analisti tonuyla yorumla. 
Neden kaynaklanıyor olabilir ve yönetici neyi proaktif olarak yapmalı? (Maks 3 cümle, aksiyon odaklı).
Anomaliler: {safe_json_dumps(anomalies[:5])}
"""
            narrative = client.generate_completion(prompt, SYSTEM_PROMPT)

    return safe_json_dumps({
        "status": "success", 
        "anomalies": anomalies,
        "narrative": narrative
    })

def generate_system_notifications(data_source_id, user=None):
    """
    Sistemdeki anomalileri tarar ve aksiyon odaklı bildirimler oluşturur.
    """
    from ...models import AINotification
    from django.contrib.auth.models import User
    
    if not user:
        user = User.objects.get(pk=1)
        
    res_json = detect_anomalies(data_source_id, user=user)
    res = json.loads(res_json)
    
    if res['status'] != 'success':
        return res_json
        
    anomalies = res.get('anomalies', [])
    narrative = res.get('narrative', '')
    created_count = 0
    
    for anom in anomalies:
        if anom['severity'] in ['warning', 'critical']:
            title = f"⚠️ {anom['metric']} ({anom['scope']}) Anomali Raporu"
            msg = f"{anom['scope']} seviyesinde {anom['metric']} metriğinde %{anom['change']} değişim saptandı. AI Yorumu: {narrative if narrative else 'Veri setinde olağan dışı oynama var.'}"
            
            # --- Akıllı Kampanya Köprüsü (Autonomous Link) ---
            target_path = "/kampanya-onerileri"
            if anom['scope'] == "Kategori":
                target_path = f"/kategori-raporu?name={anom['metric']}"
            elif anom['metric'] == "churnRate":
                target_path = "/churn-analizi"

            # Kampanya Taslağı
            campaign_draft = {
                "title": f"Proaktif Aksiyon: {anom['metric']} Düzeltme",
                "offer": f"{anom['metric']} için %10 Sadakat Bonusu",
                "segment": "Riskli Segment" if anom['type'] == 'drop' else "Yüksek Potansiyel",
                "suggested_channel": "email"
            }

            from django.utils import timezone
            from datetime import timedelta
            exists = AINotification.objects.filter(
                user=user, 
                title=title, 
                created_at__gte=timezone.now() - timedelta(hours=12)
            ).exists()
            
            if not exists:
                AINotification.objects.create(
                    user=user,
                    title=title,
                    message=msg,
                    type=anom['severity'],
                    metadata={
                        "metric": anom['metric'],
                        "scope": anom['scope'],
                        "change": anom['change'],
                        "action_required": True,
                        "link": target_path,
                        "campaign_draft": campaign_draft
                    }
                )
                created_count += 1
                
    return safe_json_dumps({
        "status": "success",
        "message": f"{created_count} yeni aksiyon odaklı bildirim oluşturuldu.",
        "anomalies_found": len(anomalies)
    })

def get_dashboard_briefing(data_source_id, user=None):

    """
    RFM özeti, temel KPI'lar ve anomalileri TEK BİR ÇAĞRIDA döner. 
    Bu araç, AI'nın birden fazla araç çağrısı yaparak vakit kaybetmesini önler.
    """
    rfm_json = get_rfm_summary(data_source_id, user=user)
    anom_json = detect_anomalies(data_source_id, user=user)
    
    try:
        rfm = json.loads(rfm_json)
        anom = json.loads(anom_json)
    except:
        rfm = {"status": "error"}
        anom = {"status": "error"}
        
    result = {
        "status": "success",
        "rfm_summary": rfm,
        "active_anomalies": anom.get("anomalies", []),
        "timestamp": str(datetime.now())
    }
    return safe_json_dumps(result)

def global_search(query, user=None):
    """Müşteri, ürün veya diğer varlıkları isimle arar."""
    from ... import db_engine
    from ..customer_portal_view import get_customer_list
    
    results = []
    
    # 1. Müşteri Araması
    factory = RequestFactory()
    request = factory.get(f"/?search={query}")
    request.user = user or AnonymousUser()
    
    response = get_customer_list(request, 0)
    if response.status_code == 200:
        results.extend([{"type": "müşteri", "id": c['id'], "name": c['ad']} for c in response.data['customers'][:5]])
    
    # 2. Ürün Araması (Database üzerinden)
    try:
        conn = db_engine.get_connection()
        cursor = conn.cursor()
        
        # Basit LIKE araması
        query_param = f"%{query}%"
        placeholder = "%s" if db_engine.DB_BACKEND == "postgresql" else "?"
        
        # Ürün tablosunda u.ad ara (dashboard_view mantığına benzer)
        cursor.execute(f"SELECT id, ad FROM urunler WHERE ad LIKE {placeholder} LIMIT 5", [query_param])
        products = cursor.fetchall()
        
        for p in products:
            p_id = p[0] if isinstance(p, tuple) else p['id']
            p_name = p[1] if isinstance(p, tuple) else p['ad']
            results.append({"type": "ürün", "id": p_id, "name": p_name})
            
        db_engine.release_connection(conn)
    except Exception as e:
        print(f"Global Product Search Error: {e}")

    return safe_json_dumps({"status": "success", "results": results, "query": query})

def navigate_to_customer(customer_id, user=None):
    """Belirli bir müşterinin detay profil sayfasını açar."""
    return safe_json_dumps({
        "status": "success",
        "action": "navigate",
        "path": f"/musteri-portali?id={customer_id}",
        "label": "Müşteri Profili"
    })

def schedule_campaign(title, description, segment, channel='email', scheduled_at=None, user=None):
    """Yeni bir pazarlama kampanyası planlar."""
    from ...models import ScheduledCampaign
    from django.utils import timezone
    from datetime import datetime
    
    if not user:
        from django.contrib.auth.models import User
        user = User.objects.get(pk=1)
        
    try:
        # Tarih parse etme
        if isinstance(scheduled_at, str):
            try:
                dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            except:
                dt = timezone.now() + timezone.timedelta(days=1)
        else:
            dt = timezone.now() + timezone.timedelta(days=1)
            
        campaign = ScheduledCampaign.objects.create(
            user=user,
            title=title,
            description=description,
            segment=segment,
            channel=channel,
            scheduled_at=dt,
            status='pending'
        )
        return safe_json_dumps({
            "status": "success", 
            "message": f"Kampanya planlandı: {title}",
            "id": campaign.id,
            "scheduled_at": str(campaign.scheduled_at)
        })
    except Exception as e:
        return safe_json_dumps({"status": "error", "message": f"Hata: {str(e)}"})

def create_dynamic_dashboard(name, description, config, user=None):
    """Yeni bir dinamik/özel dashboard oluşturur."""
    from ...models import AIDashboard
    
    if not user:
        from django.contrib.auth.models import User
        user = User.objects.get(pk=1)
        
    try:
        dashboard = AIDashboard.objects.create(
            user=user,
            name=name,
            description=description,
            config=config
        )
        return safe_json_dumps({
            "status": "success", 
            "message": f"Dinamik panel oluşturuldu: {name}",
            "id": dashboard.id
        })
    except Exception as e:
        return safe_json_dumps({"status": "error", "message": f"Hata: {str(e)}"})

def navigate_to_page(path, label=None, user=None):
    """Uygulama içindeki belirli bir sayfaya yönlendirme talep eder."""
    return safe_json_dumps({
        "status": "success",
        "action": "navigate",
        "path": path,
        "label": label or path
    })

# --- GLOBAL MASTER TOOLS ---

def get_weekly_brief(data_source_id, user=None):
    """Son 7 günlük performansı özetleyen ve yöneticiye brifing veren araç."""
    from datetime import datetime, timedelta
    from ... import db_engine as _db

    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    end_str = end_date.strftime('%Y-%m-%d')
    start_str = start_date.strftime('%Y-%m-%d')
    mid_str = (end_date - timedelta(days=7)).strftime('%Y-%m-%d')
    ph = _db.ph()

    try:
        conn = _db.get_connection()
        cursor = _db.get_dict_cursor(conn)
        date_expr = _db.strftime_expr('%Y-%m-%d', 'tarih')
        cursor.execute(
            f"SELECT {date_expr} as day, SUM(tutar) as sales FROM satislar WHERE tarih >= {ph} AND tarih <= {ph} GROUP BY {date_expr} ORDER BY day",
            [start_str, end_str]
        )
        rows = cursor.fetchall()
        _db.release_connection(conn)

        trend_data = [{"date": str(r["day"]), "sales": float(r["sales"] or 0)} for r in rows]
        current_period = [r for r in trend_data if r["date"] >= mid_str]
        previous_period = [r for r in trend_data if r["date"] < mid_str]

        curr_total = sum(r['sales'] for r in current_period)
        prev_total = sum(r['sales'] for r in previous_period)
        change_pct = ((curr_total - prev_total) / prev_total * 100) if prev_total > 0 else 0

        # Sipariş verisi için dashboard_comparison'dan sadece son 2 ayı alabiliriz veya trend'den devam edebiliriz.
        # Basitleştirme: Ciro değişimi üzerinden bir başarı skoru üret.
        if curr_total == 0 and prev_total == 0:
            ai_score = 0
        else:
            base_score = 70
            ai_score = min(max(int(base_score + (change_pct * 0.4)), 0), 100)

        # 2. AI Analizi
        client = get_llm_client()
        highlights = []
        
        if client.is_configured() and (curr_total > 0 or prev_total > 0):
            prompt = f"""
Son 7 günlük CRM performans verilerini analiz et ve bir yönetici için SADECE 3 adet çok kısa, çarpıcı ve aksiyon odaklı madde üret.
Veriler:
- Ciro Değişimi: %{change_pct:.1f}
- Cari Dönem Toplam Ciro: ₺{curr_total:,.0f}
- Önceki Dönem Toplam Ciro: ₺{prev_total:,.0f}

Yanıtı sadece maddeler halinde ver, her madde tırnak içinde olsun. Türkçe yaz.
"""
            try:
                llm_response = client.generate_completion(prompt, SYSTEM_PROMPT)
                import re
                highlights = re.findall(r'"([^"]*)"', llm_response)
            except:
                highlights = []
            
        if not highlights:
            if curr_total == 0:
                highlights = ["Sistemde bu dönem için henüz satış verisi saptanmadı.", "Veri kaynaklarını kontrol edin.", "Yeni veri girişi bekliyoruz."]
            else:
                highlights = [
                    f"Son 7 günde ciroda %{abs(change_pct):.1f} {'artış' if change_pct > 0 else 'düşüş'} gözlendi.",
                    "Müşteri etkileşimi stabil seyrediyor.",
                    "AI Önerisi: Mevcut satış trendini korumak için kampanyaları sürdürün."
                ]

        brief = {
            "period": f"{datetime.now().strftime('%Y-%m-%d')}",
            "revenue_summary": {
                "current": curr_total,
                "previous": prev_total,
                "change_pct": round(change_pct, 2)
            },
            "revenue_trend": {
                "current": [r['sales'] for r in current_period],
                "previous": [r['sales'] for r in previous_period]
            },
            "top_highlights": highlights[:3],
            "ai_score": ai_score
        }
        return safe_json_dumps({"status": "success", "brief": brief})
    except Exception as e:
        import traceback
        logging.getLogger(__name__).error(f"Weekly Brief Error: {e}\n{traceback.format_exc()}")
        return safe_json_dumps({"status": "error", "message": str(e), "traceback": traceback.format_exc()})

def get_database_schema(user=None):
    """Veritabanındaki ana tabloları ve kolon şemalarını döner."""
    schema = {
        "tables": {
            "musteriler": ["id", "ad", "telefon", "tip", "onay_durumu", "kayit_tarihi", "kayit_magazasi", "rfm_segment", "rfm_r_score", "rfm_f_score", "rfm_m_score"],
            "satislar": ["id", "fis_no", "musteri_id", "tarih", "saat", "tutar", "miktar", "urun_id", "magaza_id", "marka_id", "kategori_id", "belge_tipi", "kampanya_id"],
            "urunler": ["id", "kod", "ad", "kategori_id", "marka_id"],
            "urunkategori": ["id", "kategori_adi"],
            "magazalar": ["id", "ad", "bolge"],
            "musteridetayozet": ["musteri_id", "ad_soyad", "email", "telefon", "sehir", "rfm_segment", "r_score", "f_score", "m_score", "toplam_harcama", "toplam_alisveris", "ortalama_sepet_tutari", "aktivite_durumu", "trend", "churn_risk_skoru", "ilk_alisveris_tarihi", "son_alisveris_tarihi"],
            "musterietiketler": ["musteri_id", "sabah_alisveriscisi", "indirim_avcisi", "premium_harcayici", "enflasyon_stokcusu", "ve ~60 adet boolean etiket kolonu"],
            "brandsummary": ["brand_id", "brand_name", "total_sales", "customer_count", "order_count"],
            "categorysummary": ["category_name", "revenue", "order_count"]
        }
    }
    return safe_json_dumps({"status": "success", "schema": schema})

def query_crm_database(sql_query, user=None):
    """Güvenli, salt-okunur (read-only) SQL sorguları çalıştırır."""
    from ... import db_engine
    
    # Güvenlik Kontrolleri
    query_upper = sql_query.upper().strip()
    
    # 1. Sadece SELECT izni
    forbidden = ["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE"]
    if any(cmd in query_upper for cmd in forbidden) or not query_upper.startswith("SELECT"):
        return safe_json_dumps({"status": "error", "message": "Güvenlik kısıtlaması: Sadece SELECT sorgularına izin verilir."})
    
    # 2. Limit zorlaması
    if "LIMIT" not in query_upper:
        sql_query = f"{sql_query.rstrip(';')} LIMIT 100"
    
    try:
        results = db_engine.execute_query(sql_query, fetch=True)
        # PII Maskeleme (Safe serialization)
        json_res = safe_json_dumps({"status": "success", "data": results})
        return mask_pii(json_res)
    except Exception as e:
        return safe_json_dumps({"status": "error", "message": f"Sorgu hatası: {str(e)}"})

def get_category_analysis(category_name, level='primary', user=None):
    """Kategori bazlı derinlemesine performans verilerini getirir."""
    from ..category_report_view import get_category_report_details
    factory = RequestFactory()
    request = factory.get(f"/?category_name={category_name}&level={level}")
    request.user = user or AnonymousUser()
    
    response = get_category_report_details(request, data_source_id)
    if response.status_code != 200:
        return safe_json_dumps({"status": "error", "message": "Kategori verisi alınamadı."})
    
    data = response.data
    # AI için özetle
    summary = {
        "category": category_name,
        "kpis": data.get('kpis'),
        "top_products": data.get('top_products', [])[:5],
        "brand_distribution": data.get('brand_distribution', [])[:5]
    }
    return safe_json_dumps({"status": "success", "data": summary})

def get_clv_analytics(user=None):
    """Müşteri Yaşam Boyu Değeri (CLV) analizlerini getirir."""
    from ..clv_view import get_clv_analysis
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user or AnonymousUser()
    
    response = get_clv_analysis(request, data_source_id)
    if response.status_code != 200:
        return safe_json_dumps({"status": "error", "message": "CLV verisi alınamadı."})
    
    return safe_json_dumps({"status": "success", "data": response.data['summary'], "segments": response.data['clvSegments']})

def get_brand_analytics(brand_name, user=None):
    """Marka bazlı pazar payı ve müşteri kitlesi verilerini getirir."""
    from ..dashboard_view import get_brand_report
    factory = RequestFactory()
    request = factory.get(f"/?brand={brand_name}")
    request.user = user or AnonymousUser()
    
    response = get_brand_report(request, data_source_id)
    if response.status_code != 200:
        return safe_json_dumps({"status": "error", "message": "Marka verisi alınamadı."})
    
    # Marka araması yap ve eşleşen markayı bul
    brands = response.data.get('brands', [])
    target = next((b for b in brands if b['brand'].lower() == brand_name.lower()), None)
    
    if not target:
        return json.dumps({"status": "error", "message": f"'{brand_name}' markası raporlarda bulunamadı."}, ensure_ascii=False)
        
    return json.dumps({"status": "success", "data": target}, ensure_ascii=False)

def get_churn_analytics(user=None):
    """Kayıp müşteri (Churn) analiz verilerini getirir."""
    from ..churn_view import get_churn_analysis as get_churn_view_analysis
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user or AnonymousUser()
    
    response = get_churn_view_analysis(request, data_source_id)
    if response.status_code != 200:
        return json.dumps({"status": "error", "message": "Churn verisi alınamadı."})
    
    return json.dumps({"status": "success", "data": response.data.get('summary')}, ensure_ascii=False)

def get_sprint4_insights(user=None):
    """Enflasyon dayanıklılığı, rakip riski ve hane analizlerini getirir."""
    from ..sprint4_view import get_enflasyon_dayaniklilik, get_rakip_riski, get_hane_analizi
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user or AnonymousUser()
    
    inf_res = get_enflasyon_dayaniklilik(request, 0)
    risk_res = get_rakip_riski(request, 0)
    house_res = get_hane_analizi(request, 0)
    
    result = {
        "inflation": inf_res.data if inf_res.status_code == 200 else "Hata",
        "competitor_risk": risk_res.data if risk_res.status_code == 200 else "Hata",
        "household": house_res.data if house_res.status_code == 200 else "Hata"
    }
    return json.dumps({"status": "success", "data": result}, ensure_ascii=False)

def get_customer_narrative(customer_id, data_source_id=0, user=None):
    """
    Müşterinin geçmiş verilerini analiz ederek AI'ya ham 'anlatı' verisi sağlar.
    Bu veri; harcama döngüleri, sepet içeriği değişimi ve sentiment analizi için temel oluşturur.
    """
    profile_json = get_customer_profile(customer_id, data_source_id=data_source_id, user=user)
    profile = json.loads(profile_json)
    
    if profile.get("status") == "error":
        return profile_json
        
    from ... import db_engine
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    ph = db_engine.ph()
    
    # Cross-DB compatibility for string aggregation
    agg_func = "STRING_AGG(u.ad, ', ')" if db_engine.DB_BACKEND == 'postgresql' else "GROUP_CONCAT(u.ad, ', ')"
    
    # Son 10 satışı ve ürünleri çek (Hikaye oluşturmak için)
    query = f"""
        SELECT s.tarih, s.tutar, {agg_func} as urunler
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        WHERE s.musteri_id = {ph}
        GROUP BY s.fis_no, s.tarih, s.tutar
        ORDER BY s.tarih DESC
        LIMIT 10
    """
    cursor.execute(query, [customer_id])
    history = cursor.fetchall()
    db_engine.release_connection(conn)
    
    narrative_data = {
        "profile": profile,
        "recent_history": history,
        "narrative_focus": [
            "Müşteri neden bizi tercih ediyor?",
            "Son dönemdeki harcama alışkanlığı nasıl değişti?",
            "Hangi duygusal tetikleyiciler (indirim, yenilik, sadakat) bu müşteride çalışır?",
            "Gelecekteki potansiyel ihtiyacı ne olabilir?"
        ]
    }
    
    return safe_json_dumps({"status": "success", "data": narrative_data})

TOOLS_DEF = [
    {
        "name": "get_customer_narrative",
        "description": "Müşterinin davranışsal geçmişini 'hikaye' (narratoloji) formatında analiz etmek için ham verileri döner. Müşteri sadakati ve psikolojik profilleme için kullanılır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Müşteri ID'si"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_dashboard_briefing",
        "description": "RFM özeti, temel KPI'lar ve anomalileri TEK BİR ÇAĞRIDA döner. Genel durum sorguları için en hızlı araç budur.",
        "parameters": {
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer"}
            },
            "required": ["data_source_id"]
        }
    },
    {
        "name": "get_rfm_summary",
        "description": "Returns the RFM summary for a given data source.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "Veri kaynağı ID'si (opsiyonel, bağlamdan alınır)"},
                "filters": {"type": "object"}
            }
        }
    },
    {
        "name": "get_customer_profile",
        "description": "Returns full customer profile details.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "list_segment_customers",
        "description": "Belirli bir segmentteki müşterileri (örn: '01-) Şampiyonlar') listeler.",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_name": {"type": "string", "description": "Segment ismi (Glossary'deki tam isim)"},
                "limit": {"type": "integer", "description": "Maksimum müşteri sayısı (varsayılan: 10)"}
            },
            "required": ["segment_name"]
        }
    },
    {
        "name": "detect_anomalies",
        "description": "Identifies anomalies like sudden drops or spikes in business metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "Veri kaynağı ID'si (opsiyonel, bağlamdan alınır)"}
            }
        }
    },
    {
        "name": "schedule_campaign",
        "description": "Schedules a marketing campaign with a title, description, segment and channel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Kampanya başlığı"},
                "description": {"type": "string", "description": "Kampanya metni/açıklaması"},
                "segment": {"type": "string", "description": "Hedef müşteri segmenti"},
                "channel": {"type": "string", "enum": ["sms", "email", "push"], "description": "Gönderim kanalı"},
                "scheduled_at": {"type": "string", "description": "ISO formatında tarih/saat (opsiyonel)"}
            },
            "required": ["title", "description", "segment"]
        }
    },
    {
        "name": "get_churn_risk_customers",
        "description": "Lists customers at churn risk (no purchase in 90+ days). Can filter by city (e.g. 'İstanbul') and RFM segment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {"type": "integer", "description": "Churn eşiği (varsayılan: 70)"},
                "city": {"type": "string", "description": "Şehir filtresi (örn: 'İstanbul')"},
                "segment": {"type": "string", "description": "RFM segment filtresi"},
                "limit": {"type": "integer", "description": "Maksimum müşteri sayısı (varsayılan: 20)"}
            }
        }
    },
    {
        "name": "global_search",
        "description": "Searches for customers or other entities by name globally.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "create_dynamic_dashboard",
        "description": "Yeni bir dinamik/özel dashboard oluşturur. Örnek kullanım: 'kpi.totalRevenue', 'churn_rate', 'trend', 'rfm_summary'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Panel başlığı (örn: 'Haftalık Satış Analizi')"},
                "description": {"type": "string", "description": "Panel açıklaması (örn: 'Ciro ve müşteri kaybı odaklı analiz paneli')"},
                "config": {
                    "type": "object",
                    "description": "Dashboard bileşenleri JSON yapısı.",
                    "properties": {
                        "layout": {"type": "string", "enum": ["grid", "stack"], "description": "Panel düzeni"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["kpi", "chart", "table", "nba"], "description": "Bileşen tipi"},
                                    "title": {"type": "string", "description": "Bileşen başlığı"},
                                    "metric": {
                                        "type": "string", 
                                        "description": "Desteklenen metrik anahtarları: 'kpi.totalRevenue', 'kpi.totalCustomers', 'kpi.avgOrderValue', 'kpi.activeCustomerRate', 'clv.average', 'churn_rate', 'rfm_summary', 'trend', 'nba', 'top_customers', 'churn_risk_list', 'category.all', 'brand.all', 'category.KATEGORI_ADI', 'brand.MARKA_ADI'."
                                    },
                                    "chartType": {"type": "string", "enum": ["bar", "line", "pie", "area"], "description": "Grafik tipi (eğer type='chart' ise)"},
                                    "params": {"type": "object", "description": "Ek filtre parametreleri (opsiyonel)"},
                                    "width": {"type": "integer", "description": "Grid genişliği (1-3, varsayılan 1)"}
                                },
                                "required": ["type", "title"]
                            }
                        }
                    },
                    "required": ["items"]
                }
            },
            "required": ["name", "config"]
        }
    },
    {
        "name": "get_cohort_analysis",
        "description": "Kohort retansiyon analizi verilerini döner. Müşteri bağlılığı ve zamanla kayıp oranlarını analiz etmek için kullanılır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "Veri kaynağı ID'si (varsayılan: 0)"}
            }
        }
    },
    {
        "name": "get_product_analysis",
        "description": "Belirli bir ürünün derinlemesine CRM analizini yapar. Hangi segmentlerin bu ürünü tercih ettiğini ve beraberinde ne aldıklarını gösterir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Aranacak ürün ismi (örn: 'süt', 'yoğurt')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_database_schema",
        "description": "Veritabanındaki ana tabloları (müşteriler, satışlar, ürünler vb.) ve bunların içindeki kolonların listesini döner."
    },
    {
        "name": "query_crm_database",
        "description": "Veritabanına doğrudan SQL SELECT sorgusu gönderir. Şema bilgisi aldıktan sonra karmaşık analizler için kullanılır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql_query": {"type": "string", "description": "Çalıştırılacak SQL SELECT sorgusu"}
            },
            "required": ["sql_query"]
        }
    },
    {
        "name": "get_category_analysis",
        "description": "Kategori bazlı ciro, ürün çeşitliliği ve marka dağılımı verilerini döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category_name": {"type": "string", "description": "Kategori ismi"},
                "level": {"type": "string", "enum": ["primary", "secondary", "tertiary"], "description": "Kategori seviyesi"}
            },
            "required": ["category_name"]
        }
    },
    {
        "name": "get_clv_analytics",
        "description": "Müşteri Yaşam Boyu Değeri (CLV) özetlerini ve segment dağılımlarını döner."
    },
    {
        "name": "get_brand_analytics",
        "description": "Belirli bir markanın pazar payı, basket büyüklüğü ve RFM performansını döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "brand_name": {"type": "string", "description": "Marka ismi (örn: 'Coca Cola')"}
            },
            "required": ["brand_name"]
        }
    },
    {
        "name": "get_churn_analytics",
        "description": "Sistem genelindeki müşteri kaybı (churn) oranlarını ve trendlerini döner."
    },
    {
        "name": "get_sprint4_insights",
        "description": "Enflasyon karşısındaki direnç, rakip market riskleri ve hanehalkı bazlı özel CRM analizlerini döner."
    },
    {
        "name": "navigate_to_page",
        "description": "Kullanıcıyı uygulama içindeki belirli bir sayfaya (Müşteri Portalı, Churn Analizi, Dashboard vb.) yönlendirir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Gidilecek sayfa yolu (örn: '/musteri-portali')"},
                "label": {"type": "string", "description": "Sayfanın kullanıcıya görünecek adı (örn: 'Müşteri Portalı')"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "get_customer_nba",
        "description": "Müşteri için AI tabanlı 3 adet 'Sıradaki En İyi Aksiyon' (NBA) önerisi döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Müşteri ID'si"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "generate_system_notifications",
        "description": "Sistemdeki kritik anomalileri tarar ve kullanıcı için otomatik bildirimler oluşturur. Proaktif denetim için kullanılır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "Veri kaynağı ID'si"}
            }
        }
    },
    {
        "name": "get_weekly_brief",
        "description": "Son 7 günlük performansı özetleyen ve yöneticiye stratejik brifing veren araç.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data_source_id": {"type": "integer", "description": "Veri kaynağı ID'si"}
            }
        }
    }
]

# Projenin kalanındaki json.dumps çağrılarını safe_json_dumps ile değiştirebiliriz
# Ancak dosya çok büyük olduğu için şimdilik kritik olanları değiştirelim.
