import os
import psycopg2
from psycopg2 import pool
from pathlib import Path
from decouple import Config, RepositoryEnv, config as default_config
import logging

logger = logging.getLogger(__name__)

# Load .env explicitly from the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / '.env'

if env_path.exists():
    config = Config(RepositoryEnv(str(env_path)))
else:
    config = default_config

POSTGRES_URL = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
if POSTGRES_URL and POSTGRES_URL.startswith('postgres://'):
    POSTGRES_URL = POSTGRES_URL.replace('postgres://', 'postgresql://', 1)
# Default to postgresql if a PostgreSQL URL is present, otherwise default to sqlite
_default_backend = "postgresql" if POSTGRES_URL and ("postgresql://" in POSTGRES_URL or "postgres://" in POSTGRES_URL) else "sqlite"
DB_BACKEND = config("DB_BACKEND", default=_default_backend).split('#')[0].strip().lower()

# SQLite DB_PATH - dynamically calculated
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'database',
    'demo.sqlite3'
)

# PostgreSQL Connection Pool
_pg_pool = None

def get_pg_pool():
    global _pg_pool
    if _pg_pool is None and DB_BACKEND == "postgresql":
        try:
            # Using minconn=1 to avoid issues with concurrent connection establishment in some proxies
            _pool_max = int(config('DB_POOL_MAX', default='10'))
            # PostgreSQL session parametreleri — her bağlantıda RAM kullanımını sınırlar
            # work_mem=4MB: 10 bağlantı × 4MB = max 40MB sort/hash RAM
            # maintenance_work_mem=64MB: gece VACUUM/index build için
            # temp_file_limit=512MB: RAM taşarsa diske yazar, OOM engeller
            # idle_in_transaction_session_timeout=30s: boşta kalan tx bağlantıları kapatır
            _pg_options = (
                '-c statement_timeout=300000 '
                '-c work_mem=8MB '
                '-c maintenance_work_mem=64MB '
                '-c temp_file_limit=1024MB '
                '-c idle_in_transaction_session_timeout=60000'
            )
            _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                2, _pool_max, POSTGRES_URL,
                connect_timeout=15,
                options=_pg_options,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            logger.info(f"PostgreSQL connection pool initialized (min=2, max={_pool_max}). RAM optimized.")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL pool: {e}")
            raise e
    return _pg_pool

