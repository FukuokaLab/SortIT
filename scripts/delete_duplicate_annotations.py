#!/usr/bin/env python
"""
NOTE: this should be run inside the docker container to work on the
container database at /app/data/db.sqlite3
"""

import sqlite3

conn = sqlite3.connect("data/db.sqlite3")
c = conn.cursor()
c.execute("""
    DELETE FROM sortIT_annotation WHERE id NOT IN (
        SELECT MAX(id) FROM sortIT_annotation
        GROUP BY user_id, image_id, label_id
    )
""")
print(f"Deleted {c.rowcount} duplicate rows")
conn.commit()
conn.close()
