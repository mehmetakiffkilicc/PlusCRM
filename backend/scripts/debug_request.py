import requests
try:
    r = requests.get('http://127.0.0.1:3001/api/veri-kaynaklari/1/musteriler/1/', headers={'Authorization': 'Bearer test'}, timeout=5)
    print(f"Status: {r.status_code}")
    print("Body (start):")
    print(r.text[:5000])
except Exception as e:
    print(f"Error: {e}")
