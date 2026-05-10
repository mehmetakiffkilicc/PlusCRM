import json
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.db.models import Sum
from .client import get_llm_client
from .session_store import create_session, get_session, add_message, get_session_history, update_session_usage
from .prompt_templates import SYSTEM_PROMPT
from .guards import check_rate_limit, increment_rate_limit, sanitize_messages, check_daily_cost_alert
from .context_builder import build_full_context
from django.utils import timezone
from datetime import timedelta
from ...models import AISession, AIMessage

from rest_framework.permissions import IsAuthenticated
from ...authentication import JWTAuthentication
from .tools import TOOLS_DEF, safe_json_dumps
from .tool_executor import execute_tool


def parse_sse(chunk: dict) -> str:
    return f"data: {json.dumps(chunk)}\n\n"


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_chat_stream(request):
    data = request.data
    user = request.user
    session_id = data.get('session_id')
    message = data.get('message', '')
    context = data.get('context', {})

    if not message:
        return Response({"error": "Message is required"}, status=400)

    if session_id:
        session = get_session(user, session_id)
        if not session:
            return Response({"error": "Session not found"}, status=404)
    else:
        session = create_session(user)

    history = get_session_history(session)
    messages = [{"role": msg.role, "content": msg.content} for msg in history]
    messages.append({"role": "user", "content": message})

    add_message(session, "user", message)

    rate_check = check_rate_limit(user.id)
    if not rate_check['allowed']:
        return Response({"error": rate_check['reason']}, status=429)

    check_daily_cost_alert(user.id)
    increment_rate_limit(user.id)

    safe_messages = sanitize_messages(messages)
    full_context = build_full_context(context)
    client = get_llm_client()

    def stream_generator():
        full_response = ""
        input_tokens = 0
        output_tokens = 0
        try:
            for event in client.stream_chat(
                safe_messages,
                full_context,
                SYSTEM_PROMPT,
                tools=TOOLS_DEF,
                _tool_executor=execute_tool,
                _tool_executor_kwargs={"user": user, "context": full_context},
            ):
                etype = event.get("type")

                if etype == "text":
                    full_response += event["text"]
                    yield parse_sse({"type": "message", "text": event["text"]})

                elif etype == "tool_start":
                    yield parse_sse({"type": "tool_start", "tool": event["tool"]})

                elif etype == "tool_call":
                    # GeminiClient _tool_executor ile zaten çalıştırdı; sadece frontend'e bildir
                    yield parse_sse({"type": "tool_running", "tool": event["tool"]})

                elif etype == "tool_result":
                    # GeminiClient tool sonucunu zaten işledi, frontend'e ilet
                    yield parse_sse({"type": "tool_result", "tool": event["tool"], "result": event.get("result", {})})

                elif etype == "error":
                    yield parse_sse({"type": "error", "message": event.get("message", "Bilinmeyen hata")})

                elif etype == "done":
                    input_tokens = event.get("input_tokens", 0)
                    output_tokens = event.get("output_tokens", 0)
                    break

            if full_response:
                add_message(session, "assistant", full_response, input_tokens=input_tokens, output_tokens=output_tokens)

            if input_tokens or output_tokens:
                update_session_usage(session, input_tokens, output_tokens)

            yield parse_sse({"type": "done"})

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"stream_generator error: {e}", exc_info=True)
            
            # 429 veya 503 gibi hatalarda daha açıklayıcı mesaj
            error_msg = str(e)
            if "429" in error_msg or "503" in error_msg or "busy" in error_msg.lower():
                yield parse_sse({"type": "error", "message": "AI servisi şu an yoğun. Yedek sistem devreye alınmaya çalışılıyor veya lütfen 1 dakika sonra tekrar deneyin."})
            else:
                yield parse_sse({"type": "error", "message": f"AI Asistan bağlantı hatası: {error_msg}"})
            yield parse_sse({"type": "done"})

    response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_new_session(request):
    try:
        session = create_session(request.user)
        return Response({'id': session.id, 'title': session.title})
    except Exception as e:
        return Response({'error': f"Oturum oluşturulamadı: {str(e)}"}, status=500)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_session_history(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        from ...models import AISession
        sessions = AISession.objects.filter(user=request.user).order_by('-created_at')[:50]
        return Response({'sessions': [
            {"id": s.id, "title": s.title, "created_at": s.created_at.isoformat(), "total_tokens": s.total_tokens}
            for s in sessions
        ]})
    session = get_session(request.user, session_id)
    if not session:
        return Response({'error': 'Not found'}, status=404)
    history = get_session_history(session)
    messages = [{"id": msg.id, "role": msg.role, "content": msg.content} for msg in history]
    return Response({'messages': messages})


@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_delete_session(request, session_id):
    session = get_session(request.user, session_id)
    if session:
        session.delete()
        return Response({'status': 'deleted'})
    return Response({'error': 'Not found'}, status=404)


@api_view(['POST', 'GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_quick_summary(request):
    # Streaming desteği için GET/POST ayrımı
    if request.method == 'POST':
        text = request.data.get('text', '')
        data = request.data.get('data', '')
        context_type = request.data.get('context_type')
        context_id = request.data.get('context_id')
        ds_id = request.data.get('data_source_id')
        stream = request.data.get('stream', False)
    else:
        text = request.GET.get('text', '')
        data = request.GET.get('data', '')
        context_type = request.GET.get('context_type')
        context_id = request.GET.get('context_id')
        ds_id = request.GET.get('data_source_id')
        stream = request.GET.get('stream', 'false').lower() == 'true'

    data_source_id = int(ds_id) if ds_id and str(ds_id).isdigit() else 0

    client = get_llm_client()
    if not client.is_configured():
        return Response({"error": "AI servisi yapılandırılmamış."}, status=503)

    try:
        # Prompt Seçimi
        final_prompt = ""
        # 1. Narratoloji özel durumu
        if context_type == 'customer_narratology' and context_id:
            from .tools import get_customer_narrative
            narrative_data = get_customer_narrative(context_id, data_source_id=data_source_id, user=request.user)
            final_prompt = f"""
Sen bir 'Müşteri Stratejisti' ve 'Davranışsal Psikolog'sun. 
Aşağıdaki müşteri verilerine dayanarak, müşterinin markayla olan ilişkisini anlatan derinlemesine, 
psikolojik motivasyonları ve gelecek satın alma ihtimallerini içeren profesyonel bir 'Müşteri Hikayesi' oluştur.

KURALLAR:
- 3-5 paragraf uzunluğunda olsun.
- Müşterinin spesifik alışkanlıklarına değin (örn: "Sabahları organik ürünlere yöneliyor").
- Bir stratejik tavsiye ile bitir.
- Ton profesyonel, akıcı ve ilgi çekici olmalı.
- Sadece TÜRKÇE kullan.

VERİLER:
{narrative_data}
"""
        # 2. Segment veya Müşteri Profili için özel prompt oluşturma
        elif context_type in ('segment_profile', 'customer', 'segmentation') and text:
            final_prompt = f"""
Sana bir CRM sisteminden '{context_type}' tipinde veriler gönderiyorum. 
Bu verileri analiz et ve bir yönetici özeti çıkar. 

HEDEFLER:
- En önemli 3 bulguyu maddeler halinde yaz.
- Varsa anomalleri veya riskleri belirt.
- Müşteri kitlesini geliştirmek için 1 somut aksiyon önerisi sun.
- Profesyonel, veri odaklı ve TÜRKÇE bir dil kullan.

BİLGİLER:
Analiz ID: {context_id}
VERİ İÇERİĞİ:
{text}
"""
        else:
            # Standart özetleme
            if not text:
                 return Response({"error": "Analiz edilecek veri bulunamadı."}, status=400)
            final_prompt = f"Şu veriyi özetle:\n{text}"

        # Yanıt oluşturma (Streaming veya Standart)
        if stream:
            from django.http import StreamingHttpResponse
            
            def sse_generator():
                try:
                    for chunk in client.stream_completion(final_prompt, SYSTEM_PROMPT):
                        if chunk.get('type') == 'text':
                            yield f"data: {json.dumps({'text': chunk['text']}, ensure_ascii=False)}\n\n"
                        elif chunk.get('type') == 'error':
                            yield f"data: {json.dumps({'error': chunk['message']}, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as ex:
                    yield f"data: {json.dumps({'error': str(ex)}, ensure_ascii=False)}\n\n"

            return StreamingHttpResponse(sse_generator(), content_type='text/event-stream')
        else:
            summary = client.generate_completion(final_prompt, SYSTEM_PROMPT)
            return Response({'summary': summary})

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"AI summary error: {e}", exc_info=True)
        return Response({"error": "AI servisi şu an yanıt vermiyor."}, status=503)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_generate_variants(request):
    try:
        campaign_data = request.data
        if not campaign_data:
            return Response({"error": "Kampanya verisi gönderilmedi."}, status=400)

        client = get_llm_client()
        if not client.is_configured():
            return Response({"error": "AI servisi yapılandırılmamış. Lütfen yöneticinize başvurun."}, status=503)

        campaign_info = safe_json_dumps(campaign_data)
        prompt = f"""
Aşağıdaki kampanya detayı için SMS, Email ve Push kanallarına özel, her kanal için 2'şer adet yüksek kaliteli ve yaratıcı varyant üret.

KAMPANYA DETAYI:
{campaign_info}

BÖLÜM KURALLARI:
1. SMS: Öz, net, merak uyandırıcı, max 160 karakter.
2. Email: Profesyonel, konu başlığı (subject) ve gövde (body) içeren, ikna edici.
3. Push: Emojili, enerjik, kısa.

KALİTE KURALLARI (KRİTİK):
- DİL: Kesinlikle SADECE TÜRKÇE kullan. Anlamsız kelimeler (gibberish) veya uydurma terimler kullanma.
- TON: Profesyonel ve samimi bir pazarlama dili kullan.
- FORMAT: Yanıtı sadece aşağıdaki JSON formatında ver. JSON dışı metin ekleme.

JSON FORMATI:
{{
    "variants": {{
        "sms": ["...", "..."],
        "email": [
            {{"subject": "...", "body": "..."}},
            {{"subject": "...", "body": "..."}}
        ],
        "push": ["...", "..."]
    }}
}}
"""
        response_text = client.generate_completion(prompt, SYSTEM_PROMPT)
        if not response_text or response_text.strip() == "":
             return Response({"error": "AI servisi boş yanıt döndürdü. Lütfen tekrar deneyin."}, status=503)

        # JSON temizleme ve parse
        clean_json = response_text
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
        
        if not clean_json.strip().startswith("{"):
            import re
            match = re.search(r'\{.*\}', clean_json, re.DOTALL)
            if match:
                clean_json = match.group(0)
        
        try:
            data = json.loads(clean_json)
        except json.JSONDecodeError:
            # Yedek: Eğer JSON parse edilemiyorsa ham metni SMS olarak döndür
            data = {"variants": {"sms": [response_text[:160]], "email": [], "push": []}}
            
        # Format doğrulaması ve normalizasyon
        if "variants" not in data and any(k in data for k in ["sms", "email", "push"]):
            data = {"variants": data}
            
        v = data.get("variants", {})
        if not isinstance(v, dict):
            v = {"sms": [], "email": [], "push": []}
            data["variants"] = v
            
        # Kanal bazlı kontrol ve temizleme
        for key in ["sms", "email", "push"]:
            if key not in v or not isinstance(v[key], list):
                v[key] = []
        
        return Response(data)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Variant API Error: {e}", exc_info=True)
        return Response({
            "error": "AI servisleri şu an yanıt veremiyor veya geçersiz veri üretildi.",
            "detail": str(e)
        }, status=503)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_detect_anomalies(request):
    from .tools import detect_anomalies
    ds_id = request.GET.get('data_source_id')
    data_source_id = int(ds_id) if ds_id and str(ds_id).isdigit() else 0
    anomalies_data = json.loads(detect_anomalies(data_source_id, user=request.user))

    if not anomalies_data.get('anomalies'):
        return Response({'anomalies': [], 'narrative': 'Sistemde kritik anomali tespit edilmedi.'})

    client = get_llm_client()
    if not client.is_configured():
        return Response({'anomalies': anomalies_data['anomalies'], 'narrative': ''})

    prompt = f"""
Sistemdeki aşağıdaki anomalileri analiz et ve yönetici özeti şeklinde kısa yorum yaz.
Neden olmuş olabilir ve ne yapmalı? (2-3 cümle)

Anomaliler:
{json.dumps(anomalies_data['anomalies'], indent=2, ensure_ascii=False)}
"""
    narrative = client.generate_completion(prompt, SYSTEM_PROMPT)
    return Response({'anomalies': anomalies_data['anomalies'], 'narrative': narrative})


@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_customer_profile(request, customer_id):
    from .tools import get_customer_profile
    ds_id = request.GET.get('data_source_id')
    data_source_id = int(ds_id) if ds_id and str(ds_id).isdigit() else 0
    raw_profile = json.loads(get_customer_profile(customer_id, data_source_id=data_source_id, user=request.user))

    if raw_profile.get('status') == 'error':
        return Response({"error": "Müşteri profili verisi alınamadı."}, status=404)

    client = get_llm_client()
    if not client.is_configured():
        return Response({'customer_id': customer_id, 'narrative': '', 'raw_data': raw_profile})

    prompt = f"""
Aşağıdaki müşteri verilerine dayanarak, harcama alışkanlıklarını, markaya bağlılığını ve potansiyel fırsatları anlatan
3-4 cümlelik profesyonel bir özet yaz. 3. şahıs kullan (örn: "Bu müşteri..."). Sadece Türkçe.

Veriler:
{json.dumps(raw_profile, indent=2, ensure_ascii=False)}
"""
    narrative = client.generate_completion(prompt, SYSTEM_PROMPT)
    return Response({'customer_id': customer_id, 'narrative': narrative, 'raw_data': raw_profile})


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_customer_nba(request, customer_id):
    """
    Belirli bir müşteri için AI Next Best Action (NBA) önerilerini döner.
    """
    from .tools import get_customer_nba
    ds_id = request.GET.get('data_source_id')
    data_source_id = int(ds_id) if ds_id and str(ds_id).isdigit() else 0
    nba_results_json = get_customer_nba(customer_id, data_source_id=data_source_id, user=request.user)
    try:
        nba_results = json.loads(nba_results_json)
    except Exception as e:
        return Response({"error": f"NBA Parser Error: {str(e)}", "raw": nba_results_json}, status=500)
    
    if nba_results.get('status') == 'error':
        return Response({"error": nba_results.get('message', 'NBA verisi oluşturulamadı.')}, status=500)
        
    return Response({
        'customer_id': customer_id, 
        'actions': nba_results.get('actions', []),
        'timestamp': timezone.now()
    })


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_usage_stats(request):
    user = request.user
    sessions = AISession.objects.filter(user=user)
    
    # Bugün (son 24 saat) yapılan sorgu sayısı
    one_day_ago = timezone.now() - timedelta(days=1)
    today_queries = AIMessage.objects.filter(
        session__user=user, 
        role='user', 
        created_at__gte=one_day_ago
    ).count()
    
    # Aylık token (mevcut ay başından beri)
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_tokens = sessions.filter(created_at__gte=month_start).aggregate(t=Sum('total_tokens'))['t'] or 0
    
    # Model bilgileri
    from decouple import config
    primary_model = config('AI_DEFAULT_MODEL', default='gemini-2.0-flash')
    # fallback_active: sadece gerçek OpenRouter failover aktifse true — API key varlığı yeterli değil
    fallback_model = config('AI_FALLBACK_MODEL', default='')
    fallback_active = bool(fallback_model) and fallback_model.startswith('gpt')

    return Response({
        'today_queries': today_queries,
        'query_limit': int(config('AI_RATE_LIMIT_PER_DAY', default=200)),
        'monthly_tokens': monthly_tokens,
        'token_limit': 5000000, # 5M varsayılan
        'active_model': primary_model,
        'fallback_active': fallback_active,
        'session_count': sessions.count(),
        'total_cost': float(sessions.aggregate(c=Sum('total_cost'))['c'] or 0),
    })

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ai_weekly_brief(request):
    """
    Haftalık yönetici brifingini (get_weekly_brief tool'u üzerinden) döner.
    """
    from .tools import get_weekly_brief
    data_source_id = request.GET.get('data_source_id', 0)
    
    # Tool'u çalıştır
    brief_json = get_weekly_brief(int(data_source_id), user=request.user)
    brief_data = json.loads(brief_json)
    
    if brief_data.get('status') == 'error':
        return Response({"error": brief_data.get('message', 'Brifing oluşturulamadı.')}, status=500)
        
    return Response(brief_data.get('brief', {}))
