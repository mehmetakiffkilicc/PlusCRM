import os
import sys
import time
import json
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.analytics.llm.tool_executor import execute_tool
from api.analytics.rfm_view import get_rfm_from_database
from django.core.cache import cache

def test_performance():
    print("--- AI Performans Testi Başlatılıyor ---")
    
    # 1. RFM Cache Testi
    print("\n1. RFM Cache Testi:")
    cache.delete('global_rfm_database_summary')
    
    start = time.time()
    get_rfm_from_database()
    first_call = time.time() - start
    print(f"İlk Çağrı (Cache-Miss): {first_call:.4f} sn")
    
    start = time.time()
    get_rfm_from_database()
    second_call = time.time() - start
    print(f"İkinci Çağrı (Cache-Hit): {second_call:.4f} sn")
    
    if second_call < first_call:
        print(f"✅ BAŞARILI: Önbellekleme sayesinde hızlanma oranı: %{((first_call-second_call)/first_call)*100:.1f}")
    else:
        print("❌ HATA: Önbellekleme çalışmadı veya fark yaratmadı.")

    # 2. Unified Tool Testi
    print("\n2. Unified Tool (get_dashboard_briefing) Testi:")
    start = time.time()
    res = execute_tool("get_dashboard_briefing", {"data_source_id": 1})
    briefing_time = time.time() - start
    print(f"Brifing Araç Çağrısı: {briefing_time:.4f} sn")
    
    data = json.loads(res)
    if data.get('status') == 'success' and 'rfm_summary' in data:
        print("✅ BAŞARILI: Unified tool ('get_dashboard_briefing') veri üretti.")
    else:
        print("❌ HATA: Unified tool verisi eksik veya hatalı.")

if __name__ == "__main__":
    test_performance()
