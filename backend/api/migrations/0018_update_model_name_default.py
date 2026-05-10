from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_aidashboard'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aisession',
            name='model_name',
            field=models.CharField(default='gemini-2.5-flash', max_length=100),
        ),
    ]
