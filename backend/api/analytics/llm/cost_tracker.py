"""
Token ve maliyet telemetrisi.
Her LLM çağrısında giriş/çıkış token sayılarını ve tahmini maliyeti kaydeder.
"""
from decimal import Decimal
from ...models import AISession, AIAuditLog
import hashlib


# Yaklaşık fiyatlandırma (USD / 1M token) — gerçek fiyatlarla güncellenmeli
PRICING = {
    'claude-3-haiku-20240307':      {'input': 0.25, 'output': 1.25},
    'claude-haiku-4-5-20251001':    {'input': 1.00, 'output': 5.00},
    'claude-sonnet-4-6':            {'input': 3.00, 'output': 15.00},
    'gpt-4o-mini':                  {'input': 0.15, 'output': 0.60},
    'gpt-4o':                       {'input': 5.00, 'output': 15.00},
    'gemini-2.0-flash':             {'input': 0.10, 'output': 0.40},
    'default':                      {'input': 1.00, 'output': 5.00},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """
    Token sayılarından tahmini maliyet hesaplar (USD).
    """
    prices = PRICING.get(model, PRICING['default'])
    cost = (input_tokens * prices['input'] + output_tokens * prices['output']) / 1_000_000
    return Decimal(str(round(cost, 6)))


def record_usage(session: AISession, input_tokens: int, output_tokens: int, model: str = ''):
    """
    Oturumdaki toplam token ve maliyet bilgilerini günceller.
    """
    model_name = model or session.model_name
    cost = estimate_cost(model_name, input_tokens, output_tokens)

    session.total_tokens += input_tokens + output_tokens
    session.total_cost += cost
    session.save(update_fields=['total_tokens', 'total_cost'])


def create_audit_log(user, session=None, tool_called='', prompt_text='', response_text=''):
    """
    Güvenlik ve denetim için AI çağrı kaydı oluşturur.
    """
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:64] if prompt_text else ''
    response_hash = hashlib.sha256(response_text.encode()).hexdigest()[:64] if response_text else ''

    AIAuditLog.objects.create(
        user=user,
        session=session,
        tool_called=tool_called,
        prompt_hash=prompt_hash,
        response_hash=response_hash,
    )
