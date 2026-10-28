"""CLI.  python -m leads <command> [--db leads.db]

  parse FILE...            print parsed fields as JSON (no database; use to test a sample)
  ingest FILE...           parse .eml files into the pipeline ("-" = stdin)
  imap                     pull unread messages from the inbox (LEADS_IMAP_* env vars)
  csv FILE.csv [--company "Name"]  import a candidate export (columns auto-detected); the
                           company becomes a tag in the CRM
  list [--status new]      show leads
  push [--limit N]         send 'new' leads to the configured sink, mark 'pushed' (N per run)
  sink-test                send one fake contact to the sink to check the setup
  export OUT.csv           write leads to CSV
  draft ID                 print a follow-up email for one lead
  send [ID...|--status new] [--really]   email the follow-up from the support mailbox
                           (dry run unless --really; LEADS_SMTP_* env vars; marks 'contacted')
  status ID... --to X      set status (new/pushed/contacted/enrolled/not_interested/bad)

Settings are read from the environment, and from a .env file in the current directory
(or the file named by LEADS_ENV) first. New leads go to GoHighLevel's API when
LEADS_GHL_TOKEN + LEADS_GHL_LOCATION are set, else to LEADS_WEBHOOK / --webhook, else
they just sit in the database.  `sink-test` sends one fake contact to check the setup.
"""
import argparse
import csv as csvmod
import email
import email.policy
import email.utils
import json
import os
import re
import sys

from . import fetch, outreach
from . import send as sendmod
from .parser import EMAIL_RE, Lead, body_text, parse_bytes, parse_file
from .pipeline import STATUSES, Pipeline
from .sinks import GhlSink, SinkError, WebhookSink, sink_from_env


def load_env(path=None):
    """Minimal .env loader (KEY=value lines, # comments, optional quotes). Existing environment
    variables win. Returns the number of keys set."""
    path = path or os.environ.get("LEADS_ENV", ".env")
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v
                n += 1
    return n


CSV_COLUMNS = {  # lead field -> header words to look for (lowercased, in order of preference)
    "name": ("name", "candidate", "full name"),
    "first": ("first name", "first", "firstname", "given"),
    "last": ("last name", "last", "lastname", "surname", "family"),
    "email": ("email", "e-mail", "email_address", "email address"),
    "phone": ("phone", "mobile", "cell", "telephone", "phone_number", "phone number"),
    "job_title": ("position", "job", "role", "applied"),
    "location": ("location", "city", "address"),
    "source": ("source", "origin", "channel"),
    "stage": ("stage", "status"),
    "added": ("addeddate", "added", "applied date", "created", "date"),
}

SOURCE_TAGS = (("indeed", "indeed"), ("zip", "ziprecruiter"), ("career portal", "career_portal"),
               ("linkedin", "linkedin"), ("monster", "monster"), ("google", "google"),
               ("craigslist", "craigslist"), ("facebook", "facebook"), ("glassdoor", "glassdoor"))


def normalize_source(raw, default="csv"):
    """'Indeed Organic Jobs' -> 'indeed', 'ziprecruiter' -> 'ziprecruiter', else a slug."""
    low = (raw or "").strip().lower()
    if not low:
        return default
    for frag, tag in SOURCE_TAGS:
        if frag in low:
            return tag
    return re.sub(r"[^a-z0-9]+", "_", low).strip("_")[:40] or default


def match_columns(headers):
    """Map lead fields to CSV headers: exact header matches first, then substring matches,
    never reusing a header (so 'address' cannot grab 'email_address')."""
    low = {h.lower().strip().replace("_", " "): h for h in headers if h}
    taken, cols = set(), {}
    for field, wants in CSV_COLUMNS.items():
        for want in wants:
            w = want.replace("_", " ")
            if w in low and low[w] not in taken:
                cols[field] = low[w]; taken.add(low[w]); break
    for field, wants in CSV_COLUMNS.items():
        if field in cols or field == "name":
            continue
        for want in wants:
            w = want.replace("_", " ")
            hit = next((h for k, h in low.items() if w in k and h not in taken), None)
            if hit:
                cols[field] = hit; taken.add(hit); break
    return cols


