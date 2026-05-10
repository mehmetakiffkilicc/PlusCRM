import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api import db_engine

def explain_query():
    conn = db_engine.get_connection()
    cursor = db_engine.get_dict_cursor(conn)
    
    order = "m.rfm_segment ASC NULLS LAST, m.id DESC"
    
    query = f"""
        EXPLAIN ANALYZE
        SELECT 
            m.id, m.ad, m.rfm_segment,
            o.son_alisveris_tarihi, o.toplam_harcama, o.toplam_alisveris
        FROM musteriler m
        LEFT JOIN musteridetayozet o ON m.id = o.musteri_id
        ORDER BY {order}
        LIMIT 20 OFFSET 0
    """
    
    cursor.execute(query)
    explanation = cursor.fetchall()
    
    # Check if index is created
    cursor.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'musteriler'")
    indexes = cursor.fetchall()
    
    db_engine.release_connection(conn)
    
    print("--- INDEXES ON MUSTERILER ---")
    for idx in indexes:
        print(idx['indexname'], "->", idx['indexdef'])
        
    print("\n--- EXPLAIN ANALYZE ---")
    for row in explanation:
        print(list(row.values())[0])

if __name__ == "__main__":
    explain_query()
