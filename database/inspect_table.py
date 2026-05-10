import psycopg2

DATABASE_URL = "postgresql://postgres:kWwFXwjRzqmNFBqvGtjlJBQZqZeBnbjP@crossover.proxy.rlwy.net:48854/railway"

def inspect(table_name):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print(f"Inspecting columns for {table_name}:")
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    
    for row in cur.fetchall():
        print(f"  {row}")
        
    print(f"\nInspecting constraints for {table_name}:")
    cur.execute("""
        SELECT conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE contype IN ('p','f','u','c') AND conrelid = %s::regclass
        ORDER BY contype;
    """, (table_name,))
    
    for row in cur.fetchall():
        print(f"  {row}")
        
    conn.close()

import sys
if __name__ == "__main__":
    t_name = sys.argv[1] if len(sys.argv) > 1 else 'CrmOzet'
    inspect(t_name)
