import os
import django

# Django ortamını ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def fix_magazalar_encoding():
    with connection.cursor() as cursor:
        print("Bölge isimleri güncelleniyor...")
        # PostgreSQL için CHR(65533) kullanıyoruz
        cursor.execute("""
            UPDATE magazalar 
            SET bolge = REPLACE(bolge, CHR(65533), 'ö')
            WHERE bolge LIKE '%' || CHR(65533) || '%';
        """)
        updated_count = cursor.rowcount
        print(f"{updated_count} satır güncellendi.")

        # Mağaza isimlerini de kontrol et
        print("Mağaza isimleri kontrol ediliyor...")
        cursor.execute("""
            UPDATE magazalar 
            SET ad = REPLACE(ad, CHR(65533), 'ö')
            WHERE ad LIKE '%' || CHR(65533) || '%';
        """)
        updated_ad_count = cursor.rowcount
        print(f"{updated_ad_count} mağaza adı güncellendi.")

        # Onay durumu kontrolü
        print("Onay durumları kontrol ediliyor...")
        cursor.execute("""
            UPDATE daily_metrics_summary 
            SET onay_durumu = REPLACE(onay_durumu, CHR(65533), 'ı')
            WHERE onay_durumu LIKE '%' || CHR(65533) || '%';
        """)
        updated_onay_count = cursor.rowcount
        print(f"{updated_onay_count} onay durumu satırı güncellendi.")

if __name__ == "__main__":
    fix_magazalar_encoding()
