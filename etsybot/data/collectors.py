"""Collectors return [(metric, value)] for one (niche, keyword). Official APIs / CSV only.
No HTML scraping. Every API response shape below is my understanding; verify against
current docs before relying on it (the code uses .get so a missing field just yields no metric)."""
import json
import os
import statistics
import urllib.parse
import urllib.request


def http_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


class EtsyCollector:
    """Etsy Open API v3 (needs ETSY_API_KEY). Competition proxy = result count;
    demand proxy = median favorers on top results. Check Etsy's API terms of use."""
    source = "etsy_api"

    def __init__(self, api_key=None, fetch=http_json):
        self.key, self.fetch = api_key or os.environ["ETSY_API_KEY"], fetch

    def collect(self, niche, keyword):
        q = urllib.parse.urlencode({"keywords": keyword, "limit": 50})
        data = self.fetch(f"https://openapi.etsy.com/v3/application/listings/active?{q}",
                          {"x-api-key": self.key})
        out = []
        if "count" in data:
            out.append(("etsy_listing_count", data["count"]))
        fav = [r["num_favorers"] for r in data.get("results", []) if "num_favorers" in r]
        if fav:
            out.append(("etsy_median_favorers", statistics.median(fav)))
        return out


class YouTubeCollector:
    """YouTube Data API v3 (needs YOUTUBE_API_KEY). Interest proxy = median views of
    top recent videos. search.list is quota-expensive (I believe ~100 units/call; verify)."""
    source = "youtube_api"

    def __init__(self, api_key=None, fetch=http_json):
        self.key, self.fetch = api_key or os.environ["YOUTUBE_API_KEY"], fetch

    def collect(self, niche, keyword):
        base = "https://www.googleapis.com/youtube/v3"
        q = urllib.parse.urlencode({"part": "id", "q": keyword, "type": "video",
                                    "order": "viewCount", "maxResults": 25, "key": self.key})
        ids = [i["id"]["videoId"] for i in self.fetch(f"{base}/search?{q}").get("items", [])
               if "videoId" in i.get("id", {})]
        if not ids:
            return []
        q = urllib.parse.urlencode({"part": "statistics", "id": ",".join(ids), "key": self.key})
        views = [int(v["statistics"]["viewCount"]) for v in self.fetch(f"{base}/videos?{q}").get("items", [])
                 if "viewCount" in v.get("statistics", {})]
        return [("yt_median_views", statistics.median(views))] if views else []


class TrendsCollector:
    """Google Trends via the unofficial `pytrends` package (pip install pytrends).
    Unofficial, may break or rate-limit. Metric is relative interest (0-100), not volume."""
    source = "google_trends"

    def __init__(self, fetch=None):
        self.fetch = fetch  # injectable for tests: fetch(keyword) -> list of weekly values

    def _series(self, keyword):
        from pytrends.request import TrendReq
        t = TrendReq()
        t.build_payload([keyword], timeframe="today 12-m")
        return list(t.interest_over_time()[keyword])

    def collect(self, niche, keyword):
        s = (self.fetch or self._series)(keyword)
        if not s:
            return []
        q = max(1, len(s) // 4)
        first, last = statistics.mean(s[:q]), statistics.mean(s[-q:])
        return [("trends_interest", statistics.mean(s)),
                ("trends_growth", (last / first) if first else 0.0)]


def import_csv(store, path, source="manual_csv"):
    """CSV columns: niche,keyword,metric,value. Use for numbers you copy from
    Etsy Shop Stats, eRank, etc. (check each tool's terms)."""
    import csv
    n = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            store.add(source, row["niche"], row["keyword"], row["metric"], row["value"])
            n += 1
    return n


def run(store, collectors, niches, log=print):
    """One failing collector or keyword never aborts the rest."""
    for niche in niches:
        for kw in niche.keywords:
            for c in collectors:
                try:
                    for metric, value in c.collect(niche.name, kw):
                        store.add(c.source, niche.name, kw, metric, value)
                except Exception as e:  # network, quota, shape changes
                    log(f"[{c.source}] {niche.name}/{kw}: {type(e).__name__}: {e}")
