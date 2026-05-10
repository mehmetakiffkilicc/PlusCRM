"""
Create brandsummary table for fast brand report filtering.
"""
from django.db import migrations, connection
import sqlite3

def create_brandsummary_table(apps, schema_editor):
    with connection.cursor() as cursor:
        # Check if table already exists
        if connection.vendor == 'sqlite':
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='brandsummary'")
            if cursor.fetchone():
                return
        
        # Create table
        real_t = "DOUBLE PRECISION" if connection.vendor == "postgresql" else "REAL"
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS brandsummary (
                brand_id INTEGER,
                brand_name TEXT,
                year INTEGER,
                month INTEGER,
                region TEXT,
                customer_type TEXT,
                segment TEXT,
                approval_status TEXT,
                category_id INTEGER,
                category_main TEXT,
                category_sub1 TEXT,
                category_sub2 TEXT,
                total_sales {real_t},
                total_units {real_t},
                customer_count INTEGER,
                brand_name_norm TEXT,
                region_norm TEXT,
                customer_type_norm TEXT,
                approval_status_norm TEXT,
                segment_norm TEXT,
                category_norm TEXT,
                category_sub1_norm TEXT,
                category_sub2_norm TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_main ON brandsummary(year, month)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bs_dims ON brandsummary(region_norm, customer_type_norm, category_norm, brand_name_norm)")
        
        # Populate table with initial data (run sync logic)
        if connection.vendor == 'sqlite':
            # For SQLite, we can run the sync logic here
            try:
                from django.conf import settings
                import os
                
                # Get the sync_worker path
                sync_path = os.path.join(settings.BASE_DIR, '..', 'sync_worker')
                if not os.path.exists(sync_path):
                    sync_path = os.path.join(settings.BASE_DIR, 'sync_worker')
                
                if os.path.exists(sync_path):
                    import sys
                    sys.path.insert(0, sync_path)
                    from sync_summary import update_brand_summary
                    
                    # Get database path
                    db_path = settings.DATABASES['default']['NAME']
                    if not os.path.isabs(db_path):
                        db_path = os.path.join(settings.BASE_DIR, db_path)
                    
                    conn = sqlite3.connect(db_path)
                    update_brand_summary(conn)
                    conn.close()
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not populate brandsummary during migration: {e}")

def drop_brandsummary_table(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS brandsummary")

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_alter_aisession_model_name'),
    ]

    operations = [
        migrations.RunPython(create_brandsummary_table, reverse_code=drop_brandsummary_table),
    ]