def get_connection():
    """Get a connection based on the configured backend, with retry on failure."""
    if DB_BACKEND == "postgresql":
        import time
        last_err = None
        for attempt in range(3):
            try:
                pool = get_pg_pool()
                if pool is None:
                    raise Exception("PostgreSQL pool is not initialized")
                conn = pool.getconn()
                # Clear any stale transaction state before returning
                try:
                    conn.rollback()
                except Exception:
                    pass
                # Verify connection is alive
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                except Exception:
                    # Connection is dead, close and get a new one
                    try:
                        pool.putconn(conn, close=True)
                    except Exception:
                        pass
                    raise Exception("Stale connection, retrying")
                return conn
            except Exception as e:
                last_err = e
                logger.warning(f"Connection attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        raise last_err
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def release_connection(conn):
    """Release a connection back to the pool."""
    if DB_BACKEND == "postgresql" and _pg_pool:
        try:
            # Always rollback before returning to pool to clear any aborted transaction state
            try:
                conn.rollback()
            except Exception:
                pass
            _pg_pool.putconn(conn)
        except:
            pass
    else:
        if hasattr(conn, 'close'):
            conn.close()

def placeholder():
    """Get the SQL parameter placeholder for current backend."""
    return '%s' if DB_BACKEND == 'postgresql' else '?'

def ph():
    """Shortcut for placeholder()."""
    return placeholder()

def get_dict_cursor(conn):
    """Get a dictionary-returning cursor for current backend."""
    if DB_BACKEND == 'postgresql':
        from psycopg2.extras import RealDictCursor
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()

def val(row, key, default=0):
    """Safely get a value from a row that could be dict (PostgreSQL) or sqlite3.Row or tuple."""
    if row is None:
        return default
        
    if isinstance(row, dict):
        # 1. Direct match (highest priority)
        if key in row:
            return row[key] if row[key] is not None else default
            
        # 2. Case-insensitive match (for cross-DB compatibility)
        low_key = key.lower()
        # Find if any key matches low_key (case-insensitive)
        for rk in row.keys():
            if rk.lower() == low_key:
                return row[rk] if row[rk] is not None else default
                
        # 3. Snake Case match (Common for PascalCase -> snake_case)
        # e.g. OneriID -> oneri_id, KampanyaTipi -> kampanya_tipi
        import re
        snake_key = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        if snake_key in row:
            return row[snake_key] if row[snake_key] is not None else default
        
        # 4. Check for case-insensitive snake_key too
        for rk in row.keys():
            if rk.lower() == snake_key:
                return row[rk] if row[rk] is not None else default

        # OneriID -> oneri_id (re.sub makes it oneri_i_d)
        if '_i_d' in snake_key:
            id_key = snake_key.replace('_i_d', '_id')
            for rk in row.keys():
                if rk.lower() == id_key:
                    return row[rk] if row[rk] is not None else default

        # 5. Concatenated lowercase match (e.g. UrunAdi -> urunadi, KategoriAdi -> kategoriadi)
        concat_key = key.replace('_', '').lower()
        for rk in row.keys():
            if rk.replace('_','').lower() == concat_key:
                return row[rk] if row[rk] is not None else default

        # 6. Special cases mapping
        specials = {
            'OneriID': 'oneri_id',
            'UrunAdi': 'urun_ad',
            'KategoriAdi': 'kategori_ad',
            'IkinciUrunAdi': 'ikinci_urun_ad',
            'HedefMusteriSayisi': 'hedef_musteri_sayisi',
            'OncelikSeviye': 'oncelik_seviye',
            'OneriDurumu': 'oneri_durumu',
            'KampanyaTipi': 'kampanya_tipi'
        }
        if key in specials:
            mapped = specials[key]
            for rk in row.keys():
                if rk.lower() == mapped.lower():
                    return row[rk] if row[rk] is not None else default
            
        return default
        
    try:
        # For sqlite3.Row or tuple
        if hasattr(row, 'keys'): # sqlite3.Row
            row_keys = [k.lower() for k in row.keys()]
            if key.lower() in row_keys:
                return row[key] if row[key] is not None else default
        return row[key] if row[key] is not None else default
    except (IndexError, KeyError, TypeError):
        return default

def fetchone_val(cursor, index_or_key, default=0):
    """Execute fetchone() and safely get a single value (works with both dict and tuple rows)."""
    row = cursor.fetchone()
    return val(row, index_or_key, default)

def adapt_query(query):
    """Convert SQLite-style ? placeholders to PostgreSQL %s if needed."""
    if DB_BACKEND == 'postgresql':
        return query.replace('?', '%s')
    return query

def strftime_expr(fmt, column):
    """Return the correct date formatting expression for current backend.
    Common fmt values: '%Y-%m' -> 'YYYY-MM', '%Y' -> 'YYYY', '%m' -> 'MM', '%w' -> day of week, '%Y-%W' -> year-week
    """
    if DB_BACKEND == 'postgresql':
        fmt_map = {
            '%Y-%m-%d': f"TO_CHAR({column}, 'YYYY-MM-DD')",
            '%Y-%m': f"TO_CHAR({column}, 'YYYY-MM')",
            '%Y': f"TO_CHAR({column}, 'YYYY')",
            '%m': f"TO_CHAR({column}, 'MM')",
            '%Y-%W': f"TO_CHAR({column}, 'IYYY-IW')",
        }
        if fmt in fmt_map:
            return fmt_map[fmt]
        if fmt == '%w':
            return f"EXTRACT(DOW FROM {column}::date)::integer"
        return f"TO_CHAR({column}, '{fmt}')"
    else:
        return f"strftime('{fmt}', {column})"

def date_expr(column):
    """Return date cast expression for current backend."""
    if DB_BACKEND == 'postgresql':
        return f"{column}::date"
    return f"date({column})"

def last_year_expr(column=None):
    """Return expression for 'last 365 days' relative to column or CURRENT_DATE."""
    return date_offset_expr(-365, column)

def date_offset_expr(days, column=None):
    """Return expression for 'column + days' or 'CURRENT_DATE + days'."""
    if DB_BACKEND == 'postgresql':
        base = column if column else "CURRENT_DATE"
        if days >= 0:
            return f"{base} + INTERVAL '{days} days'"
        else:
            return f"{base} - INTERVAL '{abs(days)} days'"
    else:
        base = column if column else "'now'"
        return f"date({base}, '{days:+} days')"

def col_date_add_expr(date_col, interval_col, multiplier=1):
    """Return expression for 'date_col + interval_col * multiplier days'."""
    if DB_BACKEND == 'postgresql':
        return f"({date_col} + ({interval_col} * {multiplier} || ' days')::interval)"
    else:
        # SQLite: date(col, '+' || ROUND(val * mult) || ' days')
        return f"date({date_col}, '+' || ROUND({interval_col} * {multiplier}) || ' days')"

def date_diff_days_expr(date1, date2):
    """Return expression for 'date1 - date2' in days."""
    if DB_BACKEND == 'postgresql':
        return f"({date1}::date - {date2}::date)"
    else:
        return f"(julianday({date1}) - julianday({date2}))"

def date_trunc_expr(unit, column):
    """Return correct date truncation syntax for current backend."""
    if DB_BACKEND == 'postgresql':
        return f"date_trunc('{unit}', {column})::date"
    else:
        if unit == 'week':
            # SQLite: Monday of the current week
            return f"date({column}, 'weekday 1', '-7 days')"
        elif unit == 'month':
            # SQLite: 1st of the month
            return f"date({column}, 'start of month')"
        elif unit == 'year':
            return f"date({column}, 'start of year')"
        return f"date({column})"

def insert_or_replace():
    """Return the correct upsert syntax prefix."""
    if DB_BACKEND == 'postgresql':
        return "INSERT INTO"
    return "INSERT OR REPLACE INTO"

def bolge_expr(column='bolge'):
    """Handle broken characters (\\ufffd) in bolge column across backends."""
    if DB_BACKEND == 'postgresql':
        return f"REPLACE({column}, CHR(65533), 'ö')"
    else:
        return f"REPLACE({column}, char(65533), 'ö')"

def execute_query(query, params=None, fetch=True):
    """Utility to execute a query and handle connection/cleanup."""
    conn = get_connection()
    try:
        if DB_BACKEND == "postgresql":
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
            
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
            return [dict(row) for row in result]
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Query error: {e}")
        if DB_BACKEND == "postgresql":
            conn.rollback()
        raise e
    finally:
        release_connection(conn)

def normalize_turkish_sql(column):
    """Return SQL fragment to normalize Turkish characters and lowercase for search."""
    if DB_BACKEND == 'postgresql':
        # Translate characters to normalized lower case
        # İ/I -> i, ş -> s, ğ -> g, ü -> u, ö -> o, ç -> c, ı -> i
        return f"translate(lower({column}), 'çğışıöü', 'cgisiou')"
    else:
        # SQLite: Custom collation or manual mapping needed, but we focus on PostgreSQL
        return f"lower({column})"

def normalize_turkish_py(text):
    """Normalize Turkish characters in a string for matching or search parameters."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    mapping = str.maketrans('çğışıöü', 'cgisiou')
    return text.translate(mapping)
