"""
Kategori Analiz Önbellek Yenileme Scripti
==========================================
Bu script, kategori_analiz_ozet tablosunu doldurmak için
tüm kategorilerin analitik verilerini önceden hesaplar.

Kullanım:
    python refresh_category_cache.py

Opsiyonel:
    python refresh_category_cache.py --level ana
    python refresh_category_cache.py --level alt1
    python refresh_category_cache.py --level alt2
    python refresh_category_cache.py --category "Elektronik"
"""

import psycopg2
import psycopg2.extras
import json
import sys
import argparse
import logging
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def get_connection():
    from decouple import config
    db_url = config("DATABASE_URL", default=config("POSTGRES_URL", default=None))
    if not db_url:
        raise RuntimeError("DATABASE_URL or POSTGRES_URL env var required")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    _opts = (
        '-c statement_timeout=300000 '
        '-c work_mem=8MB '
        '-c maintenance_work_mem=64MB '
        '-c temp_file_limit=1GB '
        '-c idle_in_transaction_session_timeout=60000'
    )
    return psycopg2.connect(db_url, connect_timeout=30, options=_opts)


def get_dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ---------------------------------------------------------------------------
# Per-category analytics helpers
# ---------------------------------------------------------------------------

def compute_kpis(cursor, cat_ids):
    placeholders = ','.join(['%s'] * len(cat_ids))
    cursor.execute(f"""
        SELECT
            SUM(tutar)                               AS total_revenue,
            COUNT(DISTINCT fis_no)                   AS total_receipts,
            COUNT(DISTINCT musteri_id)               AS total_customers,
            SUM(miktar)                              AS total_quantity,
            SUM(tutar) / NULLIF(SUM(miktar), 0)      AS avg_price
        FROM satislar
        WHERE kategori_id IN ({placeholders})
    """, cat_ids)
    row = cursor.fetchone()
    return dict(row) if row else {}


def compute_trends(cursor, cat_ids):
    placeholders = ','.join(['%s'] * len(cat_ids))
    cursor.execute(f"""
        SELECT
            TO_CHAR(DATE_TRUNC('month', tarih), 'YYYY-MM') AS month,
            SUM(tutar)  AS revenue,
            SUM(miktar) AS quantity
        FROM satislar
        WHERE kategori_id IN ({placeholders})
        GROUP BY DATE_TRUNC('month', tarih)
        ORDER BY DATE_TRUNC('month', tarih) DESC
        LIMIT 12
    """, cat_ids)
    return [dict(row) for row in cursor.fetchall()]


def compute_top_products(cursor, cat_ids):
    placeholders = ','.join(['%s'] * len(cat_ids))
    cursor.execute(f"""
        SELECT
            u.id                            AS product_id,
            u.ad                            AS product_name,
            SUM(s.tutar)                    AS revenue,
            SUM(s.miktar)                   AS quantity,
            COUNT(DISTINCT s.musteri_id)    AS customer_count,
            COUNT(DISTINCT s.fis_no)        AS receipt_count
        FROM satislar s
        JOIN urunler u ON s.urun_id = u.id
        WHERE s.kategori_id IN ({placeholders})
        GROUP BY u.id, u.ad
        ORDER BY revenue DESC
        LIMIT 10
    """, cat_ids)
    return [dict(row) for row in cursor.fetchall()]


def compute_rfm(cursor, cat_ids):
    placeholders = ','.join(['%s'] * len(cat_ids))
    cursor.execute(f"""
        SELECT
            m.rfm_segment   AS segment,
            COUNT(DISTINCT s.musteri_id) AS count
        FROM satislar s
        JOIN musteriler m ON s.musteri_id = m.id
        WHERE s.kategori_id IN ({placeholders})
          AND m.rfm_segment IS NOT NULL
        GROUP BY m.rfm_segment
    """, cat_ids)
    return [dict(row) for row in cursor.fetchall()]


