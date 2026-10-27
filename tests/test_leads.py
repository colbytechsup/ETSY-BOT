import json
import os
from email.message import EmailMessage

from leads import fetch, outreach
from leads.__main__ import ingest_raw, main
from leads.parser import Lead, parse_bytes, parse_subject
from leads.pipeline import Pipeline
from leads.sinks import WebhookSink


def make(sender, subject, text=None, html=None, msgid="<a@b>"):
    m = EmailMessage()
    m["From"], m["Subject"], m["Message-ID"], m["Date"] = sender, subject, msgid, "Mon, 1 Jan 2026 10:00:00 +0000"
    if html and text:
        m.set_content(text)
        m.add_alternative(html, subtype="html")
    elif html:
        m.set_content(html, subtype="html")
    else:
        m.set_content(text or "")
    return m.as_bytes()


INDEED_HTML = """<html><body><div style="x">New candidate</div>
<table><tr><td><b>Candidate name</b>:</td><td>Jane Driver</td></tr>
<tr><td>Email:</td><td><a href="mailto:jane.driver@gmail.com">jane.driver@gmail.com</a></td></tr>
<tr><td>Phone:</td><td>(555) 123-4567</td></tr>
<tr><td>Location:</td><td>Houston, TX</td></tr></table>
<p>Questions? Contact support@indeed.com or <a href="x">unsubscribe</a>.</p>
<script>var tracking = 'noreply@indeed.com';</script></body></html>"""


def test_indeed_style_html_email():
    raw = make("Indeed <donotreply@indeed.com>", "Jane Driver applied to CDL Driver - Hazmat", html=INDEED_HTML)
    lead = parse_bytes(raw)
    assert lead.name == "Jane Driver"
    assert lead.email == "jane.driver@gmail.com"
    assert lead.phone == "(555) 123-4567"
    assert lead.location == "Houston, TX"
    assert lead.job_title == "CDL Driver - Hazmat"
    assert lead.source == "indeed"
    assert lead.dedup_key() == "email:jane.driver@gmail.com"


def test_plain_text_form_email_and_prefers_candidate_over_platform_address():
    text = ("You have a new application.\n\nName: Bob Smith\nPhone number: 555.987.6543\n"
            "Applied for: Owner Operator\nReply to: 7f3k2@relay.indeedemail.com\n"
            "Do not reply to noreply@indeed.com")
    lead = parse_bytes(make("Indeed Apply <noreply@indeed.com>", "New candidate: Bob Smith", text=text))
    assert (lead.name, lead.phone, lead.job_title) == ("Bob Smith", "555.987.6543", "Owner Operator")
    assert lead.email == "7f3k2@relay.indeedemail.com"  # relay subdomain is the way to reach them


def test_direct_email_uses_sender_and_own_domain_is_ignored():
    text = "Hey, saw your ad. Do you train for hazmat? Call me 555-222-3333.\n-- Sam\ninfo@phtruckingpros.com"
    lead = parse_bytes(make("Sam Jones <sam@example.com>", "Question about training", text=text),
                       own_domains=["phtruckingpros.com"])
    assert lead.source == "email"
    assert lead.email == "sam@example.com"
    assert lead.name == "Sam Jones"
    assert lead.phone == "555-222-3333"
    assert lead.job_title == ""


def test_breezy_system_mail_is_recognised():
    text = ("Hi there,\nYour position, LOCAL CDL-A DRIVERS, was not approved.\n"
            "Questions? support@breezy-mail.com\nView Position")
    lead = parse_bytes(make("Breezy HR <support@breezy-mail.com>", "Your position was disapproved", text=text))
    assert lead.source == "breezy" and lead.email == "" and lead.name == ""


def test_subject_patterns():
    assert parse_subject("Re: FW: New application for Local Driver: Ann Lee") == ("Ann Lee", "Local Driver")
    assert parse_subject("Carlos Ruiz has applied for Tanker Driver") == ("Carlos Ruiz", "Tanker Driver")
    assert parse_subject("Kim Park is interested in Class A Driver") == ("Kim Park", "Class A Driver")
    assert parse_subject("Weekly digest") == ("", "")
    assert parse_subject("New candidate: 12345 applied to X") == ("", "X")  # not a name


def test_phone_does_not_match_long_ids():
    lead = parse_bytes(make("a@example.com", "x", text="Application ID 123456789012345\nCell - 555 444 1212"))
    assert lead.phone == "555 444 1212"


