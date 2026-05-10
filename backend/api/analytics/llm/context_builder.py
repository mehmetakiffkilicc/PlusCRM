"""
3 Katmanlı Context Builder:
  1. Statik (cacheable): Sistem promptu + segment/etiket glossary
  2. Dinamik: Sayfa bağlamı (hangi sayfada, hangi filtreler aktif)
  3. Tool-use: LLM'in çağırdığı araç sonuçları
"""
import json
from .prompt_templates import GLOSSARY


def build_static_context() -> str:
    """
    Segment tanımları ve etiket glossary'si.
    Bu içerik prompt caching ile önbelleğe alınabilir.
    """
    glossary_text = "\n".join(
        f"- {segment}: {desc}" for segment, desc in GLOSSARY.items()
    )
    return f"""## Segment Tanımları
{glossary_text}
"""


def build_dynamic_context(page_context: dict) -> str:
    """
    Kullanıcının aktif sayfası ve filtrelerinden dinamik context oluşturur.
    page_context örnek:
    {
      "page": "churn_analysis",
      "data_source_id": 1,
      "filters": {"period": "son_6_ay"},
      "summary_data": {...}
    }
    """
    if not page_context:
        return ""

    page = page_context.get('page', 'bilinmeyen')
    filters = page_context.get('filters', {})
    summary = page_context.get('summary_data', {})
    ds_id = page_context.get('data_source_id') or filters.get('data_source_id')

    parts = [f"## Aktif Sayfa: {page}"]
    # data_source_id metinsel olarak context'e eklenmez, sessizce tool_executor tarafından yönetilir.

    if filters:
        parts.append(f"Uygulanan filtreler: {json.dumps(filters, ensure_ascii=False)}")

    if summary:
        parts.append(f"Sayfa özet verisi: {json.dumps(summary, ensure_ascii=False, default=str)[:2000]}")

    return "\n".join(parts)


def build_full_context(page_context: dict = None) -> str:
    """
    3 katmanı birleştirerek tam context döndürür.
    """
    parts = [build_static_context()]

    dynamic = build_dynamic_context(page_context or {})
    if dynamic:
        parts.append(dynamic)

    return "\n\n".join(parts)