def import_csv(pipe, path, default_source="csv", log=print, company=""):
    """Import a candidate export (Breezy, Indeed, a spreadsheet). Columns are matched by
    header text, so the exact export format does not matter as long as the headers are
    recognisable. Source is normalised to a tag; stage is kept in notes. Returns (added, skipped)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csvmod.DictReader(f))
    if not rows:
        return 0, 0
    cols = match_columns(rows[0].keys())
    added = skipped = 0
    for r in rows:
        get = lambda f: (r.get(cols[f]) or "").strip() if cols.get(f) else ""
        name = get("name") or (get("first") + " " + get("last")).strip()
        email_addr = get("email")
        if not EMAIL_RE.fullmatch(email_addr or ""):
            email_addr = ""
        lead = Lead(name=name, email=email_addr, phone=get("phone"), job_title=get("job_title"),
                    location=get("location"), source=normalize_source(get("source"), default_source),
                    received=get("added"), subject=f"csv import: {os.path.basename(path)}", company=company)
        if not (lead.email or lead.phone):
            skipped += 1
            continue
        lid = pipe.add(lead)
        if lid is None:
            skipped += 1
        else:
            added += 1
            if get("stage"):
                row = pipe.get(lid)
                pipe.set_status([lid], row["status"], note=(row["notes"] + f" breezy stage: {get('stage')}; source: {get('source')}").strip())
    log(f"{added} added, {skipped} skipped (duplicate or no email/phone) from {path}")
    return added, skipped


def own_domains():
    return [d for d in os.environ.get("LEADS_OWN_DOMAINS", "").split(",") if d]


def read_raw(path):
    return sys.stdin.buffer.read() if path == "-" else open(path, "rb").read()


def handle_opt_out(pipe, raw, log=print):
    """A reply from someone already in the pipeline that starts with stop/unsubscribe/etc.
    marks them not_interested and is not treated as a new lead. Returns True if handled."""
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    _, addr = email.utils.parseaddr(msg.get("From", ""))
    if not addr:
        return False
    rows = [r for r in pipe.all() if r["email"].lower() == addr.lower()]
    if not rows or not sendmod.is_opt_out(body_text(msg)):
        return False
    pipe.set_status([r["id"] for r in rows], "not_interested", note="opted out by reply")
    log(f"optout {addr}")
    return True


def ingest_raw(pipe, raw, webhook=None, log=print):
    if handle_opt_out(pipe, raw, log):
        return None
    lead = parse_bytes(raw, own_domains())
    if not (lead.name or lead.email or lead.phone):
        log(f"skip  nothing identifying in: {lead.subject[:60]}")
        return None
    lid = pipe.add(lead)
    if lid is None:
        log(f"dup   {lead.name or lead.email or lead.subject}")
        return None
    log(f"new   #{lid} {lead.name} <{lead.email}> {lead.phone} [{lead.source}] {lead.headline}")
    if webhook and (lead.email or lead.phone):
        webhook.send(pipe.get(lid))
        pipe.set_status([lid], "pushed")
    return lid


def draft_config():
    """Name and company are required for a real send; phone, URL and postal address are
    optional and their lines are left out of the email when unset."""
    return dict(sender_name=os.environ.get("LEADS_SENDER_NAME", "[your name]"),
                company=os.environ.get("LEADS_COMPANY", "[company]"),
                phone=os.environ.get("LEADS_PHONE", ""),
                course_url=os.environ.get("LEADS_COURSE_URL", ""),
                postal_address=os.environ.get("LEADS_POSTAL_ADDRESS", ""))


def send_followups(pipe, ids=(), status=None, really=False, smtp=None, log=print):
    """Email the follow-up to the given leads (or every lead with `status`). Dry run unless
    `really`; refuses placeholders left in the draft; skips leads with no email or already
    contacted/opted out. Returns the ids sent (or that would be sent)."""
    rows = [pipe.get(i) for i in ids] if ids else pipe.all(status or "new")
    rows = [r for r in rows if r]
    cfg = draft_config()
    if really and any(v.startswith("[") for v in cfg.values()):
        sys.exit("set LEADS_SENDER_NAME and LEADS_COMPANY before sending")
    if really and not cfg["postal_address"]:
        log("warning: LEADS_POSTAL_ADDRESS is unset; CAN-SPAM requires a physical postal address")
    from_addr = os.environ.get("LEADS_FROM") or os.environ.get("LEADS_SMTP_USER", "[from]")
    if really and smtp is None:
        smtp = sendmod.smtp_client()
    done = []
    for r in rows:
        if not r["email"]:
            log(f"skip  #{r['id']} {r['name']}: no email")
            continue
        if r["status"] in ("contacted", "enrolled", "not_interested", "bad"):
            log(f"skip  #{r['id']} {r['name']}: status {r['status']}")
            continue
        msg = sendmod.build_message(r["email"], outreach.draft(r, **cfg), from_addr)
        if really:
            sendmod.send(smtp, msg)
            pipe.set_status([r["id"]], "contacted", note="follow-up sent")
            log(f"sent  #{r['id']} {r['name']} <{r['email']}>")
        else:
            log(f"would #{r['id']} {r['name']} <{r['email']}>  subject: {msg['Subject']}")
        done.append(r["id"])
    if not really:
        log(f"dry run: {len(done)} email(s) would be sent. Add --really to send.")
    if really and smtp is not None and hasattr(smtp, "quit"):
        smtp.quit()
    return done


def main(argv=None):
    p = argparse.ArgumentParser(prog="leads", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse").add_argument("files", nargs="+")
    s = sub.add_parser("ingest"); s.add_argument("files", nargs="+"); s.add_argument("--webhook")
    s = sub.add_parser("imap"); s.add_argument("--webhook"); s.add_argument("--keep-unread", action="store_true")
    sub.add_parser("list").add_argument("--status")
    s = sub.add_parser("push"); s.add_argument("--webhook")
    s.add_argument("--limit", type=int, default=0, help="send at most N leads this run (0 = all)")
    sub.add_parser("sink-test")
    s = sub.add_parser("export"); s.add_argument("out"); s.add_argument("--status")
    sub.add_parser("draft").add_argument("id", type=int)
    s = sub.add_parser("status"); s.add_argument("ids", nargs="+", type=int); s.add_argument("--to", required=True, choices=STATUSES)
    s = sub.add_parser("send"); s.add_argument("ids", nargs="*", type=int); s.add_argument("--status")
    s.add_argument("--really", action="store_true", help="actually send (default is a dry run)")
    s = sub.add_parser("csv"); s.add_argument("file"); s.add_argument("--source", default="csv")
    s.add_argument("--company", default="", help='which Breezy company the export is from, e.g. "Small Potato Trucking"')
    load_env()
    p.set_defaults(db=os.environ.get("LEADS_DB", "leads.db"))
    a = p.parse_args(argv)

    if a.cmd == "parse":
        for f in a.files:
            print(json.dumps(parse_file(f, own_domains()).to_dict(), indent=2))
        return
    pipe = Pipeline(a.db)
    hook = WebhookSink(a.webhook) if getattr(a, "webhook", None) else sink_from_env(os.environ)
    if a.cmd == "sink-test":
        if hook is None:
            sys.exit("no sink configured: set LEADS_GHL_TOKEN + LEADS_GHL_LOCATION, or LEADS_WEBHOOK")
        print(f"sending a test contact via {type(hook).__name__} ...")
        if isinstance(hook, GhlSink):
            print(f"  location: {hook.location}   token: {hook.token[:6]}...{hook.token[-4:]} ({len(hook.token)} chars)   version: {hook.version}")
        try:
            print("response:", json.dumps(hook.send({"name": "Test Lead", "email": "test-lead@example.com",
                                                     "phone": "+15555550100", "source": "test",
                                                     "job_title": "CDL Driver (test)", "campaign": "certrig_hazmat"}), indent=1)[:1500])
        except SinkError as e:
            sys.exit(f"FAILED: {e}\n\nCommon GHL causes: 403 = token lacks the contacts.write scope or belongs to a "
                     "different sub-account than LEADS_GHL_LOCATION; 401 = bad token or Version header; "
                     "422 = a field GHL did not like (see the message above).")
        print("check GHL for a contact named 'Test Lead', then delete it.")
        return
    if a.cmd == "ingest":
        for f in a.files:
            ingest_raw(pipe, read_raw(f), hook)
    elif a.cmd == "imap":
        client = fetch.imap_client()
        try:
            n = fetch.pull_unseen(client, lambda raw: ingest_raw(pipe, raw, hook),
                                  mark_seen=not a.keep_unread)
        finally:
            client.logout()
        print(f"{n} message(s) processed")
    elif a.cmd == "list":
        for r in pipe.all(a.status):
            print(f"#{r['id']:<4} {r['status']:<14} {r['source']:<12} {r['name'][:24]:<24} "
                  f"{r['email'][:30]:<30} {r['phone']:<14} {r['job_title'][:30]}")
    elif a.cmd == "push":
        if hook is None:
            sys.exit("no sink configured: set LEADS_GHL_TOKEN + LEADS_GHL_LOCATION, or LEADS_WEBHOOK")
        todo = pipe.contactable("new")
        batch = todo[:a.limit] if a.limit else todo
        for r in batch:
            try:
                hook.send(r)
            except SinkError as e:
                sys.exit(f"stopped at #{r['id']} {r['name']}: {e}\n{len(todo) - batch.index(r)} still 'new'; rerun push to continue.")
            pipe.set_status([r["id"]], "pushed")
            print(f"pushed #{r['id']} {r['name']} <{r['email']}>")
        print(f"{len(batch)} pushed this run, {len(todo) - len(batch)} still waiting as 'new'.")
    elif a.cmd == "export":
        print(f"{pipe.export_csv(a.out, a.status)} row(s) -> {a.out}")
    elif a.cmd == "draft":
        lead = pipe.get(a.id)
        if not lead:
            sys.exit(f"no lead #{a.id}")
        print(outreach.draft(lead, **draft_config()))
    elif a.cmd == "send":
        send_followups(pipe, a.ids, a.status, a.really)
    elif a.cmd == "status":
        pipe.set_status(a.ids, a.to)
    elif a.cmd == "csv":
        import_csv(pipe, a.file, a.source, company=a.company)


if __name__ == "__main__":
    main()
