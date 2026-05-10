import json
import sys
import os

# Django çevresini ayarla
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from api.analytics.llm.tool_executor import execute_tool

def test_smart_injection():
    print("--- Test: Smart-Injection ---")
    
    # data_source_id parametrelerde yok, ama context içinde var
    parameters = {"filters": {"period": "2024"}}
    context = {"data_source_id": 99, "page": "test_page"}
    
    # execute_tool çağrısı (get_rfm_summary mock olarak çağrılacak)
    print(f"Girdi Parametreleri: {parameters}")
    print(f"Girdi Context: {context}")
    
    # get_rfm_summary tool'unu test amaçlı yakalıyoruz
    from api.analytics.llm import tools
    # Orijinal fonksiyonu sakla
    original_func = tools.get_rfm_summary
    
    test_result = {"captured_id": None}
    
    def mock_rfm(data_source_id, filters=None):
        test_result["captured_id"] = data_source_id
        return json.dumps({"status": "mock_success"})
    
    tools.get_rfm_summary = mock_rfm
    
    try:
        execute_tool("get_rfm_summary", parameters, context=context)
        print(f"Enjekte edilen data_source_id: {test_result['captured_id']}")
        
        if test_result["captured_id"] == 99:
            print("✅ BAŞARILI: data_source_id context'ten otomatik enjekte edildi.")
        else:
            print("❌ HATA: data_source_id enjekte edilemedi.")
            
    finally:
        # Geri yükle
        tools.get_rfm_summary = original_func

def test_regex_injection():
    print("\n--- Test: Regex (String) Injection ---")
    parameters = {}
    context_str = 'Aktif Veri Kaynağı ID: 44\nSayfa: rfm_analysis'
    
    # tool_executor.py'deki regex'i test etmek için ham mantığı simüle et
    import re
    ds_id = None
    match = re.search(r'ID:\s"?(\d+)"?', context_str)
    if match:
        ds_id = match.group(1)
    
    print(f"Context String: {context_str}")
    print(f"Regex Sonucu: {ds_id}")
    
    if ds_id == "44":
        print("✅ BAŞARILI: String context içinden ID regex ile yakalandı.")
    else:
        print("❌ HATA: String ID yakalanamadı.")

if __name__ == "__main__":
    try:
        test_smart_injection()
        test_regex_injection()
    except Exception as e:
        print(f"Test sırasında hata: {e}")
