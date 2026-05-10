import os
import sys
import django
from django.db import connection

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def normalize():
    print("Starting DB normalization...")
    with connection.cursor() as cursor:
        # 1. Onay Durumu - Fix broken characters and uppercase
        print("Normalizing onay_durumu in musteriler...")
        cursor.execute("UPDATE musteriler SET onay_durumu = 'ONAYLI' WHERE onay_durumu LIKE 'Onayl%' OR onay_durumu = 'ONAYLI'")
        cursor.execute("UPDATE musteriler SET onay_durumu = 'ONAYSIZ' WHERE onay_durumu = 'ONAYSIZ' OR onay_durumu = 'Onaysız'")
        print(f"Rows affected (onay_durumu): {cursor.rowcount}")

        # 2. Tip - Uppercase and standardize
        print("Normalizing tip in musteriler...")
        cursor.execute("UPDATE musteriler SET tip = 'BİREYSEL' WHERE UPPER(tip) = 'BIREYSEL' OR tip = 'Bireysel'")
        cursor.execute("UPDATE musteriler SET tip = 'KURUMSAL' WHERE UPPER(tip) = 'KURUMSAL' OR tip = 'Kurumsal'")
        print(f"Rows affected (tip): {cursor.rowcount}")

        # 3. Bolge - Fix broken characters
        print("Normalizing bolge in magazalar...")
        # CHR(65533) is the replacement character \ufffd
        cursor.execute("UPDATE magazalar SET bolge = REPLACE(bolge, CHR(65533), 'ö') WHERE bolge LIKE '%\ufffd%'")
        print(f"Rows affected (bolge): {cursor.rowcount}")

        # 4. Cleanup nulls for essential filters
        cursor.execute("UPDATE musteriler SET tip = 'BİREYSEL' WHERE tip IS NULL")
        cursor.execute("UPDATE musteriler SET onay_durumu = 'ONAYLI' WHERE onay_durumu IS NULL")
        
        connection.commit()
    print("Normalization complete.")

if __name__ == "__main__":
    normalize()