def compute_brand_trends(cursor, cat_ids, trends):
    """Marka pazar payı trendi — category monthly revenue'ya göre normalize."""
    placeholders = ','.join(['%s'] * len(cat_ids))
    cursor.execute(f"""
        SELECT
            m.ad AS name,
            TO_CHAR(DATE_TRUNC('month', s.tarih), 'YYYY-MM') AS month,
            SUM(s.tutar) AS b_rev
        FROM satislar s
        JOIN markalar m ON s.marka_id = m.id
        WHERE s.kategori_id IN ({placeholders})
        GROUP BY m.ad, DATE_TRUNC('month', s.tarih)
        ORDER BY DATE_TRUNC('month', s.tarih) DESC
    """, cat_ids)

    raw_trends = [dict(row) for row in cursor.fetchall()]
    brand_map = defaultdict(list)
    for row in raw_trends:
        brand_map[row['name']].append({'month': row['month'], 'b_rev': row['b_rev']})

    # trends listesi: [{month, revenue, ...}]
    cat_monthly_rev = {}
    for t in trends:
        m = t.get('month')
        r = t.get('revenue', 0)
        if m:
            cat_monthly_rev[m] = float(r) if r is not None else 0

    brand_trends = []
    for b_name, data in brand_map.items():
        shares = []
        total_b_rev = 0
        for r in data:
            m = r['month']
            b_rev = float(r['b_rev']) if r['b_rev'] is not None else 0
            total_b_rev += b_rev
            c_rev = cat_monthly_rev.get(m, 0)
            share = (b_rev / c_rev * 100) if c_rev > 0 else 0
            shares.append({'month': m, 'share': round(share, 2)})

        brand_trends.append({'name': b_name, 'data': shares, 'total_rev': total_b_rev})

    brand_trends.sort(key=lambda x: x['total_rev'], reverse=True)
    return brand_trends[:50]


def compute_brand_customer(cursor, cat_ids, total_customers):
    placeholders = ','.join(['%s'] * len(cat_ids))
    cursor.execute(f"""
        SELECT
            m.ad AS name,
            COUNT(DISTINCT s.musteri_id) AS customer_count
        FROM satislar s
        JOIN markalar m ON s.marka_id = m.id
        WHERE s.kategori_id IN ({placeholders})
        GROUP BY m.ad
        ORDER BY customer_count DESC
        LIMIT 50
    """, cat_ids)
    raw = [dict(row) for row in cursor.fetchall()]
    result = []
    for r in raw:
        c_count = r['customer_count']
        share = (c_count / total_customers * 100) if total_customers and total_customers > 0 else 0
        result.append({
            'name': r['name'],
            'count': c_count,
            'share': round(share, 2),
        })
    return result


