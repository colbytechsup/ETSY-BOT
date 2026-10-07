import random

from etsybot.agents import Designer, Lister, QA, jaccard, Design
from etsybot.llm import StubLLM
from etsybot.sim import Ultron


def test_deterministic():
    a, b = Ultron(seed=3), Ultron(seed=3)
    a.run(30); b.run(30)
    assert a.profit == b.profit


def test_originality_gate_rejects_copies():
    d = Designer(random.Random(0), StubLLM(), threshold=0.0)  # nothing is original enough
    assert d.create("x", ["anything"]) is None
    assert jaccard("a b c", "a b c") == 1.0


def test_qa_blocks_trademarks_and_missing_disclosure():
    l = Lister().make(Design("n", "retro fox", 0.9))
    assert QA().check(l) == []
    l.title = "Disney inspired " + l.title
    assert QA().check(l)
    l.ai_disclosed = False
    assert "missing AI disclosure" in QA().check(l)


def test_listing_limits():
    l = Lister().make(Design("n", "word " * 80, 0.9))
    assert len(l.title) <= 140 and len(l.tags) <= 13
