"""
PII maskeleme, rate limiting ve token kota kontrolleri.
TC kimlik, tam telefon numarası ve email adresleri LLM'e gönderilmez.
"""
import re
from datetime import datetime, timedelta
from django.core.cache import cache
from decouple import config

# --- PII Regex Patterns ---
TC_KIMLIK_PATTERN = re.compile(r'\b[1-9]\d{10}\b')
# Telefon: +90, 0, boşluksuz, tireli, parantezli formatları kapsar
TELEFON_PATTERN = re.compile(
    r'\b(?:\+90|0090|0)[\s\-\.]?'          # ülke kodu
    r'(?:\(?\d{3}\)?[\s\-\.]?)'             # alan kodu
    r'\d{3}[\s\-\.]?\d{2}[\s\-\.]?\d{2}\b' # numara
)
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
IBAN_PATTERN = re.compile(r'\bTR\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{2}\b')
KREDI_KART_PATTERN = re.compile(r'\b(?:\d{4}[\s\-]?){3}\d{4}\b')

RATE_LIMIT_PER_MINUTE = int(config('AI_RATE_LIMIT_PER_MINUTE', default='10'))
RATE_LIMIT_PER_DAY = int(config('AI_RATE_LIMIT_PER_DAY', default='200'))


def mask_pii(text: str) -> str:
    """Metindeki PII verilerini maskeler."""
    text = TC_KIMLIK_PATTERN.sub('[TC_KİMLİK]', text)
    text = TELEFON_PATTERN.sub('[TELEFON]', text)
    text = EMAIL_PATTERN.sub('[EMAIL]', text)
    text = IBAN_PATTERN.sub('[IBAN]', text)
    text = KREDI_KART_PATTERN.sub('[KART]', text)
    return text


DAILY_COST_ALERT_USD = float(config('AI_DAILY_COST_ALERT_USD', default='5.0'))


def check_daily_cost_alert(user_id: int) -> bool:
    """Günlük maliyet DAILY_COST_ALERT_USD'yi aştıysa True döner ve loglar."""
    try:
        from django.utils import timezone
        from ...models import AISession
        from decimal import Decimal
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sessions = AISession.objects.filter(user_id=user_id, created_at__gte=today_start)
        total_cost = sum(s.total_cost or Decimal('0') for s in sessions)
        if total_cost >= Decimal(str(DAILY_COST_ALERT_USD)):
            import logging
            logging.getLogger(__name__).warning(
                f"AI maliyet alarmı: user_id={user_id} günlük maliyet ${total_cost:.4f} (limit: ${DAILY_COST_ALERT_USD})"
            )
            return True
    except Exception:
        pass
    return False


def _get_day_count_from_db(user_id: int) -> int:
    """Günlük istek sayısını DB'den çek (cache restart güvenli)."""
    try:
        from django.utils import timezone
        from ...models import AIMessage
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return AIMessage.objects.filter(
            session__user_id=user_id,
            role='user',
            created_at__gte=today_start
        ).count()
    except Exception:
        return 0


def check_rate_limit(user_id: int) -> dict:
    """
    Kullanıcının dakikalık ve günlük istek limitini kontrol eder.
    Dakikalık: cache (hızlı). Günlük: DB (restart-safe).
    """
    minute_key = f'ai_rate_minute_{user_id}'
    minute_count = cache.get(minute_key, 0)

    if minute_count >= RATE_LIMIT_PER_MINUTE:
        return {
            'allowed': False,
            'reason': f'Dakikalık limit aşıldı ({RATE_LIMIT_PER_MINUTE} istek/dakika). Lütfen biraz bekleyin.'
        }

    day_count = _get_day_count_from_db(user_id)
    if day_count >= RATE_LIMIT_PER_DAY:
        return {
            'allowed': False,
            'reason': f'Günlük limit aşıldı ({RATE_LIMIT_PER_DAY} istek/gün). Yarın tekrar deneyebilirsiniz.'
        }

    return {'allowed': True, 'reason': None}


def increment_rate_limit(user_id: int):
    """Dakikalık cache sayacını artırır. Günlük sayaç DB'den okunur."""
    minute_key = f'ai_rate_minute_{user_id}'
    minute_count = cache.get(minute_key, 0)
    cache.set(minute_key, minute_count + 1, timeout=60)


def sanitize_messages(messages: list) -> list:
    """
    Tüm mesajlardaki PII verilerini maskeler.
    """
    return [
        {**msg, 'content': mask_pii(msg.get('content', ''))}
        for msg in messages
    ]
