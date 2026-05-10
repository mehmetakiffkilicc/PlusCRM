import sys
import os
import psycopg2
from decouple import config

# PostgreSQL Bağlantı Bilgisi
# Railway'deki DATABASE_URL veya .env'deki POSTGRES_URL kullanılır
DATABASE_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))

def log_event(message, level="INFO"):
    if not DATABASE_URL:
        print(f"[{level}] {message} (Database URL not found)")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO system_logs (service_name, level, message) VALUES (%s, %s, %s)",
            ("tailscale-boot", level, message)
        )
        conn.commit()
        conn.close()
        print(f"[{level}] {message} (Logged to DB)")
    except Exception as e:
        print(f"[{level}] {message} (Logging failed: {e})")

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "No message provided"
    lvl = sys.argv[2] if len(sys.argv) > 2 else "INFO"
    log_event(msg, lvl)
