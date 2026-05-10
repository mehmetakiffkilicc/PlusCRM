from django.db import migrations


def rename_column(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # Sütun zaten potansiyel_ciro adıyla var mı kontrol et
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'otomatikkampanyaonerileri'
                AND column_name = 'potansiyel_ciro'
            )
        """)
        already_exists = cursor.fetchone()[0]

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'otomatikkampanyaonerileri'
                AND column_name = 'tahmini_ciro'
            )
        """)
        old_exists = cursor.fetchone()[0]

        if old_exists and not already_exists:
            # Yeni sütun ekle, veriyi kopyala, eskisini sil
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                ADD COLUMN potansiyel_ciro NUMERIC(15,2)
            """)
            cursor.execute("""
                UPDATE otomatikkampanyaonerileri
                SET potansiyel_ciro = tahmini_ciro
            """)
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                DROP COLUMN tahmini_ciro
            """)
        elif old_exists and already_exists:
            # Her ikisi de varsa veriyi kopyala ve eskisini sil
            cursor.execute("""
                UPDATE otomatikkampanyaonerileri
                SET potansiyel_ciro = tahmini_ciro
                WHERE potansiyel_ciro IS NULL
            """)
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                DROP COLUMN tahmini_ciro
            """)


def reverse_rename(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'otomatikkampanyaonerileri'
                AND column_name = 'tahmini_ciro'
            )
        """)
        old_exists = cursor.fetchone()[0]

        if not old_exists:
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                ADD COLUMN tahmini_ciro NUMERIC(15,2)
            """)
            cursor.execute("""
                UPDATE otomatikkampanyaonerileri
                SET tahmini_ciro = potansiyel_ciro
            """)
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                DROP COLUMN potansiyel_ciro
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_remove_wrong_satinalmacilar'),
    ]

    operations = [
        migrations.RunPython(rename_column, reverse_rename),
    ]
