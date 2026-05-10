from django.apps import AppConfig
import os


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        """Django başladığında connection pool'u ısıt ve test et"""
        # Sadece ana süreçte çalıştır (runserver reload'dan kaçın)
        if os.environ.get('RUN_MAIN') == 'true':
            import logging
            logger = logging.getLogger(__name__)
            try:
                from api import db_engine
                if db_engine.DB_BACKEND == "postgresql":
                    pool = db_engine.get_pg_pool()
                    if pool:
                        # Test connection to warm up the pool
                        conn = pool.getconn()
                        try:
                            cur = conn.cursor()
                            cur.execute("SELECT 1")
                            cur.close()
                            logger.info("PostgreSQL connection pool warmed up successfully.")
                        finally:
                            pool.putconn(conn)
            except Exception as e:
                logger.warning(f"Connection pool warm-up failed: {e}")
