"""
M_Crm'de hangi kombinasyonun unique oldugunu kontrol eder.
Backfill icin dogru join key'i bulmak amacli.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from decouple import config
import pyodbc

def connect_sql():
    available = pyodbc.drivers()
    driver = next(('{' + d + '}' for d in available if 'SQL Server' in d), '{SQL Server}')
    return pyodbc.connect(
        f"DRIVER={driver};SERVER={config('SQL_SERVER','100.109.143.127')},{config('SQL_PORT','14330')};"
        f"DATABASE={config('SQL_DATABASE','DerinSISShow')};UID={config('SQL_USERNAME','sa2')};"
        f"PWD={config('SQL_PASSWORD','1478236950Mm..')};TrustServerCertificate=yes;Connection Timeout=30"
    )

conn = connect_sql()
cur = conn.cursor()

print("=== 1. fis+stkKod+kmp_sayisi unique mi? ===")
cur.execute("""
SELECT COUNT(*) as toplam,
       COUNT(DISTINCT CAST([PosDocumentId] AS VARCHAR(50)) + '|' + ISNULL([stkKod],'') + '|' + CAST(ISNULL([kmp_sayısı],-1) AS VARCHAR(20))) as unique_combo
FROM M_Crm WITH (NOLOCK)
WHERE [TARİH] >= '2025-01-01' AND [TARİH] < '2025-02-01'
""")
r = cur.fetchone()
print(f"  toplam={r[0]:,}  unique_combo={r[1]:,}  esit_mi={r[0]==r[1]}")

print("\n=== 2. Kampanyasiz satirlarda ayni fis+stkKod birden fazla var mi? ===")
cur.execute("""
SELECT COUNT(*) as cift_urun_fis_sayisi
FROM (
    SELECT [PosDocumentId], [stkKod]
    FROM M_Crm WITH (NOLOCK)
    WHERE [TARİH] >= '2025-01-01' AND [TARİH] < '2025-02-01'
    AND [kmp_sayısı] IS NULL
    GROUP BY [PosDocumentId], [stkKod]
    HAVING COUNT(*) > 1
) t
""")
print(f"  {cur.fetchone()[0]:,} adet fis+stkKod kombinasyonu birden fazla kez gecmiyor (kampanyasiz)")

print("\n=== 3. fis+stkKod+Miktar+BelgeToplami unique mi? (kampanyasiz) ===")
cur.execute("""
SELECT COUNT(*) as toplam,
       COUNT(DISTINCT CAST([PosDocumentId] AS VARCHAR(50)) + '|' + ISNULL([stkKod],'') + '|' +
             CAST(ISNULL([Miktar],0) AS VARCHAR(20)) + '|' + CAST(ISNULL([BelgeToplami],0) AS VARCHAR(20))) as unique_combo
FROM M_Crm WITH (NOLOCK)
WHERE [TARİH] >= '2025-01-01' AND [TARİH] < '2025-02-01'
AND [kmp_sayısı] IS NULL
""")
r = cur.fetchone()
print(f"  toplam={r[0]:,}  unique_combo={r[1]:,}  esit_mi={r[0]==r[1]}")

print("\n=== 4. Ornek: cift gecen fis+stkKod (kampanyasiz) ===")
cur.execute("""
SELECT TOP 12 [PosDocumentId], [stkKod], [kmp_sayısı], [Satış Tutarı], [Miktar], [BelgeToplami], [BelgeIndirimToplami]
FROM M_Crm WITH (NOLOCK)
WHERE [TARİH] >= '2025-01-01' AND [TARİH] < '2025-02-01'
AND [kmp_sayısı] IS NULL
AND [PosDocumentId] IN (
    SELECT TOP 3 [PosDocumentId]
    FROM M_Crm WITH (NOLOCK)
    WHERE [TARİH] >= '2025-01-01' AND [TARİH] < '2025-02-01'
    AND [kmp_sayısı] IS NULL
    GROUP BY [PosDocumentId], [stkKod]
    HAVING COUNT(*) > 1
)
ORDER BY [PosDocumentId], [stkKod]
""")
rows = cur.fetchall()
if rows:
    print(f"  {'FisNo':<15} {'stkKod':<15} {'kmp':<8} {'Tutar':<10} {'Miktar':<8} {'BelgeToplami':<14} {'BelgeIndirim'}")
    for r in rows:
        print(f"  {str(r[0]):<15} {str(r[1]):<15} {str(r[2]):<8} {str(r[3]):<10} {str(r[4]):<8} {str(r[5]):<14} {r[6]}")
else:
    print("  Hic ornek yok — ayni fis+stkKod birden fazla GECMIYOR (kampanyasiz)")

conn.close()
