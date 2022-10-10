import random
import time
import discord
from discord.ext import commands
from utils.checks import tradelock, check_admin, check_helper, check_investigator, check_mod

from dittocogs.json_files import *
from dittocogs.pokemon_list import *

multiplier_max = {"battle-multiplier": 50, "shiny-multiplier": 50}
comp_pseudos_legends = {
    "Type-null",
    "Silvally",
    "Dratini",
    "Dragonair",
    "Dragonite",
    "Larvitar",
    "Pupitar",
    "Tyranitar",
    "Bagon",
    "Shelgon",
    "Salamence",
    "Beldum",
    "Metang",
    "Metagross",
    "Gible",
    "Gabite",
    "Garchomp",
    "Deino",
    "Zweilous",
    "Hydreigon",
    "Goomy",
    "Sliggoo",
    "Sliggoo-hisui",
    "Goodra",
    "Goodra-hisui",
    "Jangmo-o",
    "Hakamo-o",
    "Kommo-o",
    "Dreepy",
    "Drakloak",
    "Dragapult",
    "Articuno",
    "Articuno-galar",
    "Zapdos",
    "Zapdos-galar",
    "Moltres",
    "Moltres-galar",
    "Mewtwo",
    "Mew",
    "Raikou",
    "Entei",
    "Suicune",
    "Lugia",
    "Ho-oh",
    "Celebi",
    "Regirock",
    "Regice",
    "Registeel",
    "Latias",
    "Latios",
    "Kyogre",
    "Groudon",
    "Rayquaza",
    "Jirachi",
    "Deoxys",
    "Uxie",
    "Mesprit",
    "Azelf",
    "Dialga",
    "Palkia",
    "Heatran",
    "Regigigas",
    "Giratina",
    "Cresselia",
    "Phione",
    "Manaphy",
    "Darkrai",
    "Shaymin",
    "Arceus",
    "Victini",
    "Cobalion",
    "Terrakion",
    "Virizion",
    "Tornadus",
    "Thundurus",
    "Reshiram",
    "Zekrom",
    "Landorus",
    "Kyurem",
    "Keldeo",
    "Meloetta",
    "Genesect",
    "Xerneas",
    "Yveltal",
    "Zygarde",
    "Diancie",
    "Hoopa",
    "Volcanion",
    "Tapu-koko",
    "Tapu-lele",
    "Tapu-bulu",
    "Tapu-fini",
    "Cosmog",
    "Cosmoem",
    "Solgaleo",
    "Lunala",
    "Nihilego",
    "Buzzwole",
    "Pheromosa",
    "Xurkitree",
    "Celesteela",
    "Kartana",
    "Guzzlord",
    "Necrozma",
    "Magearna",
    "Marshadow",
    "Poipole",
    "Naganadel",
    "Stakataka",
    "Blacephalon",
    "Zeraora",
    "Meltan",
    "Melmetal",
    "Zacian",
    "Zamazenta",
    "Eternatus",
    "Kubfu",
    "Urshifu",
    "Zarude",
    "Regieleki",
    "Regidrago",
    "Glastrier",
    "Spectrier",
    "Calyrex",
    "Enamorus",
    "Riolu",
    "Lucario",
    "Missingno",
}