def compute_comparison(cursor, cat_ids, level, category_name, kpis):
    """
    Karşılaştırmalı analiz: parent seviyesindeki kardeş kategoriler ve
    pazar payı hesabı.
    """
    comparison = {
        'marketShare': 0,
        'parentName': None,
        'levelLabel': (
            'Ana Kategori' if level == 'ana'
            else ('Alt Kategori 1' if level == 'alt1' else 'Alt Kategori 2')
        ),
        'benchmarks': {},
        'siblings': [],
    }

    try:
        cursor.execute(
            "SELECT ana, alt1, alt2 FROM kategoriler WHERE id = %s",
            (cat_ids[0],),
        )
        hierarchy_row = cursor.fetchone()
        if not hierarchy_row:
            return comparison

        hierarchy = dict(hierarchy_row)

        parent_level = None
        parent_name = None
        if level == 'alt2':
            parent_level = 'alt1'
            parent_name = hierarchy.get('alt1')
        elif level == 'alt1':
            parent_level = 'ana'
            parent_name = hierarchy.get('ana')

        if not parent_name or not parent_level:
            return comparison

        cursor.execute(
            f"SELECT id FROM kategoriler WHERE {parent_level} = %s",
            (parent_name,),
        )
        p_cat_ids = [r['id'] for r in cursor.fetchall()]

        if not p_cat_ids:
            return comparison

        p_ph = ','.join(['%s'] * len(p_cat_ids))
        cursor.execute(f"""
            SELECT
                SUM(tutar) AS rev,
                COUNT(DISTINCT musteri_id) AS cust,
                SUM(tutar) / NULLIF(SUM(miktar), 0) AS avg_price
            FROM satislar
            WHERE kategori_id IN ({p_ph})
        """, p_cat_ids)
        p_row = cursor.fetchone()

        if p_row:
            p_metrics = dict(p_row)
            if p_metrics.get('rev'):
                total_rev = kpis.get('total_revenue') or 0
                comparison['marketShare'] = (float(total_rev) / float(p_metrics['rev'])) * 100
                comparison['parentName'] = parent_name
                comparison['benchmarks'] = {
                    'parentRevenue': float(p_metrics['rev']),
                    'parentAvgPrice': float(p_metrics['avg_price']) if p_metrics.get('avg_price') else None,
                }

        cursor.execute(f"""
            SELECT k.{level} AS name, SUM(s.tutar) AS revenue
            FROM satislar s
            JOIN kategoriler k ON s.kategori_id = k.id
            WHERE k.{parent_level} = %s AND k.{level} IS NOT NULL
            GROUP BY k.{level}
            ORDER BY revenue DESC
            LIMIT 6
        """, (parent_name,))
        comparison['siblings'] = [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logger.warning(f"  Comparison error (non-fatal): {e}")

    return comparison


# ---------------------------------------------------------------------------
# JSON serialization helper — handles Decimal and date types
# ---------------------------------------------------------------------------

def safe_json(obj):
    import decimal
    import datetime as dt

    class _Enc(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            if isinstance(o, (dt.date, dt.datetime)):
                return o.isoformat()
            return super().default(o)

    return json.dumps(obj, cls=_Enc, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_category(cursor, category_name, level):
    """
    Bir kategori için tüm analitik verileri hesaplar ve
    kategori_analiz_ozet tablosuna kaydeder.
    """
    # Kategori ID'lerini al
    cursor.execute(
        f"SELECT id FROM kategoriler WHERE {level} = %s",
        (category_name,),
    )
    cat_ids = [row['id'] for row in cursor.fetchall()]

    if not cat_ids:
        logger.warning(f"  No IDs found for {category_name} ({level}) — skipping")
        return False

    kpis = compute_kpis(cursor, cat_ids)
    trends = compute_trends(cursor, cat_ids)
    top_products = compute_top_products(cursor, cat_ids)
    rfm = compute_rfm(cursor, cat_ids)
    brand_trends = compute_brand_trends(cursor, cat_ids, trends)
    total_customers = kpis.get('total_customers') or 0
    brand_customer = compute_brand_customer(cursor, cat_ids, total_customers)
    comparison = compute_comparison(cursor, cat_ids, level, category_name, kpis)

    cursor.execute("""
        INSERT INTO kategori_analiz_ozet
            (kategori_adi, level, total_revenue, total_receipts, total_customers,
             total_quantity, avg_price, trends_json, top_products_json, rfm_json,
             brand_trends_json, brand_customer_json, comparison_json, guncelleme_tarihi)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (kategori_adi, level) DO UPDATE SET
            total_revenue      = EXCLUDED.total_revenue,
            total_receipts     = EXCLUDED.total_receipts,
            total_customers    = EXCLUDED.total_customers,
            total_quantity     = EXCLUDED.total_quantity,
            avg_price          = EXCLUDED.avg_price,
            trends_json        = EXCLUDED.trends_json,
            top_products_json  = EXCLUDED.top_products_json,
            rfm_json           = EXCLUDED.rfm_json,
            brand_trends_json  = EXCLUDED.brand_trends_json,
            brand_customer_json = EXCLUDED.brand_customer_json,
            comparison_json    = EXCLUDED.comparison_json,
            guncelleme_tarihi  = EXCLUDED.guncelleme_tarihi
    """, (
        category_name,
        level,
        kpis.get('total_revenue'),
        kpis.get('total_receipts'),
        kpis.get('total_customers'),
        kpis.get('total_quantity'),
        kpis.get('avg_price'),
        safe_json(trends),
        safe_json(top_products),
        safe_json(rfm),
        safe_json(brand_trends),
        safe_json(brand_customer),
        safe_json(comparison),
        datetime.now(),
    ))
    return True


def collect_categories(cursor, filter_level=None, filter_category=None):
    """
    Veritabanındaki tüm (kategori_adi, level) çiftlerini toplar.
    Sıra: önce ana, sonra alt1, sonra alt2.
    """
    categories = []

    levels_to_process = ['ana', 'alt1', 'alt2']
    if filter_level:
        if filter_level not in levels_to_process:
            logger.error(f"Geçersiz level: {filter_level}. Geçerli değerler: ana, alt1, alt2")
            return []
        levels_to_process = [filter_level]

    for lvl in levels_to_process:
        cursor.execute(f"SELECT DISTINCT {lvl} FROM kategoriler WHERE {lvl} IS NOT NULL")
        names = [row[lvl] for row in cursor.fetchall()]

        if filter_category:
            names = [n for n in names if n == filter_category]

        for name in sorted(names):
            categories.append((name, lvl))

    return categories


def main():
    parser = argparse.ArgumentParser(
        description='Kategori analiz önbelleğini yeniler.'
    )
    parser.add_argument(
        '--level',
        choices=['ana', 'alt1', 'alt2'],
        help='Sadece bu seviyeyi işle',
    )
    parser.add_argument(
        '--category',
        help='Sadece bu kategoriyi işle (tam ad)',
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Kaç kategoride bir commit yapılsın (varsayılan: 50)',
    )
    args = parser.parse_args()

    logger.info("Veritabanına bağlanılıyor...")
    conn = get_connection()
    cursor = get_dict_cursor(conn)
    logger.info("Bağlantı kuruldu.")

    # Kategori listesini topla
    logger.info("Kategoriler listeleniyor...")
    categories = collect_categories(cursor, args.level, args.category)
    total = len(categories)
    cursor.close()
    conn.close()

    if total == 0:
        logger.warning("İşlenecek kategori bulunamadı.")
        return

    logger.info(f"Toplam {total} kategori işlenecek.")

    processed = 0
    skipped = 0
    errors = 0
    batch_count = 0

    # Her batch için yeni bağlantı aç
    conn = get_connection()
    cursor = get_dict_cursor(conn)

    for idx, (cat_name, level) in enumerate(categories, start=1):
        print(f"İşleniyor {idx}/{total}: {cat_name} ({level})", flush=True)

        try:
            success = process_category(cursor, cat_name, level)
            if success:
                processed += 1
                batch_count += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1
            logger.error(f"  HATA — {cat_name} ({level}): {e}")
            # Bağlantıyı yenile
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            try:
                conn = get_connection()
                cursor = get_dict_cursor(conn)
            except Exception as reconnect_err:
                logger.error(f"  Yeniden bağlanma hatası: {reconnect_err}")
            continue

        # Toplu commit
        if batch_count >= args.batch_size:
            try:
                conn.commit()
                logger.info(f"  Commit: {batch_count} kayıt yazıldı.")
            except Exception as commit_err:
                logger.error(f"  Commit hatası: {commit_err}")
                try:
                    conn.rollback()
                except Exception:
                    pass
            batch_count = 0
            # Commit sonrası bağlantıyı yenile (uzun süreli bağlantı kopmaları için)
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass
            conn = get_connection()
            cursor = get_dict_cursor(conn)

    # Kalan kayıtları commit et
    if batch_count > 0:
        try:
            conn.commit()
            logger.info(f"  Son commit: {batch_count} kayıt yazıldı.")
        except Exception as commit_err:
            logger.error(f"  Son commit hatası: {commit_err}")
            try:
                conn.rollback()
            except Exception:
                pass

    try:
        cursor.close()
        conn.close()
    except Exception:
        pass

    print()
    print("=" * 60)
    print(f"Tamamlandı!")
    print(f"  Toplam kategori   : {total}")
    print(f"  Başarıyla işlenen : {processed}")
    print(f"  Atlandı           : {skipped}")
    print(f"  Hata              : {errors}")
    print("=" * 60)


if __name__ == '__main__':
    main()
