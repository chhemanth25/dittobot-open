import asyncio
from datetime import datetime

import discord
from discord.ext import commands
from utils.checks import tradelock
from utils.misc import ConfirmView, get_prefix

from dittocogs.json_files import *


def trade_embed(
    p1,
    p2,
    user_names,
    user_nums,
    user_levels,
    user_credits: int,
    user_redeems: int,
    ctx_names,
    ctx_nums,
    ctx_levels,
    ctx_credits: int,
    ctx_redeems: int,
    ctx_confirm,
    user_confirm,
):
    if user_credits < 0:
        user_credits = 0
    elif ctx_credits < 0:
        ctx_credits = 0
    e = discord.Embed(color=0xFFB6C1)
    ctx_total = " "
    user_total = " "

    for idx, i in enumerate(ctx_names):
        ctx_total += f"{i.capitalize()} Level {ctx_levels[idx]}, "
    for idx, i in enumerate(user_names):
        user_total += f"{i.capitalize()} Level {user_levels[idx]}, "

    ctx_doc = f"""```Elm\n{p1.name} is Offering \nPokemon: {ctx_total}\nCredits: {ctx_credits}\nRedeems: {ctx_redeems}\nConfirmed: {'✅' if ctx_confirm else '❎'}```"""

    user_doc = f"""\n```Elm\n{p2.name} is Offering \nPokemon: {user_total}\nCredits: {user_credits}\nRedeems: {user_redeems}\nConfirmed: {'✅' if user_confirm else '❎'}```"""
    e.description = ctx_doc + user_doc
    return e


