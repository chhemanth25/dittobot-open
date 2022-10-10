from datetime import datetime, timedelta

import discord
from discord.ext import commands
from utils.misc import AsyncIter, MenuView, get_emoji, pagify

from dittocogs.json_files import *
from dittocogs.pokemon_list import *

KEYS = {
    "name": "name",  # FILTER AND ORDER
    "names": "name",
    "evo": "evo",
    "starter": "starter",
    "legend": "legend",
    "legendary": "legend",
    "ultra": "ultra",
    "pseudo": "pseudo",
    "alola": "alola",
    "galar": "galar",
    "hisui": "hisui",
    "type": "type",
    "types": "type",
    "egg-group": "egg-group",
    "egg-groups": "egg-group",
    "egg": "egg-group",
    "item": "item",
    "nickname": "nickname",
    "nick": "nickname",
    "nature": "nature",
    "female": "female",
    "male": "male",
    "genderless": "genderless",
    "shiny": "shiny",
    "radiant": "radiant",
    "regular": "regular",
    "owned": "owned",
    "ot": "ot",
    "notot": "notot",
    "fav": "fav",
    "level": "level",  # FILTER AND ORDER
    "atkiv": "atkiv",
    "defiv": "defiv",
    "spatkiv": "spatkiv",
    "spdefiv": "spdefiv",
    "hpiv": "hpiv",
    "speediv": "speediv",
    "tags": "tags",
    "tag": "tags",
    "skin": "skins",
    "skins": "skins",
    "cooldown": "cooldown",
    "cooldowned": "cooldown",
    "cooldowns": "cooldown",
    "cd": "cooldown",
    "hidden-power": "hidden-power",
    "hp": "hidden-power",
    # 'fossil':   'fossil', TODO
    "price": "price",  # FILTER AND ORDER
    "iv": "iv",  # ORDER
    "ev": "ev",  # ORDER
    "id": "id",  # ORDER
}
PRECEDENCE = {"!": 3, "&": 2, "|": 1}
PER_PAGE = 15
PAGE_COUNT = 150
POKE_COUNT = PER_PAGE * PAGE_COUNT


class ExtractionException(ValueError):
    pass


