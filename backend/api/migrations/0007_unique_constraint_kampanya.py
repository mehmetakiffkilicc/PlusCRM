from django.db import migrations


def add_unique_constraint(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        # 1. Önce mevcut duplicate kayıtları temizle
        # Aynı (kaynak_kategori_ad, kategori_id, kampanya_tipi) için en yeni kaydı tut, eskilerini sil
        cursor.execute("""
            DELETE FROM otomatikkampanyaonerileri a
            USING otomatikkampanyaonerileri b
            WHERE a.oneri_id < b.oneri_id
              AND COALESCE(a.kaynak_kategori_ad, '') = COALESCE(b.kaynak_kategori_ad, '')
              AND COALESCE(a.kategori_id::text, '') = COALESCE(b.kategori_id::text, '')
              AND a.kampanya_tipi = b.kampanya_tipi
              AND a.oneri_durumu = 'Bekliyor'
              AND b.oneri_durumu = 'Bekliyor'
        """)

        # 2. Constraint zaten var mı kontrol et
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_constraint
                WHERE conname = 'uq_kampanya_kaynak_hedef_tip'
            )
        """)
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute("""
                ALTER TABLE otomatikkampanyaonerileri
                ADD CONSTRAINT uq_kampanya_kaynak_hedef_tip
                UNIQUE (kaynak_kategori_ad, kategori_id, kampanya_tipi)
            """)


def remove_unique_constraint(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE otomatikkampanyaonerileri
            DROP CONSTRAINT IF EXISTS uq_kampanya_kaynak_hedef_tip
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_rename_tahmini_ciro_to_potansiyel_ciro'),
    ]

    operations = [
        migrations.RunPython(add_unique_constraint, remove_unique_constraint),
    ]
