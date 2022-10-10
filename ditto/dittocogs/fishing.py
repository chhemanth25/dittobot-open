import asyncio
import random
from math import floor

from discord.ext import commands
from utils.misc import get_spawn_url

from dittocogs.pokemon_list import *


def is_key(item):
    conds = [item.endswith("-orb"), item == "coin-case"]
    return any(conds)


def getcap(level):
    if level <= 50:
        ans = (level**3 * (100 - level)) / 50
    elif level >= 50 and level <= 68:
        ans = (level**3 * (150 - level)) / 100
    elif level >= 68 and level <= 98:
        ans = (level**3 * ((1911 - 10 * level) / 3)) / 500
    elif level >= 98 and level <= 100:
        ans = (level**3 * (160 - level)) / 100
    else:
        ans = 2147483647
    ans = floor(ans // 10)
    ans = max(10, ans)
    return ans


def scatter(iterable):
    new_list = []
    for i in iterable:
        if random.randint(1, 2) == 1 and new_list.count("_") <= len(iterable) // 2:
            new_list.append("_")
        else:
            new_list.append(i)

    return "".join(new_list)


class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def fish(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT *, inventory::json as cast_inv FROM users WHERE u_id = $1",
                ctx.author.id,
            )
        if details is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        rod = details["held_item"]
        if not rod or not rod.endswith("rod"):
            await ctx.send(
                "You are not Holding a Fishing Rod!\nBuy one in the shop with `/shop rods` first."
            )
            return
        rod = rod.capitalize().replace("-", " ")
        exp = details["fishing_exp"]
        level = details["fishing_level"]
        energy = details["energy"]
        cap = details["fishing_level_cap"]

        if energy <= 0:
            await ctx.send(
                f"You don't have any more energy points!\nWait for your Energy to be replenished, or vote for {self.bot.user.name} to get more energy!"
            )
            cog = ctx.bot.get_cog("Extras")
            if cog is not None:
                await cog.vote.callback(cog, ctx)
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET energy = energy - 1 WHERE u_id = $1", ctx.author.id
            )

        energy = energy - 1

        e = discord.Embed(title=f"You Cast Your {rod} into the Water!", color=0xFFB6C1)
        e.add_field(name="Fishing", value="...")
        e.set_image(url=await get_spawn_url("fishing.gif"))
        embed = await ctx.send(embed=e)

        SHOP = await ctx.bot.db[1].shop.find({}).to_list(None)
        cheaps = [
            t["item"]
            for t in SHOP
            if t["price"] <= 3500 and not is_key(t["item"]) and t["item"] != "old-rod"
        ]

        mids = [
            t["item"]
            for t in SHOP
            if t["price"] >= 3500
            and t["price"] <= 5000
            and not is_key(t["item"])
            and t["item"] != "old-rod"
        ]

        expensives = [
            t["item"]
            for t in SHOP
            if t["price"] >= 5000
            and t["price"] <= 8000
            and not is_key(t["item"])
            and t["item"] != "old-rod"
        ]

        supers = [
            t["item"]
            for t in SHOP
            if t["price"] >= 8000 and not is_key(t["item"]) and t["item"] != "old-rod"
        ]

        # Fishing EXP bonuses cap at level 100, RNG from [0...2000] to 10000 (20%)
        chance = random.uniform(max(min(100, level), 0) * 20, 10000)
        if chance < 8000:  # 80%
            item = random.choice(cheaps)
            poke = random.choice(common_water)
        elif chance < 9500:  # 15%
            item = random.choice(cheaps)
            poke = random.choice(uncommon_water)
        elif chance < 9900:  # 4%
            item = random.choice(mids)
            poke = random.choice(rare_water)
        elif chance < 9999:  # 0.99%
            item = random.choice(expensives)
            poke = random.choice(extremely_rare_water)
        else:  # 0.01%
            item = random.choice(supers)
            poke = random.choice(ultra_rare_water)
        poke = poke.capitalize()

        # chance to get chests
        if not random.randint(0, 50):
            item = "common chest"
        elif not random.randint(0, 400):
            item = "rare chest"

        # SMALL chance to get an ultra rare item 3/10000 -> 15/10000
        chance = random.uniform(0, 10000)
        chance -= min(exp, 100000) / 8333
        if chance < 3:
            item = random.choice(("rusty-sword", "rusty-shield"))

        pkid = (await ctx.bot.db[1].forms.find_one({"identifier": poke.lower()}))[
            "pokemon_id"
        ]
        name = poke
        threshold = 5000

        inventory = details["cast_inv"]
        threshold = round(
            threshold - threshold * (inventory.get("shiny-multiplier", 0) / 100)
        )
        shiny = random.choice([False for i in range(threshold)] + [True])
        exp_gain = [
            t["price"] for t in SHOP if t["item"] == rod.lower().replace(" ", "-")
        ][0] / 1000
        exp_gain += exp_gain * level / 2

        await asyncio.sleep(random.randint(3, 7))
        scattered_name = scatter(name)
        e = discord.Embed(title=f"You fished up a... ```{scattered_name}```")
        e.set_footer(text="You have 10 Seconds to guess the Pokemon's name to catch it!")
        try:
            await embed.edit(embed=e)
        except discord.NotFound:
            await ctx.send(embed=e)

        def check(m):
            return (
                m.author == ctx.author
                and poke.lower() in m.content.lower().replace(" ", "-")
            )

        try:
            await ctx.bot.wait_for("message", check=check, timeout=15)
        except asyncio.TimeoutError:
            await ctx.send(f"TIME'S UP!\nUnfortunately the {poke} got away...")
            return

        pokedata = await ctx.bot.commondb.create_poke(
            ctx.bot, ctx.author.id, poke, shiny=shiny
        )
        ivpercent = round((pokedata.iv_sum / 186) * 100, 2)
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute("UPDATE achievements SET fishing_success = fishing_success + 1 WHERE u_id = $1", ctx.author.id)
            if item not in ("common chest", "rare chest"):
                items = await pconn.fetchval(
                    "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
                )
                items[item] = items.get(item, 0) + 1
                await pconn.execute(
                    "UPDATE users SET items = $1::json WHERE u_id = $2",
                    items,
                    ctx.author.id,
                )
            else:
                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inventory[item] = inventory.get(item, 0) + 1
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    ctx.author.id,
                )
            leveled_up = cap < (exp_gain + exp) and level < 100
            if leveled_up:
                newcap = getcap(level)
                level += 1
                await pconn.execute(
                    "UPDATE users SET fishing_level = $3, fishing_level_cap = $2, fishing_exp = 0 WHERE u_id = $1",
                    ctx.author.id,
                    newcap,
                    level,
                )

            else:
                await pconn.execute(
                    "UPDATE users SET fishing_exp = fishing_exp + $2 WHERE u_id = $1",
                    ctx.author.id,
                    exp_gain,
                )

        e = discord.Embed(
            title=f"Here's what you got from fishing with your {rod}!",
            color=0xFFB6C1,
        )
        item = item.replace("-", " ").capitalize()
        e.add_field(
            name="You caught a", value=f"{pokedata.emoji}{poke} ({ivpercent}% iv)!"
        )
        e.add_field(name="You also found a", value=f"{item}")
        e.add_field(
            name=f"You also got {exp_gain} Fishing Experience Points",
            value="Increase your fishing Exp gain by buying a Better Rod!",
        )
        if leveled_up:
            e.add_field(
                name="You also Leveled Up!",
                value=f"Your Fishing Level is now Level {level}",
            )

        e.set_footer(
            text=f"You have used an Energy Point - You have {energy} remaining!"
        )
        #
        user = await ctx.bot.mongo_find(
            "users",
            {"user": ctx.author.id},
            default={"user": ctx.author.id, "progress": {}},
        )
        progress = user["progress"]
        progress["fish"] = progress.get("fish", 0) + 1
        await ctx.bot.mongo_update(
            "users", {"user": ctx.author.id}, {"progress": progress}
        )
        #
        try:
            await embed.edit(embed=e)
        except discord.NotFound:
            await ctx.send(embed=e)
        if energy <= 0:
            await ctx.send(
                f"Sorry, you seem to be out of energy!\nVote for {self.bot.user.name} to get more energy with `/vote`!"
            )
            cog = ctx.bot.get_cog("Extras")
            if cog is not None:
                await cog.vote.callback(cog, ctx)
        # Dispatches an event that a poke was fished.
        # on_poke_fish(self, channel, user)
        ctx.bot.dispatch("poke_fish", ctx.channel, ctx.author)


async def setup(bot):
    await bot.add_cog(Fishing(bot))
