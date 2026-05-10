"""Delete portal cache - let live query handle all sections"""
import psycopg2
conn = psycopg2.connect('postgresql://postgres:kWwFXwjRzqmNFBqvGtjlJBQZqZeBnbjP@crossover.proxy.rlwy.net:48854/railway')
cur = conn.cursor()
cur.execute("DELETE FROM urun_portal_ozet")
conn.commit()
print(f'Cache deleted. Portal will use live query with all sections.')
conn.close()
