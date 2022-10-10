from enum import IntFlag

import dacite
import discord
from dittocogs.json_files import *
from dittocogs.pokemon_list import *
from utils.misc import get_emoji, get_pokemon_image

from pokemon_utils.classes import *


hp_display = '<:hp:1012942710870642708>'
atk_display = '<:atk:1012942628922347641><:atk2:1012942631090786395>'
def_display = '<:def:1012942478241972304><:def2:1012942479848394824><:def3:1012942481236697160>'
spa_display = '<:spatk:1012942190743388251><:spatk2:1012942192576299098><:spatk3:1012942194228867102><:spatk4:1012942195889803304>'
spd_display = '<:spdef:1012941983339257898><:spdef2:1012941985331552353><:spdef3:1012941987130900530><:spdef4:1012941988687003710>'
spe_display = '<:speed:1012942353172021280><:speed2:1012942358205181972>'


def edit_stats(stats, inc_stat, dec_stat):
    stat_names = (
        "Hp",
        "Attack",
        "Defense",
        "Special attack",
        "Special defense",
        "Speed",
    )
    new_stats = []
    for idx, stat in enumerate(stats):
        if stat_names[idx] == inc_stat:
            stat = round(stat * 1.1)
        elif stat_names[idx] == dec_stat:
            stat = round(stat * 0.9)
        new_stats.append(stat)
    return new_stats


