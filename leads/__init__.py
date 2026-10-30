"""Lead-email parser and marketing pipeline (CertRig hazmat course).

Flow: inbox (IMAP) or .eml files -> parser.Lead -> pipeline.Pipeline (sqlite, dedup)
-> sinks (CSV / webhook to your marketing tool) -> outreach.draft (follow-up email)."""
