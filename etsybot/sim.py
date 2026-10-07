"""Ultron: runs the rooms day by day and shifts capacity toward what earns."""
import random

from .llm import StubLLM
from .market import Market
from .rooms import AssetsRoom, EtsyRoom, ServicesRoom


class Ultron:
    def __init__(self, seed=0, target=1e12, llm=None):
        self.rng = random.Random(seed)
        self.llm = llm or StubLLM()
        self.market = Market(seed)
        self.rooms = [EtsyRoom(self.rng, self.llm), ServicesRoom(self.rng, self.llm),
                      AssetsRoom(self.rng, self.llm)]
        self.target, self.day = target, 0

    @property
    def profit(self):
        return sum(r.profit for r in self.rooms)

    def rebalance(self):
        ranked = sorted(self.rooms, key=lambda r: r.recent_profit)
        worst, best = ranked[0], ranked[-1]
        if worst is not best and worst.capacity > 1:
            worst.capacity -= 1
            best.capacity += 1

    def run(self, days):
        for _ in range(days):
            self.day += 1
            self.market.step()
            for r in self.rooms:
                r.step(self.day, self.market)
            if self.day % 7 == 0:
                self.rebalance()

    def report(self):
        lines = [f"Day {self.day}  (SIMULATED figures)"]
        for r in self.rooms:
            lines.append(f"  {r.name:<9} rev ${r.revenue:>10,.2f}  profit ${r.profit:>10,.2f}  capacity {r.capacity}")
        lines.append(f"  TOTAL profit ${self.profit:,.2f}  = {100 * self.profit / self.target:.8f}% of target ${self.target:,.0f}")
        return "\n".join(lines)
