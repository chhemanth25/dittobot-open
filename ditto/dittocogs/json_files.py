import os
import random
from pathlib import Path

import discord
import ujson

RESOURCES = Path(os.environ["DIRECTORY"]) / "shared" / "data"

REDEEM_DROPS = ujson.load(open(RESOURCES / "redeem_drops.json"))

with open(RESOURCES / "pokemons.json") as f:
    PMONS = ujson.load(f)
with open(RESOURCES / "battle_items.json") as f:
    BATTLE_ITEMS = ujson.load(f)
with open(RESOURCES / "shop.json") as f:
    SHOP = ujson.load(f)
with open(RESOURCES / "pokemonfile.json") as f:
    PFILE = ujson.load(f)
with open(RESOURCES / "evofile.json") as f:
    EVOFILE = ujson.load(f)
with open(RESOURCES / "forms.json") as f:
    FORMS = ujson.load(f)
with open(RESOURCES / "statfile") as f:
    STATS = ujson.load(f)
with open(RESOURCES / "types.json") as f:
    TYPES = ujson.load(f)
with open(RESOURCES / "ptypes.json") as f:
    PTYPES = ujson.load(f)
with open(RESOURCES / "items.json") as f:
    ITEMS = ujson.load(f)
with open(RESOURCES / "moves.json") as f:
    MOVES = ujson.load(f)
with open(RESOURCES / "pokemon_abilities.json") as f:
    POKE_ABILITIES = ujson.load(f)
with open(RESOURCES / "abilities.json") as f:
    ABILITIES = ujson.load(f)
with open(RESOURCES / "region_starters.json") as f:
    REGION_STARTERS = ujson.load(f)
with open(RESOURCES / "pokemon_moves.json") as f:
    PMOVES = ujson.load(f)
with open(RESOURCES / "natures.json") as f:
    NATURES = ujson.load(f)
with open(RESOURCES / "stat_types.json") as f:
    STAT_TYPES = ujson.load(f)
with open(RESOURCES / "npc_images.json") as f:
    NPCS = ujson.load(f)

PKIDS = PFILE
T_IDS = PTYPES


def make_embed(title, description=None):
    return discord.Embed(
        title=title,
        description=description or "",
        color=random.choice(
            (16711888, 0xFFB6C1, 0xFF69B4, 0xFFC0CB, 0xC71585, 0xDB7093)
        ),
    )

def make_embed2(title, description=None, color=None):
    return discord.Embed(
        title=title,
        description=description or "",
        color=color
    )
