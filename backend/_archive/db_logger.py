import logging
import threading
import time
from . import db_engine

class DBLoggingHandler(logging.Handler):
    """
    Sistem loglarını veritabanındaki system_logs tablosuna yazar.
    Bağlantı havuzunu tüketmemek için logları batch olarak yazar.
    """
    def __init__(self, service_name='backend'):
        super().__init__()
        self.service_name = service_name
        self._table_ensured = False
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self._flush_interval = 5  # seconds
        self._max_buffer = 50
        self._start_flush_thread()

    def _start_flush_thread(self):
        """Background thread to flush log buffer periodically."""
        t = threading.Thread(target=self._flush_loop, daemon=True)
        t.start()

    def _flush_loop(self):
        while True:
            time.sleep(self._flush_interval)
            self._flush()

    def _ensure_table(self):
        """Tablonun var olduğundan emin olur."""
        try:
            conn = db_engine.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id SERIAL PRIMARY KEY,
                        service_name VARCHAR(50),
                        level VARCHAR(20),
                        message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)")
                conn.commit()
            finally:
                db_engine.release_connection(conn)
        except Exception:
            pass

    def _flush(self):
        """Flush buffered logs to DB in a single connection."""
        with self._buffer_lock:
            if not self._buffer:
                return
            entries = self._buffer[:]
            self._buffer.clear()

        if not self._table_ensured:
            self._ensure_table()
            self._table_ensured = True

        try:
            conn = db_engine.get_connection()
            try:
                cursor = conn.cursor()
                ph = db_engine.ph()
                query = f"""
                    INSERT INTO system_logs (service_name, level, message)
                    VALUES ({ph}, {ph}, {ph})
                """
                for service, level, message in entries:
                    cursor.execute(query, (service, level, message))
                conn.commit()
            except Exception:
                pass
            finally:
                db_engine.release_connection(conn)
        except Exception:
            pass

    def emit(self, record):
        try:
            log_entry = self.format(record)
            level = record.levelname
            with self._buffer_lock:
                self._buffer.append((self.service_name, level, log_entry))
                if len(self._buffer) >= self._max_buffer:
                    # Flush inline when buffer is full
                    entries = self._buffer[:]
                    self._buffer.clear()
            # Don't flush inline for every log - let the background thread handle it
        except Exception:
            self.handleError(record)