def test_pipeline_dedup_status_and_csv(tmp_path):
    pipe = Pipeline(str(tmp_path / "l.db"))
    a = Lead(name="Jane", email="Jane@x.com", phone="1")
    assert pipe.add(a) == 1
    assert pipe.add(Lead(name="Jane D", email="jane@x.com")) is None  # same email, case-insensitive
    assert pipe.add(Lead(name="Anon", phone="(555) 000-1111")) == 2
    assert pipe.add(Lead(name="Anon2", phone="555-000-1111")) is None  # same digits
    pipe.set_status([1], "contacted", note="left voicemail")
    assert pipe.get(1)["status"] == "contacted" and pipe.get(1)["notes"] == "left voicemail"
    assert [r["id"] for r in pipe.all("new")] == [2]
    out = tmp_path / "o.csv"
    assert pipe.export_csv(str(out)) == 2
    assert "jane@x.com" not in out.read_text() and "Jane@x.com" in out.read_text()


def test_webhook_sink_posts_lead_fields():
    calls = []
    sink = WebhookSink("https://hooks.example/abc", headers={"X-Key": "k"},
                       post=lambda url, payload, headers: calls.append((url, payload, headers)) or 200)
    assert sink.send({"id": 1, "name": "J", "email": "j@x", "dedup_key": "e", "added": 1.0, "campaign": "certrig_hazmat"}) == 200
    url, payload, headers = calls[0]
    assert url == "https://hooks.example/abc" and headers == {"X-Key": "k"}
    assert payload == {"id": 1, "name": "J", "email": "j@x", "campaign": "certrig_hazmat",
                       "first_name": "J", "last_name": "", "tags": ["certrig_hazmat"]}
    json.dumps(payload)


class FakeImap:
    def __init__(self, msgs):
        self.msgs, self.flagged = msgs, []

    def search(self, charset, crit):
        return "OK", [b" ".join(str(i).encode() for i in range(len(self.msgs)))]

    def fetch(self, num, what):
        assert "PEEK" in what
        return "OK", [(b"hdr", self.msgs[int(num)]), b")"]

    def store(self, num, op, flag):
        self.flagged.append((num, flag))


def test_imap_pull_ingests_and_marks_seen(tmp_path):
    raw1 = make("noreply@indeed.com", "Jane Driver applied to CDL Driver", html=INDEED_HTML, msgid="<1>")
    raw2 = make("noreply@indeed.com", "Jane Driver applied to CDL Driver", html=INDEED_HTML, msgid="<2>")
    client = FakeImap([raw1, raw2])
    pipe, logs, sent = Pipeline(str(tmp_path / "l.db")), [], []
    hook = WebhookSink("u", post=lambda u, p, h: sent.append(p) or 200)
    n = fetch.pull_unseen(client, lambda raw: ingest_raw(pipe, raw, hook, log=logs.append))
    assert n == 2 and len(client.flagged) == 2
    assert len(pipe.all()) == 1 and pipe.get(1)["status"] == "pushed"
    assert len(sent) == 1 and sent[0]["email"] == "jane.driver@gmail.com"
    assert logs[0].startswith("new") and logs[1].startswith("dup")


def test_cli_parse_ingest_list_draft(tmp_path, capsys):
    eml = tmp_path / "m.eml"
    eml.write_bytes(make("noreply@indeed.com", "Jane Driver applied to CDL Driver", html=INDEED_HTML))
    db = str(tmp_path / "c.db")
    main(["parse", str(eml)])
    assert json.loads(capsys.readouterr().out)["name"] == "Jane Driver"
    main(["--db", db, "ingest", str(eml)])
    main(["--db", db, "list", "--status", "new"])
    assert "jane.driver@gmail.com" in capsys.readouterr().out
    main(["--db", db, "draft", "1"])
    out = capsys.readouterr().out
    assert "Hi Jane," in out and "CDL Driver position" in out and "CertRig hazmat course" in out
    assert "call" not in out and "[" not in out.split("\n", 1)[1].replace("[your name]", "").replace("[company]", "")
    main(["--db", db, "status", "1", "--to", "enrolled"])
    assert Pipeline(db).get(1)["status"] == "enrolled"


def test_draft_without_name_or_job():
    assert "Hi there," in outreach.draft({"name": "", "job_title": ""})


def test_draft_optional_lines():
    bare = outreach.draft({"name": "A B"}, sender_name="Todd Bryson", company="Certrig")
    assert "call" not in bare and "More about" not in bare and bare.rstrip().endswith("Certrig")
    full = outreach.draft({"name": "A B"}, sender_name="Todd Bryson", company="Certrig",
                          phone="555", course_url="https://c", postal_address="1 Main St, Houston TX")
    assert " or call 555." in full and "More about the course: https://c" in full
    assert full.rstrip().endswith("Certrig\n1 Main St, Houston TX")


class FakeSmtp:
    def __init__(self):
        self.sent, self.quit_called = [], False

    def send_message(self, m):
        self.sent.append(m)

    def quit(self):
        self.quit_called = True


