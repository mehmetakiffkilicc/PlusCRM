import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import ScheduledCampaign

class Command(BaseCommand):
    help = 'Zamanı gelmiş (bekleyen) kampanyaları otomatik olarak yürütür.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'[{timezone.now()}] Kampanya işleme motoru başlatıldı...'))
        
        # Zamanı gelmiş ve bekleyenleri bul
        pending_campaigns = ScheduledCampaign.objects.filter(
            status='pending',
            scheduled_at__lte=timezone.now()
        )
        
        count = pending_campaigns.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('İşlenecek kampanya bulunamadı.'))
            return

        self.stdout.write(self.style.SUCCESS(f'{count} adet kampanya işleniyor...'))
        
        for campaign in pending_campaigns:
            try:
                self.stdout.write(f'  - "{campaign.title}" (ID: {campaign.id}) yürütülüyor...')
                
                # Simülasyon: Burada gerçek gönderim servisi çağrılmalı
                # Örn: send_sms(campaign.segment, campaign.message)
                
                campaign.status = 'completed'
                campaign.save()
                
                self.stdout.write(self.style.SUCCESS(f'    [OK] Tamamlandı.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    [HATA] {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'İşlem tamamlandı. Toplam {count} kampanya güncellendi.'))
