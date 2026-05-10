from api import db_engine
conn = db_engine.get_connection()
cur = db_engine.get_dict_cursor(conn)
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'satislar' AND column_name = 'tarih'")
print(cur.fetchone())
conn.close()
