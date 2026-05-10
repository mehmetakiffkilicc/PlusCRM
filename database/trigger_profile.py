import requests
import time

url = "http://127.0.0.1:8000/api/dashboard-sqlite/"
print(f"Triggering {url}...")
try:
    start = time.perf_counter()
    r = requests.get(url, timeout=30)
    end = time.perf_counter()
    print(f"Status: {r.status_code}")
    print(f"Total Time (Requests): {end-start:.4f}s")
    if r.status_code == 200:
        print("Success!")
except Exception as e:
    print(f"Error: {e}")
