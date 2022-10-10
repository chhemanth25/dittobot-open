import asyncio
import datetime
import inspect
import io
import math
import re
import textwrap
import time
import traceback
from contextlib import redirect_stdout, suppress

import discord
from discord.ext import commands
from dittocore import commondb
from utils.checks import (
    check_admin,
    check_gymauth,
    check_helper,
    check_investigator,
    check_mod,
    check_owner,
)
from utils.misc import ConfirmView, MenuView, pagify
from pokemon_utils.utils import get_pokemon_info

from dittocogs.pokemon_list import LegendList

GREEN = "\N{LARGE GREEN CIRCLE}"
YELLOW = "\N{LARGE YELLOW CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"

STAFFSERVER = discord.Object(id=999953429751414784)


class EvalContext:
    def __init__(self, interaction):
        self.interaction = interaction
        self.message = interaction.message
        self.bot = interaction.client
        self.author = interaction.user

    async def send(self, *args, **kwargs):
        await self.interaction.followup.send(*args, **kwargs)


class EvalModal(discord.ui.Modal, title="Evaluate Code"):
    body = discord.ui.TextInput(label="Code", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        start = time.time()

        startTime = datetime.datetime.now()

        ectx = EvalContext(interaction)

        env = {
            "ctx": ectx,
            "interaction": interaction,
            "bot": interaction.client,
            "channel": interaction.channel,
            "author": interaction.user,
            "guild": interaction.guild,
            "message": interaction.message,
            "source": inspect.getsource,
        }

        body = str(self.body)

        env.update(globals())

        stdout = io.StringIO()

        await interaction.followup.send(f"**Code:**\n```py\n{body}```")

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        async def paginate_send(ctx, text: str):
            """Paginates arbatrary length text & sends."""
            last = 0
            pages = []
            for curr in range(0, len(text), 1980):
                pages.append(text[last:curr])
                last = curr
            pages.append(text[last:])
            pages = list(filter(lambda a: a != "", pages))
            for page in pages:
                await ctx.send(f"```py\n{page}```")

        try:
            exec(to_compile, env)
            datetime.datetime.now() - startTime
            end = time.time()
            end - start
        except Exception as e:
            await paginate_send(ectx, f"{e.__class__.__name__}: {e}")
            return await interaction.message.add_reaction("\u2049")  # x

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await paginate_send(ectx, f"{value}{traceback.format_exc()}")
            return await interaction.message.add_reaction("\u2049")  # x
        value = stdout.getvalue()
        if ret is None:
            if value:
                await paginate_send(ectx, str(value))
        else:
            await paginate_send(ectx, f"{value}{ret}")
        await interaction.message.add_reaction("\u2705")  # tick


class EvalView(discord.ui.View):
    def __init__(self, author: int, *args, **kwargs):
        self.modal = EvalModal()
        self.author = author
        super().__init__(timeout=120)

    @discord.ui.button(label="Click Here")
    async def click_here(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.author != interaction.user.id:
            return await interaction.response.send_message(
                "You can't do this!", ephemeral=True
            )
        await interaction.response.send_modal(self.modal)
        self.stop()


class KittyCat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        self.safe_edb = ""
        if self.bot.cluster["id"] == 1:
            self.task = asyncio.create_task(self.store_lb())
        else:
            self.task = None

    async def cog_before_invoke(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "INSERT INTO skylog (u_id, command, args, jump, time) VALUES ($1, $2, $3, $4, $5)",
                ctx.author.id,
                ctx.command.qualified_name,
                ctx.message.content,
                ctx.message.jump_url,
                ctx.message.created_at.replace(tzinfo=None),
            )

    def cog_unload(self):
        if self.task is not None:
            self.task.cancel()

    async def store_lb(self):
        """Stores leaderboard entries to the 'leaderboard' mongo collection."""
        while True:
            # Sleep until the same time each day
            await asyncio.sleep(86400 - (time.time() % 86400))
            ts = time.time()
            data = {}
            async with self.bot.db[0].acquire() as pconn:
                details = await pconn.fetch(
                    """SELECT u_id, cardinality(pokes) as pokenum FROM users ORDER BY pokenum DESC LIMIT 50"""
                )

            pokes = [record["pokenum"] for record in details]
            ids = [record["u_id"] for record in details]
            for idx, id in enumerate(ids):
                pokenum = pokes[idx]
                try:
                    (await self.bot.fetch_user(id)).name
                except Exception:
                    pass
                num = idx + 1
                data[id] = {"position": num, "count": pokenum}
                await asyncio.sleep(1)
            data = {"leaderboard": data, "timestamp": ts}
            await self.bot.db[1].leaderboard.insert_one(data)

    async def load_bans_cross_cluster(self):
        launcher_res = await self.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return
        processes = len(launcher_res[0])
        body = "await bot.load_bans()"
        await self.bot.handler(
            "_eval",
            processes,
            args={"body": body, "cluster_id": "-1"},
            scope="bot",
            _timeout=10,
        )

    @check_admin()
    @commands.hybrid_group(name="admin")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def admin_cmds(self, ctx):
        ...

    @check_admin()
    @admin_cmds.command(name="combine")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def combine(self, ctx, u_id1: int, u_id2: int):
        """ADMIN: Add two users pokes together, leaving user1 with all, and user2 with none."""
        await ctx.send(
            f"Are you sure you want to move all pokemon from {u_id2} to {u_id1}?"
        )

        def check(m):
            return m.author.id == ctx.author.id and m.content.lower() in (
                "yes",
                "no",
                "y",
                "n",
            )

        try:
            m = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Request timed out.")
            return
        if m.content.lower().startswith("n"):
            await ctx.send("Cancelled.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            user1 = await pconn.fetchval(
                "SELECT pokes FROM users WHERE u_id = $1", u_id1
            )
            user2 = await pconn.fetchval(
                "SELECT pokes FROM users WHERE u_id = $1", u_id2
            )
            user1.extend(user2)
            user2 = []
            await pconn.execute(
                "UPDATE users SET pokes = $2 WHERE u_id = $1", u_id1, user1
            )
            await pconn.execute(
                "UPDATE users SET pokes = $2 WHERE u_id = $1", u_id2, user2
            )
        await ctx.send(
            f"```elm\nSuccessfully added pokemon from {u_id2} to {u_id1}.```"
        )

    @commands.hybrid_group()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def bb(self, ctx):
        ...

    @check_investigator()
    @bb.command(name="add")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def addbb(self, ctx, id: discord.User):
        """INVESTIGATOR: Ban specified user from using the bot in any server."""
        id = id.id
        banned = set(ctx.bot.banned_users)
        if id in banned:
            await ctx.send("That user is already botbanned!")
            return
        banned.add(id.id)
        await ctx.bot.mongo_update("blacklist", {}, {"users": list(banned)})
        await ctx.send(
            f"```Elm\n-Successfully Botbanned {await ctx.bot.fetch_user(id.id)}```"
        )
        await self.load_bans_cross_cluster()

    @check_investigator()
    @bb.command(name="remove")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def removebb(self, ctx, id: discord.User):
        """INVESTIGATOR: Unban specified user from the bot, allowing use of commands again"""
        id = id.id
        banned = set(ctx.bot.banned_users)
        if id not in banned:
            await ctx.send("That user is not botbanned!")
            return
        banned.remove(id.id)
        await ctx.bot.mongo_update("blacklist", {}, {"users": list(banned)})
        await ctx.send(
            f"```Elm\n- Successfully Unbotbanned {await ctx.bot.fetch_user(id.id)}```"
        )
        await self.load_bans_cross_cluster()

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
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

    @check_investigator()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def mostcommonchests(self, ctx):
        """Shows the users who have the most common chests in their inv."""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "SELECT u_id, (inventory::json->>'common chest')::int as cc FROM users "
                "WHERE (inventory::json->>'common chest')::int IS NOT NULL ORDER BY cc DESC LIMIT 10"
            )
        result = "".join(f"`{row['u_id']}` - `{row['cc']}`\n" for row in data)
        await ctx.send(embed=discord.Embed(description=result, color=0xDD00DD))

    @check_investigator()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def donations(self, ctx, userid: discord.Member):
        """INVESTIGATOR: Shows a users total recorded donations from ;donate command only"""
        async with ctx.bot.db[0].acquire() as pconn:
            money = await pconn.fetchval(
                "select sum(amount) from donations where u_id = $1", userid.id
            )
        await ctx.send(money or "0")

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
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

    @check_helper()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def marketinfo(self, ctx, market_id: int):
        """HELPER: Hidden info about marketed pokes."""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT poke, owner, price, buyer FROM market WHERE id = $1", market_id
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

    @check_admin()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def dupecheck(self, ctx, user_id: discord.Member):
        """ADMIN: Check a user to see if any of their pokemon have more than one owner."""
        async with ctx.typing():
            async with ctx.bot.db[0].acquire() as pconn:
                result = await pconn.fetch(
                    "SELECT pokes.id FROM pokes WHERE pokes.id IN (SELECT unnest(users.pokes) FROM users WHERE users.u_id = $1) AND 1 < (SELECT count(users.u_id) FROM users WHERE pokes.id = any(users.pokes))",
                    user_id.id,
                    timeout=600,
                )
        result = "\n".join([str(x["id"]) for x in result])
        if not result:
            await ctx.send(f"No dupes for {user_id.id}!")
            return
        await ctx.send(f"Dupe list for {user_id.id}.\n```py\n{result[:1900]}```")

    @check_investigator()
    @commands.hybrid_command(aliases=("yeet", "bestow", "grant"))
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def addpoke(self, ctx, userid: discord.Member, poke: int):
        """INVESTIGATOR: Add a pokemon by its ID to a user by their userID"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = $2",
                poke,
                userid.id,
            )
        await ctx.send("Successfully added the pokemon to the user specified.")

    @check_investigator()
    @commands.hybrid_command(aliases=("yoink", "rob", "take", "steal"))
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def removepoke(self, ctx, userid: discord.Member, poke: int):
        """INVESTIGATOR: Remove a pokemon by its ID to a user by their userID"""
        try:
            await ctx.bot.commondb.remove_poke(userid.id, poke)
        except commondb.UserNotStartedError:
            await ctx.send("That user has not started!")
            return
        await ctx.send("Successfully removed the pokemon from users pokemon array")

    @check_helper()
    @commands.hybrid_command(aliases=["gi"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def globalinfo(self, ctx, poke: int):
        """HELPER: Info a poke using its global id."""
        async with ctx.bot.db[0].acquire() as pconn:
            records = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", poke)
        if records is None:
            await ctx.send("That pokemon does not exist.")
            return

        # An infotype is used here to prevent it from trying to associate this info with a person.
        # The function does not try to make it a market info unless it is explicitly market,
        # however it avoids user-specific info data if *any* value is passed.
        await ctx.send(embed=await get_pokemon_info(ctx, records, info_type="global"))

    @check_gymauth()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def addev(self, ctx, userid: discord.Member, evs: int):
        """GYM: Add evs to a user by their ID"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET evpoints = evpoints + $1 WHERE u_id = $2",
                evs,
                userid.id,
            )
        await ctx.send("Successfully added Effort Value points to user")

    @check_admin()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def marketyoink(self, ctx, market_id: int):
        """ADMIN: Remove a poke from the market, assigning it to user id 1227."""
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT poke, buyer FROM market WHERE id = $1", market_id
            )
            if not details:
                await ctx.send("That listing does not exist.")
                return
            poke, buyer = details
            if buyer is not None:
                await ctx.send("That listing has already ended.")
                return
            await pconn.execute("UPDATE market SET buyer = 0 WHERE id = $1", market_id)
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = 1227",
                poke,
            )
        await ctx.send(f"User `1227` now owns poke `{poke}`.")

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
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
            return ("Locked", listing_id)
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
                    return ("InvalidID", listing_id)
                poke, owner, price, buyer = details
                if owner == ctx.author.id:
                    return ("Owner", listing_id)
                if buyer is not None:
                    return ("Ended", listing_id)
                details = await pconn.fetchrow(
                    "SELECT pokname, pokelevel FROM pokes WHERE id = $1", poke
                )
                if not details:
                    return ("InvalidPoke", listing_id)
                pokename, pokelevel = details
                pokename = pokename.capitalize()
                credits = await pconn.fetchval(
                    "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
                )
                if price > credits:
                    return ("LowBal", listing_id)
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
                with suppress(discord.HTTPException):
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
        return (None, None)

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def refreshpatreons(self, ctx):
        """MOD: Refresh the patreon tier cache"""
        await ctx.bot.redis_manager.redis.execute(
            "SET", "patreonreset", time.time() + (60 * 15)
        )
        data = await ctx.bot._fetch_patreons()
        # Expand the dict, since redis doesn't like dicts
        result = []
        for k, v in data.items():
            result += [k, v]
        await ctx.bot.redis_manager.redis.execute("DEL", "patreontier")
        await ctx.bot.redis_manager.redis.execute("HMSET", "patreontier", *result)
        await ctx.send("Refreshed.")

    @commands.hybrid_group(name="dittostats")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def ditto_stats(self, ctx):
        """HELPER: Base command"""
        ...

    @check_helper()
    @ditto_stats.command(name="db")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def db(self, ctx):
        """HELPER: Show database statistics"""
        desc = "**__Subcommands:__**\n"
        for command in ctx.command.commands:
            desc += f"{ctx.prefix}{command.qualified_name}\n"
        embed = discord.Embed(description=desc, color=ctx.bot.get_random_color())
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def radiantot(self, ctx):
        """HELPER: Show radiant OT statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select caught_by, count(caught_by) from pokes where radiant = true group by caught_by order by count desc limit 25"
            )
        result = "\n".join([f'{x["count"]} | {x["caught_by"]}' for x in data])
        embed = discord.Embed(
            title="***Radiant pokemon by Original Trainer***",
            description=f"```{result}```",
        )
        embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def radiantcount(self, ctx):
        """HELPER: Show radiant count statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select count(*), pokname from pokes where radiant = true group by pokname order by count desc"
            )
        desc = "\n".join([f'{x["count"]} | {x["pokname"]}' for x in data])
        pages = pagify(desc, base_embed=discord.Embed(title="***Radiant Counts***"))
        await MenuView(ctx, pages).start()

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def shinyot(self, ctx):
        """HELPER: Show shiny OT statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select caught_by, count(caught_by) from pokes where shiny = true group by caught_by order by count desc limit 25"
            )
        result = "\n".join([f'{x["count"]} | {x["caught_by"]}' for x in data])
        embed = discord.Embed(
            title="Shiny pokemon by Original Trainer", description=f"```{result}```"
        )
        embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def shinyrare(self, ctx):
        """HELPER: Show shiny rare count statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select count(*), pokname from pokes where shiny = true group by pokname order by count asc limit 25"
            )
        result = "\n".join([f'{x["count"]} | {x["pokname"]}' for x in data])
        embed = discord.Embed(
            title="Top 25 Rarest Shiny pokemon", description=f"```{result}```"
        )
        embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def shinycommon(self, ctx):
        """HELPER: Show shiny count statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select count(*), pokname from pokes where shiny = true group by pokname order by count desc limit 25"
            )
        result = "\n".join([f'{x["count"]} | {x["pokname"]}' for x in data])
        embed = discord.Embed(
            title="Top 25 Most Common Shiny pokemon", description=f"```{result}```"
        )
        embed.set_footer(text="dittotototobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def all_ot(self, ctx):
        """HELPER: Show all OT statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select caught_by, count(caught_by) from pokes group by caught_by order by count desc limit 25"
            )
        result = "\n".join([f'{x["count"]} | {x["caught_by"]}' for x in data])
        embed = discord.Embed(
            title="Pokemon by Original Trainer", description=f"```{result}```"
        )
        embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def legend_ot(self, ctx):
        """HELPER: Show legend OT statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "SELECT caught_by, count(caught_by) FROM pokes WHERE pokname = ANY($1) group by caught_by order by count desc LIMIT 25",
                LegendList,
            )
        result = "\n".join([f'{x["count"]} | {x["caught_by"]}' for x in data])
        embed = discord.Embed(
            title="**Legendary Pokemon by Original Trainer**",
            description=f"```{result}```",
        )
        embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def penta_ot(self, ctx):
        """HELPER: Show penta OT statistics"""
        async with ctx.typing():
            async with ctx.bot.db[0].acquire() as pconn:
                data = await pconn.fetch(
                    "SELECT caught_by, count(caught_by) FROM (SELECT caught_by, (div(atkiv, 31) + div(defiv, 31) + div(hpiv, 31) + div(speediv, 31) + div(spdefiv, 31) + div(spatkiv, 31))::int as perfects FROM pokes) data WHERE perfects = 5 group by caught_by order by count desc limit 25",
                    timeout=30.0,
                )
            result = "\n".join([f'{x["count"]} | {x["caught_by"]}' for x in data])
            embed = discord.Embed(
                title="Top 25 Pentas by Original Trainer", description=f"```{result}```"
            )
            embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_helper()
    @ditto_stats.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def lb_chests(self, ctx):
        """HELPER: Show leading chest statistics"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "select count(args), u_id from skylog where args = ';open legend' group by u_id order by count desc limit 30"
            )
        result = "\n".join([f'{x["count"]} | {x["u_id"]}' for x in data])
        embed = discord.Embed(
            title="***Chests Opened Leaderboard***", description=f"```{result}```"
        )
        embed.set_footer(text="dittobot Statistics")
        await ctx.send(embed=embed)

    @check_admin()
    @commands.hybrid_group(name="gib")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def gib_cmds(self, ctx):
        """Top layer of group"""

    @check_admin()
    @gib_cmds.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def deems(self, ctx, user: discord.User, redeems: int):
        """ADMIN: Give a user Redeems"""
        # await ctx.send("get out of here....no.")
        # return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                redeems,
                user.id,
            )
            await ctx.send(
                f"{user.name} was given {redeems} redeems by {ctx.author.id}."
            )

    @check_admin()
    @gib_cmds.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def gems(self, ctx, user: discord.User, gems: int):
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", user.id
            )
            inventory["radiant gem"] = inventory.get("radiant gem", 0) + gems
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                user.id,
            )
            embed = discord.Embed(
                title="Success!", description=f"{user} gained {gems} radiant gem(s)"
            )
            embed.set_footer(text="Definitely hax... lots of hax")
            await ctx.send(embed=embed)

    @check_admin()
    @gib_cmds.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def staff(self, ctx, redeems: int):
        """Add redeems to all staff"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1 WHERE staff in ('Admin', 'Mod', 'Helper', 'Investigator', 'Gymauth')",
                redeems,
            )
            await ctx.send(
                f"All staff members awarded with {redeems} redeems. Thank you for all that you guys do!<3"
            )

    @check_admin()
    @gib_cmds.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def chest(self, ctx, uid: discord.User, chest, num: int):
        """Add a chest"""
        if chest == "legend":
            actualchest = "legend chest"
        elif chest == "mythic":
            actualchest = "mythic chest"
        elif chest == "rare":
            actualchest = "rare chest"
        elif chest == "common":
            actualchest = "common chest"
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", uid.id
            )
            inventory[actualchest] = inventory.get(actualchest, 0) + num
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                uid.id,
            )
            await ctx.send(f"<@{uid.id}> gained `{num}` `{actualchest}'s`")

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def wss(self, ctx):
        response = await ctx.bot.http.request(discord.http.Route("GET", "/gateway/bot"))
        await ctx.send(f"```py\n{response}```")

    @check_admin()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def clusters(self, ctx):
        launcher_res = await ctx.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return await ctx.send(
                "Launcher did not respond.  Please start with the launcher to use this command."
            )

        processes = len(launcher_res[0])
        process_res = await ctx.bot.handler("send_cluster_info", processes, scope="bot")

        process_res.sort(key=lambda x: x["id"])

        pages = []
        current = None
        count = 1
        for cluster in process_res:
            if cluster["id"] % 3 == 1 or not current:
                if current:
                    pages.append(current)
                current = discord.Embed(
                    title=f"Clusters {cluster['id']} - {cluster['id'] + 2}",
                    color=0xFFB6C1,
                )
                current.set_footer(
                    text=f"{ctx.prefix}[ n|next, b|back, s|start, e|end ]"
                )
                count += 1
            msg = (
                "```prolog\n"
                f"Latency:    {cluster['latency']}ms\n"
                f"Shards:     {cluster['shards'][0]}-{cluster['shards'][-1]}\n"
                f"Guilds:     {cluster['guilds']}\n"
                f"Channels:   {cluster['channels']}\n"
                f"Users:      {cluster['users']}\n"
                "```"
            )
            current.add_field(
                name=f"Cluster #{cluster['id']} ({cluster['name']})", value=msg
            )

        current.title = current.title[: -len(str(cluster["id"]))] + str(cluster["id"])
        pages.append(current)

        embed = await ctx.send(embed=pages[0])
        current_page = 1

        def get_value(message):
            return {
                f"{ctx.prefix}n": min(len(pages), current_page + 1),
                f"{ctx.prefix}next": min(len(pages), current_page + 1),
                f"{ctx.prefix}b": max(1, current_page - 1),
                f"{ctx.prefix}back": max(1, current_page - 1),
                f"{ctx.prefix}e": len(pages),
                f"{ctx.prefix}end": len(pages),
                f"{ctx.prefix}s": 1,
                f"{ctx.prefix}start": 1,
            }.get(message)

        commands = (
            f"{ctx.prefix}n",
            f"{ctx.prefix}next",
            f"{ctx.prefix}back",
            f"{ctx.prefix}b",
            f"{ctx.prefix}e",
            f"{ctx.prefix}end",
            f"{ctx.prefix}s",
            f"{ctx.prefix}start",
        )

        while True:
            try:
                message = await ctx.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author
                    and m.content.lower() in commands,
                    timeout=60,
                )
            except asyncio.TimeoutError:
                break

            try:
                await message.delete()
            except:
                pass

            current_page = get_value(message.content.lower())
            await embed.edit(embed=pages[current_page - 1])

    @check_mod()
    @commands.group(aliases=["pn", "pnick"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def pokenick(self, ctx):
        """MOD: Nickname Utilities"""

    @check_admin()
    @pokenick.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def change(self, ctx, *, search_term: str):
        """ADMIN: Change all pokemon nicknames that meet your search"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchval(
                "SELECT count(*) FROM pokes WHERE poknick like $1", search_term
            )
        counttext = f'{data["count"]} pokemon nicknames will be changed, are you sure you wish to do this?'
        await ctx.send(f"{counttext}")

        def check(m):
            return m.author.id == ctx.author.id and m.content.lower() in (
                "yes",
                "no",
                "y",
                "n",
            )

        try:
            m = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Request timed out.")
            return
        if m.content.lower().startswith("n"):
            await ctx.send("Cancelled.")
            return
        warning = "Nickname Violation"
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET poknick = $2 WHERE poknick like $1",
                search_term,
                warning,
            )
        await ctx.send(
            f"Changed {counttext} pokemon nicknames to `Nickname Violation`."
        )

    @commands.hybrid_group(name="gym")
    async def gym_cmds(self, ctx):
        """Top layer of group"""

    @check_investigator()
    @commands.hybrid_group(aliases=["r", "repo"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def repossess(self, ctx):
        """INVESTIGATOR: COMMANDS FOR REPOSSESSING THINGS FROM OFFENDERS"""

    @check_investigator()
    @repossess.command(aliases=["c", "bread", "cheese"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def credits(self, ctx, user: discord.Member, val: int):
        """INVESTIGATOR: REPOSSESS CREDITS"""
        if ctx.author.id == user.id:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou cant take your own credits!"
            )
            return
        if val <= 0:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou need to transfer at least 1 credit!"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            giver_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = 123"
            )

        if getter_creds is None:
            await ctx.send(f"<:err:997377264511623269>!:\nIssue with fake UserID (123)")
            return
        if giver_creds is None:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) has not started."
            )
            return
        if val > giver_creds:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) does not have that many credits!"
            )
            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to move **{val}** credits from **{user.name}**({user.id}) to **dittobot's Central Bank?**",
        ).wait():
            await ctx.send("<:err:997377264511623269>!:\nTransfer **Cancelled.**")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )
            if val > curcreds:
                await ctx.send(
                    "<:err:997377264511623269>!:\nUser does not have that many credits anymore..."
                )
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = 123",
                val,
            )
            await ctx.send(
                f"{val} Credits taken from {user.name}({user.id}), added to fake u_id `123`."
            )
            await ctx.bot.get_partial_messageable(997378673214754827).send(
                f"<:err:997377264511623269>-Staff Member: {ctx.author.name}-``{ctx.author.id}``\nCredits Taken From: {user.name}-`{user.id}`\nAmount: ```{val} credits```\n"
            )
            # await pconn.execute(
            #    "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
            #    ctx.author.id, user.id, val, "repo", datetime.now()
            # )

    @check_investigator()
    @repossess.command(aliases=["d", "deems", "r"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def redeems(self, ctx, user: discord.Member, val: int):
        """INVESTIGATOR: REPOSSESS REDEEMS"""
        if ctx.author.id == user.id:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou cant take your own Redeems!"
            )
            return
        if val <= 0:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou need to transfer at least 1 Redeem!"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            giver_creds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", user.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = 123"
            )

        if getter_creds is None:
            await ctx.send(f"<:err:997377264511623269>!:\nIssue with fake UserID (123)")
            return
        if giver_creds is None:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) has not started."
            )
            return
        if val > giver_creds:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) does not have that many redeems!!"
            )
            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to move **{val}** redeems from\n**{user.name}**({user.id})\nto **dittobot's Central Bank?**",
        ).wait():
            await ctx.send("<:err:997377264511623269>!:\nTransfer **Cancelled.**")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", user.id
            )
            if val > curcreds:
                await ctx.send(
                    "<:err:997377264511623269>!:\nUser does not have that many redeems anymore..."
                )
                return
            await pconn.execute(
                "UPDATE users SET redeems = redeems - $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1 WHERE u_id = 123",
                val,
            )
            await ctx.send(
                f"{val} redeems taken from {user.name}({user.id}), added to fake u_id `123`."
            )
            await ctx.bot.get_partial_messageable(997378673214754827).send(
                f"<:err:997377264511623269>-Staff Member: {ctx.author.name}-``{ctx.author.id}``\nredeems Taken From: {user.name}-`{user.id}`\nAmount: ```{val} redeems```\n"
            )
            # await pconn.execute(
            #    "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
            #    ctx.author.id, user.id, val, "repo", datetime.now()
            # )

    @check_investigator()
    @repossess.command(aliases=["a", "everything"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def all(self, ctx, user: discord.Member):
        """INVESTIGATOR: REPOSSESS EVERYTHING"""
        if ctx.author.id == user.id:
            await ctx.send("<:err:997377264511623269>!: You cant take your own stuff!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            giver_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = 123"
            )

        if getter_creds is None:
            await ctx.send("<:err:997377264511623269>!: Issue with fake UserID (123)")
            return
        if giver_creds is None:
            await ctx.send(
                f"<:err:997377264511623269>!: {user.name}({user.id}) has not started."
            )
            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to move all **REDEEMS AND CREDITS** from\n**{user.name}**({user.id})\nto **dittobot's Central Bank?**",
        ).wait():
            await ctx.send("<:err:997377264511623269>!:\nTransfer **Cancelled.**")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchrow(
                "SELECT mewcoins, redeems FROM users WHERE u_id = $1", user.id
            )
            credits = curcreds["mewcoins"]
            redeems = curcreds["redeems"]
            await pconn.execute(
                "UPDATE users SET redeems = redeems = 0, mewcoins = 0 WHERE u_id = $1",
                user.id,
            )
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1, mewcoins = mewcoins + $2 WHERE u_id = 123",
                redeems,
                credits,
            )
            await ctx.send(
                f"{redeems} redeems\n{credits} credits\ntaken from {user.name}({user.id}), added to fake u_id `123`."
            )
            await ctx.bot.get_partial_messageable(997378673214754827).send(
                f"<:err:997377264511623269>-Staff Member: {ctx.author.name}-``{ctx.author.id}``\nEVERYTHING Taken From: {user.name}-`{user.id}`\nAmount: ```{credits} credits\n{redeems} redeems```\n"
            )
            # await pconn.execute(
            #    "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
            #    ctx.author.id, user.id, val, "repo", datetime.now()
            # )

    @check_investigator()
    @repossess.command(aliases=["b", "balance"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def bank(self, ctx):
        """INVESTIGATOR: BANK BALANCES"""
        async with ctx.bot.db[0].acquire() as pconn:
            redeems = await pconn.fetchval("SELECT redeems FROM users WHERE u_id = 123")
            mewcoins = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = 123"
            )
        embed = discord.Embed(title="Balances", color=0xFF0000)
        embed.set_author(
            name="dittobot Central Bank",
            url="https://discord.com/channels/999953429751414784/793744327746519081/",
        )
        embed.set_thumbnail(
            url="https://bot.to/wp-content/uploads/edd/2020/09/d5a4713693a852257ca24ec8d251e295.png"
        )
        embed.add_field(name="Total Credits:", value=f"{mewcoins}", inline=False)
        embed.add_field(name="Total Redeems:", value=f"{redeems}", inline=False)
        embed.set_footer(text="All credits/redeems are from Bot-banned Users")
        await ctx.send(embed=embed)

    @check_investigator()
    @repossess.command(aliases=["h", "info"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def help(self, ctx):
        """INVESTIGATOR: COMMANDS"""
        embed = discord.Embed(
            title="Repossess Command",
            description="**Base Command:** `;repossess <sub-command>`\n**Aliases:** `;r`",
            color=0xFF0000,
        )
        embed.set_author(
            name="Investigation Team Only",
            url="https://discord.com/channels/999953429751414784/793744327746519081/",
            icon_url="https://static.thenounproject.com/png/3022281-200.png",
        )
        embed.set_thumbnail(
            url="https://bot.to/wp-content/uploads/edd/2020/09/d5a4713693a852257ca24ec8d251e295.png"
        )
        embed.add_field(
            name=";r redeems <user id> <amount>",
            value="Moves redeems to bank\n**Aliases**: `r, d, deems`",
            inline=False,
        )
        embed.add_field(
            name=";r credits <user id> <amount>",
            value="Moves credits to bank\n**Aliases**: `c, bread, cheese`",
            inline=False,
        )
        embed.add_field(
            name=";r everything <user id>",
            value="Moves all redeems and credits to bank\n**Aliases**: `r, d, deems`",
            inline=True,
        )
        embed.set_footer(text="All commands are logged in support bot server!")
        await ctx.send(embed=embed)

    @check_admin()
    @commands.hybrid_group()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def demote(self, ctx):
        """ADMIN: Demote users."""

    @check_admin()
    @demote.command(name="staff")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _demote_staff(self, ctx, member: discord.Member):
        """ADMIN: Demote a user from Staff."""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET staff = 'User' WHERE u_id = $1", member.id
            )

        msg = f"{GREEN} Removed bot permissions.\n"
        if ctx.guild.id != 999953429751414784:
            msg += (
                f"{RED} Could not remove OS roles, as this command was not run in OS.\n"
            )
            await ctx.send(msg)
            return

        ranks = {
            "Support": ctx.guild.get_role(544630193449598986),
            "Helper": ctx.guild.get_role(728937101285916772),
            "Mod": ctx.guild.get_role(519468261780357141),
            "Investigator": ctx.guild.get_role(781716697500614686),
            "Gymauth": ctx.guild.get_role(758853378515140679),
            "Admin": ctx.guild.get_role(519470089318301696),
        }
        removeset = set(ranks.values())
        currentset = set(member.roles)
        removeset &= currentset
        if not removeset:
            msg += f"{YELLOW} User had no rank roles to remove.\n"
        else:
            removelist = list(removeset)
            await member.remove_roles(
                *removelist, reason=f"Staff demotion - {ctx.author}"
            )
            removelist = [str(x) for x in removelist]
            msg += (
                f"{GREEN} Removed existing rank role(s) **{', '.join(removelist)}.**\n"
            )

        staff_role = ctx.guild.get_role(764870105741393942)
        if staff_role not in member.roles:
            msg += f"{YELLOW} User did not have the **{staff_role}** role.\n"
        else:
            await member.remove_roles(
                staff_role, reason=f"Staff demotion - {ctx.author}"
            )
            msg += f"{GREEN} Removed the **{staff_role}** role.\n"

        await ctx.send(msg)

    @check_admin()
    @demote.command(name="gym")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _demote_gym(self, ctx, user_id: discord.Member):
        """ADMIN: Demote a user from Gym Leader."""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET gym_leader = false WHERE u_id = $1", user_id.id
            )
        await ctx.send("Done.")

    @check_admin()
    @commands.hybrid_group()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def promote(self, ctx):
        """ADMIN: Promote users."""

    @check_admin()
    @promote.command(name="staff")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _promote_staff(self, ctx, rank: str, member: discord.Member):
        """ADMIN: Promote a user to a Staff rank."""
        rank = rank.title()
        if rank not in (
            "User",
            "Support",
            "Trial",
            "Mod",
            "Investigator",
            "Gymauth",
            "Admin",
            "Developer",
        ):
            await ctx.send(f"{RED} Invalid rank.")
            return
        if rank == "Developer":
            await ctx.send(f"{RED} Cannot promote a user to Developer, do so manually.")
            return
        if rank == "User":
            await ctx.send(f"{RED} To demote a user, use `;demote staff`.")
            return

        if rank != "Trial":
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET staff = $2 WHERE u_id = $1", member.id, rank
                )
            msg = f"{GREEN} Gave bot permission level **{rank}**.\n"

        if ctx.guild.id != 999953429751414784:
            msg += f"{RED} Could not add or remove OS roles, as this command was not run in OS.\n"
            await ctx.send(msg)
            return

        ranks = {
            "Support": ctx.guild.get_role(544630193449598986),
            "Trial": ctx.guild.get_role(809624282967310347),
            "Mod": ctx.guild.get_role(519468261780357141),
            "Investigator": ctx.guild.get_role(781716697500614686),
            "Gymauth": ctx.guild.get_role(758853378515140679),
            "Admin": ctx.guild.get_role(519470089318301696),
        }
        removeset = set(ranks.values())
        removeset.remove(ranks[rank])
        currentset = set(member.roles)
        removeset &= currentset
        if not removeset:
            msg += f"{YELLOW} User had no other rank roles to remove.\n"
        else:
            removelist = list(removeset)
            await member.remove_roles(
                *removelist, reason=f"Staff promotion - {ctx.author}"
            )
            removelist = [str(x) for x in removelist]
            msg += (
                f"{GREEN} Removed existing rank role(s) **{', '.join(removelist)}.**\n"
            )

        if ranks[rank] in member.roles:
            msg += f"{YELLOW} User already had the **{ranks[rank]}** role.\n"
        else:
            await member.add_roles(
                ranks[rank], reason=f"Staff promotion - {ctx.author}"
            )
            msg += f"{GREEN} Added new rank role **{ranks[rank]}**.\n"

        if rank != "Support":
            staff_role = ctx.guild.get_role(764870105741393942)
            if staff_role in member.roles:
                msg += f"{YELLOW} User already had the **{staff_role}** role.\n"
            else:
                await member.add_roles(
                    staff_role, reason=f"Staff promotion - {ctx.author}"
                )
                msg += f"{GREEN} Added the **{staff_role}** role.\n"

        await ctx.send(msg)

    @check_admin()
    @promote.command(name="gym")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _promote_gym(self, ctx, user_id: discord.Member):
        """ADMIN: Promote a user to Gym Leader."""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET gym_leader = true WHERE u_id = $1", user_id.id
            )
        await ctx.send("Done.")

    # @check_mod()
    # @commands.hybrid_command()
    async def modcmds(self, ctx):
        """MOD: Mod level commands. CURRENTLY DEPRECATED"""
        desc = "" + "`dittostats` - **Show different database statistics**\n"
        desc += "> `lb_chests` - **Show leading chest statistics**\n"
        desc += "> `radiantcount` - **Show radiant count statistics**\n"
        desc += "> `legend_ot` - **Show legend OT statistics**\n"
        desc += "> `radiantot` - **Show radiant OT statistics**\n"
        desc += "> `shinyrare` - **Show shiny rare count statistics**\n"
        desc += "> `shinyot` - **Show shiny OT statistics**\n"
        desc += "> `shinycommon` - **Show shiny count statistics**\n"
        desc += "> `all_ot` - **Show all OT statistics**\n"
        desc += "> `penta_ot` - **Show penta OT statistics**\n"
        desc += "`spcount` - **Returns a users special pokemon counts, such as shiny and radiant**\n"
        desc += "`getpoke` - **Get pokemon info by ID**\n"
        desc += "`findot` - **Find the OT userid of a pokemon**\n"
        desc += "`getuser` - **Get user info by ID**\n"
        desc += "`textsky` - **Send a text to sky**\n"
        desc += "`whoowns` - **Shows who owns a specific pokemon by its global ID**\n"
        desc += "`grantsupport` - **Promote a user to Support Team**\n"
        desc += "`refreshpatreons` - **Refresh the patreon tier cache**\n"
        desc += "`globalinfo` - **Info a poke using its global id.**\n"
        desc += "`mocksession` - **Same as mock, but toggled on and off for total mocking of a user id**\n"
        desc += "`mocksessionend` - **Ends the mocking session**\n"
        desc += "`mock` - **mock another user by ID**\n"
        desc += "`marketmany` - **Buy multiple pokes from the market at once.**\n"
        desc += "`marketinfo` - **Hidden info about marketed pokes.**\n"
        desc += "`tradable` - **Set pokemon trade-able or not**\n"
        embed = discord.Embed(title="Moderators", description=desc, color=0xFF0000)
        embed.set_author(name="Commands Usable by:")
        embed.set_footer(text="Use of these commands is logged in detail")
        await ctx.send(embed=embed)

    @check_mod()
    @pokenick.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def search(self, ctx, search_term: str):
        """MOD: Global Pokemon Nickname search"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "SELECT * FROM pokes WHERE poknick like $1", search_term
            )
        msg = "".join(f'`{x["id"]} | {x["poknick"]}`\n' for x in data)
        embed = discord.Embed(title="***GlobalID | Nickname***", color=0xDD00DD)
        pages = pagify(msg, per_page=20, base_embed=embed)
        await MenuView(ctx, pages).start()

    @check_admin()
    @pokenick.command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def regex(self, ctx, search_term: str):
        """ADMIN: Global Pokemon Nickname search (REGEX)"""
        search_term_regex = f"^{search_term}$"
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "SELECT * FROM pokes WHERE poknick ~ $1", search_term_regex
            )
        msg = "".join(f'`{x["id"]} | {x["poknick"]}`\n' for x in data)
        embed = discord.Embed(title="***GlobalID | Nickname***", color=0xDD00DD)
        pages = pagify(msg, per_page=20, base_embed=embed)
        await MenuView(ctx, pages).start()

    @check_owner()
    @commands.hybrid_command(name="neval")
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def _eval(self, ctx):
        """Evaluates python code"""
        await ctx.send(
            "Please click the below button to evaluate your code.",
            view=EvalView(ctx.author.id),
        )

    @check_owner()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def sync(self, ctx):
        # class FSnow():
        #   def __init__(self, id):
        #      self.id = id

        await ctx.send("syncing...")
        await ctx.bot.tree.sync()
        await ctx.bot.tree.sync(guild=STAFFSERVER)
        await ctx.send("Successfully synced.")

    @check_admin()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def refresh(self, ctx):
        COMMAND = "cd /ditto/ditto/ && git pull"
        addendum = ""

        proc = await asyncio.create_subprocess_shell(
            COMMAND, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        stdout = stdout.decode()

        if "no tracking information" in stderr.decode():
            COMMAND = "cd /ditto/ditto/  && git pull"
            proc = await asyncio.create_subprocess_shell(
                COMMAND, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            stdout = stdout.decode()
            addendum = "\n\n**Warning: no upstream branch is set.  I automatically pulled from origin/clustered but this may be wrong.  To remove this message and make it dynamic, please run `git branch --set-upstream-to=origin/<branch> <branch>`**"

        embed = discord.Embed(title="Git pull", description="", color=0xFFB6C1)

        if "Fast-forward" not in stdout:
            if "Already up to date." in stdout:
                embed.description = "Code is up to date."
            else:
                embed.description = "Pull failed: Fast-forward strategy failed.  Look at logs for more details."
                ctx.bot.logger.warning(stdout)
            embed.description += addendum
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

        cogs = re.findall(r"\sditto\/dittocogs\/(\w+)", stdout)
        if len(cogs) > 1:
            embed.description += f"The following cogs were updated and needs to be reloaded: `{'`, `'.join(cogs)}`.\n"
        elif len(cogs) == 1:
            embed.description += f"The following cog was updated and needs to be reloaded: `{cogs[0]}`.\n"
        else:
            embed.description += "No cogs were updated.\n"

        main_files = re.findall(r"\sditto\/(?!dittocogs)(\S*)", stdout)
        if len(main_files) > 1:
            embed.description += f"The following non-cog files were updated and require a restart: `{'`, `'.join(main_files)}`."
        elif main_files:
            embed.description += f"The following non-cog file was updated and requires a restart: `{main_files[0]}`."
        else:
            embed.description += "No non-cog files were updated."

        callbacks = re.findall(r"\scallbacks\/(\w+)", stdout)
        if len(callbacks) > 1:
            embed.description += f"The following callback files were updated and require a docker build: `{'`, `'.join(callbacks)}`."
        elif callbacks:
            embed.description += f"The following callback file was updated and requires a docker build: `{callbacks[0]}`."

        duelapi = re.findall(r"\sduelapi\/(\w+)", stdout)
        if len(duelapi) > 1:
            embed.description += f"The following duel API files were updated and require a docker build: `{'`, `'.join(duelapi)}`."
        elif duelapi:
            embed.description += f"The following duel API file was updated and requires a docker build: `{duelapi[0]}`."

        embed.description += addendum

        await ctx.send(embed=embed)

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
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
        desc = f"**__Information on {user.name}__**"
        desc += f"\n**Trainer Nickname**: `{tnick}`"
        desc += f"\n**dittobotID**: `{uid}`"
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
        embed = discord.Embed(color=0xFFB6C1, description=desc)
        embed.add_field(name="Inventory", value=f"{inv}", inline=False)
        embed.set_footer(text="Information live from Database")
        await ctx.send(embed=embed)

    @check_helper()
    @commands.hybrid_command()
    @discord.app_commands.guilds(STAFFSERVER)
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
        # desc += f"|**Ability ID**: `{ability_index}`"
        desc += f"| **Gender**: `{gender}`"
        desc += f"\n**Is Shiny**: `{shiny}` "
        desc += f"| **Is Radiant**: `{radiant}`"
        desc += f"\n**Age**: `{caught_at}` days "
        desc += f"\n**O.T.**: `{caught_by}`"
        if pokname.lower() == "egg":
            desc += f"Egg-Remaining Steps: `{counter}`"
        embed = discord.Embed(color=0xFFB6C1, description=desc)
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

    @check_admin()
    @commands.hybrid_command(aliases=["edb"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def executedb(self, ctx, type, *, execution: str):
        """Run SQL commands directly"""
        # try:
        #    await ctx.bot.log(
        #        527031932110897152, f"{ctx.author.name} used edb - Execution = `{execution}`"
        #    )a
        # except:
        #    pass

        # Sanity checks
        low_exe = execution.lower()
        if low_exe != self.safe_edb:
            self.safe_edb = low_exe
            if "update" in low_exe and "where" not in low_exe:
                await ctx.send(
                    "**WARNING**: You attempted to run an `UPDATE` without a `WHERE` clause. If you are **absolutely sure** this action is safe, run this command again."
                )
                return
            if "drop" in low_exe:
                await ctx.send(
                    "**WARNING**: You attempted to run a `DROP`. If you are **absolutely sure** this action is safe, run this command again."
                )
                return
            if "delete from" in low_exe:
                await ctx.send(
                    "**WARNING**: You attempted to run a `DELETE FROM`. If you are **absolutely sure** this action is safe, run this command again."
                )
                return

        try:
            async with ctx.bot.db[0].acquire() as pconn:
                if type == "row":
                    result = await pconn.fetchrow(execution)
                elif type == "fetch":
                    result = await pconn.fetch(execution)
                elif type == "val":
                    result = await pconn.fetchval(execution)
                elif type == "execute":
                    result = await pconn.execute(execution)
        except Exception as e:
            await ctx.send(f"```py\n{e}```")
            raise

        result = str(result)
        if len(result) > 1950:
            result = result[:1950] + "\n\n..."
        await ctx.send(f"```py\n{result}```")

    @check_admin()
    @commands.hybrid_command(aliases=["ass"])
    @discord.app_commands.guilds(STAFFSERVER)
    @discord.app_commands.default_permissions(administrator=True)
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
        # This is probably not super efficient, but I don't care to optimize
        # dev-facing code super hard...
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
        # Just... trust me, this gets a list of type objects for the command's args
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
                "Too many args provided. Make sure you surround arguments that "
                "would have spaces in the slash UI with quotes."
            )
            return
        await com


async def setup(bot):
    await bot.add_cog(KittyCat(bot))
