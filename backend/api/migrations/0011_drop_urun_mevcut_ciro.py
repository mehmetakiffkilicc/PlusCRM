from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_add_urun_ciro_roi'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE otomatikkampanyaonerileri
                DROP COLUMN IF EXISTS urun_mevcut_ciro;
                ALTER TABLE otomatikkampanyaonerileri
                DROP COLUMN IF EXISTS urun_roi;
            """,
            reverse_sql="""
                ALTER TABLE otomatikkampanyaonerileri
                ADD COLUMN IF NOT EXISTS urun_mevcut_ciro NUMERIC(15,2);
                ALTER TABLE otomatikkampanyaonerileri
                ADD COLUMN IF NOT EXISTS urun_roi NUMERIC(8,2);
            """
        ),
    ]