class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # If no args are provided, male | !male is used to just ensure the user gets an output.
    # This is equivalent to no filter without breaking the code

    @commands.hybrid_group(name="f")
    async def f(self, ctx):
        ...

    @f.command(name="m")
    async def filter_market(self, ctx, args="male | !male"):
        try:
            await self._build_query(ctx, args, "m")
        except ExtractionException as e:
            await ctx.send(f"Your filter args were not valid.\n{e}")

    @f.command(name="p")
    async def filter_pokemon(self, ctx, args="male | !male"):
        try:
            await self._build_query(ctx, args, "p")
        except ExtractionException as e:
            await ctx.send(f"Your filter args were not valid.\n{e}")

    async def _expand_forms(self, ctx, names):
        forms = set()
        for name in names:
            forms.add(name)
            if name == "Egg":
                continue
            region = ""
            if any(name.endswith(x) for x in ["-galar", "-alola", "-hisui"]):
                region = name[:-6]
                name = name[:-6]
            cursor = ctx.bot.db[1].forms.find(
                {"identifier": {"$regex": f"{name.lower()}-.*"}}
            )
            forms |= {
                t.capitalize() + region
                for t in await cursor.distinct("identifier")
                if not any(t.endswith(x) for x in ["-galar", "-alola", "-hisui"])
            }

        return forms

    async def _build_query(self, ctx, args, filter_type):
        """
        Takes the args of a filter command and builds a PostgreSQL query for that set of args.

        Supports "&" or "." for AND, "|" for OR, and "!" for NOT.
        Respects order of opperations and parentheses.
        Sends a menu view of the filtered results to ctx.
        https://www.digitalocean.com/community/conceptual_articles/understanding-order-of-operations
        """
        args = args.strip(".&| ")
        order_col = None  # The column to sort by.
        order_dir = "DESC"  # The direction of the sort.
        sql_data = (
            []
        )  # The raw data values by the user to be past to postgres. Using $1 notation to prevent an SQL injection.
        mothers = {}

        if filter_type == "p":
            async with ctx.bot.db[0].acquire() as pconn:
                pokes = await pconn.fetchval(
                    "SELECT pokes FROM users WHERE u_id = $1", ctx.author.id
                )
                mother_raw = await pconn.fetch(
                    f"SELECT pokemon_id, entry_time FROM mothers WHERE pokemon_id = ANY($1)",
                    pokes,
                )
                mothers = {t["pokemon_id"]: t["entry_time"] for t in mother_raw}
            if pokes is None:
                await ctx.send(f"You have not started!\nStart with `/start` first.")
                return
            pokes = tuple(pokes)
            sql_data.append(pokes)

        # Splits the raw args string into a list of "tokens" that are easier for the code to understand.
        tokens = []
        hold = ""
        for c in args:
            if c in (".", "!", "&", "|", "(", ")"):
                hold = hold.strip()
                if hold:
                    tokens.append(hold)
                tokens.append(c.replace(".", "&"))
                hold = ""
            else:
                hold += c
        hold = hold.strip()
        if hold:
            tokens.append(hold)

        # Converts the raw tokens into a postfix notation based on order of opperations.
        # Also converts the operands from user-syntax to postgres-syntax.
        postfix = []
        operator_stack = []
        for token in tokens:
            if token == "(":
                operator_stack.append(token)
            elif token == ")":
                if "(" not in operator_stack:
                    raise ExtractionException("A `)` symbol is missing a matching `(`.")
                while operator_stack[-1] != "(":
                    postfix.append(operator_stack.pop())
                operator_stack.pop()
            elif token in ("!", "&", "|"):
                while (
                    operator_stack
                    and operator_stack[-1] != "("
                    and PRECEDENCE[operator_stack[-1]] > PRECEDENCE[token]
                ):
                    postfix.append(operator_stack.pop())
                operator_stack.append(token)
            else:
                part = token.split()
                if not part:
                    continue
                if part[0] not in KEYS:
                    raise ExtractionException(f"`{part[0]}` is not a valid arg.")
                key = KEYS[part[0]]
                data = part[1:]

                # Converts key/data into a postgres conditional
                if key == "name":
                    if not data:
                        order_col = "pokname"
                        order_dir = "ASC"
                        postfix.append("false")
                    elif data[0] in ("d", "desc", "descending"):
                        order_col = "pokname"
                        order_dir = "DESC"
                        postfix.append("false")
                    elif data[0] in ("a", "asc", "ascending"):
                        order_col = "pokname"
                        order_dir = "ASC"
                        postfix.append("false")
                    else:
                        names = set()
                        for name in data:
                            name = name.replace(".", "").capitalize()
                            names.add(name)
                        names = await self._expand_forms(ctx, names)
                        sql_data.append(list(names))
                        postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "evo":
                    names = set()
                    for evo in data:
                        evo = evo.replace(".", "").lower()
                        evo_poke = await ctx.bot.db[1].pfile.find_one(
                            {"identifier": evo.lower()}
                        )
                        if not evo_poke:
                            continue
                        evo_chain = evo_poke["evolution_chain_id"]
                        async for file in ctx.bot.db[1].pfile.find(
                            {"evolution_chain_id": evo_chain}
                        ):
                            names.add(file["identifier"].capitalize())
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "starter":
                    names = set(starterList)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "legend":
                    names = set(LegendList)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "ultra":
                    names = set(ubList)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "pseudo":
                    names = set(pseudoList)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "alola":
                    names = set(alolans)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "galar":
                    names = set(galarians)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "hisui":
                    names = set(hisuians)
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "type":
                    names = set()
                    for type in data:
                        type = type.lower()
                        type_info = await ctx.bot.db[1].types.find_one(
                            {"identifier": type}
                        )
                        if not type_info:
                            continue
                        cursor = ctx.bot.db[1].ptypes.find({"types": type_info["id"]})
                        pokemon_ids = [
                            record["id"] for record in await cursor.to_list(length=None)
                        ]
                        cursor = ctx.bot.db[1].forms.find(
                            {"pokemon_id": {"$in": pokemon_ids}}
                        )
                        names.update(
                            [
                                record["identifier"].capitalize()
                                for record in await cursor.to_list(length=None)
                            ]
                        )
                    # Does NOT expand forms, as forms can have different types
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "egg-group":
                    names = set()
                    egg_group_ids = [
                        result["id"]
                        for result in await ctx.bot.db[1]
                        .egg_groups_info.find(
                            {"identifier": {"$in": [group.lower() for group in data]}}
                        )
                        .to_list(length=None)
                    ]
                    pokemon_ids = [
                        result["species_id"]
                        for result in await ctx.bot.db[1]
                        .egg_groups.find({"egg_groups": {"$in": egg_group_ids}})
                        .to_list(length=800)
                    ]
                    cursor = ctx.bot.db[1].forms.find(
                        {"pokemon_id": {"$in": pokemon_ids}}
                    )
                    names.update(
                        [
                            record["identifier"].capitalize()
                            for record in await cursor.to_list(length=None)
                        ]
                    )
                    names = await self._expand_forms(ctx, names)
                    sql_data.append(list(names))
                    postfix.append(f"pokname = ANY(${len(sql_data)})")
                elif key == "item":
                    items = set()
                    for item in data:
                        items.add(item.lower())
                    sql_data.append(list(items))
                    postfix.append(f"hitem = ANY(${len(sql_data)})")
                elif key == "nickname":
                    nick = " ".join(data).lower()
                    sql_data.append(nick)
                    postfix.append(f"lower(poknick) = ${len(sql_data)}")
                elif key == "nature":
                    natures = set()
                    for nature in data:
                        natures.add(nature.capitalize())
                    sql_data.append(list(natures))
                    postfix.append(f"nature = ANY(${len(sql_data)})")
                elif key == "tags":
                    tags = set()
                    for tag in data:
                        tags.add(tag.lower())
                    sql_data.append(list(tags))
                    postfix.append(f"tags && ${len(sql_data)}")
                elif key == "skins":
                    if not data:
                        postfix.append(f"skin IS NOT NULL")
                    else:
                        skins = set()
                        for skin in data:
                            skins.add(skin.lower())
                        sql_data.append(list(skins))
                        postfix.append(f"skin = ANY(${len(sql_data)})")
                elif key == "cooldown":
                    if filter_type != "p":
                        raise ExtractionException(
                            "`cooldown` is only a valid key in pokemon filters."
                        )
                    sql_data.append(tuple(mothers.keys()))
                    postfix.append(f"id = ANY(${len(sql_data)})")
                elif key == "female":
                    postfix.append("gender = '-f'")
                elif key == "male":
                    postfix.append("gender = '-m'")
                elif key == "genderless":
                    postfix.append("gender = '-x'")
                elif key == "shiny":
                    postfix.append("shiny = true")
                elif key == "radiant":
                    postfix.append("radiant = true")
                elif key == "regular":
                    postfix.append("(NOT shiny AND NOT radiant)")
                elif key == "owned":
                    if filter_type != "m":
                        raise ExtractionException(
                            "`owned` is only a valid key in market filters."
                        )
                    sql_data.append(ctx.author.id)
                    postfix.append(f"owner = ${len(sql_data)}")
                elif key == "ot":
                    if not data:
                        sql_data.append(ctx.author.id)
                    else:
                        try:
                            sql_data.append(int(data[0]))
                        except ValueError:
                            raise ExtractionException(
                                "`ot` only accepts a discord user id."
                            )
                    postfix.append(f"caught_by = ${len(sql_data)}")
                elif key == "notot":
                    sql_data.append(ctx.author.id)
                    postfix.append(f"NOT caught_by = ${len(sql_data)}")
                elif key == "fav":
                    postfix.append(f"fav = true")
                elif key == "level":
                    try:
                        is_filter = False
                        if not data:
                            order_col = "pokelevel"
                            order_dir = "DESC"
                            postfix.append("false")
                        elif data[0].startswith("d"):
                            order_col = "pokelevel"
                            order_dir = "DESC"
                            postfix.append("false")
                        elif data[0].startswith("a"):
                            order_col = "pokelevel"
                            order_dir = "ASC"
                            postfix.append("false")
                        elif data[0] == ">" and len(data) > 1:
                            level_min = int(data[1])
                            level_max = 100
                            is_filter = True
                        elif data[0] == "<" and len(data) > 1:
                            level_min = 0
                            level_max = int(data[1])
                            is_filter = True
                        else:
                            level = int(data[0])
                            level_min = level
                            level_max = level
                            is_filter = True
                    except ValueError:
                        raise ExtractionException(
                            "`level` received invalid non-numeric input."
                        )
                    else:
                        if is_filter:
                            sql_data.append(level_max)
                            sql_data.append(level_min)
                            postfix.append(
                                f"(pokelevel <= ${len(sql_data) - 1} AND pokelevel >= ${len(sql_data)})"
                            )
                elif key == "atkiv":
                    try:
                        if not data:
                            raise ExtractionException(
                                "`atkiv` requires additional information."
                            )
                        elif data[0] == ">" and len(data) > 1:
                            atkiv_min = int(data[1])
                            atkiv_max = 31
                        elif data[0] == "<" and len(data) > 1:
                            atkiv_min = 0
                            atkiv_max = int(data[1])
                        else:
                            atkiv = int(data[0])
                            atkiv_min = atkiv
                            atkiv_max = atkiv
                    except ValueError:
                        raise ExtractionException(
                            "`atkiv` received invalid non-numeric input."
                        )
                    else:
                        sql_data.append(atkiv_max)
                        sql_data.append(atkiv_min)
                        postfix.append(
                            f"(atkiv <= ${len(sql_data) - 1} AND atkiv >= ${len(sql_data)})"
                        )
                elif key == "defiv":
                    try:
                        if not data:
                            raise ExtractionException(
                                "`defiv` requires additional information."
                            )
                        elif data[0] == ">" and len(data) > 1:
                            defiv_min = int(data[1])
                            defiv_max = 31
                        elif data[0] == "<" and len(data) > 1:
                            defiv_min = 0
                            defiv_max = int(data[1])
                        else:
                            defiv = int(data[0])
                            defiv_min = defiv
                            defiv_max = defiv
                    except ValueError:
                        raise ExtractionException(
                            "`defiv` received invalid non-numeric input."
                        )
                    else:
                        sql_data.append(defiv_max)
                        sql_data.append(defiv_min)
                        postfix.append(
                            f"(defiv <= ${len(sql_data) - 1} AND defiv >= ${len(sql_data)})"
                        )
                elif key == "spatkiv":
                    try:
                        if not data:
                            raise ExtractionException(
                                "`spatkiv` requires additional information."
                            )
                        elif data[0] == ">" and len(data) > 1:
                            spatkiv_min = int(data[1])
                            spatkiv_max = 31
                        elif data[0] == "<" and len(data) > 1:
                            spatkiv_min = 0
                            spatkiv_max = int(data[1])
                        else:
                            spatkiv = int(data[0])
                            spatkiv_min = spatkiv
                            spatkiv_max = spatkiv
                    except ValueError:
                        raise ExtractionException(
                            "`spatkiv` received invalid non-numeric input."
                        )
                    else:
                        sql_data.append(spatkiv_max)
                        sql_data.append(spatkiv_min)
                        postfix.append(
                            f"(spatkiv <= ${len(sql_data) - 1} AND spatkiv >= ${len(sql_data)})"
                        )
                elif key == "spdefiv":
                    try:
                        if not data:
                            raise ExtractionException(
                                "`spdefiv` requires additional information."
                            )
                        elif data[0] == ">" and len(data) > 1:
                            spdefiv_min = int(data[1])
                            spdefiv_max = 31
                        elif data[0] == "<" and len(data) > 1:
                            spdefiv_min = 0
                            spdefiv_max = int(data[1])
                        else:
                            spdefiv = int(data[0])
                            spdefiv_min = spdefiv
                            spdefiv_max = spdefiv
                    except ValueError:
                        raise ExtractionException(
                            "`spdefiv` received invalid non-numeric input."
                        )
                    else:
                        sql_data.append(spdefiv_max)
                        sql_data.append(spdefiv_min)
                        postfix.append(
                            f"(spdefiv <= ${len(sql_data) - 1} AND spdefiv >= ${len(sql_data)})"
                        )
                elif key == "hpiv":
                    try:
                        if not data:
                            raise ExtractionException(
                                "`hpiv` requires additional information."
                            )
                        elif data[0] == ">" and len(data) > 1:
                            hpiv_min = int(data[1])
                            hpiv_max = 31
                        elif data[0] == "<" and len(data) > 1:
                            hpiv_min = 0
                            hpiv_max = int(data[1])
                        else:
                            hpiv = int(data[0])
                            hpiv_min = hpiv
                            hpiv_max = hpiv
                    except ValueError:
                        raise ExtractionException(
                            "`hpiv` received invalid non-numeric input."
                        )
                    else:
                        sql_data.append(hpiv_max)
                        sql_data.append(hpiv_min)
                        postfix.append(
                            f"(hpiv <= ${len(sql_data) - 1} AND hpiv >= ${len(sql_data)})"
                        )
                elif key == "speediv":
                    try:
                        if not data:
                            raise ExtractionException(
                                "`speediv` requires additional information."
                            )
                        elif data[0] == ">" and len(data) > 1:
                            speediv_min = int(data[1])
                            speediv_max = 31
                        elif data[0] == "<" and len(data) > 1:
                            speediv_min = 0
                            speediv_max = int(data[1])
                        else:
                            speediv = int(data[0])
                            speediv_min = speediv
                            speediv_max = speediv
                    except ValueError:
                        raise ExtractionException(
                            "`speediv` received invalid non-numeric input."
                        )
                    else:
                        sql_data.append(speediv_max)
                        sql_data.append(speediv_min)
                        postfix.append(
                            f"(speediv <= ${len(sql_data) - 1} AND speediv >= ${len(sql_data)})"
                        )
                elif key == "price":
                    if filter_type != "m":
                        raise ExtractionException(
                            "`price` is only a valid key in market filters."
                        )
                    if not data:
                        order_col = "pokeprice"
                        order_dir = "DESC"
                        postfix.append("false")
                    elif data[0].startswith("d"):
                        order_col = "pokeprice"
                        order_dir = "DESC"
                        postfix.append("false")
                    elif data[0].startswith("a"):
                        order_col = "pokeprice"
                        order_dir = "ASC"
                        postfix.append("false")
                    else:
                        try:
                            if data[0] == ">" and len(data) > 1:
                                price_min = int(data[1])
                                price_max = 2147483647
                            elif data[0] == "<" and len(data) > 1:
                                price_min = 0
                                price_max = int(data[1])
                            else:
                                price = int(data[0])
                                price_min = price
                                price_max = price
                        except ValueError:
                            raise ExtractionException(
                                "`price` received invalid non-numeric input."
                            )
                        else:
                            sql_data.append(price_max)
                            sql_data.append(price_min)
                            postfix.append(
                                f"(market.price <= ${len(sql_data) - 1} AND market.price >= ${len(sql_data)})"
                            )
                elif key == "iv":
                    order_col = 1
                    if not data:
                        pass
                    elif data[0].startswith("d"):
                        order_dir = "DESC"
                    elif data[0].startswith("a"):
                        order_dir = "ASC"
                    postfix.append("false")
                elif key == "ev":
                    order_col = 2
                    if not data:
                        pass
                    elif data[0].startswith("d"):
                        order_dir = "DESC"
                    elif data[0].startswith("a"):
                        order_dir = "ASC"
                    postfix.append("false")
                elif key == "id":
                    order_col = "orderid"
                    if not data:
                        order_dir = "ASC"
                    elif data[0].startswith("d"):
                        order_dir = "DESC"
                    elif data[0].startswith("a"):
                        order_dir = "ASC"
                    if filter_type != "m":
                        # Extract out only the pokemon that actually need to get searched
                        # to reduce O(N^2)'s N from len(pokes) to min(len(pokes), POKE_COUNT)
                        if order_dir == "ASC":
                            sql_data[0] = sql_data[0][:POKE_COUNT]
                        else:
                            sql_data[0] = list(reversed(sql_data[0][-POKE_COUNT:]))
                    postfix.append("false")
                elif key == "hidden-power":
                    if not data:
                        raise ExtractionException(
                            "`hidden-power` requires specifying a type."
                        )
                    raw = data[0]
                    t = {
                        "FIGHTING": 0,
                        "FLYING": 1,
                        "POISON": 2,
                        "GROUND": 3,
                        "ROCK": 4,
                        "BUG": 5,
                        "GHOST": 6,
                        "STEEL": 7,
                        "FIRE": 8,
                        "WATER": 9,
                        "GRASS": 10,
                        "ELECTRIC": 11,
                        "PSYCHIC": 12,
                        "ICE": 13,
                        "DRAGON": 14,
                        "DARK": 15,
                    }.get(raw.upper(), None)
                    if t is None:
                        raise ExtractionException(
                            "`{raw}` is not a valid type for `hidden-power`."
                        )
                    sql_data.append(t)
                    postfix.append(
                        (
                            "(MOD(hpiv, 2) + 2 * MOD(atkiv, 2) + 4 * MOD(defiv, 2) + 8 * MOD(speediv, 2) + "
                            f"16 * MOD(spatkiv, 2) + 32 * MOD(spdefiv, 2)) * 15 / 63 = ${len(sql_data)}"
                        )
                    )

        while operator_stack:
            postfix.append(operator_stack.pop())

        # Convert the postfix back to infix, with explicit ()s
        stack = []
        try:
            for item in postfix:
                if item == "|":
                    left = stack.pop()
                    right = stack.pop()
                    stack.append(f"({left} OR {right})")
                elif item == "&":
                    left = stack.pop()
                    right = stack.pop()
                    stack.append(f"({left} AND {right})")
                elif item == "!":
                    left = stack.pop()
                    stack.append(f"NOT {left}")
                else:
                    stack.append(item)
        except IndexError:
            raise ExtractionException(
                "A `!`, `&`, or `|` symbol does not have associated conditions."
            )
        if len(stack) != 1:
            raise ExtractionException(
                "All tokens must be split by either a `&` or a `|` symbol."
            )
        conditions = stack[0]

        # Build the full query based on what type of filter this is
        if filter_type == "p":
            extra = (
                ", array_position($1, id) as orderid" if order_col == "orderid" else ""
            )
            query = (
                "SELECT COALESCE(atkiv,0) + COALESCE(defiv,0) + COALESCE(spatkiv,0) + COALESCE(spdefiv,0) + COALESCE(speediv,0) + COALESCE(hpiv,0) AS ivs, "
                "COALESCE(atkev,0) + COALESCE(defev,0) + COALESCE(spatkev,0) + COALESCE(spdefev,0) + COALESCE(speedev,0) + COALESCE(hpev,0) as evs, "
                f"pokelevel, pokname, name{extra}, * FROM pokes WHERE id = ANY($1) AND {conditions}"
            )
        elif filter_type == "m":
            query = (
                "SELECT COALESCE(atkiv,0) + COALESCE(defiv,0) + COALESCE(spatkiv,0) + COALESCE(spdefiv,0) + COALESCE(speediv,0) + COALESCE(hpiv,0) AS ivs, "
                "COALESCE(atkev,0) + COALESCE(defev,0) + COALESCE(spatkev,0) + COALESCE(spdefev,0) + COALESCE(speedev,0) + COALESCE(hpev,0) as evs, "
                "pokelevel, pokname, market.id as orderid, market.price as pokeprice, * "
                "FROM pokes INNER JOIN market ON pokes.id = market.poke WHERE "
                f"buyer IS NULL AND {conditions}"
            )
        if order_col:
            query += f" ORDER BY {order_col} {order_dir}"
        # Since order args require a token to place them, they add a hanging false. This removes it in AND cases.
        query = query.replace(" AND false", "").replace("false AND ", "")

        # Fetch the pokes that satisfy the filter
        async with self.bot.db[0].acquire() as pconn:
            async with pconn.transaction():
                cur = await pconn.cursor(query, *sql_data)
                records = await cur.fetch(POKE_COUNT, timeout=20)
        if not records:
            await ctx.send(
                "Your filter did not find any pokemon. Try a less narrow search."
            )
            return

        # Prep the results for formatting
        max_id = 0
        max_lvl = 0
        max_name = 0
        max_price = 0
        async for record in AsyncIter(records):
            name = record["pokname"]
            if name.capitalize() == "Egg":
                name = record["name"]
            max_name = max(max_name, len(name))
            if filter_type == "p":
                cur_id = str(pokes.index(record["id"]) + 1)
            elif filter_type == "m":
                cur_id = str(record["orderid"])
                cur_price = f"{record['pokeprice']:,.0f}"
                max_price = max(max_price, len(cur_price))
            max_id = max(max_id, len(cur_id))
            max_lvl = 3

        # Format the returned pokes
        desc = ""
        async for record in AsyncIter(records):
            nr = record["pokname"].capitalize()
            is_egg = False
            if nr == "Egg":
                is_egg = True
                nr = record["name"].capitalize()
            formatted_name = nr.ljust(max_name, " ")
            if filter_type == "p":
                pn = pokes.index(record["id"]) + 1
                price = ""
            elif filter_type == "m":
                pn = record["orderid"]
                price = record["pokeprice"]
            pn = str(pn).rjust(max_id, " ")
            gid = record["id"]
            nick = record["poknick"]
            iv = record["ivs"]
            shiny = record["shiny"]
            radiant = record["radiant"]
            level = str(record["pokelevel"]).rjust(max_lvl, " ")
            level = f"<:stop:1012773630649827451>`{level}`"
            emoji = get_emoji(
                blank="<:blank:942623726715936808>",
                shiny=shiny,
                radiant=radiant,
                skin=record["skin"],
            )
            extra_text = ""
            if filter_type == "m":
                price = f"{price:,.0f}".rjust(max_price, " ")
                extra_text = f"<:dittocoin:1010679749212901407>`{price})`"
            elif is_egg:
                level = str(record["counter"]).rjust(max_lvl, " ")
                level = f"<:egg:844434416200712193>`{level}`"
            elif gid in mothers:
                end = mothers[gid] + timedelta(hours=6)
                now = datetime.now()
                expires_in = end - now
                if now > end:
                    time = "0s"
                elif expires_in.seconds // 3600:
                    time = str(expires_in.seconds // 3600) + "h"
                elif expires_in.seconds // 60:
                    time = str(expires_in.seconds // 60) + "m"
                else:
                    time = str(expires_in.seconds) + "s"
                extra_text = f"\N{STOPWATCH}`{time}`"
            gender = (
                "<:male:1011932024438800464>"
                if record["gender"] == "-m"
                else "<:female:1011935234067021834>"
                if record["gender"] == "-f"
                else "<:ditto_genderless:1004767591237169223>"
                if record["gender"] == "-x"
                else ""
            )
            iv = f"{iv/186:02.0%}".rjust(4, " ")
            desc += (
                f"{emoji}{gender}"
                f"<:our:1012769128085463170>**`{pn}`** "
                f"__`{formatted_name}`__"
                f"{level}"
                f"<:stealing:1012771006278021141>`{iv}`"
                f"{extra_text}\n"
            )

        # Send the result
        embed = discord.Embed(title="Filtered Pokemon", color=0xFFB6C1)
        pages = pagify(desc, per_page=PER_PAGE, base_embed=embed)
        await MenuView(ctx, pages).start()
    
    @commands.hybrid_command()    
    async def getids(self, ctx, msg_id: str):
        """Trade/breeding Utility for getting list of id's from a filter list using message id"""
        message_id = int(msg_id)
        m = await ctx.channel.fetch_message(message_id)
        lines = m.embeds[0].description.split('\n')
        result = []  #  <---here?
        for line in lines:
            form = '<:our:1012769128085463170>**`'
            start = line.find(form)
            sub = line[start + len(form):]
            end = sub.find('`**')
            final = sub[:end]
            result.append(int(final))
        result = " ".join([str(x) for x in result])
        embed = discord.Embed(title = "ID's requested", description=result, color=0xEE8700)
        await ctx.send(embed=embed)
        await ctx.send(result)
            
async def setup(bot):
    await bot.add_cog(Filter(bot))
