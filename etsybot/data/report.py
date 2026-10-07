"""Rank niches from stored signals. Scores are relative across YOUR niches only,
built from proxies (not sales). Treat as a shortlist, not a forecast."""
import statistics
from collections import defaultdict

DEMAND = {"etsy_median_favorers", "yt_median_views", "trends_interest", "trends_growth"}
COMPETITION = {"etsy_listing_count"}


def rank(rows, niches):
    by = defaultdict(lambda: defaultdict(list))        # metric -> niche -> values
    for niche, _kw, metric, value, _src in rows:
        by[metric][niche].append(value)
    norm = defaultdict(dict)                           # niche -> metric -> 0..1
    for metric, per in by.items():
        avg = {n: statistics.mean(v) for n, v in per.items()}
        lo, hi = min(avg.values()), max(avg.values())
        for n, a in avg.items():
            norm[n][metric] = 0.5 if hi == lo else (a - lo) / (hi - lo)
    out = []
    for n in niches:
        m = norm.get(n.name, {})
        dem = [v for k, v in m.items() if k in DEMAND]
        com = [v for k, v in m.items() if k in COMPETITION]
        score = (statistics.mean(dem) if dem else 0) - 0.5 * (statistics.mean(com) if com else 0)
        out.append({"niche": n.name, "score": score, "ip_risk": n.ip_risk,
                    "metrics": sorted(m), "n_signals": len(m)})
    return sorted(out, key=lambda r: r["score"], reverse=True)


def format_report(ranked):
    lines = [f"{'niche':<14}{'score':>7}  {'IP':<5}signals"]
    for r in ranked:
        flag = "HIGH" if r["ip_risk"] == "high" else "low"
        lines.append(f"{r['niche']:<14}{r['score']:>7.2f}  {flag:<5}{', '.join(r['metrics']) or 'NO DATA'}")
    lines.append("\nHIGH IP = fans expect licensed names/logos; use original, unlicensed designs only.")
    lines.append("Scores are relative proxies across these niches, not sales forecasts.")
    return "\n".join(lines)
