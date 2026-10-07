"""Synthetic marketplace. All numbers are SIMULATED, not real Etsy data."""
import math
import random
from dataclasses import dataclass, field


@dataclass
class Niche:
    name: str
    demand: float          # baseline daily sales per well-made listing
    trend: float           # drift in log-demand per day
    saturation: float      # 0..1, how crowded the niche is
    competitor_concepts: list = field(default_factory=list)


NICHES = [
    ("birth flower prints", 0.9, 0.004, 0.55),
    ("teacher appreciation gifts", 0.7, 0.000, 0.40),
    ("cottagecore candles", 0.8, 0.006, 0.60),
    ("pet memorial keepsakes", 0.6, 0.002, 0.30),
    ("bookish tote bags", 0.5, 0.005, 0.25),
    ("garden humor mugs", 0.4, -0.002, 0.35),
]


class Market:
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.niches = {
            n: Niche(n, d, t, s, [f"{n} classic design", f"{n} minimalist line art"])
            for n, d, t, s in NICHES
        }

    def step(self):
        for n in self.niches.values():
            n.demand *= math.exp(n.trend + self.rng.gauss(0, 0.02))
            n.saturation = min(0.95, max(0.05, n.saturation + self.rng.gauss(0.001, 0.005)))

    def signals(self):
        """What the research lab sees: public, aggregate signals per niche."""
        return [
            {"niche": n.name, "demand": n.demand, "trend": n.trend, "saturation": n.saturation}
            for n in self.niches.values()
        ]

    def expected_daily_sales(self, niche: str, quality: float, sibling_listings: int) -> float:
        n = self.niches[niche]
        # Own listings in one niche cannibalize each other.
        return n.demand * quality * (1 - n.saturation) / (1 + 0.1 * sibling_listings)
