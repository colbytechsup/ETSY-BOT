"""Factory rooms. Each room runs one business and reports daily profit."""
from .agents import Designer, Lister, QA, Researcher

ETSY_FEE = 0.065      # ASSUMPTION: verify current Etsy fees before trusting P&L
LISTING_FEE = 0.20    # ASSUMPTION
FIVERR_FEE = 0.20     # ASSUMPTION


class Room:
    name = "room"

    def __init__(self, rng, llm):
        self.rng, self.llm = rng, llm
        self.capacity = 2          # work units per day; Ultron reallocates this
        self.revenue = self.cost = 0.0
        self.trailing = []         # recent daily profits

    def record(self, rev, cost):
        self.revenue += rev
        self.cost += cost
        self.trailing = (self.trailing + [rev - cost])[-14:]

    @property
    def profit(self):
        return self.revenue - self.cost

    @property
    def recent_profit(self):
        return sum(self.trailing) / len(self.trailing) if self.trailing else 0.0

    def _sales(self, expected):
        return int(expected) + (self.rng.random() < expected % 1)


class EtsyRoom(Room):
    name = "etsy"

    def __init__(self, rng, llm, stores=3):
        super().__init__(rng, llm)
        self.stores = {f"store-{i+1}": [] for i in range(stores)}
        self.researcher, self.lister, self.qa = Researcher(), Lister(), QA()
        self.designer = Designer(rng, llm)
        self.rejected = 0

    def step(self, day, market):
        rev = cost = 0.0
        for listings in self.stores.values():
            for niche in self.researcher.rank(market.signals(), k=1):
                known = market.niches[niche].competitor_concepts + [l.design.concept for l in listings]
                for _ in range(self.capacity):
                    design = self.designer.create(niche, known)
                    if not design:
                        self.rejected += 1
                        continue
                    listing = self.lister.make(design)
                    if self.qa.check(listing):
                        self.rejected += 1
                        continue
                    listings.append(listing)
                    known.append(design.concept)
                    cost += LISTING_FEE
            counts = {}
            for l in listings:
                counts[l.design.niche] = counts.get(l.design.niche, 0) + 1
            for l in listings:
                n = self._sales(market.expected_daily_sales(
                    l.design.niche, l.design.quality, counts[l.design.niche] - 1))
                rev += n * l.price
                cost += n * (l.price * 0.45 + l.price * ETSY_FEE)   # POD base cost ~45%: ASSUMPTION
        self.record(rev, cost)


class ServicesRoom(Room):
    """Thumbnail design service. Sells real work, with revisions, at a fair price."""
    name = "services"
    PRICE = 20.0

    def __init__(self, rng, llm):
        super().__init__(rng, llm)
        self.rating = 4.5

    def step(self, day, market):
        orders = self._sales(self.capacity * 1.5 * (self.rating / 5))
        rev = cost = 0.0
        for _ in range(orders):
            good = self.rng.random() < 0.85
            self.rating = min(5.0, max(3.0, self.rating + (0.01 if good else -0.05)))
            rev += self.PRICE * (1 - FIVERR_FEE)
            cost += 0.80 + (0 if good else 0.80)   # a revision costs another pass
        self.record(rev, cost)


class AssetsRoom(Room):
    """2D game-asset packs sold on marketplaces; each pack sells slowly forever."""
    name = "assets"
    PRICE = 12.0

    def __init__(self, rng, llm):
        super().__init__(rng, llm)
        self.packs = []   # per-pack daily sale rates

    def step(self, day, market):
        cost = 0.0
        for _ in range(self.capacity):
            self.packs.append(self.rng.uniform(0.02, 0.15))
            cost += 1.50
        sold = sum(self._sales(r) for r in self.packs)
        self.record(sold * self.PRICE * 0.7, cost)   # 30% marketplace cut: ASSUMPTION
