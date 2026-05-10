"""
Performance indexes for high-cost full table scans.

satislar.tarih  — delta sync saatte bir bu sütunu WHERE ile sorgular (3M+ satır)
musteriler.tip  — SELECT DISTINCT tip her dashboard isteğinde (130K satır)
magazalar.bolge — SELECT DISTINCT bolge her dashboard isteğinde
"""
from django.db import migrations, connection


def add_indexes(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_satislar_tarih ON satislar (tarih DESC);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_musteriler_tip ON musteriler (tip) WHERE tip IS NOT NULL;"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_magazalar_bolge ON magazalar (bolge) WHERE bolge IS NOT NULL;"
        )


def remove_indexes(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS idx_satislar_tarih;")
        cursor.execute("DROP INDEX IF EXISTS idx_musteriler_tip;")
        cursor.execute("DROP INDEX IF EXISTS idx_magazalar_bolge;")


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_update_model_name_default'),
    ]

    operations = [
        migrations.RunPython(add_indexes, reverse_code=remove_indexes),
    ]
