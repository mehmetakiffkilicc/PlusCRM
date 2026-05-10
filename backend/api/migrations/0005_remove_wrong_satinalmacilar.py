from django.db import migrations


def migrate_satinalmacilar(apps, schema_editor):
    # Yanlış isimleri sil (tablo adına göre önce hangisi var kontrol et)
    with schema_editor.connection.cursor() as cursor:
        # Önce satinalmacilar tablosu var mı kontrol et
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'satinalmacilar'
            )
        """)
        has_old_table = cursor.fetchone()[0]

        # kategori_yoneticileri tablosu var mı kontrol et
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'kategori_yoneticileri'
            )
        """)
        has_new_table = cursor.fetchone()[0]

        if has_old_table and not has_new_table:
            # Tabloyu yeniden adlandır
            cursor.execute("ALTER TABLE satinalmacilar RENAME TO kategori_yoneticileri")

        # Yanlış isimleri temizle
        if has_new_table or has_old_table:
            target = 'kategori_yoneticileri' if (has_new_table or has_old_table) else None
            if target:
                cursor.execute(
                    f"DELETE FROM {target} WHERE ad IN ('Ahmet Yılmaz', 'Ayşe Kaya', 'Mehmet Demir')"
                )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_dashboard_created_at_alter_dashboard_name_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_satinalmacilar, migrations.RunPython.noop),
    ]