def get_perks(plan):
    dets = {}
    if plan == "regular":
        dets["nature-capsules"] = 2
        dets["battle-multiplier"] = 0
        dets["shiny-multiplier"] = 0
        dets["daycare-limit"] = 3
        dets["coin-case"] = 150000
        dets["price"] = 5
    elif plan == "gold":
        dets["nature-capsules"] = 5
        dets["honey"] = 5
        dets["battle-multiplier"] = 1
        dets["shiny-multiplier"] = 2
        dets["daycare-limit"] = 6
        dets["coin-case"] = 300000
        dets["price"] = 10
    elif plan == "platinum":
        dets["nature-capsules"] = 7
        dets["honey"] = 10
        dets["battle-multiplier"] = 4
        dets["shiny-multiplier"] = 6
        dets["daycare-limit"] = 9
        dets["coin-case"] = 600000
        dets["price"] = 25
    elif plan == "diamond":
        dets["nature-capsules"] = 15
        dets["honey"] = 25
        dets["battle-multiplier"] = 10
        dets["shiny-multiplier"] = 10
        dets["daycare-limit"] = 15
        dets["coin-case"] = 800000
        dets["price"] = 50
    elif plan == "worth too much":
        dets["nature-capsules"] = 30
        dets["honey"] = 40
        dets["battle-multiplier"] = 30
        dets["shiny-multiplier"] = 10
        dets["daycare-limit"] = 20
        dets["coin-case"] = 2000000
        dets["ultranecronium-z"] = 1
        dets["bike"] = 1
        dets["price"] = 150
    return dets


def get_descrip(item):
    return {
        "nature-capsules": "Use Nature Capsules to change your Pokemon's Nature",
        "honey": "Honey Increases your chance of spawning a Legendary while talking in a Server",
        "battle-multiplier": "Battle Multipliers Multiply all Reward from a battle or duel such as happiness, credits and experience",
        "shiny-multiplier": "Shiny Multipliers Increase your chance of Redeeming or Spawning a shiny while talking in a Server",
        "daycare-limit": "Daycare Limit increases the amount of Offspring you can breed at a time!",
        "coin-case": "Get Coins to Use and Play the Slots in the Game corner!",
        "ultranecronium-z": "Transform Necrozma to it's Ultra form",
        "bike": ":bike: Speed up egg hatching by 2x",
    }.get(item)


