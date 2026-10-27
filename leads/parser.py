"""Parse a lead/applicant email (Indeed, ZipRecruiter, a website form, ...) into a Lead.

The subject and label patterns here are heuristics, not a spec: I do not have verified
samples of Indeed's current notification emails. Run a real message through
`python -m leads parse message.eml` and, if a field comes back blank, add the label or
subject shape you see to LABELS / SUBJECT_PATTERNS below."""
import email
import email.policy
import email.utils
import html
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

# Sender-domain fragment -> source name. Anything else is "email".
SOURCES = {
    "breezy": "breezy",  # Breezy system mail comes from support@breezy-mail.com (seen 2026-10)
    "indeed": "indeed", "ziprecruiter": "ziprecruiter", "linkedin": "linkedin",
    "craigslist": "craigslist", "facebookmail": "facebook", "glassdoor": "glassdoor",
    "monster": "monster", "careerbuilder": "careerbuilder",
}

# Platform addresses that are never the candidate. Exact domain match, so a relay
# subdomain (the kind a job board uses to mask a candidate's real address) still counts.
PLATFORM_DOMAINS = {"breezy-mail.com", "breezy.hr", "indeed.com", "ziprecruiter.com", "linkedin.com",
                    "craigslist.org", "facebookmail.com", "glassdoor.com", "monster.com",
                    "careerbuilder.com"}
NOISE_LOCALPARTS = ("noreply", "no-reply", "no_reply", "donotreply", "do-not-reply",
                    "unsubscribe", "support", "help", "privacy", "notifications", "alerts")

LABELS = {
    "name": ("candidate name", "applicant name", "full name", "candidate", "applicant", "name"),
    "email": ("email address", "e-mail", "email"),
    "phone": ("phone number", "telephone", "mobile", "phone", "cell"),
    "location": ("location", "city", "address"),
    "job_title": ("job title", "applied for", "applied to", "position", "job", "role"),
}

SUBJECT_PATTERNS = [
    r"^new (?:candidate|applicant|application|lead)(?: for (?P<job>.+?))?\s*[:\-]\s*"
    r"(?P<name>[^:]+?)(?: (?:has )?applied (?:to|for) (?P<job2>.+))?$",
    r"^(?P<name>[^:]+?) (?:has )?applied (?:to|for)(?: your)?(?: job)?[:\s]+(?P<job>.+)$",
    r"^(?P<name>[^:]+?) is interested in (?P<job>.+)$",
    r"^(?:you have a )?new (?:lead|inquiry|message)(?: from)?[:\-]?\s*(?P<name>.+)$",
    r"^(?:questionnaire|assessment|document) \w+ from (?P<name>.+)$",  # Breezy follow-ups
]

BREEZY_LINK_RE = re.compile(r"https://app\.breezy\.hr/r\?[^\"'\s]*candidate_id=([0-9a-f]+)")
BREEZY_HEADLINE_RE = re.compile(r"^(?P<h>[^\n@]{2,80} @ [^\n]{2,80})$", re.M)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\d-])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\d-])")
NAME_OK = re.compile(r"^[A-Za-z][A-Za-z' .-]{1,59}$")


@dataclass
class Lead:
    name: str = ""
    email: str = ""
    phone: str = ""
    source: str = "email"
    job_title: str = ""
    location: str = ""
    subject: str = ""
    sender: str = ""
    received: str = ""
    message_id: str = ""
    campaign: str = "certrig_hazmat"
    external_id: str = ""  # e.g. "breezy:<candidate_id>" from a notification link
    headline: str = ""     # e.g. "CDL Driver @ Sea Glass Trucking" (Breezy notification)

    def to_dict(self):
        return asdict(self)

    def dedup_key(self):
        if self.email:
            return "email:" + self.email.lower()
        if self.phone:
            return "phone:" + digits(self.phone)
        if self.external_id:
            return "ext:" + self.external_id
        if self.message_id:
            return "msgid:" + self.message_id
        return "subj:" + (self.name + "|" + self.subject).lower()


