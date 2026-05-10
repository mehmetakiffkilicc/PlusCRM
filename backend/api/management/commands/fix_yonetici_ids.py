from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Mevcut tüm kampanya kayıtlarının yonetici_id sini kaynak kategoriye (kaynak_kategori_ad) göre düzeltir'

    def handle(self, *args, **options):
        self.stdout.write('Yonetici ID düzeltmesi başlıyor...')

        with connection.cursor() as cursor:
            # Önce mevcut durumu göster
            cursor.execute("""
                SELECT ky.ad, COUNT(*) as adet
                FROM otomatikkampanyaonerileri o
                LEFT JOIN kategori_yoneticileri ky ON o.yonetici_id = ky.id
                GROUP BY ky.ad
                ORDER BY adet DESC
            """)
            rows = cursor.fetchall()
            self.stdout.write('\nMevcut durum (güncelleme öncesi):')
            for row in rows:
                self.stdout.write(f'  {row[0] or "NULL"}: {row[1]} kayıt')

            # Güncelle
            cursor.execute("""
                UPDATE otomatikkampanyaonerileri
                SET yonetici_id = COALESCE(
                    (SELECT yonetici_id FROM kategoriler
                     WHERE alt2 = otomatikkampanyaonerileri.kaynak_kategori_ad
                       AND yonetici_id IS NOT NULL LIMIT 1),
                    (SELECT yonetici_id FROM kategoriler
                     WHERE id = otomatikkampanyaonerileri.kategori_id
                       AND yonetici_id IS NOT NULL LIMIT 1)
                )
            """)
            updated = cursor.rowcount

            # Sonuçları göster
            cursor.execute("""
                SELECT ky.ad, COUNT(*) as adet
                FROM otomatikkampanyaonerileri o
                LEFT JOIN kategori_yoneticileri ky ON o.yonetici_id = ky.id
                GROUP BY ky.ad
                ORDER BY adet DESC
            """)
            rows = cursor.fetchall()
            self.stdout.write(f'\nGüncellendi: {updated} kayıt')
            self.stdout.write('\nYeni durum (güncelleme sonrası):')
            for row in rows:
                self.stdout.write(f'  {row[0] or "NULL"}: {row[1]} kayıt')

        self.stdout.write(self.style.SUCCESS('\nTamamlandı!'))
