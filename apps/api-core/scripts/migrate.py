import sqlite3

conn = sqlite3.connect('tizon.db')
cur = conn.cursor()

cur.execute("PRAGMA table_info(ventas)")
cols = [row[1] for row in cur.fetchall()]
print('Current columns:', cols)

if 'anulada' not in cols:
    cur.execute('ALTER TABLE ventas ADD COLUMN anulada BOOLEAN DEFAULT FALSE')
    conn.commit()
    print('Migration successful: anulada column added')
else:
    print('Column anulada already exists, skipping migration')

conn.close()
