"""Send the follow-up from the support mailbox over SMTP (stdlib smtplib).

Env: LEADS_SMTP_HOST, LEADS_SMTP_PORT (465 = SSL, 587 = STARTTLS), LEADS_SMTP_USER,
LEADS_SMTP_PASSWORD, LEADS_FROM (defaults to the user). Gmail/Google Workspace wants an App
Password here, same as IMAP. Nothing is sent unless the caller passes a real `smtp`."""
import os
import smtplib
from email.message import EmailMessage


def smtp_client(host=None, port=None, user=None, password=None):
    host = host or os.environ["LEADS_SMTP_HOST"]
    port = int(port or os.environ.get("LEADS_SMTP_PORT", "465"))
    user = user or os.environ["LEADS_SMTP_USER"]
    password = password or os.environ["LEADS_SMTP_PASSWORD"]
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        s = smtplib.SMTP(host, port, timeout=30)
        s.starttls()
    s.login(user, password)
    return s


def build_message(to_addr, draft_text, from_addr, reply_to=None):
    """`draft_text` is outreach.draft() output: first line 'Subject: ...', blank line, body."""
    first, _, body = draft_text.partition("\n")
    subject = first[len("Subject:"):].strip() if first.lower().startswith("subject:") else first
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = from_addr, to_addr, subject
    if reply_to:
        m["Reply-To"] = reply_to
    m["List-Unsubscribe"] = f"<mailto:{reply_to or from_addr}?subject=stop>"
    m.set_content(body.lstrip("\n"))
    return m


def send(smtp, message):
    smtp.send_message(message)
    return message["To"]


OPT_OUT_WORDS = ("stop", "unsubscribe", "remove me", "opt out", "no thanks", "not interested")


def is_opt_out(text):
    head = (text or "").strip().lower()[:200]
    return any(head.startswith(w) or f"\n{w}" in head for w in OPT_OUT_WORDS)