class Redeem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CREDITS_PER_MULTI = 125000

    @commands.hybrid_command()
    async def packs(self, ctx):
        packs = ["regular", "gold", "platinum", "diamond", "worth too much"]
        for idx, pack in enumerate(packs, start=1):
            e = discord.Embed(title=f"{pack.capitalize()} Pack", color=0xFFB6C1)
            s = get_perks(pack)
            price = s["price"]
            s.pop("price", None)
            e.description = f"Price - {price} Redeems\nPack ID - {idx} Buy this pack with `/redeem pack {idx}`\nIn this pack you get these: "
            for thing in s:
                desc = get_descrip(thing)
                n_thing = thing.replace("-", " ").capitalize()
                n_thing = (
                    "Honey (Increased Legendary encounter chance)"
                    if "Honey" in n_thing
                    else n_thing
                )
                e.add_field(
                    name=n_thing.replace("multiplier", "chance")
                    if "Shiny" in n_thing
                    else n_thing,
                    value=f"{s[thing]}{'%' if 'shiny' in thing or 'honey' in thing else 'x'}\n{desc}",
                    inline=False,
                )
            e.set_footer(text="Shiny Chance and Honey have a Max of 50")
            try:
                await ctx.author.send(embed=e)
            except discord.HTTPException:
                await ctx.send("I could not DM you the Pack information!")
                return
        await ctx.send(
            "All available Packs and their information has been sent to DMs!"
        )

    @commands.hybrid_group()
    async def redeem(self, ctx):
        ...

    @redeem.command(name="shop")
    async def redeem_shop(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            redeems = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", ctx.author.id
            )
            if redeems is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return

        e = discord.Embed(title="Redeem Shop", color=ctx.bot.get_random_color())
        e.description = (
            f"You have {redeems} Redeems, get more with `/donate` or `/vote`"
        )
        e.add_field(
            name="Pokemon | 1 Redeem",
            value="`/redeem <pokemon_name> | Redeem any Pokemon of your choice`",
            inline=False,
        )

        e.add_field(name="Redeem multiple!", value="Redeem any Amount of Pokemon with `{}redeemmultiple <amount> <pokemon_name>` or redeem multiple credits using `{ctx.prefix}redeemmultiple credits <amount_of_redeem_to_use>`")
        e.add_field(
            name="Credits | 1 Redeem = 50,000 Credits",
            value="`/redeem credits | Redeem 50,000 credits`",
            inline=False,
        )

        e.add_field(
            name="Nature capsules | 1 Redeem = 5 Nature Capsules",
            value="`/redeem nature capsules | Use nature capsules to edit Pokemon nature.`",
            inline=False,
        )

        e.add_field(
            name="Honey | 5 Redeems = 1 Honey",
            value="`/redeem honey | /spread honey <amount> | Redeem and Spread honey on a channel`",
            inline=False,
        )

        # e.add_field(name="Packs", value="Get Extra Features, Items with `{ctx.prefix}packs`\nRedeem a pack with `{ctx.prefix}redeem pack <pack_id>`")
        e.add_field(
            name="EV points | 1 Redeem = 255 EVs",
            value="`/redeem evs | Redeem 255 EV points`",
            inline=False,
        )

        e.add_field(
            name="30 Redeems = 1 Random Shiny",
            value="`/redeem shiny | Redeem random Shiny Legendary, Mythical, or Common Pokemon`",
            inline=False,
        )

        e.add_field(
            name="Bike | 100 Redeems = 1 Bike",
            value="`/redeem bike | Redeem a bike and double egg hatching rate`",
            inline=False,
        )

        e.add_field(
            name="Packs",
            value="`/packs | Get extra bundles, features, items from packs`",
        )

        await ctx.send(embed=e)
        return

    @redeem.command(with_app_command=True)  # This has to be registered
    @tradelock
    async def single(self, ctx, val: str):
        async with ctx.bot.db[0].acquire() as pconn:
            redeems = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", ctx.author.id
            )
            if redeems is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
        if not val:
            return await ctx.send("Something went wrong, please try again!")
        elif val.lower() == "shiny":
            e = discord.Embed(color=ctx.bot.get_random_color())
            shiny = random.choice(totalList)
            async with ctx.bot.db[0].acquire() as pconn:
                if redeems < 30:
                    await ctx.send("You don't have 30 Redeems!")
                    return
                await pconn.execute(
                    "UPDATE users SET redeems = redeems - 30 WHERE u_id = $1",
                    ctx.author.id,
                )
                await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 30 WHERE u_id = $1", ctx.author.id)
            pokedata = await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, shiny, shiny=True
            )
            ivpercent = round((pokedata.iv_sum / 186) * 100, 2)
            await ctx.bot.get_partial_messageable(1004755418511310878).send(
                f"``User:`` {ctx.author} | ``ID:`` {ctx.author.id}\nHas redeemed a random shiny {shiny} (`{pokedata.id}`)\n----------------------------------"
            )
            e.add_field(
                name="Random Shiny", value=f"{shiny} ({ivpercent}% iv)", inline=False
            )
            await ctx.send(embed=e)
        elif val.lower() == "bike":
            e = discord.Embed(color=ctx.bot.get_random_color())
            async with ctx.bot.db[0].acquire() as pconn:
                if redeems < 100:
                    await ctx.send("You do not have enough redeems")
                    return

                await pconn.execute(
                    "UPDATE users SET bike = $2, redeems = redeems - 100 where u_id = $1",
                    ctx.author.id,
                    True,
                )
                await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 100 WHERE u_id = $1", ctx.author.id)
            e.description = "You have Successfully purchased a :bike:"
            await ctx.send(embed=e)
        elif val.startswith("pack"):
            args = val.split()
            try:
                id = int(args[1])
            except:
                await ctx.send(
                    f"Invalid pack specified!\nSee all available packs with `/packs`!"
                )
                return
            if id == 1:
                perk = "regular"
            elif id == 2:
                perk = "gold"
            elif id == 3:
                perk = "platinum"
            elif id == 4:
                perk = "diamond"
            elif id == 5:
                perk = "worth too much"
            else:
                await ctx.send(
                    f"Invalid Pack ID!\nSee all available packs with `/packs`"
                )
                return
            pack = get_perks(perk)
            price = pack["price"]
            if redeems < price:
                await ctx.send(
                    f"You cannot afford the {price} redeem it would cost to purchase that pack!"
                )
                return
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems - $1 where u_id = $2",
                    price,
                    ctx.author.id,
                )
                await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + $2 WHERE u_id = $1", ctx.author.id, price)
            daycarelimit = pack["daycare-limit"]
            pack.pop("price", None)
            pack.pop("daycare-limit", None)
            async with ctx.bot.db[0].acquire() as pconn:
                current_inv = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                current_items = await pconn.fetchval(
                    "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
                )
            # current_inv.pop('coin-case', None) if 'coin-case' in current_inv else None
            extra_creds = 0
            for item in pack:
                try:
                    if item.endswith("-z"):
                        current_items[item] = current_items.get(item, 0) + 1
                        async with ctx.bot.db[0].acquire() as pconn:
                            await pconn.execute(
                                "UPDATE users SET items = $1::json where u_id = $2",
                                current_items,
                                ctx.author.id,
                            )
                    elif item == "bike":
                        async with ctx.bot.db[0].acquire() as pconn:
                            await pconn.execute(
                                "UPDATE users SET bike = $2 where u_id = $1",
                                ctx.author.id,
                                True,
                            )
                    else:
                        extra = max(
                            0,
                            (current_inv.get(item, 0) + pack[item])
                            - (multiplier_max.get(item, 9999999999999999999999999)),
                        )
                        extra_creds += extra * self.CREDITS_PER_MULTI
                        current_inv[item] = min(
                            current_inv.get(item, 0) + pack[item],
                            multiplier_max.get(item, 9999999999999999999999999),
                        )
                except:
                    continue
            async with ctx.bot.db[0].acquire() as pconn:
                try:
                    await pconn.execute(
                        "UPDATE users SET inventory = $1::json, daycarelimit = daycarelimit + $3, mewcoins = mewcoins + $4 WHERE u_id = $2",
                        current_inv,
                        ctx.author.id,
                        daycarelimit,
                        extra_creds,
                    )
                except Exception as e:
                    raise e
                    # await ctx.send(
                    #     "You do not have enough Redeems or you have stacked up your perks to the limit!"
                    # )
                    # return

            e = discord.Embed(title=f"{perk.capitalize()} Pack", color=0xFFB6C1)
            e.description = "You have Successfully purchased these: "
            for item in pack:
                n_thing = item.replace("-", " ").capitalize()
                n_thing = (
                    "Honey (Increased Legendary encounter chance)"
                    if "Honey" in n_thing
                    else n_thing
                )
                e.add_field(
                    name=n_thing.replace("multiplier", "chance")
                    if "Shiny" in n_thing
                    else n_thing,
                    value=f"{pack[item]}{'%' if 'shiny' in item or 'honey' in item else 'x'}",
                    inline=False,
                )
            if extra_creds:
                e.add_field(
                    name="Credits",
                    value=f"{extra_creds}",
                    inline=False,
                )
            await ctx.send(embed=e)
        elif val == "credits":
            async with ctx.bot.db[0].acquire() as pconn:
                try:
                    await pconn.execute(
                        "UPDATE users SET mewcoins = mewcoins + 50000, redeems = redeems - 1 Where u_id = $1",
                        ctx.author.id,
                    )
                    await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 1 WHERE u_id = $1", ctx.author.id)
                except:
                    await ctx.send("You do not have enough redeems")
                    return
                await ctx.send("50,000 Has been credited to your balance!")
        elif val == "honey":
            async with ctx.bot.db[0].acquire() as pconn:
                inv = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inv["honey"] = inv.get("honey", 0) + 1
                try:
                    await pconn.execute(
                        "UPDATE users SET inventory = $1::json, redeems = redeems - 5 WHERE u_id = $2",
                        inv,
                        ctx.author.id,
                    )
                    await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 5 WHERE u_id = $1", ctx.author.id)
                except:
                    await ctx.send("You do not have enough redeems")
                    return
                await ctx.send("You redeemed 1x honey!")
        elif val.startswith("ev"):
            async with ctx.bot.db[0].acquire() as pconn:
                try:
                    await pconn.execute(
                        "UPDATE users SET evpoints = evpoints + 255, redeems = redeems - 1 WHERE u_id = $1",
                        ctx.author.id,
                    )
                    await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 1 WHERE u_id = $1", ctx.author.id)
                except:
                    await ctx.send("You do not have enough redeems")
                    return
                await ctx.send(
                    "You now have 255 Effort Value Points!\nSee them on your Trainer Card!"
                )
        elif val.lower().endswith("capsules") or val.lower().endswith("capsule"):
            async with ctx.bot.db[0].acquire() as pconn:
                inv = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inv["nature-capsules"] = inv.get("nature-capsules", 0) + 5
                try:
                    await pconn.execute(
                        "UPDATE users SET redeems = redeems - 1, inventory = $1::json WHERE u_id = $2",
                        inv,
                        ctx.author.id,
                    )
                    await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 1 WHERE u_id = $1", ctx.author.id)
                except:
                    await ctx.send("You do not have enough redeems")
                    return
                await ctx.send("You have Successfully purchased 5 Nature Capsules")
        elif val.capitalize().replace(" ", "-") in totalList:
            pokemon = val.capitalize().replace(" ", "-")
            threshold = 4000
            async with ctx.bot.db[0].acquire() as pconn:
                inventory, items, redeems = await pconn.fetchrow(
                    "SELECT inventory::json, items::json, redeems FROM users WHERE u_id = $1",
                    ctx.author.id,
                )

            threshold = round(
                threshold - threshold * (inventory["shiny-multiplier"] / 100)
            )
            shiny = random.choice([False for _ in range(threshold)] + [True])

            if redeems < 1:
                await ctx.send("You do not have enough redeems")
                return
            item = None
            async with ctx.bot.db[0].acquire() as pconn:
                if (
                    max(1, int(random.random() * 30))
                    == max(1, int(random.random() * 30))
                    and pokemon.lower() in REDEEM_DROPS
                ):
                    item = REDEEM_DROPS[pokemon.lower()]
                    items[item] = items.get(item, 0) + 1
                await pconn.execute(
                    "UPDATE users SET redeems = redeems - 1, items = $1::json, inventory = $2::json WHERE u_id = $3",
                    items,
                    inventory,
                    ctx.author.id,
                )
                await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + 1 WHERE u_id = $1", ctx.author.id)
            pokedata = await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, shiny=shiny
            )
            ivpercent = round((pokedata.iv_sum / 186) * 100, 2)
            await ctx.bot.get_partial_messageable(1004755418511310878).send(
                f"``User:`` {ctx.author} | ``ID:`` {ctx.author.id}\nHas redeemed a {pokedata.emoji}{val} (`{pokedata.id}`)\n----------------------------------"
            )
            msg = f"Here's your {pokedata.emoji}{val} ({ivpercent}% iv)!\n"
            if item:
                msg += f"Dropped - {item}"
            await ctx.send(msg)
        else:
            await ctx.send(
                "You did not select a valid option. Use `/redeem` to see all options."
            )

            return
        #
        user = await ctx.bot.mongo_find(
            "users",
            {"user": ctx.author.id},
            default={"user": ctx.author.id, "progress": {}},
        )
        progress = user["progress"]
        progress["redeem"] = progress.get("redeem", 0) + 1
        await ctx.bot.mongo_update(
            "users", {"user": ctx.author.id}, {"progress": progress}
        )
        #

    @redeem.command(with_app_command=True)  # This has to be registered
    @tradelock
    async def multiple(self, ctx, amount: int, option: str):

        if option == "credits":
            async with ctx.bot.db[0].acquire() as pconn:                                              # no point in this being uncommented if it isnt being used - motz
                redeems = await pconn.fetchval(
                    "SELECT redeems FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
                if redeems < amount:
                    await ctx.send("You do not have enough redeems")
                    return
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + (50000 * $1), redeems = redeems - $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
                await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + $2 WHERE u_id = $1", ctx.author.id, amount)
                await ctx.bot.get_partial_messageable(1004755418511310878).send(
                    f"``User:`` {ctx.author} | ``ID:`` {ctx.author.id}\nHas redeemed {amount} redeems for {50000*amount:,} credits ON <t:{int((time.time()))}:F> about <t:{int((time.time()))}:R\n----------------------------------"
                )
                await ctx.send(
                    f"You redeemed {amount} redeems for {50000*amount:,} credits!"
                )
            return
        # Option is probably a pokemon name
        pokemon = option
        if pokemon.capitalize().replace(" ", "-") not in totalList:
            await ctx.send("That's not a valid pokemon name!")
            return
        pokemon = pokemon.capitalize().replace(" ", "-")
        threshold = 4000
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT inventory::json, items::json, redeems FROM users WHERE u_id = $1",
                ctx.author.id,
            )
        if details is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        inventory, items, redeems = details
        threshold = round(threshold - threshold * (inventory["shiny-multiplier"] / 100))   
        if redeems < amount:
            await ctx.send("You do not have enough redeems")
            return
        if amount > 1000:
            await ctx.send("For performance reasons, redeem multiple is capped at 1000 redeems at a time. Please adjust your command accordingly and send again.")
            return
        else:
            await ctx.bot.get_partial_messageable(1004755418511310878).send(
                f"``User:`` {ctx.author} | ``ID:`` {ctx.author.id}\nHas redeemed {amount} {pokemon} with redeemmultiple ON <t:{int((time.time()))}:F> about <t:{int((time.time()))}:R\n----------------------------------"
            )
            await ctx.send(f"Redeeming {amount} {pokemon}...")
            iters = 0
            for i in range(amount):
                item = None
                shiny = not random.randrange(threshold)
                pokedata = await ctx.bot.commondb.create_poke(
                    ctx.bot, ctx.author.id, pokemon, shiny=shiny
                )
                if not random.randrange(30) and pokemon.lower() in REDEEM_DROPS:
                    item = REDEEM_DROPS[pokemon.lower()]
                    items[item] = items.get(item, 0) + 1
                iters += 1
                if item:
                    await ctx.send(f"Dropped - {iters}x {item}")
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems - $1, items = $2::json, inventory = $3::json WHERE u_id = $4",
                    amount,
                    items,
                    inventory,
                    ctx.author.id,
                )
                await pconn.execute("UPDATE achievements SET redeems_used = redeems_used + $2 WHERE u_id = $1", ctx.author.id, amount)
                #await ctx.bot.get_partial_messageable(1004755418511310878).send(
                #   f"``User:`` {ctx.author} | ``ID:`` {ctx.author.id}\nHas redeemed a {pokedata.emoji}{pokemon} (`{pokedata.id}`) with redeem-multiple command.\n----------------------------------"
                #)
                #
                user = await ctx.bot.mongo_find(
                    "users",
                    {"user": ctx.author.id},
                    default={"user": ctx.author.id, "progress": {}},
                )
                progress = user["progress"]
                progress["redeem"] = progress.get("redeem", 0) + amount
                await ctx.bot.mongo_update(
                    "users", {"user": ctx.author.id}, {"progress": progress}
                )
                
            await ctx.send(f"Successfully redeemed {amount} {pokemon}!")

    #@commands.hybrid_command()
   # @#tradelock
    async def compensation(self, ctx, pokemon: str):
        async with self.bot.db[0].acquire() as pconn:
            has_got_comp = await pconn.fetchval(
                "SELECT comp FROM users WHERE u_id = $1", ctx.author.id
            )

            if has_got_comp:
                await ctx.send(
                    "You have already claimed compensation, or started after the announcement."
                )

                return
            elif pokemon.capitalize().replace(" ", "-") not in totalList:
                await ctx.send("You did not select a valid Pokemon.")
                return
            elif pokemon.capitalize().replace(" ", "-") in comp_pseudos_legends:
                await ctx.send("Pseudos/legends are disallowed, please try again.")
                return
            else:
                chosen_mon = pokemon.capitalize().replace(" ", "-")
                patreon_status = await ctx.bot.patreon_tier(ctx.author.id)
                if patreon_status in ("Crystal Patreon", "Elite Patreon"):
                    await pconn.execute(
                        "UPDATE users SET chain = chain + 1000 WHERE u_id = $1",
                        ctx.author.id,
                    )

                elif patreon_status == "Gold Patreon":
                    await pconn.execute(
                        "UPDATE users SET chain = chain + 750 WHERE u_id = $1",
                        ctx.author.id,
                    )

                else:
                    await pconn.execute(
                        "UPDATE users SET chain = chain + 500 WHERE u_id = $1",
                        ctx.author.id,
                    )

                if patreon_status in (
                    "Crystal Patreon",
                    "Elite Patreon",
                    "Gold Patreon",
                    "Silver Patreon",
                    "MewBot Patreon",
                ):
                    inventory = await pconn.fetchval(
                        "SELECT inventory::json FROM users WHERE u_id = $1",
                        ctx.author.id,
                    )

                    inventory["legend chest"] = inventory.get("legend chest", 0) + 1
                    await pconn.execute(
                        "UPDATE users SET inventory = $1::json where u_id = $2",
                        inventory,
                        ctx.author.id,
                    )

                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )

                inventory["mythic chest"] = inventory.get("mythic chest", 0) + 1

                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    ctx.author.id,
                )

                await pconn.execute(
                    "UPDATE users SET redeems = redeems + 100 WHERE u_id = $1",
                    ctx.author.id,
                )

                pokedata = await ctx.bot.commondb.create_poke(
                    ctx.bot, ctx.author.id, chosen_mon, shiny=True
                )

                ivpercent = round(pokedata.iv_sum / 186 * 100, 2)
                await ctx.send(
                    f"{ctx.author.id}\nHas obtained a shiny {chosen_mon} ({ivpercent}% iv), as well as redeems, a chest, and a boost to their shadow hunt. Thank you for your patience <3"
                )

                await pconn.execute(
                    "UPDATE users SET comp = $2 WHERE u_id = $1", ctx.author.id, True
                )


    @commands.hybrid_command()
    @tradelock
    async def claim_skin(self, ctx):
        async with self.bot.db[0].acquire() as pconn:
            has_got_skin = await pconn.fetchval(
                "SELECT comp FROM users WHERE u_id = $1", ctx.author.id
            )
            if has_got_skin:
                await ctx.send(
                    "You already got this skin."
                )
                return
            else:
                poke = "ditto"
                skin = "verification"
                skins = await pconn.fetchval(
                    "SELECT skins::json FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
                #skins = skins["data"]
                if poke not in skins:
                    skins[poke] = {}
                skins[poke][skin] = skins[poke].get(skin, 0) + 1
                await pconn.execute(
                    "UPDATE users SET comp = $3, skins = $2::json WHERE u_id = $1",
                    ctx.author.id,
                    skins,
                    True,
                )
                await ctx.send("Thanks for being a Founding member of DittoBOT and seeing us get Verified!\nHere is the Ditto Skin we promised!\nThe skin should show in your `/skin list`!\n(There may be some bugs using ditto with a skin in duels, we are aware<3) ")
                await ctx.bot.get_partial_messageable(1004755418511310878).send(
                       f"`User:` {ctx.author} | `ID:` {ctx.author.id}\n**Claimed their __VERIFICATION SKIN__** on  <t:{int((time.time()))}:F> about <t:{int((time.time()))}:R>\n----------------------------------"
                    )


async def setup(bot):
    await bot.add_cog(Redeem(bot))