def digits(s):
    return re.sub(r"\D", "", s or "")


class _Text(HTMLParser):
    BLOCK = {"br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "table", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(src):
    p = _Text()
    p.feed(src)
    return html.unescape("".join(p.parts))


def clean_text(text):
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def body_text(msg):
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        content = html_to_text(content)
    return clean_text(content)


def detect_source(sender_addr):
    domain = sender_addr.rsplit("@", 1)[-1].lower()
    for frag, name in SOURCES.items():
        if frag in domain:
            return name
    return "email"


def _label_value(text, field):
    labels = "|".join(re.escape(l) for l in LABELS[field])
    m = re.search(rf"^(?:{labels})\s*[:\-–]\s*(?P<v>.+?)$", text, re.I | re.M)
    return m.group("v").strip() if m else ""


def parse_subject(subject):
    s = re.sub(r"^\s*(?:(?:re|fwd?|fw)\s*:\s*)+", "", subject, flags=re.I).strip()
    for pat in SUBJECT_PATTERNS:
        m = re.match(pat, s, re.I)
        if m:
            d = m.groupdict()
            name = (d.get("name") or "").strip(" \"'")
            job = (d.get("job") or d.get("job2") or "").strip()
            return (name if NAME_OK.match(name) else ""), job
    return "", ""


def pick_email(text, sender_addr, own_domains=()):
    own = {d.lower() for d in own_domains}
    for cand in EMAIL_RE.findall(text):
        local, domain = cand.lower().rsplit("@", 1)
        if cand.lower() == sender_addr.lower() or domain in own or domain in PLATFORM_DOMAINS:
            continue
        if any(n in local for n in NOISE_LOCALPARTS):
            continue
        return cand
    return ""


def raw_html(msg):
    part = msg.get_body(preferencelist=("html",))
    return part.get_content() if part is not None else ""


def parse_message(msg, own_domains=()):
    """`msg` is an email.message.EmailMessage (policy=email.policy.default)."""
    sender_name, sender_addr = email.utils.parseaddr(msg.get("From", ""))
    subject = str(msg.get("Subject", "")).strip()
    text = body_text(msg)
    external_id, headline = "", ""
    if "breezy" in sender_addr.lower():
        # Breezy's "X applied to Y" notification (seen 2026-10): no email/phone in it, just the
        # name, position, a "Title @ Employer" line and a review link carrying candidate_id.
        m = BREEZY_LINK_RE.search(html.unescape(raw_html(msg)))
        if m:
            external_id = "breezy:" + m.group(1)
        m = BREEZY_HEADLINE_RE.search(text)
        if m:
            headline = m.group("h").strip()
    subj_name, subj_job = parse_subject(subject)

    name = _label_value(text, "name") or subj_name
    email_addr = _label_value(text, "email")
    if not EMAIL_RE.fullmatch(email_addr or "x"):
        email_addr = pick_email(text, sender_addr, own_domains)
    phone = _label_value(text, "phone")
    if not PHONE_RE.search(phone or ""):
        m = PHONE_RE.search(text)
        phone = m.group(0).strip() if m else ""
    source = detect_source(sender_addr)
    # A plain "someone emailed us directly" lead: the sender is the person.
    if source == "email" and not email_addr and sender_addr and not any(
            n in sender_addr.lower() for n in NOISE_LOCALPARTS):
        email_addr, name = sender_addr, name or sender_name

    return Lead(
        name=name[:80], email=email_addr, phone=phone, source=source,
        job_title=(_label_value(text, "job_title") or subj_job)[:120],
        location=_label_value(text, "location")[:120],
        subject=subject[:200], sender=sender_addr,
        received=str(msg.get("Date", "")), message_id=str(msg.get("Message-ID", "")).strip(),
        external_id=external_id, headline=headline,
    )


def parse_bytes(raw, own_domains=()):
    return parse_message(email.message_from_bytes(raw, policy=email.policy.default), own_domains)


def parse_file(path, own_domains=()):
    with open(path, "rb") as f:
        return parse_bytes(f.read(), own_domains)
