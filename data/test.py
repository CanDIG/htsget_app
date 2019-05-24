import sqlite3

conn = sqlite3.connect('files.db')
c = conn.cursor()

# c.execute("""CREATE TABLE files (
#             id text,
#             file_type text,
#             format text
#             )""")

c.execute("INSERT INTO files VALUES ('NA02102', '.bam', 'BAM')")

c.execute("SELECT * FROM files")
print(c.fetchall())

conn.commit()
conn.close()

