import sqlite3, json
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT app, name FROM django_migrations ORDER BY app, name")
migrations = cur.fetchall()
print(json.dumps(migrations, indent=2))
