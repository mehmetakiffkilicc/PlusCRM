from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Kampanya önerilerini yeniden üretir'

    def handle(self, *args, **options):
        try:
            from database.campaign_manager import kampanya_onerileri_uret
            self.stdout.write('Kampanya önerileri üretiliyor...')
            kampanya_onerileri_uret()
            self.stdout.write(self.style.SUCCESS('Kampanya önerileri başarıyla güncellendi.'))
        except Exception as e:
            self.stderr.write(f'Hata: {e}')
            raise
