"""Niches to research. ip_risk='high' means fans expect licensed names/logos,
so only original, unlicensed designs are safe there."""
from dataclasses import dataclass


@dataclass
class Niche:
    name: str
    keywords: list
    ip_risk: str  # "low" | "high"


NICHES = [
    Niche("skiing", ["ski shirt", "skiing gift", "ski poster", "apres ski sweatshirt"], "low"),
    Niche("climbing", ["climbing shirt", "bouldering gift", "climbing poster", "rock climbing sticker"], "low"),
    Niche("surf_skate", ["surf shirt", "skateboard sticker", "surf poster", "skate tee"], "low"),
    Niche("classic_style", ["vintage graphic tee", "retro poster", "70s style print", "classic crewneck"], "low"),
    Niche("gaming", ["gamer shirt", "gaming poster", "gamer gift", "retro gaming tee"], "high"),
    Niche("ufc_mma", ["mma shirt", "jiu jitsu gift", "martial arts poster", "fight night tee"], "high"),
    Niche("football", ["football shirt", "football gift", "football poster", "game day sweatshirt"], "high"),
    Niche("meme", ["meme shirt", "funny graphic tee", "meme sticker", "ironic tee"], "high"),
]
