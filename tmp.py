import sqlite3
conn=sqlite3.connect('manyproxy.db')
conn.row_factory=sqlite3.Row
rows=conn.execute("SELECT id, username FROM users").fetchall()
print([dict(r) for r in rows])
conn.close()
