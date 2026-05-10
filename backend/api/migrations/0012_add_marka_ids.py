from django.db import migrations


def add_columns_and_populate(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # Kolon ekle
        cursor.execute("""
            ALTER TABLE otomatikkampanyaonerileri
            ADD COLUMN IF NOT EXISTS kaynak_marka_id INTEGER
        """)
        cursor.execute("""
            ALTER TABLE otomatikkampanyaonerileri
            ADD COLUMN IF NOT EXISTS hedef_marka_id INTEGER
        """)

        # kaynak_marka_id: kaynak_kategori_ad -> kategoriler -> urunler.marka_id (en yaygın marka)
        cursor.execute("""
            UPDATE otomatikkampanyaonerileri o
            SET kaynak_marka_id = (
                SELECT u.marka_id
                FROM urunler u
                JOIN kategoriler k ON k.id = u.kategori_id
                WHERE k.alt2 = o.kaynak_kategori_ad
                GROUP BY u.marka_id
                ORDER BY COUNT(*) DESC
                LIMIT 1
            )
            WHERE kaynak_marka_id IS NULL AND kaynak_kategori_ad IS NOT NULL
        """)

        # hedef_marka_id: kategori_ad -> kategoriler -> urunler.marka_id (en yaygın marka)
        cursor.execute("""
            UPDATE otomatikkampanyaonerileri o
            SET hedef_marka_id = (
                SELECT u.marka_id
                FROM urunler u
                JOIN kategoriler k ON k.id = u.kategori_id
                WHERE k.alt2 = o.kategori_ad
                GROUP BY u.marka_id
                ORDER BY COUNT(*) DESC
                LIMIT 1
            )
            WHERE hedef_marka_id IS NULL AND kategori_ad IS NOT NULL
        """)


def remove_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE otomatikkampanyaonerileri
            DROP COLUMN IF EXISTS kaynak_marka_id
        """)
        cursor.execute("""
            ALTER TABLE otomatikkampanyaonerileri
            DROP COLUMN IF EXISTS hedef_marka_id
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_drop_urun_mevcut_ciro'),
    ]

    operations = [
        migrations.RunPython(add_columns_and_populate, remove_columns),
    ]