def test_build_message_from_draft():
    from leads import send
    text = outreach.draft({"name": "Jane Driver", "job_title": "CDL Driver"}, sender_name="Todd",
                          company="PH", phone="555", course_url="https://x")
    m = send.build_message("jane@x.com", text, "support@course.com")
    assert m["Subject"] == "Jane, a hazmat endorsement could open more doors"
    assert m["To"] == "jane@x.com" and m["From"] == "support@course.com"
    assert "mailto:support@course.com" in m["List-Unsubscribe"]
    assert m.get_content().startswith("Hi Jane,")


def test_send_followups_dry_run_then_real(tmp_path, monkeypatch):
    from leads.__main__ import send_followups
    for k, v in {"LEADS_SENDER_NAME": "Todd", "LEADS_COMPANY": "PH",
                 "LEADS_FROM": "support@course.com"}.items():
        monkeypatch.setenv(k, v)
    pipe = Pipeline(str(tmp_path / "l.db"))
    pipe.add(Lead(name="Jane", email="jane@x.com"))
    pipe.add(Lead(name="NoMail", phone="555-111-2222"))
    pipe.add(Lead(name="Done", email="done@x.com"))
    pipe.set_status([3], "contacted")
    logs = []
    assert send_followups(pipe, really=False, log=logs.append) == [1]
    assert pipe.get(1)["status"] == "new" and any(l.startswith("dry run") for l in logs)
    smtp = FakeSmtp()
    assert send_followups(pipe, really=True, smtp=smtp, log=logs.append) == [1]
    assert [m["To"] for m in smtp.sent] == ["jane@x.com"] and smtp.quit_called
    assert pipe.get(1)["status"] == "contacted"
    # second run sends nothing: already contacted
    assert send_followups(pipe, really=True, smtp=FakeSmtp(), log=logs.append) == []


def test_send_refuses_placeholders(tmp_path, monkeypatch):
    import pytest
    from leads.__main__ import send_followups
    for k in ("LEADS_SENDER_NAME", "LEADS_COMPANY"):
        monkeypatch.delenv(k, raising=False)
    pipe = Pipeline(str(tmp_path / "l.db"))
    pipe.add(Lead(name="Jane", email="jane@x.com"))
    with pytest.raises(SystemExit):
        send_followups(pipe, really=True, smtp=FakeSmtp(), log=lambda s: None)


def test_opt_out_reply_marks_not_interested(tmp_path):
    pipe = Pipeline(str(tmp_path / "l.db"))
    pipe.add(Lead(name="Jane", email="jane@x.com"))
    logs = []
    raw = make("Jane <jane@x.com>", "Re: a hazmat endorsement", text="STOP please\n\n> original quoted")
    assert ingest_raw(pipe, raw, log=logs.append) is None
    assert pipe.get(1)["status"] == "not_interested" and logs == ["optout jane@x.com"]
    assert len(pipe.all()) == 1
    # a normal reply from a known lead is not an opt-out and not a duplicate lead either
    raw = make("Jane <jane@x.com>", "Re: a hazmat endorsement", text="Yes, send me the dates!")
    assert ingest_raw(pipe, raw, log=logs.append) is None and logs[-1].startswith("dup")
    # an unknown sender saying stop is just a (weird) new lead, not an opt-out
    raw = make("New Guy <guy@x.com>", "hi", text="stop by anytime, interested in hazmat")
    assert ingest_raw(pipe, raw, log=logs.append) == 2


def test_load_env_and_webhook_default(tmp_path, monkeypatch):
    from leads.__main__ import load_env
    env = tmp_path / ".env"
    env.write_text("# comment\nLEADS_COMPANY='Certrig'\nLEADS_WEBHOOK=https://h/x\n\nBAD LINE\nLEADS_PHONE=\n")
    monkeypatch.delenv("LEADS_COMPANY", raising=False)
    monkeypatch.setenv("LEADS_WEBHOOK", "https://already/set")
    monkeypatch.delenv("LEADS_PHONE", raising=False)
    assert load_env(str(env)) == 2
    assert os.environ["LEADS_COMPANY"] == "Certrig"
    assert os.environ["LEADS_WEBHOOK"] == "https://already/set"  # existing env wins
    assert os.environ["LEADS_PHONE"] == ""


def test_webhook_payload_is_ghl_friendly():
    from leads.sinks import enrich
    p = enrich({"id": 1, "name": "Jane Q Driver", "email": "j@x", "source": "indeed",
                "campaign": "certrig_hazmat", "dedup_key": "k", "added": 1.0})
    assert (p["first_name"], p["last_name"]) == ("Jane", "Q Driver")
    assert p["tags"] == ["certrig_hazmat", "indeed"] and "dedup_key" not in p
    assert enrich({"name": ""})["first_name"] == ""


