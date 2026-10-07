"""python -m etsybot.collect run --sources youtube,etsy,trends | csv FILE | report"""
import argparse
import os

from .data.collectors import EtsyCollector, TrendsCollector, YouTubeCollector, import_csv, run
from .data.niches import NICHES
from .data.report import format_report, rank
from .data.store import Store

p = argparse.ArgumentParser(prog="etsybot.collect")
p.add_argument("cmd", choices=["run", "csv", "report"])
p.add_argument("arg", nargs="?")
p.add_argument("--sources", default="youtube,etsy,trends")
p.add_argument("--db", default="signals.db")
a = p.parse_args()
store = Store(a.db)

if a.cmd == "csv":
    print(f"imported {import_csv(store, a.arg)} rows")
elif a.cmd == "run":
    makers = {"youtube": (YouTubeCollector, "YOUTUBE_API_KEY"), "etsy": (EtsyCollector, "ETSY_API_KEY"),
              "trends": (TrendsCollector, None)}
    cols = []
    for s in a.sources.split(","):
        cls, env = makers[s]
        if env and not os.environ.get(env):
            print(f"skipping {s}: set {env}")
        else:
            cols.append(cls())
    run(store, cols, NICHES)
print(format_report(rank(store.latest(), NICHES)))
