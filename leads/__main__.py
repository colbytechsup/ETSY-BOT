"""CLI.  python -m leads <command> [--db leads.db]

  parse FILE...            print parsed fields as JSON (no database; use to test a sample)
  ingest FILE...           parse .eml files into the pipeline ("-" = stdin)
  imap                     pull unread messages from the inbox (LEADS_IMAP_* env vars)
  list [--status new]      show leads
  push --webhook URL       POST every 'new' lead to your marketing tool, mark 'pushed'
  export OUT.csv           write leads to CSV
  draft ID                 print a follow-up email for one lead
  send [ID...|--status new] [--really]   email the follow-up from the support mailbox
                           (dry run unless --really; LEADS_SMTP_* env vars; marks 'contacted')
  status ID... --to X      set status (new/pushed/contacted/enrolled/not_interested/bad)
"""
import argparse
import email
import email.policy
import email.utils
import json
import os
import sys

from . import fetch, outreach
from . import send as sendmod
from .parser import body_text, parse_bytes, parse_file
from .pipeline import STATUSES, Pipeline
from .sinks import WebhookSink


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
    lid = pipe.add(lead)
    if lid is None:
        log(f"dup   {lead.name or lead.email or lead.subject}")
        return None
    log(f"new   #{lid} {lead.name} <{lead.email}> {lead.phone} [{lead.source}]")
    if webhook:
        webhook.send(pipe.get(lid))
        pipe.set_status([lid], "pushed")
    return lid


def draft_config():
    return dict(sender_name=os.environ.get("LEADS_SENDER_NAME", "[your name]"),
                company=os.environ.get("LEADS_COMPANY", "[company]"),
                phone=os.environ.get("LEADS_PHONE", "[phone]"),
                course_url=os.environ.get("LEADS_COURSE_URL", "[course URL]"))


def send_followups(pipe, ids=(), status=None, really=False, smtp=None, log=print):
    """Email the follow-up to the given leads (or every lead with `status`). Dry run unless
    `really`; refuses placeholders left in the draft; skips leads with no email or already
    contacted/opted out. Returns the ids sent (or that would be sent)."""
    rows = [pipe.get(i) for i in ids] if ids else pipe.all(status or "new")
    rows = [r for r in rows if r]
    cfg = draft_config()
    if really and any(v.startswith("[") for v in cfg.values()):
        sys.exit("set LEADS_SENDER_NAME, LEADS_COMPANY, LEADS_PHONE and LEADS_COURSE_URL before sending")
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
    p.add_argument("--db", default=os.environ.get("LEADS_DB", "leads.db"))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse").add_argument("files", nargs="+")
    s = sub.add_parser("ingest"); s.add_argument("files", nargs="+"); s.add_argument("--webhook")
    s = sub.add_parser("imap"); s.add_argument("--webhook"); s.add_argument("--keep-unread", action="store_true")
    sub.add_parser("list").add_argument("--status")
    sub.add_parser("push").add_argument("--webhook", required=True)
    s = sub.add_parser("export"); s.add_argument("out"); s.add_argument("--status")
    sub.add_parser("draft").add_argument("id", type=int)
    s = sub.add_parser("status"); s.add_argument("ids", nargs="+", type=int); s.add_argument("--to", required=True, choices=STATUSES)
    s = sub.add_parser("send"); s.add_argument("ids", nargs="*", type=int); s.add_argument("--status")
    s.add_argument("--really", action="store_true", help="actually send (default is a dry run)")
    a = p.parse_args(argv)

    if a.cmd == "parse":
        for f in a.files:
            print(json.dumps(parse_file(f, own_domains()).to_dict(), indent=2))
        return
    pipe = Pipeline(a.db)
    hook = WebhookSink(a.webhook) if getattr(a, "webhook", None) else None
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
        for r in pipe.all("new"):
            hook.send(r)
            pipe.set_status([r["id"]], "pushed")
            print(f"pushed #{r['id']} {r['name']}")
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


if __name__ == "__main__":
    main()
