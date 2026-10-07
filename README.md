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
- Niches marked `ip_risk=high` (gaming, UFC, football, meme) need original, unlicensed designs.