async def get_pokemon_qinfo(ctx, records, info_type=None):
    _id = records["id"]
    async with ctx.bot.db[0].acquire() as pconn:
        ids = await pconn.fetchval(
            "SELECT pokes FROM users WHERE u_id = $1", ctx.author.id
        )
    if not info_type:
        try:
            pnum = ids.index(_id) + 1
        except ValueError:
            # The user *probably* has a pokemon selected that they do not own, so clear the
            # user's selected pokemon for the future.
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET selected = null WHERE u_id = $1", ctx.author.id
                )
            return discord.Embed(description="You do not have a selected pokemon!")
    pn = records["pokname"]
    atkiv = records["atkiv"]
    defiv = records["defiv"]
    spatkiv = records["spatkiv"]
    spdefiv = records["spdefiv"]
    speediv = records["speediv"]
    pnick = records["poknick"]
    plevel = records["pokelevel"]
    hpiv = records["hpiv"]
    hi = records["hitem"]
    records["exp"]
    records["expcap"]
    hpev = records["hpev"]
    atkev = records["atkev"]
    defev = records["defev"]
    spaev = records["spatkev"]
    spdev = records["spdefev"]
    speedev = records["speedev"]
    shiny = records["shiny"]
    radiant = records["radiant"]
    nature = records["nature"]
    records["happiness"]
    ab_index = records["ability_index"]
    skin = records["skin"]
    gender, counter = records["gender"], records["counter"]
    if records["caught_by"]:
        ctx.bot.get_user(records["caught_by"])
    else:
        ctx.bot.get_user(455277032625012737)
    str(pn)

    ab_ids = []
    abilities = []
    types = []
    egg_groups = []

    iurl = await get_pokemon_image(pn, ctx.bot, shiny, radiant=radiant, skin=skin)

    nature = await ctx.bot.db[1].natures.find_one({"identifier": nature.lower()})
    dec_stat_id = nature["decreased_stat_id"]
    inc_stat_id = nature["increased_stat_id"]
    dec_stat = await ctx.bot.db[1].stat_types.find_one({"id": dec_stat_id})
    inc_stat = await ctx.bot.db[1].stat_types.find_one({"id": inc_stat_id})
    dec_stat = dec_stat["identifier"].capitalize().replace("-", " ")
    inc_stat = inc_stat["identifier"].capitalize().replace("-", " ")
    stat_deltas = {
        "Attack": 1,
        "Defense": 1,
        "Special attack": 1,
        "Special defense": 1,
        "Speed": 1,
    }
    if dec_stat != inc_stat:
        stat_deltas[dec_stat] = 0.9
        stat_deltas[inc_stat] = 1.1

    form_info = await ctx.bot.db[1].forms.find_one({"identifier": pn.lower()})
    if pn.lower() != "egg":
        type_ids = (
            await ctx.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]})
        )["types"]
        for _type in type_ids:
            types.append(
                str(
                    ctx.bot.misc.get_type_emote(
                        (await ctx.bot.db[1].types.find_one({"id": _type}))[
                            "identifier"
                        ]
                    )
                )
            )

        try:
            egg_groups_ids = (
                await ctx.bot.db[1].egg_groups.find_one(
                    {"species_id": form_info["pokemon_id"]}
                )
            )["egg_groups"]
        except:
            egg_groups_ids = [15]

        for egg_group_id in egg_groups_ids:
            egg_groups.append(
                str(
                    ctx.bot.misc.get_egg_emote(
                        (
                            await ctx.bot.db[1].egg_groups_info.find_one(
                                {"id": egg_group_id}
                            )
                        )["identifier"]
                    )
                )
            )
        try:
            stats = (
                await ctx.bot.db[1].pokemon_stats.find_one(
                    {"pokemon_id": form_info["pokemon_id"]}
                )
            )["stats"]
        except:
            await ctx.send(records)

        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])

        try:
            ab_id = ab_ids[ab_index]
        except:
            ab_id = ab_ids[0]

        abilities.append(
            (await ctx.bot.db[1].abilities.find_one({"id": ab_id}))["identifier"]
        )

        pokemonSpeed = stats[5]
        pokemonSpd = stats[4]
        pokemonSpa = stats[3]
        pokemonDef = stats[2]
        pokemonAtk = stats[1]
        pokemonHp = stats[0]
        tlist = ", ".join(types)
        egg_groups = ", ".join(egg_groups)

        round((((2 * pokemonHp + hpiv + (hpev / 4)) * plevel) / 100) + plevel + 10)
        attack = round(
            ((((2 * pokemonAtk + atkiv + (atkev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Attack"]
        )
        defense = round(
            ((((2 * pokemonDef + defiv + (defev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Defense"]
        )
        specialattack = round(
            ((((2 * pokemonSpa + spatkiv + (spaev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Special attack"]
        )
        specialdefense = round(
            ((((2 * pokemonSpd + spdefiv + (spdev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Special defense"]
        )
        speed = round(
            ((((2 * pokemonSpeed + speediv + (speedev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Speed"]
        )
        t_ivs = hpiv + atkiv + defiv + spatkiv + spdefiv + speediv
        if "arceus-" in pn.lower():
            tlist = pn.split("-")[1]
    else:
        abilities = "?"
        t_ivs = int(hpiv + atkiv + defiv + spatkiv + spdefiv + speediv)
        tlist = "?"
        egg_groups = "?"

    emoji = get_emoji(
        shiny=shiny,
        radiant=radiant,
        skin=skin,
    )

    if pn.lower() == "shedinja":
        pass

    abilities = ", ".join(abilities).capitalize().replace("-", " ")
    nature = nature["identifier"].capitalize()
    pn = pn.capitalize()
    ivs, txt = (
        round(t_ivs / 186 * 100, 2) if not pn.lower() == "egg" else "?",
        f" | Will hatch in {counter} Messages"
        if (pn.lower() == "egg" and counter > 0)
        else "",
    )
    gender = (
        "<:male:1011932024438800464>"
        if gender == "-m"
        else ("<:female:1011935234067021834>" if gender == "-f" else "Genderless")
    )
    gender = (
        "Genderless" if pn.split("-")[0] in LegendList + ubList + ["Ditto"] else gender
    )
    if info_type == "market":
        price = records["pokeprice"]
        mid = records["mid"]
    embed = discord.Embed(
        title=f'Market ID# {mid}{emoji}{pn} "{gender}" - Price {price:,.0f}'
        if info_type and info_type == "market"
        else f'{emoji}{gender} Level {plevel} {pn} "{pnick}"',
        color=random.choice(ctx.bot.colors),
    )
    embed.description = f"""**Ability**: `{abilities}` | **Nature**: `{nature}`\n**Types**: {tlist}\n**Egg Groups**: {egg_groups}\n`HP`: **{hpiv}** | `Attack`: **{atkiv}** | `Defense`: **{defiv}**\n`SP.A`: **{spatkiv}** | `SP.D`: **{spdefiv}** | `Speed`: **{speediv}**\n__**Total IV%:**__ `{ivs}`\nHeld item : `{hi}{txt}`"""
    # embed.set_thumbnail(url=ctx.author.avatar_url)
    # embed.set_image(url=iurl)
    id_count = len(ids)
    embed.set_footer(
        text=f"Number {pnum}/{id_count} | Global ID: {_id}" if not info_type else ""
    )
    return embed


async def get_pokemon_info(ctx, records, info_type=None):
    _id = records["id"]
    async with ctx.bot.db[0].acquire() as pconn:
        ids = await pconn.fetchval(
            "SELECT pokes FROM users WHERE u_id = $1", ctx.author.id
        )
        tnick = await pconn.fetchval(
            "SELECT tnick FROM users WHERE u_id = $1", records["caught_by"]
        )
    tnick = str(tnick)[:20]
    if not info_type:
        try:
            pnum = ids.index(_id) + 1
        except ValueError:
            # The user *probably* has a pokemon selected that they do not own, so clear the
            # user's selected pokemon for the future.
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET selected = null WHERE u_id = $1", ctx.author.id
                )
            return discord.Embed(description="You do not have a selected pokemon!")
    pn = records["pokname"]
    atkiv = records["atkiv"]
    defiv = records["defiv"]
    spatkiv = records["spatkiv"]
    spdefiv = records["spdefiv"]
    speediv = records["speediv"]
    pnick = records["poknick"]
    plevel = records["pokelevel"]
    hpiv = records["hpiv"]
    hi = records["hitem"].capitalize().replace("-", " ")
    exp = records["exp"]
    expcap = records["expcap"]
    hpev = records["hpev"]
    atkev = records["atkev"]
    defev = records["defev"]
    spaev = records["spatkev"]
    spdev = records["spdefev"]
    speedev = records["speedev"]
    shiny = records["shiny"]
    radiant = records["radiant"]
    nature = records["nature"]
    happiness = records["happiness"]
    ab_index = records["ability_index"]
    skin = records["skin"]
    gender, counter = records["gender"], records["counter"]
    if records["caught_by"]:
        ctx.bot.get_user(records["caught_by"])
    else:
        ctx.bot.get_user(631840748924436490)
    str(pn)

    ab_ids = []
    abilities = []
    types = []
    egg_groups = []

    iurl = await get_pokemon_image(pn, ctx.bot, shiny, radiant=radiant, skin=skin)

    skindisp = ""
    if skin == "shadow":
        skindisp = "<:emoji_55:947332001122385940><:emoji_56:947332044273360987><:emoji_57:947332082047266856>"
    elif skin == "glitch":
        skindisp = "<a:glitch1:988175512109211728><a:glitch2:988175552009629696><a:glitch3:988175669584355390><a:glitch4:988175155954061394>"
    elif skin:
        skindisp = "<:sp6:875570797673086986><:sp5:875570797668876298><:sp4:875570797589172274><:sp3:875570797148770375><:sp2:875570797199118388><:sp1:875570797173948458>"

    nature = await ctx.bot.db[1].natures.find_one({"identifier": nature.lower()})
    dec_stat_id = nature["decreased_stat_id"]
    inc_stat_id = nature["increased_stat_id"]
    dec_stat = await ctx.bot.db[1].stat_types.find_one({"id": dec_stat_id})
    inc_stat = await ctx.bot.db[1].stat_types.find_one({"id": inc_stat_id})
    dec_stat = dec_stat["identifier"].capitalize().replace("-", " ")
    inc_stat = inc_stat["identifier"].capitalize().replace("-", " ")
    stat_deltas = {
        "Attack": 1,
        "Defense": 1,
        "Special attack": 1,
        "Special defense": 1,
        "Speed": 1,
    }
    if dec_stat != inc_stat:
        stat_deltas[dec_stat] = 0.9
        stat_deltas[inc_stat] = 1.1

    form_info = await ctx.bot.db[1].forms.find_one({"identifier": pn.lower()})
    if pn.lower() != "egg":
        type_ids = (
            await ctx.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]})
        )["types"]
        for _type in type_ids:
            types.append(
                str(
                    ctx.bot.misc.get_type_emote(
                        (await ctx.bot.db[1].types.find_one({"id": _type}))[
                            "identifier"
                        ]
                    )
                )
            )

        try:
            egg_groups_ids = (
                await ctx.bot.db[1].egg_groups.find_one(
                    {"species_id": form_info["pokemon_id"]}
                )
            )["egg_groups"]
        except:
            egg_groups_ids = [15]
        for egg_group_id in egg_groups_ids:
            egg_groups.append(
                str(
                    ctx.bot.misc.get_egg_emote(
                        (
                            await ctx.bot.db[1].egg_groups_info.find_one(
                                {"id": egg_group_id}
                            )
                        )["identifier"]
                    )
                )
            )

        try:
            stats = (
                await ctx.bot.db[1].pokemon_stats.find_one(
                    {"pokemon_id": form_info["pokemon_id"]}
                )
            )["stats"]
        except:
            await ctx.send(records)

        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])

        try:
            ab_id = ab_ids[ab_index]
        except:
            ab_id = ab_ids[0]

        abilities.append(
            (await ctx.bot.db[1].abilities.find_one({"id": ab_id}))["identifier"]
        )

        pokemonSpeed = stats[5]
        pokemonSpd = stats[4]
        pokemonSpa = stats[3]
        pokemonDef = stats[2]
        pokemonAtk = stats[1]
        pokemonHp = stats[0]
        tlist = ", ".join(types)
        egg_groups = ", ".join(egg_groups)

        hp = round((((2 * pokemonHp + hpiv + (hpev / 4)) * plevel) / 100) + plevel + 10)
        attack = round(
            ((((2 * pokemonAtk + atkiv + (atkev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Attack"]
        )
        defense = round(
            ((((2 * pokemonDef + defiv + (defev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Defense"]
        )
        specialattack = round(
            ((((2 * pokemonSpa + spatkiv + (spaev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Special attack"]
        )
        specialdefense = round(
            ((((2 * pokemonSpd + spdefiv + (spdev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Special defense"]
        )
        speed = round(
            ((((2 * pokemonSpeed + speediv + (speedev / 4)) * plevel) / 100) + 5)
            * stat_deltas["Speed"]
        )
        t_ivs = hpiv + atkiv + defiv + spatkiv + spdefiv + speediv
        if "arceus-" in pn.lower():
            tlist = pn.split("-")[1]
    else:
        hp = "?"
        attack = "?"
        defense = "?"
        specialattack = "?"
        specialdefense = "?"
        speed = "?"
        abilities = "?"
        t_ivs = int(hpiv + atkiv + defiv + spatkiv + spdefiv + speediv)
        tlist = "?"

    emoji = get_emoji(
        shiny=shiny,
        radiant=radiant,
        skin=skin,
    )

    if pn.lower() == "shedinja":
        hp = 1

    abilities = ", ".join(abilities).capitalize().replace("-", " ")
    nature = nature["identifier"].capitalize()
    pn = pn.capitalize()
    if pn.lower() != "egg":
        ivs = round(t_ivs / 186 * 100, 2)
        txt = ""
        type_idx = hpiv % 2
        type_idx += 2 * (atkiv % 2)
        type_idx += 4 * (defiv % 2)
        type_idx += 8 * (speediv % 2)
        type_idx += 16 * (spatkiv % 2)
        type_idx += 32 * (spdefiv % 2)
        type_idx = (type_idx * 15) // 63
        type_options = {
            0: "FIGHTING",
            1: "FLYING",
            2: "POISON",
            3: "GROUND",
            4: "ROCK",
            5: "BUG",
            6: "GHOST",
            7: "STEEL",
            8: "FIRE",
            9: "WATER",
            10: "GRASS",
            11: "ELECTRIC",
            12: "PSYCHIC",
            13: "ICE",
            14: "DRAGON",
            15: "DARK",
        }
        hidden_power = type_options[type_idx].title()
    else:
        ivs = "?"
        txt = f" | Will hatch in {counter} Messages"
        hidden_power = "?"

    gender = (
        "<:male:1011932024438800464>"
        if gender == "-m"
        else ("<:female:1011935234067021834>" if gender == "-f" else "<:genderless:923737986447847435>")
    )
    pnick = f"'{pnick}'" if pnick or not pnick.lower() == "none" else ""

    if info_type == "market":
        price = records["pokeprice"]
        mid = records["mid"]
    embed = discord.Embed(
        title=f"Market ID# {mid}{emoji}{gender} {pn} - Price {price:,.0f}"
        if info_type and info_type == "market"
        else f"{emoji} {gender} {pn} {pnick}",
        color=random.choice(ctx.bot.colors),
    )
    hpev_display = f"┃<:evs:1013182984632926299>`{hpev}`"
    atkev_display = f"┃<:evs:1013182984632926299>`{atkev}`"
    defev_display = f"┃<:evs:1013182984632926299>`{defev}`"
    spaev_display = f"┃<:evs:1013182984632926299>`{spaev}`"
    spdev_display = f"┃<:evs:1013182984632926299>`{spdev}`"
    speedev_display = f"┃<:evs:1013182984632926299>`{speedev}`"
    desc = ""

    desc += f"**<:stop:1012773630649827451> {plevel}**\n**Ability**: {abilities}\n**Exp**: `{exp}/{expcap}`\n**Nature**: `{nature}` - `+{inc_stat}/-{dec_stat}`\n**Types**: {tlist}\n**Egg Groups**: {egg_groups}\n\n"
    desc += "__**Stats** `(total (iv/evs))`__\n"
    desc += f"**HP:**  `{hp}` (<:stealing:1012771006278021141>`{hpiv}`{hpev_display if hpev != 0 else ''})\n" 
    desc += f"**Attack:** `{attack}` (<:stealing:1012771006278021141>`{atkiv}`{atkev_display if atkev != 0 else ''})\n"
    desc += f"**Defense:** `{defense}` (<:stealing:1012771006278021141>`{defiv}`{defev_display if defev != 0 else ''})\n"
    desc += f"**Sp. Atk:** `{specialattack}` (<:stealing:1012771006278021141>`{spatkiv}`{spaev_display if spaev != 0 else ''})\n"
    desc += f"**Sp. Def:** `{specialdefense}` (<:stealing:1012771006278021141>`{spdefiv}`{spdev_display if spdev != 0 else ''})\n"
    desc += f"**Speed:** `{speed}` (<:stealing:1012771006278021141>`{speediv}`{speedev_display if speedev != 0 else ''})\n"
    desc += f"**IV %**: `{ivs}`\n"
    desc += f"**Hidden Power**: `{hidden_power}`\n"
    desc += f"**Happiness**: `{happiness}`\n"
    desc += f"{skindisp}"
    embed.description = desc
    move1, move2, move3, move4 = (
        move.capitalize().replace("-", " ") for move in records["moves"]
    )
    embed.add_field(
        name="**__Learned Moves__**:",
        value=f"**{move1}**\n**{move2}**\n**{move3}**\n**{move4}**",
    )
    embed.add_field(name="__Held Item:__", value=f"**{hi}**")
    embed.add_field(name="__OT:__", value=f"**{tnick}**")
    if ctx.author.avatar is not None:
        embed.set_thumbnail(url=ctx.author.avatar.url)
    embed.set_image(url=iurl)
    id_count = len(ids)
    embed.set_footer(
        text=f"Number {pnum}/{id_count} | Global ID#: {_id}{txt}"
        if not info_type
        else ""
    )
    return embed


class EvoReqs(IntFlag):
    """Stores the requirements for a particular evolution."""

    EMPTY = 0
    PHYSICALSTATS = 1
    GENDER = 2
    LEVEL = 4
    HAPPINESS = 8
    MOVE = 16
    HELDITEM = 32
    ACTIVEITEM = 64
    REGION = 128

    def used_active_item(self):
        return EvoReqs.ACTIVEITEM in self

    @staticmethod
    def from_raw(raw):
        score = EvoReqs.EMPTY
        if raw["relative_physical_stats"] is not None:
            score |= EvoReqs.PHYSICALSTATS
        if raw["gender_id"]:
            score |= EvoReqs.GENDER
        if raw["minimum_level"]:
            score |= EvoReqs.LEVEL
        if raw["minimum_happiness"]:
            score |= EvoReqs.HAPPINESS
        if raw["known_move_id"]:
            score |= EvoReqs.MOVE
        if raw["held_item_id"]:
            score |= EvoReqs.HELDITEM
        if raw["trigger_item_id"]:
            score |= EvoReqs.ACTIVEITEM
        if raw["region"]:
            score |= EvoReqs.REGION
        return score


async def _check_evo_reqs(
    bot, pokemon, held_item_id, active_item_id, region, evoreq, override_lvl_100
):
    """Checks that "poke" meets all of the criteria of "evoreq"."""
    req_flags = EvoReqs.from_raw(evoreq)
    # They used an active item but this evo doesn't use an active item, don't use it.
    if active_item_id is not None and not req_flags.used_active_item():
        return False
    # If a pokemon is level 100, ONLY evolve via an override or active item.
    if pokemon.pokelevel >= 100 and not (
        override_lvl_100 or active_item_id is not None
    ):
        return False
    if evoreq["trigger_item_id"]:
        if evoreq["trigger_item_id"] != active_item_id:
            return False
    if evoreq["held_item_id"]:
        if evoreq["held_item_id"] != held_item_id:
            return False
    if evoreq["gender_id"]:
        if evoreq["gender_id"] == 1 and pokemon.gender == "-m":
            return False
        if evoreq["gender_id"] == 2 and pokemon.gender == "-f":
            return False
    if evoreq["minimum_level"]:
        if pokemon.pokelevel < evoreq["minimum_level"]:
            return False
    if evoreq["known_move_id"]:
        identifier = await bot.db[1].moves.find_one({"id": evoreq["known_move_id"]})
        identifier = identifier["identifier"]
        if identifier not in pokemon.moves:
            return False
    if evoreq["minimum_happiness"]:
        if pokemon.happiness < evoreq["minimum_happiness"]:
            return False
    if evoreq["relative_physical_stats"] is not None:
        # WARNING
        # Currently this is only used by Tyrogue, which has identical base stats for atk and def.
        # If this is used on a poke WITHOUT identical base stats, the base stat needs to be considered.
        attack = pokemon.atkiv + pokemon.atkev
        defense = pokemon.defiv + pokemon.defev
        if evoreq["relative_physical_stats"] == 1 and not attack > defense:
            return False
        elif evoreq["relative_physical_stats"] == -1 and not attack < defense:
            return False
        elif evoreq["relative_physical_stats"] == 0 and not attack == defense:
            return False
    if evoreq["region"]:
        if evoreq["region"] != region:
            return False
        # Temp blocker since previously radiants could never evolve to regional forms, so they were released separately
        if pokemon.radiant:
            return False
    return True


def _pick_evo(valid_evos):
    """
    Picks one of the valid evos, and returns that evo's id.

    Prioritizes evos that are more explicit than implicit ones.
    IE: held item evos > level evos
    """
    best_score = -1
    best_id = None
    for evo in valid_evos:
        score = EvoReqs.from_raw(evo)
        if score > best_score:
            best_score = score
            best_id = evo["evolved_species_id"]
    return (best_id, best_score)


async def evolve(
    bot, pokemon_data, owner, *, channel=None, active_item=None, override_lvl_100=False
):
    """
    Attempts to evolve the poke using its current data and the optional active_item.

    Returns False if the poke did not evolve, and an instance of EvoReqs if it did.
    If channel is passed, also sends a message indicating that the poke evolved.
    """
    pokemon = dacite.from_dict(data_class=Pokemon, data=pokemon_data)
    original_name = pokemon.pokname
    pokemon.pokname = pokemon.pokname.lower()

    # Everstones block evolutions, don't try to evolve
    if pokemon.hitem in ("everstone", "eviolite"):
        return False

    # The pokemon is an egg, eggs cannot evolve
    if pokemon.pokname == "egg":
        return False

    # Don't try to evolve forms
    if is_formed(pokemon.pokname) or any(
        pokemon.pokname.endswith(x) for x in ("-staff", "-custom")
    ):
        return False

    # Get the necessary info of this poke to find evos
    pokemon_info = await bot.mongo_pokemon_db.forms.find_one(
        {"identifier": pokemon.pokname}
    )
    if pokemon_info is None:
        bot.logger.warning(
            f"A poke exists that is not in the mongo forms table - {pokemon.pokname}"
        )
        return False
    pokemon_info = dacite.from_dict(
        data_class=FormInfo,
        data=pokemon_info,
    )
    raw_pfile = await bot.mongo_pokemon_db.pfile.find_one(
        {"identifier": pokemon_info.identifier}
    )
    if raw_pfile is None:
        bot.logger.warning(
            f"A non-formed poke exists that is not in the mongo pfile table - {pokemon.pokname}"
        )
        return False
    pokemon_info.pfile = dacite.from_dict(data_class=PFile, data=raw_pfile)

    # Get a list of pokes in this poke's evo chain
    evoline = bot.mongo_pokemon_db.pfile.find(
        {"evolution_chain_id": pokemon_info.pfile.evolution_chain_id}
    )
    async for record in evoline:
        pokemon_info.evoline.append(record)
    pokemon_info.evoline.sort(key=lambda doc: doc["is_baby"], reverse=True)

    # Filter the potential evos to only include ones that are evolved from this poke
    potential_evos = []
    for x in pokemon_info.evoline:
        if not x["evolves_from_species_id"] == pokemon_info.pokemon_id:
            continue
        val = await bot.db[1].evofile.find_one({"evolved_species_id": x["id"]})
        if val is None:
            bot.logger.warning(
                f"An evofile does not exist for a poke - {x['identifier']}"
            )
        else:
            potential_evos.append(val)

    # This pokemon has no future evos, so it can't evolve into anything
    if not potential_evos:
        return False

    # Prep held and active items
    if active_item is None:
        active_item_id = None
    else:
        active_item_id = await bot.mongo_pokemon_db.items.find_one(
            {"identifier": active_item}
        )
        if active_item_id is None:
            bot.logger.warning(
                f"A poke is trying to use an active item that is not in the mongo table - {active_item}"
            )
        else:
            active_item_id = active_item_id["id"]
    held_item_id = await bot.mongo_pokemon_db.items.find_one(
        {"identifier": pokemon.hitem}
    )
    if held_item_id is not None:
        held_item_id = held_item_id["id"]

    # Get the owner's current region
    async with bot.db[0].acquire() as pconn:
        region = await pconn.fetchval(
            "SELECT region FROM users WHERE u_id = $1", owner.id
        )
    if region is None:
        return False

    # Filter out evos that this poke does not meet the requirements for
    valid_evos = []
    for evoreq in potential_evos:
        if await _check_evo_reqs(
            bot, pokemon, held_item_id, active_item_id, region, evoreq, override_lvl_100
        ):
            valid_evos.append(evoreq)

    # This poke does not meet the conditions of any potential evos
    if not valid_evos:
        return False

    evo_id, evo_reqs = _pick_evo(valid_evos)
    evo = await bot.mongo_pokemon_db.pfile.find_one({"id": evo_id})
    evo = evo["identifier"].capitalize()

    # We evolved, actually update the poke & notify the user
    async with bot.db[0].acquire() as pconn:
        await pconn.execute(
            "UPDATE pokes SET pokname = $2, gender = $3 WHERE id = $1",
            pokemon.id,
            evo,
            pokemon.gender,
        )
    if channel:
        try:
            await channel.send(
                embed=discord.Embed(
                    title="Congratulations!!!",
                    description=f"{owner.name}, your {original_name} has evolved into {evo}!",
                    color=bot.get_random_color(),
                )
            )
        except discord.HTTPException:
            pass
    return evo_reqs


async def devolve(ctx, pokeid):
    """
    Instantly devolve the given poke id (if applicable).

    This DOES NOT check items, but DOES check if the pokemon has a prior evolution.
    Returns a bool, indicating if the poke was successfully devolved.
    """
    async with ctx.bot.db[0].acquire() as pconn:
        pokename = await pconn.fetchval(
            "SELECT pokname FROM pokes WHERE id = $1", pokeid
        )
    pokedata = await ctx.bot.mongo_pokemon_db.pfile.find_one(
        {"identifier": pokename.lower()}
    )
    preid = pokedata["evolves_from_species_id"]
    # The pokemon is the base evolution, or otherwise does not exist.
    if not preid:
        return False
    preevo = await ctx.bot.mongo_pokemon_db.pfile.find_one({"id": preid})
    new_name = preevo["identifier"].capitalize()
    async with ctx.bot.db[0].acquire() as pconn:
        await pconn.execute(
            "UPDATE pokes SET pokname = $2 WHERE id = $1", pokeid, new_name
        )
    return True
