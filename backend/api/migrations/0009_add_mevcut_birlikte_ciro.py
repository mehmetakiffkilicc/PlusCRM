from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_add_birlikte_ciro'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE otomatikkampanyaonerileri
                ADD COLUMN IF NOT EXISTS mevcut_birlikte_ciro NUMERIC(15,2);
            """,
            reverse_sql="""
                ALTER TABLE otomatikkampanyaonerileri
                DROP COLUMN IF EXISTS mevcut_birlikte_ciro;
            """
        ),
    ]
