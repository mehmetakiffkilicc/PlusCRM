import psycopg2

DATABASE_URL = "postgresql://postgres:kWwFXwjRzqmNFBqvGtjlJBQZqZeBnbjP@crossover.proxy.rlwy.net:48854/railway"

def list_schema():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    
    rows = cur.fetchall()
    current_table = None
    for table_name, column_name, data_type, is_nullable in rows:
        if table_name != current_table:
            print(f"\nTable: {table_name}")
            current_table = table_name
        print(f"  - {column_name}: {data_type} (Nullable: {is_nullable})")
    
    conn.close()

if __name__ == "__main__":
    list_schema()
