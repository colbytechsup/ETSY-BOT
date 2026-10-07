"""Worker agents. Researcher reads signals; Designer must pass an originality gate."""
import re
from dataclasses import dataclass

TWISTS = ["watercolor", "retro 70s", "botanical", "hand-lettered", "geometric",
          "storybook", "moody dark academia", "pastel", "woodcut", "folk art"]
SUBJECTS = ["fox", "moth", "teapot", "mountain", "fern", "owl", "lantern", "mushroom"]
# Illustrative only; a real deployment must use a maintained trademark list.
BANNED = {"disney", "pokemon", "nike", "taylor swift", "harry potter", "marvel"}


def tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


@dataclass
class Design:
    niche: str
    concept: str
    quality: float


@dataclass
class Listing:
    title: str
    tags: list
    description: str
    price: float
    design: Design
    ai_disclosed: bool = True


class Researcher:
    """Ranks niches by demand, trend and headroom. Never looks at individual sellers."""

    def rank(self, signals, k=1):
        score = lambda s: s["demand"] * (1 + 50 * s["trend"]) * (1 - s["saturation"])
        return [s["niche"] for s in sorted(signals, key=score, reverse=True)[:k]]


class Designer:
    def __init__(self, rng, llm, threshold=0.5):
        self.rng, self.llm, self.threshold = rng, llm, threshold

    def create(self, niche, known_concepts):
        """Returns a Design, or None if nothing original enough was found."""
        for _ in range(8):
            base = f"{self.rng.choice(TWISTS)} {self.rng.choice(SUBJECTS)} {niche}"
            concept = self.llm.complete(
                f"Give a one-line original product concept for the niche '{niche}', "
                f"different from: {known_concepts[-5:]}", fallback=base)
            if all(jaccard(concept, k) < self.threshold for k in known_concepts):
                return Design(niche, concept, quality=self.rng.uniform(0.5, 1.0))
        return None


class Lister:
    def make(self, design: Design) -> Listing:
        words = design.concept.title()
        title = f"{words} | Unique Gift | Original Design"[:140]
        tags = list(dict.fromkeys(tokens(design.concept) | tokens(design.niche)))[:13]
        desc = (f"{words}. Designed with AI assistance and produced on demand. "
                "Original artwork; no licensed characters or brands.")
        return Listing(title, [t[:20] for t in tags], desc, price=24.0, design=design)


class QA:
    """Blocks listings that break basic marketplace rules."""

    def check(self, listing: Listing):
        issues, blob = [], f"{listing.title} {listing.description} {' '.join(listing.tags)}".lower()
        issues += [f"banned term: {b}" for b in BANNED if b in blob]
        if len(listing.title) > 140:
            issues.append("title too long")
        if len(listing.tags) > 13:
            issues.append("too many tags")
        if not listing.ai_disclosed:
            issues.append("missing AI disclosure")
        return issues
