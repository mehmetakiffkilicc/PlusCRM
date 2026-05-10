from django.db import migrations


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS kategori_analiz_ozet (
    id SERIAL PRIMARY KEY,
    kategori_adi TEXT NOT NULL,
    level TEXT NOT NULL,
    total_revenue NUMERIC(18,2),
    total_receipts INTEGER,
    total_customers INTEGER,
    total_quantity NUMERIC(15,2),
    avg_price NUMERIC(10,2),
    trends_json TEXT,
    top_products_json TEXT,
    rfm_json TEXT,
    brand_trends_json TEXT,
    brand_customer_json TEXT,
    comparison_json TEXT,
    guncelleme_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(kategori_adi, level)
);
CREATE INDEX IF NOT EXISTS idx_kategori_analiz_ozet_name_level ON kategori_analiz_ozet(kategori_adi, level);
"""

DROP_SQL = """
DROP INDEX IF EXISTS idx_kategori_analiz_ozet_name_level;
DROP TABLE IF EXISTS kategori_analiz_ozet;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_add_marka_ids'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_SQL,
            reverse_sql=DROP_SQL,
        ),
    ]
