import argparse

from .llm import make_llm
from .sim import Ultron

p = argparse.ArgumentParser(prog="etsybot")
p.add_argument("--days", type=int, default=90)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--target", type=float, default=1e12)
p.add_argument("--api", action="store_true", help="use Anthropic API for concepts")
a = p.parse_args()

u = Ultron(seed=a.seed, target=a.target, llm=make_llm(a.api))
for _ in range(a.days // 30):
    u.run(30)
    print(u.report())
if a.days % 30:
    u.run(a.days % 30)
    print(u.report())
