import asyncio
from contextlib import redirect_stdout
import inspect
import textwrap
import time
import io
import datetime
import traceback

import discord
from contextlib import suppress
from discord.ext import commands
from utils.checks import check_admin, check_helper, check_investigator, check_mod

GREEN = "\N{LARGE GREEN CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"
OS = discord.Object(id=999953429751414784)
OSGYMS = discord.Object(id=857746524259483679)
OSAUCTIONS = discord.Object(id=857745448717516830)
VK_SERVER = discord.Object(id=829791746221277244)


def round_speed(speed):
    try:
        s = f"{speed:.0f}"
    except:
        s = "?"
    return s


def round_stat(stat):
    return "?" if stat == "?" else round(stat)


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


class staff(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

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
                with suppress(Exception):
                    (await self.bot.fetch_user(id)).name
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
    @commands.hybrid_command()
    # @app_commands.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def sync(self, ctx) -> None:
        await self.bot.tree.sync()
        await self.bot.tree.sync(guild=OS)
        await self.bot.tree.sync(guild=OSGYMS)
        await self.bot.tree.sync(guild=OSAUCTIONS)
        desc = "**Staff Command's Synced to:**\n"
        desc += f"{GREEN}-OS\n"
        desc += f"{GREEN}-OS Gym Server\n"
        desc += f"{GREEN}-OS Auction Server\n"
       #desc += f"{GREEN}-VK's Private Server"
        sync_message = discord.Embed(
            title="Global/Guild Sync Status", type="rich", description=desc
        )
        await ctx.send(embed=sync_message)

    @check_mod()
    @commands.hybrid_command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def nitro_fix(self, ctx, user: discord.User) -> None:
        """Staff only: Fix for those stuck in nitro-claim selection"""
        try:
            await self.bot.redis_manager.redis.execute("LREM", "nitrorace", "1", str(user.id))
            desc = f"**{user.mention} boost-lock reset, user should be able to use `/nitro claim` now.**\n"
            sync_message = discord.Embed(
            title="Nitro Claim Fixomattic-3000", type="rich", description=desc
            )
            await ctx.send(embed=sync_message)
        except:
            desc = f"**{user.mention} - boost-lock reset was not able to be applied-ask sky about this one**\n"
            sync_message = discord.Embed(
            title="Uh oh-", type="rich", description=desc
            )
            await ctx.send(embed=sync_message)

    @check_admin()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command()
    async def load(self, ctx, extension_name: str):
        """Loads an extension."""
        if "ditto.cogs" in extension_name:
            extension_name = extension_name.replace("ditto.cogs", "dittocogs")
        if not extension_name.startswith("dittocogs."):
            extension_name = f"dittocogs.{extension_name}"

        launcher_res = await ctx.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return await ctx.send(
                f"Launcher did not respond.  Please start with the launcher to use this command across all clusters.  If attempting to reload on this cluster alone, please use `{ctx.prefix}loadsingle {extension_name}`"
            )

        processes = len(launcher_res[0])
        load_res = await ctx.bot.handler(
            "load", processes, args={"cogs": [extension_name]}, scope="bot"
        )
        load_res.sort(key=lambda x: x["cluster_id"])

        e = discord.Embed(color=0xFFB6C1)
        builder = ""
        if (
            message_same := all(
                load_res[0]["cogs"][extension_name]["message"]
                == nc["cogs"][extension_name]["message"]
                for nc in load_res
            )
            and load_res[0]["cogs"][extension_name]["message"]
        ):
            e.description = f"Failed to load package on all clusters:\n`{load_res[0]['cogs'][extension_name]['message']}`"
        else:
            for cluster in load_res:
                if cluster["cogs"][extension_name]["success"]:
                    builder += (
                        f"`Cluster #{cluster['cluster_id']}`: Successfully loaded\n"
                    )
                else:
                    msg = cluster["cogs"][extension_name]["message"]
                    builder += f"`Cluster #{cluster['cluster_id']}`: {msg}\n"
            e.description = builder
        await ctx.send(embed=e)

    @check_mod()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command()
    async def reload(self, ctx, extension_name: str):
        """Reloads an extension."""
        if "ditto.cogs" in extension_name:
            extension_name = extension_name.replace("ditto.cogs", "dittocogs")
        if not extension_name.startswith("dittocogs."):
            extension_name = f"dittocogs.{extension_name}"

        launcher_res = await ctx.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return await ctx.send(
                f"Launcher did not respond.  Please start with the launcher to use this command across all clusters.  If attempting to reload on this cluster alone, please use `{ctx.prefix}reloadsingle {extension_name}`"
            )

        processes = len(launcher_res[0])
        # We don't really care whether or not it fails to unload... the main thing is just to get it loaded with a refresh
        await ctx.bot.handler(
            "unload", processes, args={"cogs": [extension_name]}, scope="bot"
        )
        load_res = await ctx.bot.handler(
            "load", processes, args={"cogs": [extension_name]}, scope="bot"
        )
        load_res.sort(key=lambda x: x["cluster_id"])

        e = discord.Embed(color=0xFFB6C1)
        builder = ""
        if (
            message_same := all(
                load_res[0]["cogs"][extension_name]["message"]
                == nc["cogs"][extension_name]["message"]
                for nc in load_res
            )
            and load_res[0]["cogs"][extension_name]["message"]
        ):
            e.description = f"Failed to reload package on all clusters:\n`{load_res[0]['cogs'][extension_name]['message']}`"
        else:
            for cluster in load_res:
                if cluster["cogs"][extension_name]["success"]:
                    builder += (
                        f"`Cluster #{cluster['cluster_id']}`: Successfully reloaded\n"
                    )
                else:
                    msg = cluster["cogs"][extension_name]["message"]
                    builder += f"`Cluster #{cluster['cluster_id']}`: {msg}\n"
            e.description = builder
        await ctx.send(embed=e)

    @check_admin()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command()
    async def unload(self, ctx, extension_name: str):
        """Unloads an extension."""
        if "ditto.cogs" in extension_name:
            extension_name = extension_name.replace("ditto.cogs", "dittocogs")
        if not extension_name.startswith("dittocogs."):
            extension_name = f"dittocogs.{extension_name}"

        launcher_res = await ctx.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return await ctx.send(
                f"Launcher did not respond.  Please start with the launcher to use this command across all clusters.  If attempting to reload on this cluster alone, please use `{ctx.prefix}unloadsingle {extension_name}`"
            )

        processes = len(launcher_res[0])
        unload_res = await ctx.bot.handler(
            "unload", processes, args={"cogs": [extension_name]}, scope="bot"
        )
        unload_res.sort(key=lambda x: x["cluster_id"])

        e = discord.Embed(color=0xFFB6C1)
        builder = ""
        if (
            message_same := all(
                unload_res[0]["cogs"][extension_name]["message"]
                == nc["cogs"][extension_name]["message"]
                for nc in unload_res
            )
            and unload_res[0]["cogs"][extension_name]["message"]
        ):
            e.description = f"Failed to unload package on all clusters:\n`{unload_res[0]['cogs'][extension_name]['message']}`"
        else:
            for cluster in unload_res:
                if cluster["cogs"][extension_name]["success"]:
                    builder += (
                        f"`Cluster #{cluster['cluster_id']}`: Successfully unloaded\n"
                    )
                else:
                    msg = cluster["cogs"][extension_name]["message"]
                    builder += f"`Cluster #{cluster['cluster_id']}`: {msg}\n"
            e.description = builder
        await ctx.send(embed=e)

    @check_admin()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command()
    async def reloadsingle(self, ctx, extension_name: str):
        """smh"""
        if "ditto.cogs" in extension_name:
            extension_name = extension_name.replace("ditto.cogs", "dittocogs")
        if not extension_name.startswith("dittocogs."):
            extension_name = f"dittocogs.{extension_name}"
        try:
            ctx.bot.unload_extension(extension_name)
        except:
            # eh
            pass

        try:
            ctx.bot.load_extension(extension_name)
        except Exception as e:
            await ctx.send(f"Failed to reload package: `{type(e).__name__}: {str(e)}`")
            return

        await ctx.send(
            f"you should be running from the launcher :p\n\nSuccessfully reloaded {extension_name}."
        )

    @check_admin()
    @discord.app_commands.default_permissions(administrator=True)
    @commands.hybrid_command()
    async def cogs(self, ctx):
        """View the currently loaded cogs."""
        cogs = sorted([x.replace("dittocogs.", "") for x in ctx.bot.extensions.keys()])
        embed = discord.Embed(
            title=f"{len(cogs)} loaded:",
            description=f" - {GREEN}\n".join(cogs),
            color=0xFF0060,
        )
        await ctx.send(embed=embed)

    @check_mod()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command(aliases=["detradelock", "deltradelock"])
    async def resettradelock(self, ctx, user: int):
        """Reset the redis market tradelock for a user"""
        result = await ctx.bot.redis_manager.redis.execute(
            "LREM", "tradelock", "1", str(user)
        )
        if result == 0:
            await ctx.send(
                "That user was not in the Redis tradelock.  Are you sure you have the right user?"
            )
        else:
            await ctx.send("Successfully removed the user from the Redis tradelock.")

    @check_investigator()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command()
    async def tradeban(self, ctx, id: discord.User):
        async with ctx.bot.db[0].acquire() as pconn:
            is_tradebanned = await pconn.fetchval(
                "SELECT tradelock FROM users WHERE u_id = $1", id.id
            )
            if is_tradebanned is None:
                await ctx.send("User has not started, cannot trade ban.")
                return
            if is_tradebanned:
                await ctx.send("User already trade banned.")
                return
            await pconn.execute(
                "UPDATE users SET tradelock = $1 WHERE u_id = $2", True, id.id
            )
        await ctx.send(f"Successfully trade banned USER ID - {id.id}")

    @check_mod()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command(aliases=["untradeban", "deltradeban"])
    async def detradeban(self, ctx, id: discord.User):
        async with ctx.bot.db[0].acquire() as pconn:
            is_tradebanned = await pconn.fetchval(
                "SELECT tradelock FROM users WHERE u_id = $1", id.id
            )
            if is_tradebanned is None:
                await ctx.send("User has not started, cannot remove trade ban.")
                return
            if not is_tradebanned:
                await ctx.send("User is not trade banned.")
                return
            await pconn.execute(
                "UPDATE users SET tradelock = $1 WHERE u_id = $2", False, id.id
            )
        await ctx.send(f"Successfully removed trade ban from USER ID - {id.id}")

    @check_helper()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command(enabled=False)
    async def lb(self, ctx, val, num: int = None):
        official_admin_role = ctx.bot.official_server.get_role(1004221991198396417)
        admins = [member.id for member in official_admin_role.members]

        official_mod_role = ctx.bot.official_server.get_role(1004221993014534174)
        mods = [member.id for member in official_mod_role.members]

        if num == 1 or num is None:
            num = 25
            snum = 0

        else:
            num *= 25
            snum = num - 25

        if val is None:
            em = discord.Embed(title="Leaderboard options", color=0xFFBC61)
            em.add_field(
                name="Redeems",
                value=f"`{ctx.prefix}leaderboard redeems` for redeems leaderboard",
            )
            await ctx.send(embed=em)
        elif val.lower() in ("creds", "credits"):
            index_num = 0
            async with ctx.bot.db[0].acquire() as pconn:
                leaders = await pconn.fetch(
                    f"SELECT tnick, mewcoins, u_id, staff FROM users ORDER BY mewcoins DESC LIMIT {num}"
                )
            nicks = [record["tnick"] for record in leaders]
            coins = [record["mewcoins"] for record in leaders]
            ids = [record["u_id"] for record in leaders]
            staffs = [record["staff"] for record in leaders]
            embed = discord.Embed(title="Credit Rankings!", color=0xFFB6C1)
            desc = ""
            for idx, coin in enumerate(coins[snum:num], start=snum):
                id = ids[idx]
                is_staff = staffs[idx] != "User"
                # if (id in mods) or (id in admins) or (is_staff):
                #    continue
                nicks[idx]
                try:
                    name = (await ctx.bot.fetch_user(id)).name
                except:
                    name = "Unknown User"
                index_num += 1
                desc += f"__{index_num}__. {coin:,.0f} Credits - {name}\n"
                # {coins} Credits {coins} Credits
            embed.description = desc
            await ctx.send(embed=embed)
        elif val.lower() in ("redeems", "redeem", "deems"):
            index_num = 0
            async with ctx.bot.db[0].acquire() as pconn:
                leaders = await pconn.fetch(
                    f"SELECT tnick, redeems, u_id FROM users ORDER BY redeems DESC LIMIT {num}"
                )
            nicks = [record["tnick"] for record in leaders]
            coins = [record["redeems"] for record in leaders]
            ids = [record["u_id"] for record in leaders]
            embed = discord.Embed(title="Redeem Rankings!", color=0xFFB6C1)
            desc = ""
            for idx, id in enumerate(ids[snum:num], start=snum):
                if id in mods or id in admins:
                    continue
                coin = coins[idx]
                nicks[idx]
                name = ctx.bot.get_user(id)
                index_num += 1
                desc += f"__{index_num}__. {name.name} - {coin:,.0f} Redeems\n"
            embed.description = desc
            await ctx.send(embed=embed)
        else:
            await ctx.send("Choose Redeems, and thats it! Just redeems!")

    @check_helper()
    @discord.app_commands.default_permissions(ban_members=True)
    @commands.hybrid_command()
    async def shards(self, ctx, shards_of_cluster: int = None):
        if shards_of_cluster is None:
            shards_of_cluster = ctx.bot.cluster["id"]
        process_res = await ctx.bot.handler(
            "send_shard_info", 1, args={"cluster_id": shards_of_cluster}, scope="bot"
        )
        if not len(process_res):
            await ctx.send("Cluster is dead or does not exist.")
            return

        process_res = process_res[0]

        shard_groups = process_res["shards"]
        cluster_id = process_res["id"]
        cluster_name = process_res["name"]

        pages = []
        current = discord.Embed(
            title=f"Cluster #{cluster_id} ({cluster_name})",
            color=0xFFB6C1,
        )
        current.set_footer(text=f"{ctx.prefix}[ n|next, b|back, s|start, e|end ]")
        for s in shard_groups.values():
            msg = (
                "```prolog\n"
                f"Latency:   {s['latency']}ms\n"
                f"Guilds:    {s['guilds']}\n"
                f"Channels:  {s['channels']}\n"
                f"Users:     {s['users']}\n"
                "```"
            )
            current.add_field(
                name=f"Shard `{s['id']}/{ctx.bot.shard_count}`", value=msg
            )

        pages.append(current)

        embed = await ctx.send(embed=pages[0])
        current_page = 1

        def get_value(message):
            return {
                f"{ctx.prefix}n": min(len(pages) - 1, current_page + 1),
                f"{ctx.prefix}next": min(len(pages) - 1, current_page + 1),
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(staff(bot))
