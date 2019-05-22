import sqlite3

conn = sqlite3.connect('files.db')
c = conn.cursor()
c.execute("SELECT * FROM  files WHERE file_name = 'HG02102'")

res = c.fetchone()

print(res[0])

conn.commit()

conn.close()