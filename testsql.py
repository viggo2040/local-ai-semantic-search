import sqlite3

conn = sqlite3.connect("backend/data/registry.sqlite")
cur = conn.cursor()

cur.execute("""
SELECT file_name, extension
FROM files
ORDER BY file_name
""")

for row in cur.fetchall():
    print(row)