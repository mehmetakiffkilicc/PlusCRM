from api import db_engine
conn = db_engine.get_connection()
cur = db_engine.get_dict_cursor(conn)
cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'satislar'")
for row in cur.fetchall():
    print(f"Index: {row['indexname']}")
    print(f"Def: {row['indexdef']}")
conn.close()
