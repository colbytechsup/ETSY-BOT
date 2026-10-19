"""Pull unread messages from an IMAP inbox. Gmail: turn on IMAP in settings and use an
App Password (needs 2-step verification), not the account password. Messages are fetched
with BODY.PEEK so a crash mid-run does not mark anything read; a message is flagged Seen
only after the caller's handler returns."""
import imaplib
import os


def imap_client(host=None, user=None, password=None, folder=None):
    host = host or os.environ["LEADS_IMAP_HOST"]
    user = user or os.environ["LEADS_IMAP_USER"]
    password = password or os.environ["LEADS_IMAP_PASSWORD"]
    m = imaplib.IMAP4_SSL(host)
    m.login(user, password)
    m.select(folder or os.environ.get("LEADS_IMAP_FOLDER", "INBOX"))
    return m


def pull_unseen(client, handle, mark_seen=True, criteria="UNSEEN"):
    """Call handle(raw_bytes) for each matching message; returns how many were handled.
    `client` needs search/fetch/store like imaplib.IMAP4 (a fake works in tests)."""
    typ, data = client.search(None, criteria)
    if typ != "OK":
        raise RuntimeError(f"IMAP search failed: {typ} {data}")
    n = 0
    for num in data[0].split():
        typ, parts = client.fetch(num, "(BODY.PEEK[])")
        if typ != "OK" or not parts or not isinstance(parts[0], tuple):
            continue
        handle(parts[0][1])
        if mark_seen:
            client.store(num, "+FLAGS", "\\Seen")
        n += 1
    return n