def test_csv_import_detects_columns(tmp_path):
    from leads.__main__ import import_csv
    f = tmp_path / "export.csv"
    f.write_text("\ufeffFirst Name,Last Name,Email Address,Phone Number,Position,Stage\n"
                 "Ann,Lee,ann@x.com,555-111-2222,CDL Driver,Applied\n"
                 "Bob,Ray,not-an-email,,Tanker,Applied\n"
                 "Cat,Fox,cat@x.com,,CDL Driver,Hired\n"
                 "Ann,Lee,ANN@x.com,,CDL Driver,Applied\n")
    pipe = Pipeline(str(tmp_path / "l.db"))
    logs = []
    assert import_csv(pipe, str(f), "breezy", log=logs.append) == (2, 2)
    rows = pipe.all()
    assert [(r["name"], r["email"], r["job_title"], r["source"]) for r in rows] == [
        ("Ann Lee", "ann@x.com", "CDL Driver", "breezy"), ("Cat Fox", "cat@x.com", "CDL Driver", "breezy")]
    assert rows[0]["phone"] == "555-111-2222" and "stage: Applied" in rows[0]["notes"]


def test_csv_import_breezy_export_layout(tmp_path):
    from leads.__main__ import import_csv, normalize_source
    f = tmp_path / "breezy.csv"
    f.write_text('"name","match_score","score","email_address","phone_number","address","salary","position","stage","source","sourced_by_name","addedDate","addedTime"\n'
                 '"Pat Example","",,"pat@example.com","+1 555 010 0001","Arizona, US","","CDL-A Regional Driver","Applied","Indeed Organic Jobs","","2026-10-15","21:10"\n'
                 '"Sam Sample","",,"sam@example.org","+15550100002","Massachusetts, US","","Furniture Driver","Contacted","ziprecruiter","","2026-10-24","12:10"\n')
    pipe = Pipeline(str(tmp_path / "l.db"))
    assert import_csv(pipe, str(f), "breezy", log=lambda s: None) == (2, 0)
    r = pipe.get(1)
    assert (r["email"], r["phone"], r["location"], r["job_title"]) == ("pat@example.com", "+1 555 010 0001", "Arizona, US", "CDL-A Regional Driver")
    assert r["source"] == "indeed" and r["received"] == "2026-10-15" and "Indeed Organic Jobs" in r["notes"]
    assert pipe.get(2)["source"] == "ziprecruiter"
    assert normalize_source("Career Portal") == "career_portal" and normalize_source("jobs.transforce.com") == "jobs_transforce_com"
    assert normalize_source("") == "csv"


def test_cli_csv_and_env_file(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("LEADS_DB=fromenv.db\n")
    monkeypatch.delenv("LEADS_DB", raising=False)
    (tmp_path / "x.csv").write_text("name,email\nZed Zed,zed@x.com\n")
    main(["csv", "x.csv"])
    assert "1 added" in capsys.readouterr().out
    assert Pipeline("fromenv.db").get(1)["name"] == "Zed Zed"


def test_ghl_sink_builds_upsert_request():
    from leads.sinks import GhlSink, sink_from_env
    calls = []
    sink = GhlSink("tok", "loc123", post=lambda url, body, headers: calls.append((url, body, headers)) or {"ok": 1})
    sink.send({"name": "Jane Q Driver", "email": "j@x.com", "phone": "", "source": "breezy",
               "job_title": "CDL Driver", "campaign": "certrig_hazmat"})
    url, body, headers = calls[0]
    assert url.endswith("/contacts/upsert")
    assert headers["Authorization"] == "Bearer tok" and headers["Version"] == "2021-07-28"
    assert body["locationId"] == "loc123" and body["firstName"] == "Jane" and body["lastName"] == "Q Driver"
    assert body["email"] == "j@x.com" and "phone" not in body and body["tags"] == ["certrig_hazmat", "breezy"]
    assert body["customFields"] == [{"key": "job_applied_for", "field_value": "CDL Driver"}]
    assert isinstance(sink_from_env({"LEADS_GHL_TOKEN": "t", "LEADS_GHL_LOCATION": "l"}), GhlSink)
    assert sink_from_env({"LEADS_WEBHOOK": "https://h"}).url == "https://h"
    assert sink_from_env({}) is None


def test_cli_sink_test_without_config(tmp_path, monkeypatch, capsys):
    import pytest
    monkeypatch.chdir(tmp_path)
    for k in ("LEADS_GHL_TOKEN", "LEADS_GHL_LOCATION", "LEADS_WEBHOOK"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(SystemExit):
        main(["--db", str(tmp_path / "x.db"), "sink-test"])
