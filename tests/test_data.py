from etsybot.data.collectors import EtsyCollector, TrendsCollector, YouTubeCollector, import_csv, run
from etsybot.data.niches import Niche
from etsybot.data.report import rank
from etsybot.data.store import Store


def test_etsy_collector_parses_and_tolerates_missing_fields():
    c = EtsyCollector("k", fetch=lambda url, h: {"count": 500, "results": [{"num_favorers": 4}, {"num_favorers": 10}, {}]})
    assert dict(c.collect("n", "kw")) == {"etsy_listing_count": 500, "etsy_median_favorers": 7}
    assert EtsyCollector("k", fetch=lambda u, h: {}).collect("n", "kw") == []


def test_youtube_collector():
    def fake(url, headers=None):
        if "/search" in url:
            return {"items": [{"id": {"videoId": "a"}}, {"id": {"videoId": "b"}}]}
        return {"items": [{"statistics": {"viewCount": "100"}}, {"statistics": {"viewCount": "300"}}]}
    assert YouTubeCollector("k", fetch=fake).collect("n", "kw") == [("yt_median_views", 200)]


def test_trends_growth():
    out = dict(TrendsCollector(fetch=lambda kw: [10, 10, 20, 20]).collect("n", "kw"))
    assert out["trends_growth"] == 2.0


def test_runner_survives_failures_and_report_ranks(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    niches = [Niche("a", ["x"], "low"), Niche("b", ["y"], "high")]

    class Boom:
        source = "boom"
        def collect(self, n, k): raise RuntimeError("quota")

    class Fake:
        source = "fake"
        def collect(self, n, k):
            return [("yt_median_views", 1000 if n == "a" else 10), ("etsy_listing_count", 5 if n == "a" else 900)]

    logs = []
    run(store, [Boom(), Fake()], niches, log=logs.append)
    assert len(logs) == 2
    ranked = rank(store.latest(), niches)
    assert ranked[0]["niche"] == "a" and ranked[1]["ip_risk"] == "high"


def test_csv_import(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("niche,keyword,metric,value\nskiing,ski shirt,etsy_listing_count,1234\n")
    store = Store(str(tmp_path / "s.db"))
    assert import_csv(store, str(f)) == 1
    assert store.latest()[0][3] == 1234
