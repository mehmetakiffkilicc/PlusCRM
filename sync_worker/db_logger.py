import logging
try:
    import models
except ImportError:
    try:
        from . import models
    except (ImportError, ValueError):
        from sync_worker import models


class DBLoggingHandler(logging.Handler):
    """
    Sistem loglarını veritabanındaki system_logs tablosuna yazar.
    Worker versiyonu.
    """
    def __init__(self, service_name='worker'):
        super().__init__()
        self.service_name = service_name

    def emit(self, record):
        try:
            # SQLite kilitlenmelerini önlemek için PostgreSQL değilse DB loglamayı atla
            if models.DB_BACKEND != "postgresql":
                return
                
            log_entry = self.format(record)
            level = record.levelname
            
            conn = models.get_connection()
            try:
                cursor = conn.cursor()
                is_pg = (models.DB_BACKEND == "postgresql")
                ph = "%s" if is_pg else "?"
                
                query = f"""
                    INSERT INTO system_logs (service_name, level, message)
                    VALUES ({ph}, {ph}, {ph})
                """
                cursor.execute(query, (self.service_name, level, log_entry))
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()
                
        except Exception:
            self.handleError(record)

def setup_db_logging(logger_name=None, service_name='worker'):
    """Logger'a DB handler'ı ekle"""
    handler = DBLoggingHandler(service_name=service_name)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger() # Root logger
        
    logger.addHandler(handler)
    return logger
