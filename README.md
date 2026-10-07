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
