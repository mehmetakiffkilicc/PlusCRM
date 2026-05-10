import json
import os
import sys

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from api.analytics.llm.client import get_llm_client
from api.analytics.llm.prompt_templates import SYSTEM_PROMPT

def test_variant_generation():
    campaign_data = {
        "title": "Bahar Kampanyası",
        "description": "Tüm süt ürünlerinde %20 indirim",
        "segment": "Sadık Müşteriler",
        "category": "Süt & Kahvaltı"
    }
    
    prompt = f"""
Aşağıdaki kampanya önerisi için SMS, Email ve Push kanallarına özel, her kanal için 2'şer adet yaratıcı reklam/duyuru varyantı üret.
Kanallar:
1. SMS (Kısa, net, aksiyon odaklı, max 160 karakter)
2. Email (Konu başlığı ve gövde metni dahil, samimi ve detaylı)
3. Push Notification (Dikkat çekici, emojili)

Kampanya Detayı:
{json.dumps(campaign_data, ensure_ascii=False)}

Yanıtı SADECE şu JSON formatında ver, başka hiçbir şey ekleme:
{{"variants": {{
    "sms": ["...", "..."],
    "email": [{{"subject": "...", "body": "..."}}, {{"subject": "...", "body": "..."}}],
    "push": ["...", "..."]
}}}}
Türkçe yaz.
"""
    
    print("AI'ya istek gönderiliyor...")
    client = get_llm_client()
    try:
        response_text = client.generate_completion(prompt, SYSTEM_PROMPT)
        print("AI Yanıtı Alındı:")
        print(response_text)
        
        # llm_view.py'deki temizleme mantığı
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
        
        print("\nTemizlenmiş JSON:")
        print(clean_json)
        
        data = json.loads(clean_json)
        print("\nParse Edilmiş Veri:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if "variants" in data:
            print("✅ BAŞARILI: Varyantlar başarıyla üretildi ve parse edildi.")
        else:
            print("❌ HATA: 'variants' anahtarı bulunamadı.")
            
    except Exception as e:
        print(f"❌ HATA: {e}")

if __name__ == "__main__":
    test_variant_generation()
