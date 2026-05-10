import requests
import time

def ping():
    print("Testing RAW API Endpoint Speed (127.0.0.1:8000)")
    
    # Measure Health
    t0 = time.time()
    try:
        r = requests.get("http://127.0.0.1:8000/api/health/", timeout=5)
        print(f"Health API ({r.status_code}): {time.time()-t0:.3f} sec")
    except Exception as e:
        print("Health failed:", e)

    # Measure Customer Portal (No Auth -> Expect 401 fast)
    t0 = time.time()
    try:
        r = requests.get("http://127.0.0.1:8000/api/veri-kaynaklari/1/musteriler/?page=1", timeout=5)
        print(f"Customer API - No Auth ({r.status_code}): {time.time()-t0:.3f} sec")
    except Exception as e:
        print("Customer API failed:", e)

if __name__ == "__main__":
    ping()
