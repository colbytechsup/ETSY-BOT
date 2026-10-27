# Certrig lead pipeline: to-do

Status 2026-10-27. Code is on branch `claude/loving-cerf-labso0` (PR #1). Tests pass.

## Decided
- Everyone in Breezy gets the course offer, regardless of stage (incl. Disqualified / Contacted).
- Offer content: limited-time pricing + the free demo. Lives in the GHL campaign, not in this code.
- Leads go into GoHighLevel (API with a Private Integration token, or an Inbound Webhook workflow).
- Breezy's "applied" notification email has NO contact details (verified on a real message).
  The candidate CSV export is the feed that carries email/phone; the email is an early signal
  that the export fills in (same name -> same record).
- Zoho Mail is not needed; its free plan has no IMAP. Don't pay for it for this.

## Needs a human (in order of value)
1. **GHL Private Integration token + Location ID** -> `.env` on the work PC, then
   `python -m leads sink-test`. Paste the output here. (Settings > Private Integrations,
   scope contacts.write; Settings > Business Profile for the Location ID.)
2. **Work PC setup**: Python 3 (Add to PATH), Git, clone repo, `git checkout claude/loving-cerf-labso0`,
   `copy certrig.env.example .env`, fill values.
3. **First real load**: export all candidates from Breezy (Candidates > tick all > More >
   Export Candidates), then `python -m leads csv <file>.csv --source breezy` and `python -m leads push`.
   Repeat the export weekly, or daily. Duplicates are ignored automatically.
4. **Intake Gmail (optional, for instant signal)**: pick the Gmail that gets Breezy's emails,
   turn on 2-Step Verification, create an App Password, put it in `.env`, and schedule
   `run_leads.cmd` every 15 min (README has the command).
5. **Other Breezy companies**: Mary's inbox also gets mail for "herman-n-logistics". If that
   company's candidates should get the offer too, export them as well.
6. **Legal check before the first send**: Breezy/Indeed terms on using applicant data for
   marketing; CAN-SPAM (postal address + opt-out are in the template); TCPA if GHL texts them.
7. **Fix the disapproved Breezy position** (LOCAL CDL-A DRIVERS UP TO $90K): unrelated to
   this pipeline; Breezy flagged an external apply link / phone-apply wording.

## Nice to have
- Breezy automated stage email with a course line (zero code, instant, but sent as the
  trucking company, not Certrig).
- GHL custom field for the job applied for (the sink sends `job_applied_for`; create the
  field in GHL or drop it from `GhlSink.send`).