class Trade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_task = asyncio.create_task(self.initialize())
        # 2 different users could make a trade to the same person, who does `;accept` and gets both before either notices the other started.
        # Since this issue only happens in a single guild, a cluster-local tradelock can prevent it.
        self.start_tradelock = []

    async def initialize(self):
        await self.bot.redis_manager.redis.execute("LPUSH", "tradelock", "123")

    @commands.hybrid_group(name="gift")
    async def gift_cmds(self, ctx):
        """Top layer of group"""

    @gift_cmds.command()
    @tradelock
    async def redeems(self, ctx, user: discord.Member, val: int):
        if ctx.guild.id != 999953429751414784:
            await ctx.send(
                f"This command can only be used in the {self.bot.user.name} Official Server."
            )
            return
        if ctx.author.id == user.id:
            await ctx.send("You can not give yourself redeems.")
            return
        if val <= 0:
            await ctx.send("You need to give at least 1 redeem!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if any(
                i["tradelock"]
                for i in (
                    await pconn.fetch(
                        "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                        [user.id, ctx.author.id],
                    )
                )
            ):
                await ctx.send("A user is not allowed to Trade")
                return
            giver_deems = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", ctx.author.id
            )
            getter_deems = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", user.id
            )
        if getter_deems is None:
            await ctx.send(f"{user.name} has not started... Start with `/start` first!")
            return
        if giver_deems is None:
            await ctx.send(
                f"{ctx.author.name} has not started... Start with `/start` first!"
            )
            return
        if val > giver_deems:
            await ctx.send("You don't have that many redeems!")
            return
        if not await ConfirmView(
            ctx, f"Are you sure you want to give {val} redeems to {user.name}?"
        ).wait():
            await ctx.send("Trade Canceled")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", ctx.author.id
            )
            if val > curcreds:
                await ctx.send("You don't have that many redeems anymore...")
                return
            await pconn.execute(
                "UPDATE users SET redeems = redeems - $1 WHERE u_id = $2",
                val,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await ctx.send(f"{ctx.author.name} has given {user.name} {val} redeems.")
            await ctx.bot.get_partial_messageable(1004571710323957830).send(
                f"\N{SMALL BLUE DIAMOND}- {ctx.author.name} - ``{ctx.author.id}`` has given \n{user.name} - `{user.id}`\n```{val} redeems```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_redeems, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                val,
                "gift_redeems",
                datetime.now(),
            )

    @gift_cmds.command()
    @tradelock
    async def credits(self, ctx, user: discord.Member, val: int):
        if ctx.author.id == user.id:
            await ctx.send("You can not give yourself credits.")
            return
        if val <= 0:
            await ctx.send("You need to give at least 1 credit!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if any(
                i["tradelock"]
                for i in (
                    await pconn.fetch(
                        "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                        [user.id, ctx.author.id],
                    )
                )
            ):
                await ctx.send("A user is not allowed to Trade")
                return
            giver_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )

        if getter_creds is None:
            await ctx.send(f"{user.name} has not started... Start with `/start` first!")
            return
        if giver_creds is None:
            await ctx.send(
                f"{ctx.author.name} has not started... Start with `/start` first!"
            )
            return
        if val > giver_creds:
            await ctx.send("You don't have that many credits!")
            return
        if not await ConfirmView(
            ctx, f"Are you sure you want to give {val} credits to {user.name}?"
        ).wait():
            await ctx.send("Trade Canceled")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
            )
            if val > curcreds:
                await ctx.send("You don't have that many credits anymore...")
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                val,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await ctx.send(f"{ctx.author.name} has given {user.name} {val} credits.")
            await ctx.bot.get_partial_messageable(1004571710323957830).send(
                f"\N{SMALL BLUE DIAMOND}- {ctx.author.name} - ``{ctx.author.id}`` has gifted \n{user.name} - `{user.id}`\n```{val} credits```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                val,
                "gift",
                datetime.now(),
            )

    @gift_cmds.command()
    @tradelock
    async def pokemon(self, ctx, user: discord.Member, val: int):
        if ctx.author == user:
            await ctx.send("You cannot give a Pokemon to yourself.")
            return
        if val <= 1:
            await ctx.send("You can not give away that Pokemon")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            for u in (ctx.author, user):
                id_ = await pconn.fetchval(
                    "SELECT u_id FROM users WHERE u_id = $1", u.id
                )
                if id_ is None:
                    await ctx.send(f"{u.name} has not started!")
                    return
            if any(
                i["tradelock"]
                for i in (
                    await pconn.fetch(
                        "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                        [user.id, ctx.author.id],
                    )
                )
            ):
                await ctx.send("A user is not allowed to Trade")
                return
            poke_id = await pconn.fetchval(
                "SELECT pokes[$1] FROM users WHERE u_id = $2", val, ctx.author.id
            )
            name = await pconn.fetchrow(
                "SELECT market_enlist, pokname, shiny, radiant, fav, tradable FROM pokes WHERE id = $1",
                poke_id,
            )
        if not name:
            await ctx.send("Invalid Pokemon Number")
            return
        shine = ""
        if name["shiny"]:
            shine += "Shiny "
        if name["radiant"]:
            shine += "Radiant "
        if name["fav"]:
            await ctx.send(
                "You can't give away a favorited pokemon. Unfavorite it first!"
            )
            return
        if not name["tradable"]:
            await ctx.send("That pokemon is not tradable.")
            return
        name = name["pokname"]
        if name == "Egg":
            await ctx.send("You can not give Eggs!")
            return

        if not await ConfirmView(
            ctx, f"Are you sure you want to give a {name} to {user.name}?"
        ).wait():
            await ctx.send("Trade Canceled")
            return

        await ctx.bot.commondb.remove_poke(ctx.author.id, poke_id)
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = $2",
                poke_id,
                user.id,
            )
            await ctx.send(f"{ctx.author.name} has given {user.name} a {name}")
            await ctx.bot.get_partial_messageable(1004571710323957830).send(
                f"\N{SMALL BLUE DIAMOND}- {ctx.author.name} - ``{ctx.author.id}`` has given \n{user.name} - `{user.id}`\n```{poke_id} {name}```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_pokes, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                [poke_id],
                "give",
                datetime.now(),
            )

    @commands.hybrid_command()
    async def trade(self, ctx, user: discord.Member):
        # SETUP
        if ctx.author.id == user.id:
            await ctx.send("You cannot trade with yourself!")
            return
        current_traders = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if ctx.author.id in current_traders:
            await ctx.send(f"{ctx.author.name} is currently in a Trade!")
            return
        if user.id in current_traders:
            await ctx.send(f"{user.name} is currently in a Trade!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if any(
                [
                    i["tradelock"]
                    for i in (
                        await pconn.fetch(
                            "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                            [user.id, ctx.author.id],
                        )
                    )
                ]
            ):
                await ctx.send(f"A user is not allowed to Trade")
                return
            if (
                await pconn.fetchval(
                    "SELECT 1 FROM users WHERE u_id = $1", ctx.author.id
                )
                is None
            ):
                await ctx.send(
                    f"{ctx.author.display_name} has not started!\nStart with `/start` first!"
                )
                return
            if (
                await pconn.fetchval("SELECT 1 FROM users WHERE u_id = $1", user.id)
                is None
            ):
                await ctx.send(
                    f"{user.display_name} has not started!\nStart with `/start` first!"
                )
                return
        await self.bot.redis_manager.redis.execute(
            "LPUSH", "tradelock", str(ctx.author.id)
        )
        prefix = await get_prefix(ctx.bot, ctx)

        def check(m):
            return (
                m.author.id == user.id
                and m.content in (f"{prefix}accept", f"{prefix}reject")
                and m.channel == ctx.channel
            )

        await ctx.send(
            f"{ctx.author.mention} has requested a trade with {user.mention}!\n"
            f"Say `{prefix}accept` to accept the trade or `{prefix}reject` to reject it!"
        )
        try:
            acceptance = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await ctx.send(f"{user.mention} took too long to accept the Trade...")
            return
        if acceptance.content.lower() == f"{prefix}reject":
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await ctx.send("Trade Rejected!")
            return
        # double check now that the trade is ready to go after the wait_for
        if user.id in self.start_tradelock:
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await ctx.send(f"{user.name} is currently in a Trade!")
            return
        self.start_tradelock.append(user.id)
        current_traders = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if user.id in current_traders:
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await ctx.send(f"{user.name} is currently in a Trade!")
            return
        await self.bot.redis_manager.redis.execute("LPUSH", "tradelock", str(user.id))
        self.start_tradelock.remove(user.id)
        # ESTABLISH TRADE CONTENTS
        user_names = []
        user_nums = []
        user_shine = []
        user_levels = []
        user_ids = []
        user_credits = 0
        user_redeems = 0
        ctx_confirm, user_confirm = None, None
        ctx_names = []
        ctx_shine = []
        ctx_nums = []
        ctx_levels = []
        ctx_credits = 0
        ctx_redeems = 0
        ctx_ids = []
        e = discord.Embed(title=f"Trade Between {ctx.author.name} and {user.name}")
        desc = (
            "Initiate the Trade by Adding a Pokemon or Credits\n"
            f"`{prefix}add p <pokemon_numbers>`\n"
        )
        desc += (
            f"`{prefix}add r <redeem_amount>`\n"
            if ctx.guild.id == 999953429751414784
            else ""
        )
        desc += (
            f"`{prefix}add c <credits_amount>`\n\n"
            f"Confirm the Trade with `{prefix}confirm`\n"
            f"[Replace `{prefix}add p` with `{prefix}remove p` to remove Pokemon"
        )
        desc += ", Redeems," if ctx.guild.id == 999953429751414784 else ""
        desc += " or Credits]"
        e.description = desc
        first_embed = await ctx.send(embed=e)
        poke_length = len(f"{prefix}add p")
        try:
            while True:

                def first_check(first_add):
                    return first_add.author.id in (ctx.author.id, user.id) and any(
                        first_add.content.lower().startswith(com)
                        for com in (
                            f"{prefix}add r ",
                            f"{prefix}add c ",
                            f"{prefix}add p ",
                            f"{prefix}remove r ",
                            f"{prefix}remove c ",
                            f"{prefix}remove p ",
                            f"{prefix}confirm",
                            f"{prefix}cancel",
                        )
                    )

                try:
                    first_msg = await ctx.bot.wait_for(
                        "message", check=first_check, timeout=60
                    )
                except asyncio.TimeoutError:
                    await ctx.send(f"You took too long to add Credits or Pokemon!")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "tradelock", "1", str(ctx.author.id)
                    )
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "tradelock", "1", str(user.id)
                    )
                    return

                if f"{prefix}add p" in first_msg.content.lower():
                    pokes_list = first_msg.content.lower()[poke_length:]
                    pokes_list = pokes_list.split()
                    try:
                        pokes_list = [int(x) for x in pokes_list]
                    except ValueError:
                        await ctx.send("Invalid Pokemon Number!")
                        continue
                    if 1 in pokes_list:
                        await ctx.send("You can not give off your Number 1 Pokemon")
                        continue
                    if len(pokes_list) == 1:
                        async with ctx.bot.db[0].acquire() as pconn:
                            details = await pconn.fetch(
                                "SELECT id, pokname, pokelevel, shiny, radiant, tradable FROM pokes WHERE id = (SELECT pokes[$1] FROM users WHERE u_id = $2)",
                                pokes_list[0],
                                first_msg.author.id,
                            )

                            temp = [t["id"] for t in details]
                            the_ids = temp
                    else:
                        the_ids = ""
                        async with ctx.bot.db[0].acquire() as pconn:
                            stmt = await pconn.prepare(
                                "SELECT pokes[$1] FROM users WHERE u_id = $2"
                            )
                            for s in pokes_list:
                                num = await stmt.fetchval(s, first_msg.author.id)
                                the_ids += f" {num} "

                        the_ids = the_ids.split()
                        try:
                            the_ids = [int(t) for t in the_ids]
                        except ValueError:
                            await ctx.send("You do not have those Pokemon!")
                            continue
                        async with ctx.bot.db[0].acquire() as pconn:
                            details = await pconn.fetch(
                                "SELECT id, pokname, pokelevel, shiny, radiant, tradable FROM pokes WHERE id = ANY ($1) AND market_enlist <> True",
                                the_ids,
                            )

                    if details in ([], None):
                        await ctx.send(
                            "You do not have that Pokemon or that Pokemon is currently in the market!"
                        )
                        continue
                    names = [t["pokname"] for t in details]
                    levels = [t["pokelevel"] for t in details]
                    shine = []
                    for t in details:
                        hold = ""
                        if t["shiny"]:
                            hold += "Shiny"
                        if t["radiant"]:
                            hold += "Radiant"
                        shine.append(hold)
                    if "Egg" in names:
                        await ctx.send("You can not trade Eggs!")
                        continue
                    if any([id in ctx_ids for id in the_ids]):
                        await ctx.send(
                            f"{ctx.author.mention} you have already added that Pokemon!"
                        )
                        continue
                    if any([id in user_ids for id in the_ids]):
                        await ctx.send(
                            f"{user.mention} you have already added that Pokemon!"
                        )
                        continue
                    if not all(t["tradable"] for t in details):
                        await ctx.send("That pokemon is not tradable.")
                        continue
                    else:
                        if first_msg.author == ctx.author:
                            ctx_names += names
                            ctx_shine += shine
                            ctx_levels += levels
                            ctx_nums += list(pokes_list)
                            ctx_ids += the_ids
                        else:
                            user_names += names
                            user_shine += shine
                            user_levels += levels
                            user_nums += list(pokes_list)
                            user_ids += the_ids

                elif f"{prefix}cancel" in first_msg.content.lower():
                    await ctx.send(f"Trade Canceled")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "tradelock", "1", str(ctx.author.id)
                    )
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "tradelock", "1", str(user.id)
                    )
                    return

                elif f"{prefix}add c" in first_msg.content.lower():
                    creds = first_msg.content.lower()[poke_length:]
                    creds = (
                        creds.replace("k", "000")
                        if "k" in creds
                        else (creds.replace("m", "000000") if "m" in creds else creds)
                    )
                    async with ctx.bot.db[0].acquire() as pconn:
                        cur_creds = await pconn.fetchval(
                            "SELECT mewcoins FROM users WHERE u_id = $1",
                            first_msg.author.id,
                        )
                    try:
                        creds = int(creds.replace(",", "").replace(".", ""))
                    except ValueError:
                        await ctx.send("That was not an amount of credits...")
                        continue
                    if first_msg.author == ctx.author:
                        if ctx_credits + creds > cur_creds:
                            await ctx.send("You do not have that many Credits!")
                            continue
                        ctx_credits += creds
                    else:
                        if user_credits + creds > cur_creds:
                            await ctx.send("You do not have that many Credits!")
                            continue
                        user_credits += creds
                    user_confirm = False
                    ctx_confirm = False
                    ctx_credits = 0 if ctx_credits <= 0 else ctx_credits
                    user_credits = 0 if user_credits <= 0 else user_credits

                elif f"{prefix}add r" in first_msg.content.lower():
                    if ctx.guild.id != 999953429751414784:
                        continue
                    redeems = first_msg.content.lower()[poke_length:]
                    redeems = (
                        redeems.replace("k", "000")
                        if "k" in redeems
                        else (
                            redeems.replace("m", "000000")
                            if "m" in redeems
                            else redeems
                        )
                    )
                    async with ctx.bot.db[0].acquire() as pconn:
                        cur_deems = await pconn.fetchval(
                            "SELECT redeems FROM users WHERE u_id = $1",
                            first_msg.author.id,
                        )
                    try:
                        redeems = int(redeems.replace(",", "").replace(".", ""))
                    except ValueError:
                        await ctx.send("That was not an amount of redeems...")
                        continue
                    if first_msg.author == ctx.author:
                        if ctx_redeems + redeems > cur_deems:
                            await ctx.send("You do not have that many Redeems!")
                            continue
                        ctx_redeems += redeems
                    else:
                        if user_redeems > cur_deems:
                            await ctx.send("You do not have that much Redeems!")
                            continue
                        user_redeems += redeems
                    user_confirm = False
                    ctx_confirm = False
                    ctx_redeems = 0 if ctx_redeems <= 0 else ctx_redeems
                    user_redeems = 0 if user_redeems <= 0 else user_redeems

                elif f"{prefix}remove p" in first_msg.content.lower():
                    pokes_list = first_msg.content.lower()[poke_length + 3 :]
                    pokes_list = pokes_list.split()
                    try:
                        pokes_list = [int(x) for x in pokes_list]
                    except ValueError:
                        await ctx.send("Invalid pokemon number!")
                        continue
                    user_confirm = False
                    ctx_confirm = False
                    if first_msg.author == ctx.author:
                        for poke in pokes_list:
                            if poke not in ctx_nums:
                                continue
                            position = ctx_nums.index(poke)
                            ctx_names.pop(position)
                            ctx_nums.pop(position)
                            ctx_shine.pop(position)
                            ctx_levels.pop(position)
                            ctx_ids.pop(position)
                    else:
                        for poke in pokes_list:
                            if poke not in user_nums:
                                continue
                            position = user_nums.index(poke)
                            user_names.pop(position)
                            user_nums.pop(position)
                            user_shine.pop(position)
                            user_levels.pop(position)
                            user_ids.pop(position)

                elif f"{prefix}remove c" in first_msg.content.lower():
                    creds = first_msg.content.lower()[poke_length + 3 :]
                    creds = (
                        creds.replace("k", "000")
                        if "k" in creds
                        else (creds.replace("m", "000000") if "m" in creds else creds)
                    )
                    try:
                        creds = int(creds.replace(",", "").replace(".", ""))
                    except ValueError:
                        await ctx.send("That was not an amount of credits...")
                        continue
                    if creds < 0:
                        await ctx.send("Nice try...")
                        continue
                    if first_msg.author == ctx.author:
                        ctx_credits -= creds
                    else:
                        user_credits -= creds
                    user_confirm = False
                    ctx_confirm = False
                    ctx_credits = 0 if ctx_credits <= 0 else ctx_credits
                    user_credits = 0 if user_credits <= 0 else user_credits

                elif f"{prefix}remove r" in first_msg.content.lower():
                    # not used atm
                    continue

                    redeems = first_msg.content.lower()[poke_length + 3 :]
                    redeems = (
                        redeems.replace("k", "000")
                        if "k" in redeems
                        else (
                            redeems.replace("m", "000000")
                            if "m" in redeems
                            else redeems
                        )
                    )
                    try:
                        redeems = int(redeems.replace(",", "").replace(".", ""))
                    except ValueError:
                        await ctx.send("That was not an amount of redeems...")
                        continue
                    if redeems < 0:
                        await ctx.send("Nice try...")
                        continue
                    if first_msg.author == ctx.author:
                        ctx_redeems -= redeems
                    else:
                        user_redeems -= redeems
                    user_confirm = False
                    ctx_confirm = False
                    ctx_redeems = 0 if ctx_redeems <= 0 else ctx_redeems
                    user_redeems = 0 if user_redeems <= 0 else user_redeems

                elif f"{prefix}confirm" == first_msg.content.lower():
                    if first_msg.author == ctx.author:
                        ctx_confirm = True
                    else:
                        user_confirm = True

                try:
                    await first_embed.edit(
                        embed=trade_embed(
                            ctx.author,
                            user,
                            user_names,
                            user_nums,
                            user_levels,
                            user_credits,
                            user_redeems,
                            ctx_names,
                            ctx_nums,
                            ctx_levels,
                            ctx_credits,
                            ctx_redeems,
                            ctx_confirm,
                            user_confirm,
                        )
                    )
                except Exception:
                    await ctx.send("Trade Canceled")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "tradelock", "1", str(ctx.author.id)
                    )
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "tradelock", "1", str(user.id)
                    )
                    return

                if ctx_confirm and user_confirm:
                    break
            # positive total_ here means AUTHOR -> USER
            # negative total_ here means USER -> AUTHOR
            total_creds = ctx_credits - user_credits
            total_deems = ctx_redeems - user_redeems
            # RE-CHECK THE TRADE
            async with ctx.bot.db[0].acquire() as pconn:
                if ctx_ids:
                    is_owner = await pconn.fetchval(
                        "SELECT u_id FROM users WHERE pokes @> $1",
                        ctx_ids,
                    )
                    if is_owner != ctx.author.id:
                        await ctx.send(
                            f"{ctx.author.display_name} no longer owns one or more of the pokemon they were trading, canceling trade!"
                        )
                        await self.bot.redis_manager.redis.execute(
                            "LREM", "tradelock", "1", str(ctx.author.id)
                        )
                        await self.bot.redis_manager.redis.execute(
                            "LREM", "tradelock", "1", str(user.id)
                        )
                        return
                if user_ids:
                    is_owner = await pconn.fetchval(
                        "SELECT u_id FROM users WHERE pokes @> $1",
                        user_ids,
                    )
                    if is_owner != user.id:
                        await ctx.send(
                            f"{user.display_name} no longer owns one or more of the pokemon they were trading, canceling trade!"
                        )
                        await self.bot.redis_manager.redis.execute(
                            "LREM", "tradelock", "1", str(ctx.author.id)
                        )
                        await self.bot.redis_manager.redis.execute(
                            "LREM", "tradelock", "1", str(user.id)
                        )
                        return
                selected_ctx, cur_ctx_credits, cur_ctx_redeems = await pconn.fetchrow(
                    "SELECT selected, mewcoins, redeems FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
                (
                    selected_user,
                    cur_user_credits,
                    cur_user_redeems,
                ) = await pconn.fetchrow(
                    "SELECT selected, mewcoins, redeems FROM users WHERE u_id = $1",
                    user.id,
                )
                if total_creds > 0:
                    if cur_ctx_credits < total_creds:
                        await ctx.send(
                            f"{ctx.author.display_name} no longer has enough credits, canceling trade!"
                        )
                        return
                else:
                    if cur_user_credits < abs(total_creds):
                        await ctx.send(
                            f"{user.display_name} no longer has enough credits, canceling trade!"
                        )
                        return
                if total_deems > 0:
                    if cur_ctx_redeems < total_deems:
                        await ctx.send(
                            f"{ctx.author.display_name} no longer has enough redeems, canceling trade!"
                        )
                        return
                else:
                    if cur_user_redeems < abs(total_deems):
                        await ctx.send(
                            f"{user.display_name} no longer has enough redeems, canceling trade!"
                        )
                        return
                if selected_ctx in ctx_ids:
                    await ctx.send(
                        f"{ctx.author.display_name} needs to unselect their pokemon before trading it!"
                    )
                    return
                if selected_user in user_ids:
                    await ctx.send(
                        f"{user.display_name} needs to unselect their pokemon before trading it!"
                    )
                    return

            # RUN THE TRADE
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    total_creds,
                    user.id,
                )
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                    total_deems,
                    user.id,
                )
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    -total_creds,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                    -total_deems,
                    ctx.author.id,
                )
                await pconn.execute(
                    (
                        "INSERT INTO trade_logs "
                        "(sender, receiver, sender_credits, sender_redeems, sender_pokes, "
                        "receiver_credits, receiver_redeems, receiver_pokes, command, time) "
                        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) "
                    ),
                    ctx.author.id,
                    user.id,
                    ctx_credits,
                    ctx_redeems,
                    ctx_ids,
                    user_credits,
                    user_redeems,
                    user_ids,
                    "trade",
                    datetime.now(),
                )
                if ctx_ids:
                    await pconn.execute(
                        "UPDATE users SET pokes = pokes || $1 WHERE u_id = $2",
                        set(ctx_ids),
                        user.id,
                    )
                    for num in ctx_ids:
                        await pconn.execute(
                            "UPDATE users set pokes = array_remove(pokes, $1) WHERE u_id = $2",
                            num,
                            ctx.author.id,
                        )
                        await pconn.execute(
                            "UPDATE pokes SET market_enlist = False WHERE id = $1",
                            num,
                        )
                if user_ids:
                    await pconn.execute(
                        "UPDATE users SET pokes = pokes || $1 WHERE u_id = $2",
                        set(user_ids),
                        ctx.author.id,
                    )
                    for num in user_ids:
                        await pconn.execute(
                            "UPDATE users set pokes = array_remove(pokes, $1) WHERE u_id = $2",
                            num,
                            user.id,
                        )
                        await pconn.execute(
                            "UPDATE pokes SET market_enlist = False WHERE id = $1",
                            num,
                        )
            await ctx.send(
                embed=make_embed(
                    title="Trade confirmed",
                    description="Checking for Trade Evolutions...",
                )
            )
            # TRADE EVOS
            async with ctx.bot.db[0].acquire() as pconn:
                if len(ctx_ids) > 0:
                    for _id in ctx_ids:
                        try:
                            pokename = await pconn.fetchval(
                                "SELECT pokname FROM pokes WHERE id = $1",
                                _id,
                            )
                            helditem = await pconn.fetchval(
                                "SELECT hitem FROM pokes WHERE id = $1", _id
                            )
                            pokename = pokename.lower()
                            pid = [
                                t["id"] for t in PFILE if t["identifier"] == pokename
                            ][0]
                            eids = [
                                t["id"]
                                for t in PFILE
                                if t["evolves_from_species_id"] == pid
                            ]
                            for eid in eids:
                                hitem = [
                                    t["held_item_id"]
                                    for t in EVOFILE
                                    if t["evolved_species_id"] == eid
                                ][0]
                                evo_trigger = [
                                    t["evolution_trigger_id"]
                                    for t in EVOFILE
                                    if t["evolved_species_id"] == eid
                                ][0]

                                if hitem:
                                    item = [
                                        t["identifier"]
                                        for t in ITEMS
                                        if t["id"] == hitem
                                    ]
                                    item = item[0]
                                    if not helditem.lower() == item.lower():
                                        continue

                                    else:
                                        evoname = [
                                            t["identifier"]
                                            for t in PFILE
                                            if t["id"] == eid
                                        ]
                                        evoname = evoname[0]
                                        await pconn.execute(
                                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                                            evoname.capitalize(),
                                            _id,
                                        )
                                        await ctx.send(
                                            embed=make_embed(
                                                title="Congratulations!!!",
                                                description=f"{user.name} Your {pokename.capitalize()} has evolved into {evoname.capitalize()}!",
                                            )
                                        )

                                elif evo_trigger == 2:
                                    evoname = [
                                        t["identifier"] for t in PFILE if t["id"] == eid
                                    ]
                                    evoname = evoname[0]
                                    await pconn.execute(
                                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                                        evoname.capitalize(),
                                        _id,
                                    )

                                    await ctx.send(
                                        embed=make_embed(
                                            title="Congratulations!!!",
                                            description=f"{user.name} Your {pokename.capitalize()} has evolved into {evoname.capitalize()}!",
                                        )
                                    )
                                else:
                                    continue
                        except:
                            pass
                if len(user_ids) > 0:
                    for _id in user_ids:
                        try:
                            pokename = await pconn.fetchval(
                                "SELECT pokname FROM pokes WHERE id = $1",
                                _id,
                            )
                            helditem = await pconn.fetchval(
                                "SELECT hitem FROM pokes WHERE id = $1", _id
                            )
                            pokename = pokename.lower()
                            try:
                                pid = [
                                    t["id"]
                                    for t in PFILE
                                    if t["identifier"] == pokename
                                ][0]
                            except:
                                continue

                            eids = [
                                t["id"]
                                for t in PFILE
                                if t["evolves_from_species_id"] == pid
                            ]

                            for eid in eids:
                                hitem = [
                                    t["held_item_id"]
                                    for t in EVOFILE
                                    if t["evolved_species_id"] == eid
                                ][0]
                                evo_trigger = [
                                    t["evolution_trigger_id"]
                                    for t in EVOFILE
                                    if t["evolved_species_id"] == eid
                                ][0]

                                if hitem:
                                    item = [
                                        t["identifier"]
                                        for t in ITEMS
                                        if t["id"] == hitem
                                    ]
                                    item = item[0]
                                    if not helditem.lower() == item.lower():
                                        continue

                                    else:
                                        evoname = [
                                            t["identifier"]
                                            for t in PFILE
                                            if t["id"] == eid
                                        ]
                                        evoname = evoname[0]
                                        await pconn.execute(
                                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                                            evoname.capitalize(),
                                            _id,
                                        )
                                        await ctx.send(
                                            embed=make_embed(
                                                title="Congratulations!!!",
                                                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {evoname.capitalize()}!",
                                            )
                                        )
                                elif evo_trigger == 2:
                                    evoname = [
                                        t["identifier"] for t in PFILE if t["id"] == eid
                                    ]
                                    evoname = evoname[0]
                                    await pconn.execute(
                                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                                        evoname.capitalize(),
                                        _id,
                                    )
                                    await ctx.send(
                                        embed=make_embed(
                                            title="Congratulations!!!",
                                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {evoname.capitalize()}!",
                                        )
                                    )
                                else:
                                    continue
                        except:
                            pass
            await ctx.send(embed=make_embed(title="Trade Complete"))
        except Exception:
            raise
        finally:
            # Just in case
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(user.id)
            )


async def setup(bot):
    await bot.add_cog(Trade(bot))
