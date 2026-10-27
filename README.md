# ETSY-BOT

A multi-agent business simulation: an orchestrator ("Ultron") runs **factory rooms**
(Etsy print-on-demand stores, a thumbnail service, game-asset packs). Worker agents
research, design, list, and QA products; Ultron shifts capacity toward the rooms that earn.

    python -m etsybot --days 90 [--seed N] [--target 1e12] [--api]
    pip install pytest && pytest

## Important caveats
- **All money figures are simulated** against a synthetic market (`market.py`). They say
  nothing about real Etsy/Fiverr income. Fee rates in `rooms.py` are marked ASSUMPTION; verify them.
- **Research uses aggregate signals, not other sellers' products.** Designs must pass an
  originality gate (`agents.Designer`) and QA (`agents.QA`): trademark list, Etsy title/tag
  limits (140 chars / 13 tags, as I understand them; verify), and AI disclosure.
  The trademark list is a tiny illustrative sample, not a legal filter.
- The services room sells real work with revisions. Don't sell something while hiding that it's free.
- `--api` uses the Anthropic API (`pip install anthropic`, set `ANTHROPIC_API_KEY` and `ETSYBOT_MODEL`). It is untested here.

## Next steps
Real marketplace APIs (check each one's terms), an image-generation agent, an affiliate-blog room, persistent state.

## Data collection agents (start here)
Collect real signals for the niches in `etsybot/data/niches.py`, then rank them.

    export YOUTUBE_API_KEY=...   # YouTube Data API v3
    export ETSY_API_KEY=...      # Etsy Open API v3 (needs an approved key)
    python -m etsybot.collect run --sources youtube,etsy,trends
    python -m etsybot.collect csv mydata.csv      # niche,keyword,metric,value (manual numbers)
    python -m etsybot.collect report

- Official APIs and CSV import only; no scraping of Etsy pages.
- API response shapes are my understanding and untested against the live services. Verify.
- Google Trends uses the unofficial `pytrends` package (may break or rate-limit).
- Scores are relative proxies (favorites, views, listing counts), not sales. They are a shortlist, not a forecast.
- Niches marked `ip_risk=high` (UFC, meme) need original, unlicensed designs.

## Lead email parser -> marketing pipeline (`leads/`)
Turns applicant/lead emails (Indeed, ZipRecruiter, direct emails, website forms) into rows
in a sqlite pipeline, pushes new ones to your marketing tool, and drafts a CertRig hazmat
course follow-up. Stdlib only.

    python -m leads parse sample.eml            # test the parser on a saved email (no DB)
    python -m leads ingest a.eml b.eml          # parse into leads.db (dedups by email/phone)
    export LEADS_IMAP_HOST=imap.gmail.com LEADS_IMAP_USER=... LEADS_IMAP_PASSWORD=...
    export LEADS_OWN_DOMAINS=phtruckingpros.com # addresses that are never the lead
    python -m leads sink-test                   # one fake contact into GHL to prove the setup
    python -m leads imap                        # pull unread, push new leads to GHL
    python -m leads list --status new
    python -m leads push --webhook URL          # push anything still 'new'
    python -m leads export leads.csv            # for a mail-merge / import into your CRM
    python -m leads draft 3                     # follow-up email for lead #3
    cp certrig.env.example .env && $EDITOR .env && set -a && . ./.env && set +a   # Zoho + Certrig values
    python -m leads send                        # dry run: shows who would get the follow-up
    python -m leads send --really               # sends to every 'new' lead, marks them 'contacted'
    python -m leads status 3 --to enrolled

**Simplest setup, no marketing tool needed:** use the course's support mailbox for everything.
Have the Breezy/Indeed notifications auto-forwarded to it (a Gmail filter on Todd's account),
point `LEADS_IMAP_*` and `LEADS_SMTP_*` at that mailbox, and run `imap` then `send --really`
on a schedule. Follow-ups go out from the support address, replies land in the same inbox,
and a reply starting with "stop"/"unsubscribe" from a known lead automatically marks them
`not_interested` on the next `imap` run (they are never emailed again).

    python -m leads csv breezy-export.csv --source breezy   # backfill from a candidate export

**Windows (always-on work PC) setup.** Install Python 3 from python.org (tick "Add to PATH"),
clone this repo, copy `certrig.env.example` to `.env` in the repo folder and fill in the
Zoho password and the GHL webhook URL. Test by hand first:

    python -m leads ingest sample.eml      # or: python -m leads imap --keep-unread
    python -m leads list

Then schedule `run_leads.cmd` every 15 minutes (run from an admin Command Prompt, one line):

    schtasks /Create /SC MINUTE /MO 15 /TN "Certrig leads" /TR "\"C:\path\to\ETSY-BOT\run_leads.cmd\"" /RL LIMITED

Output accumulates in `leads.log` next to the script. Zoho Mail: switch on IMAP access in
its settings and use an app-specific password if two-factor auth is on.

**GoHighLevel.** Two ways in. (A) The public API with a Private Integration token
(`LEADS_GHL_TOKEN` + `LEADS_GHL_LOCATION`): each lead is upserted as a contact tagged
`certrig_hazmat` and its source, with the job in a custom field; no per-run charge that I
know of. The endpoint/header values are my reading of the v2 docs and are untested against
the live API, so run `sink-test` first. (B) A workflow "Inbound Webhook" trigger
(`LEADS_WEBHOOK`); that is a Premium Action billed per execution. Either way GHL's own
campaign does the emailing, so `send` and the SMTP settings are not needed.

- **Indeed's email layout is not verified.** The parser looks for labelled lines
  (`Name:`, `Phone:`, `Email:`, `Applied for:` ...) and subjects like "Jane Doe applied to
  CDL Driver". Save a real notification as .eml (Gmail: "Show original" -> download) and run
  `parse` on it; if a field is blank, add the label/subject shape to `leads/parser.py`.
  Indeed may mask the candidate's real address behind a relay address; the parser keeps
  those, but replies through them may be subject to Indeed's rules.
- **Check before marketing to applicants.** They applied for a job, not a course. Indeed's
  terms (as I understand them; verify in the current Indeed Employer terms) restrict use of
  candidate data to recruiting for the posted job. Email marketing falls under CAN-SPAM
  (identify yourself, honest subject, working opt-out) and texting/auto-dialing under the
  TCPA, which generally needs prior consent. I am not a lawyer; verify with one before
  turning this on. The draft in `leads/outreach.py` includes an opt-out line for that reason.
- The webhook payload is the Lead fields as JSON; map them to your tool's fields on the
  receiving side (Zapier/Make/HubSpot). No tool-specific API is implemented.
