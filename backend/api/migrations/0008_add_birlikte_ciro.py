from django.db import migrations


def add_column(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = 'otomatikkampanyaonerileri'
                AND column_name = 'birlikte_ciro'
            )
        """)
        if not cursor.fetchone()[0]:
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                ADD COLUMN birlikte_ciro NUMERIC(15,2)
            """)


def remove_column(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE otomatikkampanyaonerileri
            DROP COLUMN IF EXISTS birlikte_ciro
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_unique_constraint_kampanya'),
    ]

    operations = [
        migrations.RunPython(add_column, remove_column),
    ]
