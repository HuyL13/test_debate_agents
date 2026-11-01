import json
import sqlite3
from contextlib import closing
from pathlib import Path

from src.io_utils import canonical


class Cache:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, value TEXT NOT NULL)')

    def get(self, key):
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute('SELECT value FROM responses WHERE key = ?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, value):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT OR REPLACE INTO responses VALUES (?, ?)', (key, canonical(value)))
