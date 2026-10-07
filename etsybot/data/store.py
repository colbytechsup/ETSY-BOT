import sqlite3
import time


class Store:
    def __init__(self, path="signals.db"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS signals("
                        "ts REAL, source TEXT, niche TEXT, keyword TEXT, metric TEXT, value REAL)")

    def add(self, source, niche, keyword, metric, value, ts=None):
        self.db.execute("INSERT INTO signals VALUES(?,?,?,?,?,?)",
                        (ts or time.time(), source, niche, keyword, metric, float(value)))
        self.db.commit()

    def latest(self):
        """Newest value per (niche, keyword, metric)."""
        return self.db.execute(
            "SELECT niche, keyword, metric, value, source FROM signals s WHERE ts = "
            "(SELECT MAX(ts) FROM signals WHERE niche=s.niche AND keyword=s.keyword AND metric=s.metric)"
        ).fetchall()
