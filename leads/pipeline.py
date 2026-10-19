"""SQLite lead store with dedup and a simple status workflow: new -> pushed -> contacted -> enrolled."""
import csv
import sqlite3
import time

from .parser import Lead

STATUSES = ("new", "pushed", "contacted", "enrolled", "not_interested", "bad")
COLUMNS = ("id", "name", "email", "phone", "source", "job_title", "location", "subject",
           "sender", "received", "message_id", "campaign", "status", "added", "notes")


class Pipeline:
    def __init__(self, path="leads.db"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, dedup_key TEXT UNIQUE,"
            " name TEXT, email TEXT, phone TEXT, source TEXT, job_title TEXT, location TEXT,"
            " subject TEXT, sender TEXT, received TEXT, message_id TEXT, campaign TEXT,"
            " status TEXT DEFAULT 'new', added REAL, notes TEXT DEFAULT '')")

    def add(self, lead: Lead):
        """Insert; returns the new row id, or None if this person is already in the pipeline."""
        d = lead.to_dict()
        cur = self.db.execute(
            "INSERT OR IGNORE INTO leads(dedup_key, name, email, phone, source, job_title, location,"
            " subject, sender, received, message_id, campaign, added)"
            " VALUES(:k, :name, :email, :phone, :source, :job_title, :location, :subject,"
            " :sender, :received, :message_id, :campaign, :added)",
            dict(d, k=lead.dedup_key(), added=time.time()))
        self.db.commit()
        return cur.lastrowid if cur.rowcount else None

    def all(self, status=None):
        q, args = "SELECT * FROM leads", ()
        if status:
            q, args = q + " WHERE status = ?", (status,)
        return [dict(r) for r in self.db.execute(q + " ORDER BY id", args)]

    def get(self, lead_id):
        r = self.db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return dict(r) if r else None

    def set_status(self, ids, status, note=None):
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        for i in ids:
            if note is None:
                self.db.execute("UPDATE leads SET status=? WHERE id=?", (status, i))
            else:
                self.db.execute("UPDATE leads SET status=?, notes=? WHERE id=?", (status, note, i))
        self.db.commit()

    def export_csv(self, path, status=None):
        rows = self.all(status)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        return len(rows)
