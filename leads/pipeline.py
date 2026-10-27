"""SQLite lead store with dedup and a simple status workflow: new -> pushed -> contacted -> enrolled."""
import csv
import sqlite3
import time

from .parser import Lead

STATUSES = ("new", "pushed", "contacted", "enrolled", "not_interested", "bad")
COLUMNS = ("id", "name", "email", "phone", "source", "job_title", "location", "subject",
           "sender", "received", "message_id", "campaign", "status", "added", "notes",
           "external_id", "headline")


class Pipeline:
    def __init__(self, path="leads.db"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, dedup_key TEXT UNIQUE,"
            " name TEXT, email TEXT, phone TEXT, source TEXT, job_title TEXT, location TEXT,"
            " subject TEXT, sender TEXT, received TEXT, message_id TEXT, campaign TEXT,"
            " status TEXT DEFAULT 'new', added REAL, notes TEXT DEFAULT '',"
            " external_id TEXT DEFAULT '', headline TEXT DEFAULT '')")
        have = {r[1] for r in self.db.execute("PRAGMA table_info(leads)")}
        for col in ("external_id", "headline"):  # databases created before these columns
            if col not in have:
                self.db.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT DEFAULT ''")
        self.db.commit()

    def _placeholder_for(self, lead):
        """A row with the same name and no contact details (from a notification email)."""
        if not lead.name:
            return None
        return self.db.execute(
            "SELECT id FROM leads WHERE lower(name)=lower(?) AND email='' AND phone='' AND status='new'",
            (lead.name.strip(),)).fetchone()

    def _known_by_name(self, lead):
        if not lead.name:
            return None
        return self.db.execute("SELECT id FROM leads WHERE lower(name)=lower(?)", (lead.name.strip(),)).fetchone()

    def add(self, lead: Lead):
        """Insert; returns the new row id, or None if this person is already in the pipeline.
        A lead with contact details fills in an earlier placeholder of the same name (a Breezy
        notification carries no email/phone; the export does) and returns that row's id. A
        contact-less lead whose name is already known is treated as a duplicate."""
        d = lead.to_dict()
        if lead.email or lead.phone:
            ph = self._placeholder_for(lead)
            if ph:
                self.db.execute(
                    "UPDATE leads SET dedup_key=?, email=?, phone=?, location=COALESCE(NULLIF(?, ''), location),"
                    " job_title=COALESCE(NULLIF(job_title, ''), ?), source=CASE WHEN source IN ('breezy','email') THEN ? ELSE source END,"
                    " notes=notes || ?, received=COALESCE(NULLIF(received, ''), ?) WHERE id=?",
                    (lead.dedup_key(), lead.email, lead.phone, lead.location, lead.job_title, lead.source,
                     f" [contact filled from {lead.subject or lead.source}]", lead.received, ph[0]))
                self.db.commit()
                return ph[0]
        elif self._known_by_name(lead):
            return None
        cur = self.db.execute(
            "INSERT OR IGNORE INTO leads(dedup_key, name, email, phone, source, job_title, location,"
            " subject, sender, received, message_id, campaign, added, external_id, headline)"
            " VALUES(:k, :name, :email, :phone, :source, :job_title, :location, :subject,"
            " :sender, :received, :message_id, :campaign, :added, :external_id, :headline)",
            dict(d, k=lead.dedup_key(), added=time.time()))
        self.db.commit()
        return cur.lastrowid if cur.rowcount else None

    def contactable(self, status="new"):
        """Leads with an email or phone, ready to go to the CRM."""
        return [r for r in self.all(status) if r["email"] or r["phone"]]

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
