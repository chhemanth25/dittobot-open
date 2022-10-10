import asyncio
import contextlib
import inspect
import math
import re
import time

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands.converter import (
    MemberConverter,
    TextChannelConverter,
    _convert_to_bool,
)
from discord.ext.commands.view import StringView
from ditto.utils.checks import Rank
from utils.checks import check_mod
from pokemon_utils.utils import get_pokemon_info

OS = discord.Object(id=999953429751414784)
OSGYMS = discord.Object(id=857746524259483679)
OSAUCTIONS = discord.Object(id=857745448717516830)
VK_SERVER = discord.Object(id=829791746221277244)

GREEN = "\N{LARGE GREEN CIRCLE}"
YELLOW = "\N{LARGE YELLOW CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"


class Mod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.safe_edb = ""

    @check_mod()
    @commands.hybrid_group(name="mod")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def moderator(self, ctx):
        await ctx.send("Affirmative.")
        ...

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def spcount(self, ctx, userid: discord.Member):
        """MOD: Returns a users special pokemon counts, such as shiny and radiant"""
        async with ctx.bot.db[0].acquire() as pconn:
            shiny = await pconn.fetchval(
                "select count(*) from pokes where shiny = true AND id in (select unnest(u.pokes) from users u where u.u_id = $1)",
                userid.id,
            )
            radiant = await pconn.fetchval(
                "select count(*) from pokes where radiant = true AND id in (select unnest(u.pokes) from users u where u.u_id = $1)",
                userid.id,
            )
        embed = discord.Embed()
        embed.add_field(name="Number of Shiny pokemon", value=f"{shiny}", inline=True)
        embed.add_field(
            name="Number of Radiant pokemon", value=f"{radiant}", inline=False
        )
        embed.set_footer(text="Special Pokemon Counts")
        await ctx.send(embed=embed)

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def whoowns(self, ctx, poke: int):
        """MOD: Shows who owns a specific pokemon by its global ID"""
        async with ctx.typing():
            async with ctx.bot.db[0].acquire() as pconn:
                user = await pconn.fetch(
                    "SELECT u_id FROM users WHERE $1 = ANY(pokes)", poke
                )
                market = await pconn.fetch(
                    "SELECT id FROM market WHERE poke = $1 AND buyer IS NULL", poke
                )

            msg = ""
            if user:
                uids = [str(x["u_id"]) for x in user]
                uids = "\n".join(uids)
                msg += f"Users who own poke `{poke}`:\n```{uids}" + "```\n\n"
            if market:
                mids = [str(x["id"]) for x in market]
                mids = "\n".join(mids)
                msg += f"Market listings for poke `{poke}`:\n```{mids}" + "```\n\n"
            if not msg:
                await ctx.send(f"Nobody owns poke `{poke}`.")
                return
            await ctx.send(msg[:1999])

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def marketinfo(self, ctx, market_id: int):
        """MOD: Hidden info about marketed pokes."""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT poke, owner, price, buyer FROM market WHERE id = $1",
                market_id,
            )
        if not data:
            await ctx.send("That market id does not exist!")
            return
        msg = f"[Market info for listing #{market_id}]\n"
        msg += f"[Poke]  - {data['poke']}\n"
        msg += f"[Owner] - {data['owner']}\n"
        msg += f"[Price] - {data['price']}\n"
        if data["buyer"] is None:
            msg += "[Buyer] - Currently listed\n"
        elif not data["buyer"]:
            msg += "[Buyer] - Removed by owner\n"
        else:
            msg += f"[Buyer] - {data['buyer']}\n"
        msg = f"```ini\n{msg}```"
        await ctx.send(msg)

    @check_mod()
    @moderator.command(aliases=["gi"])
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def globalinfo(self, ctx, poke: int):
        """MOD: Info a poke using its global id."""
        async with ctx.bot.db[0].acquire() as pconn:
            records = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", poke)
        if records is None:
            await ctx.send("That pokemon does not exist.")
            return
        # An infotype is used here to prevent it from trying to associate this info with a person.
        # The function does not try to make it a market info unless it is explicitly market,
        # however it avoids user-specific info data if *any* value is passed.
        await ctx.send(embed=await get_pokemon_info(ctx, records, info_type="global"))

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def mock(self, ctx, user_id: discord.Member, *, raw):
        """MOD:
        Mock another user invoking a command.
        The prefix must not be entered.
        """
        if not await self._mock_check(ctx.author.id, user_id.id):
            await ctx.send("Yeah, I'm not touching that.")
            return
        user = ctx.bot.get_user(user_id.id)
        if not user:
            try:
                user = await ctx.bot.fetch_user(user_id.id)
            except discord.HTTPException:
                await ctx.send("User not found.")
                return
        ctx.author = user

        class FakeInteraction:
            pass

        ctx._interaction = FakeInteraction()
        ctx._interaction.id = ctx.message.id
        path = []
        command = None
        args = ""
        for part in raw.split(" "):
            if command is not None:
                args += f"{part} "
            else:
                path.append(part)
                if tuple(path) in ctx.bot.slash_commands:
                    command = ctx.bot.slash_commands[tuple(path)]
        if command is None:
            await ctx.send("I can't find a command that matches that input.")
            return
        signature = [
            x.annotation
            for x in inspect.signature(command.callback).parameters.values()
        ][2:]

        view = StringView(args.strip())
        args = []
        for arg_type in signature:
            if view.eof:
                break
            arg = view.get_quoted_word()
            view.skip_ws()
            try:
                if arg_type in (str, inspect._empty):
                    pass
                elif arg_type in (discord.Member, discord.User):
                    arg = await MemberConverter().convert(ctx, arg)
                elif arg_type in (discord.TextChannel, discord.Channel):
                    arg = await TextChannelConverter().convert(ctx, arg)
                elif arg_type is int:
                    arg = int(arg)
                elif arg_type is bool:
                    arg = _convert_to_bool(arg)
                elif arg_type is float:
                    arg = float(arg)
                else:
                    await ctx.send(f"Unexpected parameter type, `{arg_type}`.")
                    return
            except Exception:
                await ctx.send("Could not convert an arg to the expected type.")
                return
            args.append(arg)
        try:
            com = command.callback(command.cog, ctx, *args)
        except TypeError:
            await ctx.send(
                "Too many args provided. Make sure you surround arguments that would have spaces in the slash UI with quotes."
            )

            return
        await com

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def mocksession(self, ctx, user_id: discord.Member):
        """MOD: Same as mock, but toggled on and off for total mocking of a user id"""
        if not await self._mock_check(ctx.author.id, user_id.id):
            await ctx.send("Yeah, I'm not touching that.")
            return
        user = ctx.bot.get_user(user_id.id)
        if not user:
            try:
                user = await ctx.bot.fetch_user(user_id.id)
            except discord.HTTPException:
                await ctx.send("User not found.")
                return
        if (
            ctx.channel.id in self.sessions
            and ctx.author.id in self.sessions[ctx.channel.id]
        ):
            await ctx.send("You are already running a mock session in this channel.")
            return
        elif ctx.channel.id in self.sessions:
            self.sessions[ctx.channel.id][ctx.author.id] = {}
        else:
            self.sessions[ctx.channel.id] = {ctx.author.id: {}}
        self.sessions[ctx.channel.id][ctx.author.id] = {
            "mocking": user,
            "last": time.time(),
        }

        await ctx.send(
            "Mock session started.\nUse `:your_command_here` to run a command\nUse `m:Your message here` to fake a message\nUse `;mocksessionend` to stop."
        )

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def mocksessionend(self, ctx):
        """MOD: Ends the mocking session"""
        if ctx.channel.id not in self.sessions:
            await ctx.send("You are not running a mock session in this channel.")
            return
        if ctx.author.id not in self.sessions[ctx.channel.id]:
            await ctx.send("You are not running a mock session in this channel.")
            return
        del self.sessions[ctx.channel.id][ctx.author.id]
        if not self.sessions[ctx.channel.id]:
            del self.sessions[ctx.channel.id]
        await ctx.send("Mock session ended.")

    async def _mock_check(self, mocker: int, mocked: int):
        """Check if "mocker" has permission to mock "mocked"."""
        async with self.bot.db[0].acquire() as pconn:
            mocked_rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", mocked
            )
            if mocked_rank is None:
                return True
            mocked_rank = Rank[mocked_rank.upper()]
            mocker_rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", mocker
            )
            # Should not happen, but just in case
            if mocker_rank is None:
                return False
            mocker_rank = Rank[mocker_rank.upper()]
        return mocker_rank > mocked_rank

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def marketmany(self, ctx, ids: str):
        """MOD: Buy multiple pokes from the market at once. Seperate ids by commas."""
        _ids = []
        for id in ids.replace(" ", ""):
            if id.isdigit():
                _ids.append(int(id))
        if not _ids:
            await ctx.send("No valid ids provided.")
            return
        ids = _ids
        c = ctx.bot.get_cog("Market")
        if c is None:
            await ctx.send("Market needs to be loaded to use this command!")
            return
        await ctx.send(
            f"Are you sure you want to buy {len(ids)} pokes?\n"
            f"Say `{ctx.prefix}confirm` to confirm or `{ctx.prefix}reject` to stop the market purchase."
        )

        def check(m):
            return (
                m.author == ctx.author
                and m.content.lower() in (f"{ctx.prefix}confirm", f"{ctx.prefix}reject")
                and m.channel == ctx.channel
            )

        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond.")
            return
        if msg.content.lower() == f"{ctx.prefix}reject":
            await ctx.send("Market Purchase Canceled!")
            return
        locked = [
            int(id_)
            for id_ in await ctx.bot.redis_manager.redis.execute(
                "LRANGE", "marketlock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        funcs = [self._marketbuy(ctx, i, locked) for i in ids]
        results = await asyncio.gather(*funcs)
        types = [x[0] for x in results]
        msg = ""
        if types.count(None):
            msg += f"You successfully bought {types.count(None)} pokes.\n"
        if types.count("Locked"):
            data = ", ".join([str(x[1]) for x in results if x[0] == "Locked"])
            msg += f"There is a marketlock on the following pokes: `{data}`\n"
        if types.count("InvalidID"):
            data = ", ".join([str(x[1]) for x in results if x[0] == "InvalidID"])
            msg += f"The following market ids were invalid: `{data}`\n"
        if types.count("Owner"):
            data = ", ".join([str(x[1]) for x in results if x[0] == "Owner"])
            msg += f"You already own the following listings: `{data}`\n"
        if types.count("Ended"):
            data = ", ".join([str(x[1]) for x in results if x[0] == "Ended"])
            msg += f"The poke was already bought for the following listings: `{data}`\n"
        if types.count("InvalidPoke"):
            data = ", ".join([str(x[1]) for x in results if x[0] == "InvalidPoke"])
            msg += f"The pokemon from the listing was deleted for the following listings: `{data}`\n"
        if types.count("LowBal"):
            data = ", ".join([str(x[1]) for x in results if x[0] == "LowBal"])
            msg += f"You could not afford the following listings: `{data}`\n"
        if types.count("Error"):
            data = ", ".join(
                [str(x[1]) for x in results if isinstance(x[0], Exception)]
            )
            msg += f"An unknown error occurred in the following listings: `{data}`\n"
            data = [x[0] for x in results if isinstance(x[0], Exception)]
            msg += f"These are the exceptions: `{data}`\n"
        if not msg:
            msg = "No pokes were attempted to be bought?"
        await ctx.send(msg)

    @staticmethod
    async def _marketbuy(ctx, listing_id, locked):
        """Helper function to buy a poke from the market."""
        if listing_id in locked:
            return "Locked", listing_id
        await ctx.bot.redis_manager.redis.execute(
            "LPUSH", "marketlock", str(listing_id)
        )

        try:
            async with ctx.bot.db[0].acquire() as pconn:
                details = await pconn.fetchrow(
                    "SELECT poke, owner, price, buyer FROM market WHERE id = $1",
                    listing_id,
                )

                if not details:
                    return "InvalidID", listing_id
                poke, owner, price, buyer = details
                if owner == ctx.author.id:
                    return "Owner", listing_id
                if buyer is not None:
                    return "Ended", listing_id
                details = await pconn.fetchrow(
                    "SELECT pokname, pokelevel FROM pokes WHERE id = $1", poke
                )

                if not details:
                    return "InvalidPoke", listing_id
                pokename, pokelevel = details
                pokename = pokename.capitalize()
                credits = await pconn.fetchval(
                    "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
                )

                if price > credits:
                    return "LowBal", listing_id
                await pconn.execute(
                    "UPDATE market SET buyer = $1 WHERE id = $2",
                    ctx.author.id,
                    listing_id,
                )

                await pconn.execute(
                    "UPDATE users SET pokes = array_append(pokes, $1), mewcoins = mewcoins - $2 WHERE u_id = $3",
                    poke,
                    price,
                    ctx.author.id,
                )

                gain = price
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    gain,
                    owner,
                )

                with contextlib.suppress(discord.HTTPException):
                    user = await ctx.bot.fetch_user(owner)
                    await user.send(
                        f"<@{owner}> Your {pokename} has been sold for {price} credits."
                    )

                await ctx.bot.log(
                    557926149284691969,
                    f"{ctx.author.name} - {ctx.author.id} has bought a {pokename} on the market. Seller - {owner}. Listing id - {listing_id}",
                )

        except Exception as e:
            return e, listing_id
        finally:
            await ctx.bot.redis_manager.redis.execute(
                "LREM", "marketlock", "1", str(listing_id)
            )

        return None, None

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def textsky(self, ctx, text: str):
        """HELPER: Send a text to sky"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://textbelt.com/text",
                json={
                    "phone": "5029746666",
                    "message": text,
                    "replyWebhookUrl": "https://hooks.zapier.com/hooks/catch/6433731/by0jj91/",
                    "key": "a7684210ed572847d8854fc05c9e8e9a49b062c4pVb5Xb1BxIjBI1W71pzu7kVgP",
                },
            ) as r:
                embed = discord.Embed(
                    title="Successfully sent!",
                    description="Message sent to Sky's phone.",
                )

                embed.set_footer(text="better be important...")
                if str(r.status)[0] == "2":
                    return await ctx.send(embed=embed)
                else:
                    return await ctx.send("Failed to send")

        #    Moved this over despite being commented in case code needed in future - Crui
        #
        #    @check_mod()
        #       @moderator.command()
        #    async def rchest(self, ctx, uid: int, chest, num: int):
        #        """CHEESE-ONLY: Add a chest"""
        #        if ctx.author.id not in (790722073248661525,478605505145864193):
        #            await ctx.send("...no.")
        #            return
        #        elif chest == "legend":
        #            actualchest = "legend chest"
        #        elif chest == "mythic":
        #            actualchest = "mythic chest"
        #        elif chest == "rare":
        #            actualchest = "rare chest"
        #        elif chest == "common":
        #            actualchest = "common chest"
        #        async with ctx.bot.db[0].acquire() as pconn:
        #            inventory = await pconn.fetchval(
        #                "SELECT inventory::json FROM users WHERE u_id = $1", uid
        #            )
        #            inventory[actualchest ] = inventory.get(actualchest , 0) + num
        #            await pconn.execute(
        #                "UPDATE users SET inventory = $1::json where u_id = $2",
        #                inventory,
        #                uid ,
        #            )
        #            await ctx.send(f"<@{uid}> gained `{num}` `{actualchest}'s`")

    @check_mod()
    @moderator.command(aliases=["ot"])
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def findot(self, ctx, poke: int):
        """HELPER: Find the OT userid of a pokemon"""
        async with ctx.bot.db[0].acquire() as pconn:
            caught_by = await pconn.fetchval(
                "SELECT caught_by FROM pokes WHERE id = $1", poke
            )
        if caught_by is None:
            await ctx.send("That pokemon does not exist.")
            return
        await ctx.send(f"`{caught_by}`")

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def getuser(self, ctx, user: discord.User):
        """MOD: Get user info by ID"""
        async with ctx.bot.db[0].acquire() as pconn:
            info = await pconn.fetchrow("SELECT * FROM users WHERE u_id = $1", user.id)
        if info is None:
            await ctx.send("User has not started.")
            return
        pokes = info["pokes"]
        count = len(pokes)
        uid = info["id"]
        redeems = info["redeems"]
        evpoints = info["evpoints"]
        tnick = info["tnick"]
        upvote = info["upvotepoints"]
        mewcoins = info["mewcoins"]
        inv = info["inventory"]
        daycare = info["daycare"]
        dlimit = info["daycarelimit"]
        energy = info["energy"]
        fishing_exp = info["fishing_exp"]
        fishing_level = info["fishing_level"]
        party = info["party"]
        luck = info["luck"]
        selected = info["selected"]
        visible = info["visible"]
        voted = info["voted"]
        tradelock = info["tradelock"]
        botbanned = ctx.bot.botbanned(user.id)
        mlimit = info["marketlimit"]
        staff = info["staff"]
        gym_leader = info["gym_leader"]
        patreon_tier = await ctx.bot.patreon_tier(user.id)
        intrade = user.id in [
            int(id_)
            for id_ in await ctx.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        desc = f"**__Information on {user.id}__**"
        desc += f"\n**Trainer Nickname**: `{tnick}`"
        desc += f"\n**DittoBOT ID**: `{uid}`"
        desc += f"\n**Patreon Tier**: `{patreon_tier}`"
        desc += f"\n**Staff Rank**: `{staff}`"
        desc += f"\n**Gym Leader?**: `{gym_leader}`"
        desc += f"\n**Selected Party**: `{party}`"
        desc += f"\n**Selected Pokemon**: `{selected}`"
        desc += f"\n**Pokemon Owned**: `{count}`"
        desc += f"\n**Mewcoins**: `{mewcoins}`"
        desc += f"\n**Redeems**: `{redeems}`"
        desc += f"\n**EvPoints**: `{evpoints}`"
        desc += f"\n**UpVOTE Points**: `{upvote}`"
        desc += f"\n\n**Daycare Slots**: `{daycare}`"
        desc += f"\n**Daycare Limit**: `{dlimit}`"
        desc += f"\n**Market Limit**: `{mlimit}`"
        desc += f"\n\n**Energy**: `{energy}`"
        desc += f"\n**Fishing Exp**: `{fishing_exp}`"
        desc += f"\n**Fishing Level**: `{fishing_level}`"
        desc += f"\n**Luck**: `{luck}`"
        desc += f"\n\n**Visible Balance?**: `{visible}`"
        desc += f"\n**Voted?**: `{voted}`"
        desc += f"\n**Tradebanned?**: `{tradelock}`"
        desc += f"\n**In a trade?**: `{intrade}`"
        desc += f"\n**Botbanned?**: `{botbanned}`"
        embed = discord.Embed(color=16758465, description=desc)
        embed.add_field(name="Inventory", value=f"{inv}", inline=False)
        embed.set_footer(text="Information live from Database")
        await ctx.send(embed=embed)

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def getpoke(self, ctx, pokem: int):
        """MOD: Get pokemon info by ID"""
        async with ctx.bot.db[0].acquire() as pconn:
            info = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", pokem)
            info2 = await pconn.fetchval(
                "SELECT age(time_stamp) FROM pokes WHERE id = $1", pokem
            )

            tradeinfo = await pconn.fetch(
                "SELECT * FROM trade_logs WHERE $1 = any(sender_pokes) OR $1 = any(receiver_pokes) order by t_id DESC limit 4",
                pokem,
            )

            tradeage = await pconn.fetch(
                "SELECT age(time) FROM trade_logs WHERE $1 = any(sender_pokes) OR $1 = any(receiver_pokes) order by t_id DESC limit 4",
                pokem,
            )

        if info is None:
            await ctx.send("Global ID not valid.")
            return
        info["id"]
        pokname = info["pokname"]
        hpiv = info["hpiv"]
        atkiv = info["atkiv"]
        defiv = info["defiv"]
        spatkiv = info["spatkiv"]
        spdefiv = info["spdefiv"]
        speediv = info["speediv"]
        hpev = info["hpev"]
        atkev = info["atkev"]
        defev = info["defev"]
        spatkev = info["spatkev"]
        spdefev = info["spdefev"]
        speedev = info["speedev"]
        pokelevel = info["pokelevel"]
        moves = info["moves"]
        hitem = info["hitem"]
        info["nature"]
        poknick = info["poknick"]
        happiness = info["happiness"]
        gender = info["gender"]
        shiny = info["shiny"]
        counter = info["counter"]
        info["name"]
        caught_at = info2.days
        caught_by = info["caught_by"]
        radiant = info["radiant"]

        def age_get(age):
            trade_age = math.ceil(abs(age.total_seconds()))
            trade_age_min, trade_age_sec = divmod(trade_age, 60)
            trade_age_hr, trade_age_min = divmod(trade_age_min, 60)
            return trade_age_hr, trade_age_min, trade_age_sec

        desc = f"**__Information on pokemon:`{pokem}`__**"
        desc += f"\n**Name**: `{pokname}` "
        desc += f"| **Nickname**: `{poknick}`"
        desc += f"| **Level**: `{pokelevel}`"
        desc += f"\n**IV's**: `{hpiv}|{atkiv}|{defiv}|{spatkiv}|{spdefiv}|{speediv}` "
        desc += f"| **EV's**: `{hpev}|{atkev}|{defev}|{spatkev}|{spdefev}|{speedev}`"
        desc += f"\n**Held Item**: `{hitem}` "
        desc += f"\n| **Happiness**: `{happiness}` "
        desc += f"| **Gender**: `{gender}`"
        desc += f"\n**Is Shiny**: `{shiny}` "
        desc += f"| **Is Radiant**: `{radiant}`"
        desc += f"\n**Age**: `{caught_at}` days "
        desc += f"\n**O.T.**: `{caught_by}`"
        if pokname.lower() == "egg":
            desc += f"Egg-Remaining Steps: `{counter}`"
        embed = discord.Embed(color=16758465, description=desc)
        embed.add_field(name="Moves", value=", ".join(moves), inline=False)
        if not tradeinfo:
            embed.add_field(
                name="Trade History", value="```No trade info found```", inline=False
            )

        else:
            embed.add_field(
                name=".",
                value="<:image_part_0011:871809643054243891><:image_part_0021:871809642928406618><:image_part_0021:871809642928406618><:image_part_0021:871809642928406618><:image_part_0021:871809642928406618><:image_part_003:871809643020693504>",
                inline=False,
            )

            i = 1
            for trade in tradeinfo:
                try:
                    hr, minu, sec = age_get(tradeage[i - 1]["age"])
                except Exception as exc:
                    hr, minu, sec = "Unknown", "Unknown", str(exc)
                embed.add_field(
                    name=f"Trade #{i}",
                    value=f"**Sender**: `{trade['sender']}`\n**Receiver**: `{trade['receiver']}`\n**Trade Command:** `{trade['command']}`\n**Traded:** `{hr} hours, {minu} minutes and {sec} seconds`",
                    inline=False,
                )

                i += 1
        embed.set_footer(text="Information live from Database")
        await ctx.send(embed=embed)

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def gib_support(self, ctx, redeems: int):
        """CHICHIRI: Add redeems to all support team"""
        await ctx.send("get out of here....no.")
        return
        # async with ctx.bot.db[0].acquire() as pconn:
        #     await pconn.execute(
        #         "UPDATE users SET redeems = redeems + $1 WHERE staff = 'Support'",
        #         redeems,
        #     )
        #     await ctx.send(
        #         f"Support team rewarded with {redeems} redeems. Thank you for all that you guys do!<3"
        #     )

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def credits_donated(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchval(
                "select mewcoins from users where u_id = 920827966928326686"
            )
            embed = discord.Embed(
                title="**Total Credits Donated**", description=f"```{data}```"
            )
            embed.set_footer(text="Raffle is on Christmas!")
            await ctx.send(embed=embed)

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def irefresh(self, ctx):
        """MOD: IMAGE REFRESH, pull new images to both servers"""
        COMMAND = "cd /ditto/ditto/shared/duel/images && git pull"
        addendum = ""
        proc = await asyncio.create_subprocess_shell(
            COMMAND, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        stdout = stdout.decode()
        if "no tracking information" in stderr.decode():
            COMMAND = "cd /ditto/ditto/ && git pull"
            proc = await asyncio.create_subprocess_shell(
                COMMAND, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()
            stdout = stdout.decode()
            addendum = "\n\n**Warning: no upstream branch is set.  I automatically pulled from origin/clustered but this may be wrong.  To remove this message and make it dynamic, please run `git branch --set-upstream-to=origin/<branch> <branch>`**"

        embed = discord.Embed(title="Git pull", description="", color=16758465)
        if "Fast-forward" not in stdout:
            if "Already up to date." in stdout:
                embed.description = "up to date.\n"
            else:
                embed.description = "Pull failed: Fast-forward strategy failed.  Look at logs for more details."

                ctx.bot.logger.warning(stdout)
            embed.description += addendum
            embed.description += f"```py\n{stdout}\n\nrefreshed!\n```"
            await ctx.send(embed=embed)
            return
        cogs = []
        main_files = []
        try:
            current = await self.get_commit(ctx)
        except ValueError:
            pass
        else:
            embed.description += f"`{current[2:]}`\n"
        cogs = re.findall("\sditto\/dittocogs\/(\w+)", stdout)
        if len(cogs) > 1:
            embed.description += f"The following cogs were updated and needs to be reloaded: `{'`, `'.join(cogs)}`.\n"

        elif len(cogs) == 1:
            embed.description += f"The following cog was updated and needs to be reloaded: `{cogs[0]}`.\n"

        else:
            embed.description += "No cogs were updated.\n"
        main_files = re.findall("\sditto\/(?!dittocogs)(\S*)", stdout)
        if len(main_files) > 1:
            embed.description += f"The following non-cog files were updated and require a restart: `{'`, `'.join(main_files)}`."

        elif main_files:
            embed.description += f"The following non-cog file was updated and requires a restart: `{main_files[0]}`."

        else:
            embed.description += "No non-cog files were updated."
        callbacks = re.findall("\scallbacks\/(\w+)", stdout)
        if len(callbacks) > 1:
            embed.description += f"The following callback files were updated and require a docker build: `{'`, `'.join(callbacks)}`."

        elif callbacks:
            embed.description += f"The following callback file was updated and requires a docker build: `{callbacks[0]}`."

        duelapi = re.findall("\sduelapi\/(\w+)", stdout)
        if len(duelapi) > 1:
            embed.description += f"The following duel API files were updated and require a docker build: `{'`, `'.join(duelapi)}`."

        elif duelapi:
            embed.description += f"The following duel API file was updated and requires a docker build: `{duelapi[0]}`."

        embed.description += addendum
        embed.description += f"```py\n{stdout}\nrefreshed!\n```"
        await ctx.send(embed=embed)

    @check_mod()
    @commands.hybrid_group(name="patreon")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def patreon(self, ctx):
        """VK: Promote users."""

    @check_mod()
    @patreon.command(name="add")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _patreonoverride(
        self, ctx, tier: str, member: discord.Member, *, reason: str
    ):
        """ADMIN: Promote a user to a Patreon tier."""
        if ctx.author.id not in (
            790722073248661525,
            499740738138013696,
            318844987464876034,
            154049270348120064,
            517355062318727180,
            573321526439575582,
            749299865334448249,
            145519400223506432,
        ):
            await ctx.send("Only Admins and vKoIIextionz may use this command")
            return
        tier = tier.title()
        if tier not in (
            "Silver Patreon",
            "Gold Patreon",
            "Crystal Patreon",
            "Elite Patreon",
        ):
            await ctx.send(f"{RED} Invalid tier.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET patreon_override = $2 WHERE u_id = $1",
                member.id,
                tier,
            )

        msg = f"{GREEN} Patreon Override set to **{tier}**.\n"
        if ctx.guild.id != 999953429751414784:
            msg += f"{RED} Could not add or remove OS roles, as this command was not run in OS.\n"

            await ctx.send(msg)
            return
        tiers = {
            "Silver Patreon": ctx.guild.get_role(556832145629380608),
            "Gold Patreon": ctx.guild.get_role(556832150637379604),
            "Crystal Patreon": ctx.guild.get_role(713121816180162602),
            "Elite Patreon": ctx.guild.get_role(902750193840177182),
        }

        removeset = set(tiers.values())
        removeset.remove(tiers[tier])
        currentset = set(member.roles)
        removeset &= currentset
        if not removeset:
            msg += f"{YELLOW} User had no other tier roles to remove.\n"
        else:
            removelist = list(removeset)
            await member.remove_roles(
                *removelist, reason=f"Patreon Override - {ctx.author}"
            )

            removelist = [str(x) for x in removelist]
            msg += (
                f"{GREEN} Removed existing tier role(s) **{', '.join(removelist)}.**\n"
            )
        if tiers[tier] in member.roles:
            msg += f"{YELLOW} User already had the **{tiers[tier]}** role.\n"
        else:
            await member.add_roles(
                tiers[tier], reason=f"Patreon Override - {ctx.author}"
            )
            msg += f"{GREEN} Added new tier role **{tiers[tier]}**.\n"
        supporter_role = ctx.guild.get_role(519472731285225475)
        if supporter_role in member.roles:
            msg += f"{YELLOW} User already had the **{supporter_role}** role.\n"
        else:
            await member.add_roles(
                supporter_role, reason=f"Patreon Override - {ctx.author}"
            )

            msg += f"{GREEN} Added the **{supporter_role}** role.\n"
        msg += "Any changes to patreon over-rides take 15min to take effect."
        await ctx.bot.log(
            988999272794058762,
            f"{GREEN}| {ctx.author} added {tier} over-ride for {member}\n**Note:** ```{reason}```\n",
        )

        await ctx.send(msg)

    @check_mod()
    @patreon.command(name="remove")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _patreonremove(self, ctx, member: discord.Member, *, reason: str):
        """ADMIN: Remove a users patreon over-ride"""
        if ctx.author.id not in (
            790722073248661525,
            499740738138013696,
            318844987464876034,
            154049270348120064,
            517355062318727180,
            573321526439575582,
            749299865334448249,
            145519400223506432,
        ):
            await ctx.send("Only Admins and vKoIIextionz may use this command")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET patreon_override = null WHERE u_id = $1", member.id
            )

        msg = f"{GREEN} Removed patreon over-ride for <@{member}>.\n"
        if ctx.guild.id != 999953429751414784:
            msg += (
                f"{RED} Could not remove OS roles, as this command was not run in OS.\n"
            )
            await ctx.send(msg)
            return

        tiers = {
            "Silver Patreon": ctx.guild.get_role(556832145629380608),
            "Gold Patreon": ctx.guild.get_role(556832150637379604),
            "Crystal Patreon": ctx.guild.get_role(713121816180162602),
            "Elite Patreon": ctx.guild.get_role(902750193840177182),
        }
        removeset = set(tiers.values())
        currentset = set(member.roles)
        removeset &= currentset
        if not removeset:
            msg += f"{YELLOW} User had no tier roles to remove.\n"
        else:
            removelist = list(removeset)
            await member.remove_roles(
                *removelist, reason=f"Remove Patreon Over-ride - {ctx.author}"
            )
            removelist = [str(x) for x in removelist]
            msg += (
                f"{GREEN} Removed existing tier role(s) **{', '.join(removelist)}.**\n"
            )
            msg += "Any changes to patreon over-rides take 15min to take effect."
        await ctx.bot.log(
            988999272794058762,
            f"{RED}| {ctx.author} removed patreon over-ride for {member}\n**Note:** {reason}",
        )
        await ctx.send(msg)

    @check_mod()
    @moderator.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def tradable(self, ctx, pokeid: int, answer: bool):
        """MOD: Set pokemon trade-able or not"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET tradable = $1 WHERE id = $2",
                answer,
                pokeid,
            )
        await ctx.send(f"Successfully set trade-able to {answer}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mod(bot))
