import asyncio
import datetime
import inspect
import io
import random
import re
import textwrap
import time
import traceback
from contextlib import redirect_stdout, suppress

import discord
from discord.ext import commands
from utils.checks import check_admin, check_owner
from utils.misc import get_pokemon_image

from dittocogs.json_files import *
from dittocogs.pokemon_list import *

GREEN = "\N{LARGE GREEN CIRCLE}"
YELLOW = "\N{LARGE YELLOW CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"

OS = discord.Object(id=999953429751414784)
OSGYMS = discord.Object(id=857746524259483679)
OSAUCTIONS = discord.Object(id=857745448717516830)
VK_SERVER = discord.Object(id=829791746221277244)


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


class admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.safe_edb = ""

    def get_insert_query(self, val, ivs, evs, level, shiny, gender):
        hpiv = ivs[0]
        atkiv = ivs[1]
        defiv = ivs[2]
        spaiv = ivs[3]
        spdiv = ivs[4]
        speiv = ivs[5]
        rnat = random.choice(natlist)
        if shiny is not True:
            shiny_chance = random.randint(1, 8000)
            shiny_chance2 = random.randint(1, 41)
            shiny = shiny_chance == shiny_chance2
        try:
            pkid = [i["pokemon_id"] for i in FORMS if i["identifier"] == val.lower()][0]
            tids = [i["type_id"] for i in PTYPES[str(pkid)]]
            ab_ids = [
                t["ability_id"] for t in POKE_ABILITIES if t["pokemon_id"] == int(pkid)
            ]

            if len(tids) == 2:
                id2 = [i["identifier"] for i in TYPES if i["id"] == tids[1]][0]
            else:
                id2 = "None"
            id1 = [i["identifier"] for i in TYPES if i["id"] == tids[0]][0]
        except:
            id1 = "None"
            id2 = "None"
            ab_ids = [0]
        query2 = """
            INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, move1, move2, move3, move4, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, happiness, fav, type1, type2, ability_index, gender)

            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32) RETURNING id
            """

        args = (
            val,
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            evs[0],
            evs[1],
            evs[2],
            evs[3],
            evs[4],
            evs[5],
            level,
            "tackle",
            "tackle",
            "tackle",
            "tackle",
            "None",
            0,
            rnat,
            35,
            "None",
            shiny,
            0,
            False,
            0,
            False,
            id1.capitalize(),
            id2.capitalize(),
            ab_ids.index(random.choice(ab_ids)),
            gender,
        )

        return query2, args

    def get_stats(self, msg):
        msg = (
            msg.replace("|0", "| 0")
            .replace("|2", "| 2")
            .replace("|1", "| 1")
            .replace("|3", "| 3")
            .replace("|3", "| 3")
            .replace("|4", "| 4")
            .replace("|5", "| 5")
            .replace("|6", "| 6")
            .replace("|7", "| 7")
            .replace("|8", "| 8")
            .replace("|9", "| 9")
        )

        msg = msg.split()
        result = [int(lt) for lt in msg if lt.isdigit()]
        ivs = []
        evs = []
        for counter, res in enumerate(result):
            if counter in (0, 3, 6, 9, 12, 15):
                pass
            elif counter in (1, 4, 7, 10, 13, 16):
                ivs.append(res)
            elif counter in (2, 5, 8, 11, 14, 17):
                evs.append(res)
        return ivs, evs

    def get_name(self, msg):
        msg = msg.replace("**", "")
        levels = []
        shiny = "<:sparkless:506398917475434496>" in msg
        if (
            "<:male:1011932024438800464>" in msg
            or "<:female:1011935234067021834>" not in msg
        ):
            gender = "-m"
        else:
            gender = "-f"
        msg = (
            msg.replace("Level", "")
            .replace("<:sparkless:506398917475434496>", "")
            .split()
        )

        for lt in msg:
            if lt.isdigit():
                levels.append(int(lt))
                msg.remove(lt)
        return msg[0], shiny, levels[0], gender

    def get_check_string(self, ivs, name, shiny, gender):
        return f"SELECT * FROM pokes WHERE pokname = '{name}' AND hpiv = {ivs[0]} AND atkiv = {ivs[1]} AND defiv = {ivs[2]} AND spatkiv = {ivs[3]} AND spdefiv = {ivs[4]} AND speediv = {ivs[5]} AND shiny = {shiny} AND gender = '{gender}'"

    def check_desc_conditions(self, embed):
        return "**Nature**" in embed.description

    def check_title_conditions(self, embed):
        return "Market" not in embed.title and "Level" in embed.title

    #    @check_admin()
    #    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    #    @discord.app_commands.default_permissions(administrator=True)
    #    @admin_cmd.command()
    #    async def dupecheck(self, ctx, user_id: discord.User):
    #        """ADMIN: Check a user to see if any ofs their pokemon have more than one owner."""
    #        async with ctx.typing():
    #            async with ctx.bot.db[0].acquire() as pconn:
    #                result = await pconn.fetch(
    #                    "SELECT pokes.id FROM pokes WHERE pokes.id IN (SELECT unnest(users.pokes) FROM users WHERE users.u_id = $1) AND 1 < (SELECT count(users.u_id) FROM users WHERE pokes.id = any(users.pokes))",
    #                    user_id.id,
    #                    timeout=600,
    #                )
    #        result = "\n".join([str(x["id"]) for x in result])
    #        if not result:
    #            await ctx.send(f"No dupes for {user_id.id}!")
    #            return

    @check_admin()
    @commands.hybrid_group(name="admin")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def admin_cmd(self, ctx):
        # await ctx_send("Affirmative.")
        """Admin Top-Level group command"""

    async def get_commit(self, ctx):
        COMMAND = f"cd {ctx.bot.app_directory} && git branch -vv"

        proc = await asyncio.create_subprocess_shell(
            COMMAND, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        stdout = stdout.decode().split("\n")

        for branch in stdout:
            if branch.startswith("*"):
                return branch

        raise ValueError()

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def show_cmds(self, interaction: discord.Interaction, parameter: str = None):
        embed = discord.Embed(title="Staff Help (admin)")
        cmd = interaction.client.get_command(parameter)
        ctx: commands.Context = await interaction.client.get_context(interaction)
        interaction._baton = ctx  # sketchy, but it works
        try:
            await cmd.can_run(ctx)
            embed.add_field(name="Usable by you:", value=f"Yes: {GREEN}")
        except commands.CommandError as exc:
            embed.add_field(name="Usable by you:", value=f"No: {RED}\n{exc}")
        await ctx.send(embed=embed)

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def commit(self, ctx):
        try:
            current = await self.get_commit(ctx)
        except ValueError:
            await ctx.send("I failed to determine the currently checked out branch!")
            return

        embed = discord.Embed(
            description=f"**Current branch/commit**\n```\n{current}```", color=0xFFB6C1
        )
        await ctx.send(embed=embed)

    @check_admin()
    @commands.hybrid_group(name="restart")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def restart_commands(self, ctx):
        """Bot Restart Top-Level group command"""

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @restart_commands.command()
    async def cluster(self, ctx, cluster_id: int = None):
        if cluster_id:
            embed = discord.Embed(
                title=f"Are you sure you want to restart Cluster #{cluster_id}?",
                color=0x36FF00,
            )
            message = await ctx.send(embed=embed)

            def check(m):
                return m.author.id == ctx.author.id and m.content.lower() in (
                    "yes",
                    "no",
                    "y",
                    "n",
                )

            try:
                msg = await ctx.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(f"Restart cancelled. {RED}")
                return

            if msg.content.lower().startswith("y"):
                res = await ctx.bot.handler(
                    "restart", 1, scope="launcher", args={"id": cluster_id}
                )

                if not res:
                    await ctx.send(
                        "Launcher did not respond.  Did you start with launcher and are sure cluster with that ID exists?"
                    )
                    return

                if res[0] == "ok":
                    embed = discord.Embed(
                        title=f"Cluster #{cluster_id} restarting...", color=0x36FF00
                    )
                    await message.edit(embed=embed)
                else:
                    # This should never be anything else, really
                    await message.edit(
                        content="rip, something went weird with the response.  Maybe it worked?"
                    )
            else:
                await ctx.send("Restart cancelled.")
        else:
            embed = discord.Embed(
                title=f"Are you sure you want to restart all clusters? {GREEN}",
                color=0x36FF00,
            )
            message = await ctx.send(embed=embed)

            def check(m):
                return m.author.id == ctx.author.id and m.content.lower() in (
                    "yes",
                    "no",
                    "y",
                    "n",
                    "fuck you",
                )

            try:
                msg = await ctx.bot.wait_for("message", check=check, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send("Restart cancelled.")
                return

            if msg.content.lower().startswith("y"):
                embed = discord.Embed(title="Restarting...", color=0x36FF00)
                await message.edit(embed=embed)

                res = await ctx.bot.handler(
                    "restartclusters",
                    1,
                    scope="launcher",
                )
            if msg.content.lower().startswith("fuck you"):
                embed = discord.Embed(
                    title="Dieing a slow painful death-fucking right off </3",
                    color=0xFFB6C1,
                )

                await message.edit(embed=embed)

                res = await ctx.bot.handler(
                    "restartclusters",
                    1,
                    scope="launcher",
                )

                if not res:
                    await ctx.send(
                        "Launcher did not respond.  Did you start with launcher?"
                    )
                    return

            else:
                await ctx.send(f"Restart cancelled. {RED}")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @restart_commands.command()
    async def launcher(self, ctx):
        embed = discord.Embed(
            title="Are you sure you want to restart the process?",
            description="This includes the cluster launcher!  This will default back to Systemctl handling the program exit.",
            color=0xFFB6C1,
        )

        message = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id and m.content.lower() in (
                "yes",
                "no",
                "y",
                "n",
            )

        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Restart cancelled.")
            return

        if msg.content.lower().startswith("y"):
            embed = discord.Embed(title="Restarting process...", color=0xFFB6C1)
            await message.edit(embed=embed)

            res = await ctx.bot.handler(
                "restartprocess",
                1,
                scope="launcher",
            )

            if not res:
                await ctx.send(
                    "Launcher did not respond.  Did you start with launcher?"
                )
                return

        else:
            await ctx.send("Restart cancelled.")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @restart_commands.command()
    async def end(self, ctx):
        embed = discord.Embed(
            title="Are you sure you want to shutdown the WHOLE process?",
            description="This includes the cluster launcher!  Everything will be shut down and must be started manually afterwords.",
            color=0xFFB6C1,
        )
        message = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id and m.content.lower() in (
                "yes",
                "no",
                "y",
                "n",
            )

        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Shutdown cancelled.")
            return

        if msg.content.lower().startswith("y"):
            embed = discord.Embed(title="Shutting down...", color=0xFFB6C1)
            await message.edit(embed=embed)

            res = await ctx.bot.handler(
                "stopprocess",
                1,
                scope="launcher",
            )

            if not res:
                await ctx.send(
                    "Launcher did not respond.  Did you start with launcher?"
                )
                return

        else:
            await ctx.send("Shutdown cancelled.")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @restart_commands.command()
    async def rolling(self, ctx):
        embed = discord.Embed(
            title="Are you sure you want to start a rolling restart?",
            description="This will restart your clusters one by one and wait for the previous to come online before restarting the next.",
            color=16758465,
        )

        message = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id and m.content.lower() in (
                "yes",
                "no",
                "y",
                "n",
            )

        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Restart cancelled.")
            return
        if msg.content.lower().startswith("y"):
            embed = discord.Embed(title="Starting rolling restart...", color=16758465)
            await message.edit(embed=embed)
            res = await ctx.bot.handler("rollingrestart", 1, scope="launcher")
            if not res:
                await ctx.send(
                    "Launcher did not respond.  Did you start with launcher?"
                )
                return
        else:
            await ctx.send("Restart cancelled.")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def donation_since(self, ctx, date: str = None):
        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except:
            await ctx.send(
                "Incorrect date format passed. Format must be, `;[ how_much_since | hms | howmuchsince ] YYYY-MM-DD`\n`;hms 2021-04-10`"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            result = await pconn.fetchval(
                "SELECT sum(amount) FROM donations WHERE date_donated >= $1", date
            )
            await ctx.send(f"Total donations since {date} = ${result}")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def traceback(self, ctx, public: bool = True):
        if not ctx.bot.traceback:
            await ctx.send("No exception has occurred yet.")
            return

        def paginate(text: str):
            """Simple generator that paginates text."""
            last = 0
            pages = []
            for curr in range(len(text)):
                if curr % 1980 == 0:
                    pages.append(text[last:curr])
                    last = curr
                    appd_index = curr
            if appd_index != len(text) - 1:
                pages.append(text[last:curr])
            return list(filter(lambda a: a != "", pages))

        destination = ctx.channel if public else ctx.author
        for page in paginate(ctx.bot.traceback):
            await destination.send("```py\n" + page + "```")

    @check_admin()
    @commands.hybrid_group(name="ditto_updates")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def public_updates(self, ctx):
        """Bot Updates Top-Level group command"""

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @public_updates.command()
    async def editupdate(self, ctx, id: int, *, update: str):
        async with ctx.bot.db[0].acquire() as pconn:
            if id == 0:
                id = await pconn.fetchval("SELECT max(id) FROM updates")
            old_update = await pconn.fetchval(
                "SELECT update FROM updates WHERE id = $1", id
            )
            update = old_update + "\n" + update
            await pconn.execute(
                "UPDATE updates SET update = $1 WHERE id = $2", update, id
            )
        await ctx.send("Updated Update")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @public_updates.command()
    async def add(self, ctx, *, update):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "INSERT INTO updates (update, dev) VALUES ($1, $2)",
                update,
                ctx.author.mention,
            )
        await ctx.send("Update Successfully Added")

    # @check_admin()
    # @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    # @discord.app_commands.default_permissions(administrator=True)
    # @admin_cmd.command()
    # async def marketyoink(self, ctx, market_id: int):
    #    """ADMIN: Remove a poke from the market, assigning it to user id 1227."""
    #    async with ctx.bot.db[0].acquire() as pconn:
    #        details = await pconn.fetchrow(
    #            "SELECT poke, buyer FROM market WHERE id = $1", market_id
    #        )
    #        if not details:
    #            await ctx.send("That listing does not exist.")
    #            return
    #        poke, buyer = details
    #        if buyer is not None:
    #            await ctx.send("That listing has already ended.")
    #            return
    #        await pconn.execute("UPDATE market SET buyer = 0 WHERE id = $1", market_id)
    #        await pconn.execute(
    #            "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = 1227",
    #            poke,
    #        )
    #    await ctx.send(f"User `1227` now owns poke `{poke}`.")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def grantsupport(self, ctx, member: discord.User):
        """ADMIN: Promote a user to Support Team"""
        com = ctx.bot.get_command("promote staff")
        if com is None:
            await ctx.send(
                "The `promote staff` command needs to be loaded to use this!"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", member.id
            )
        if rank != "User":
            await ctx.send("You cannot grant support to that user.")
            return
        await com.callback(com.cog, ctx, "support", member)

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
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

    # @check_admin()
    # @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    # @discord.app_commands.default_permissions(administrator=True)
    # @admin_cmd.command(name="frelease")
    # async def forcerelease(self, ctx, user: discord.User, pokemon_number: str = None):
    #    """ADMIN: Force release a pokemon from  a user"""
    #    if not pokemon_number is None:
    #        if pokemon_number.lower() == "latest":
    #            async with ctx.bot.db[0].acquire() as pconn:
    #                pokes = await pconn.fetchval(
    #                    "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1",
    #                    user.id,
    #                )
    #            pokes = pokes.split()
    #        else:
    #            pokes = pokemon_number.split()
    #        try:
    #            pokes = [int(x) for x in pokes]
    #        except:
    #            await ctx.send("Invalid Pokemon Number(s)")
    #            return
    #        ids = []
    #        async with ctx.bot.db[0].acquire() as pconn:
    #            stmt = await pconn.prepare(
    #                "SELECT pokes[$1] FROM users WHERE u_id = $2"
    #            )
    #            for poke in pokes:
    #                id = await stmt.fetchval(poke, user.id)
    #                if id == None:
    #                    await ctx.send("You do not have that Pokemon!")
    #                    return
    #                else:
    #                    ids.append(id)
    #            query = f"SELECT pokname FROM pokes WHERE id {'=' if len(ids) == 1 else 'in'} {ids[0] if len(ids) == 1 else tuple(ids)}"
    #            pokenames = await pconn.fetch(query)
    #        pokenames = [t["pokname"] for t in pokenames]
    #        await ctx.send(
    #            f"You are releasing {', '.join(pokenames).capitalize()}\nSay `"
    #            + await pre(ctx.bot, ctx.message)
    #            + "confirm` or `"
    #            + await pre(ctx.bot, ctx.message)
    #            + "reject`"
    #        )
    #        prefix = await pre(ctx.bot, ctx.message)
    #
    #        def check(m):
    #            return m.author.id == ctx.author.id and m.content in (
    #                f"{prefix}confirm",
    #                f"{prefix}reject",
    #            )
    #
    #        try:
    #            msg = await ctx.bot.wait_for("message", check=check, timeout=30)
    #        except asyncio.TimeoutError:
    #            await ctx.send("Release cancelled, took too long to confirm")
    #            return
    #        if msg.content.lower() == f"{await pre(ctx.bot, ctx.message)}reject":
    #            await ctx.send("Release cancelled")
    #            return
    #        elif msg.content.lower() == f"{await pre(ctx.bot, ctx.message)}confirm":
    #            async with ctx.bot.db[0].acquire() as pconn:
    #                for poke_id in ids:
    #                    await pconn.execute(
    #                        "UPDATE users SET pokes = array_remove(pokes, $1) WHERE u_id = $2",
    #                        poke_id,
    #                        user.id,
    #                    )
    #        await ctx.send(
    #            f"You have successfully released {', '.join(pokenames).capitalize()} from {user.name}"
    #        )
    #    else:
    #        await ctx.send("You dont have that Pokemon")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def announce(self, ctx, *, announce_msg: str):
        """ADMIN: Add an announcement to the bot"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "INSERT INTO announce (announce, staff) VALUES ($1, $2)",
                announce_msg,
                ctx.author.mention,
            )
        await ctx.send("Bot announcement has been Added")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def setot(self, ctx, id: int, userid: discord.User):
        """ADMIN: Set pokes OT"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET caught_by = $1 where id = $2", userid.id, id
            )
            await ctx.send(
                f"```Elm\n- Successflly set OT of `{id}` to {await ctx.bot.fetch_user(userid.id)}```"
            )

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def set_skin(self, ctx, pokeid: int, skinid: str):
        """ADMIN: Add a skin to users pokemon"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET skin = $1 WHERE id = $2",
                skinid,
                pokeid,
            )
        await ctx.send("Successfully added skin to pokemon")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def give_skin(self, ctx, userid: discord.User, pokname: str, skinname: str):
        """ADMIN: Give a skin to a user"""
        pokname = pokname.lower()
        skinname = skinname.lower()
        async with ctx.bot.db[0].acquire() as pconn:
            skins = await pconn.fetchval(
                "SELECT skins::json FROM users WHERE u_id = $1", userid.id
            )
            if pokname not in skins:
                skins[pokname] = {}
            if skinname not in skins[pokname]:
                skins[pokname][skinname] = 1
            else:
                skins[pokname][skinname] += 1
            await pconn.execute(
                "UPDATE users SET skins = $1::json WHERE u_id = $2",
                skins,
                userid.id,
            )
        await ctx.send(
            f"Gave `{userid.name}({userid.id})` a `{skinname}` skin for `{pokname}`."
        )

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def make_first(self, ctx, user: discord.User, poke_id: int):
        """ADMIN: Change a users poke to their #1 spot"""
        async with ctx.bot.db[0].acquire() as pconn:
            poke_id = await pconn.fetchval(
                "SELECT pokes[$1] FROM users WHERE u_id = $2", poke_id, user.id
            )
            if poke_id is None:
                await ctx.send(
                    "That user does not have that many pokes, or does not exist!"
                )
                return
            await pconn.execute(
                "UPDATE users SET pokes = array_remove(pokes, $1) WHERE u_id = $2",
                poke_id,
                user.id,
            )
            await pconn.execute(
                "UPDATE users SET pokes = array_prepend($1, pokes) WHERE u_id = $2",
                poke_id,
                user.id,
            )
        await ctx.send("Successfully changed poke to users #1")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command(name="skydb")
    async def unsafeedb(self, ctx, type: str, *, execution: str):
        """DEV: No timeout EDB"""
        # await ctx.send("...no.")
        # return
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
                    result = await pconn.fetchrow(execution, timeout=100)
                elif type == "fetch":
                    result = await pconn.fetch(execution, timeout=100)
                elif type == "val":
                    result = await pconn.fetchval(execution, timeout=100)
                elif type == "execute":
                    result = await pconn.execute(execution, timeout=100)
        except Exception as e:
            await ctx.send(f"```py\n{e}```")
            raise
        result = str(result)
        if len(result) > 1950:
            result = result[:1950] + "\n\n..."
        await ctx.send(f"```py\n{result}```")

    # @check_admin()
    # @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    # @discord.app_commands.default_permissions(administrator=True)
    # @admin_cmd.command(name="raffle")
    # async def raffle_winner(self, ctx):
    #    """ADMIN: Raffle command"""
    #    async with ctx.bot.db[0].acquire() as pconn:
    #        data = await pconn.fetch(
    #            "SELECT raffle, u_id FROM users WHERE raffle > 0"
    #        )
    #    uids = []
    #    weights = []
    #    for user in data:
    #        uids.append(user["u_id"])
    #        weights.append(user["raffle"])
    #    winnerid = random.choices(uids, weights=weights)[0]
    #    winner = await ctx.bot.fetch_user(winnerid)
    #    async with ctx.bot.db[0].acquire() as pconn:
    #        await pconn.execute(
    #            "UPDATE users SET raffle = raffle - 1 WHERE u_id = $1",
    #            winnerid,
    #        )
    #    await ctx.send("<:3_:924118114671665243>")
    #    await asyncio.sleep(1)
    #    await ctx.send("<:2:924118115103674418>")
    #    await asyncio.sleep(1)
    #    await ctx.send("<:1:924118115078524928>")
    #    await asyncio.sleep(1)
    #    await ctx.send(f"Winner - **{winner}** ({winnerid})")

    @check_admin()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    @admin_cmd.command()
    async def setstats(
        self,
        ctx,
        id: int,
        hp: int,
        atk: int,
        defe: int,
        spatk: int,
        spdef: int,
        speed: int,
    ):
        """ADMIN: Set stats"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "call newstats($1,$2,$3,$4,$5,$6,$7)",
                id,
                hp,
                atk,
                defe,
                spatk,
                spdef,
                speed,
            )

            await ctx.send("```Successfully set stats```")

    @check_admin()
    @commands.hybrid_group(name="bot")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def ditto_rank(self, ctx):
        """ADMIN: Promote users."""

    @check_admin()
    @ditto_rank.command(name="promote")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
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
            "Support": ctx.guild.get_role(1004222019619012699),
            "Trial": ctx.guild.get_role(1004222006474068019),
            "Mod": ctx.guild.get_role(1004221993014534174),
            "Investigator": ctx.guild.get_role(1004221992116961372),
            "Gymauth": ctx.guild.get_role(1004746164098322512),
            "Admin": ctx.guild.get_role(1004221991198396417),
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
            staff_role = ctx.guild.get_role(1004222018310389780)
            if staff_role in member.roles:
                msg += f"{YELLOW} User already had the **{staff_role}** role.\n"
            else:
                await member.add_roles(
                    staff_role, reason=f"Staff promotion - {ctx.author}"
                )
                msg += f"{GREEN} Added the **{staff_role}** role.\n"
        await ctx.send(msg)

    @check_admin()
    @ditto_rank.command(name="gym")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def _promote_gym(self, ctx, user_id: discord.User):
        """ADMIN: Promote a user to Gym Leader."""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET gym_leader = True WHERE u_id = $1", user_id.id
            )
        await ctx.send("Done.")

        # @check_admin()
        # @commands.hybrid_group()
        # @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
        # @discord.app_commands.default_permissions(administrator=True)
        # async def demote(self, ctx):
        #    """ADMIN: Demote users."""

    @check_admin()
    @ditto_rank.command(name="demote")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
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
            "Support": ctx.guild.get_role(1004222019619012699),
            "Trial": ctx.guild.get_role(1004222006474068019),
            "Mod": ctx.guild.get_role(1004221993014534174),
            "Investigator": ctx.guild.get_role(1004221992116961372),
            "Gymauth": ctx.guild.get_role(1004746164098322512),
            "Admin": ctx.guild.get_role(1004221991198396417),
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
        staff_role = ctx.guild.get_role(1004222018310389780)
        if staff_role not in member.roles:
            msg += f"{YELLOW} User did not have the **{staff_role}** role.\n"
        else:
            await member.remove_roles(
                staff_role, reason=f"Staff demotion - {ctx.author}"
            )
            msg += f"{GREEN} Removed the **{staff_role}** role.\n"
        await ctx.send(msg)

    @check_admin()
    @ditto_rank.command(name="gym_demote")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def _demote_gym(self, ctx, user_id: discord.Member):
        """ADMIN: Demote a user from Gym Leader."""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET gym_leader = false WHERE u_id = $1", user_id.id
            )
        await ctx.send("Done.")

    @check_admin()
    @admin_cmd.command(name="boostedspwn")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def boostedspwn(self, ctx, *, val1: str):
        with suppress(discord.HTTPException):
            await ctx.message.delete()
        try:
            guild = await ctx.bot.mongo_find("guilds", {"id": ctx.guild.id})
            delspawn = guild["delete_spawns"]
        except Exception as e:
            delspawn = False
        shiny = False
        radiant = False
        val1 = val1.lower().split()
        if "shiny" in val1:
            shiny = True
            ind = val1.index("shiny")
            val1.pop(ind)
        if "radiant" in val1:
            radiant = True
            ind = val1.index("radiant")
            val1.pop(ind)
        val2 = val1[0]
        channel = ctx.channel
        val = val2.lower()
        irul = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        start = val[0]
        embed = discord.Embed(
            title="A wild Pokémon has Spawned, Say its name to catch it!",
            color=random.choice(ctx.bot.colors),
        )

        embed.add_field(name="-", value=f"This Pokémons name starts with {start}")
        embed.set_image(url=irul)
        embedmsg = await channel.send(embed=embed)

        def check(m):
            return (
                m.content.lower() in (val.replace("-", " "), val)
                and m.channel == channel
            )

        msg = await ctx.bot.wait_for("message", check=check, timeout=60)
        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        pokemon_info = await ctx.bot.db[1].pfile.find_one(
            {"id": form_info["pokemon_id"]}
        )

        try:
            gender_rate = pokemon_info["gender_rate"]
        except:
            print(f"\n\nCould not spawn {form_info['identifier']}\n\n")
        gender_rate = pokemon_info["gender_rate"]
        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        hpiv = random.randint(17, 31)
        atkiv = random.randint(17, 31)
        defiv = random.randint(17, 31)
        spaiv = random.randint(17, 31)
        spdiv = random.randint(17, 31)
        speiv = random.randint(17, 31)
        plevel = random.randint(90, 100)
        nature = random.choice(natlist)
        plevel**2
        if "idoran" in val.lower():
            gender = val[-2:]
        elif val.lower() == "volbeat":
            gender = "-m"
        elif val.lower() == "illumise":
            gender = "-f"
        elif val.lower() == "gallade":
            gender = "-m"
        elif val.lower() == "nidoking":
            gender = "-m"
        elif val.lower() == "nidoqueen":
            gender = "-f"
        else:
            if gender_rate in (8, -1) and val.capitalize() in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-f"
            elif gender_rate in (8, -1, 0) and val.capitalize() not in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-m"
            else:
                gender = "-f" if random.randint(1, 10) == 1 else "-m"
        query2 = """
                INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, moves, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, fav, ability_index, gender, caught_by, radiant, tradable)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29) RETURNING id
                """

        args = (
            val2.capitalize(),
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            ["tackle", "tackle", "tackle", "tackle"],
            "None",
            0,
            nature,
            35,
            "None",
            shiny,
            0,
            False,
            False,
            random.choice(ab_ids),
            gender,
            msg.author.id,
            radiant,
            False,
        )

        async with ctx.bot.db[0].acquire() as pconn:
            pokeid = await pconn.fetchval(query2, *args)
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $2) WHERE u_id = $1",
                msg.author.id,
                pokeid,
            )

        teext = f"Congratulations {msg.author.mention}, you have caught a {val}!\n"
        await ctx.channel.send(embed=make_embed(title="", description=teext))
        await asyncio.sleep(5)
        await msg.delete()
        if delspawn:
            await embedmsg.delete()

    async def get_commit(self, ctx):
        COMMAND = "cd /ditto/ditto/ && git branch -vv"
        proc = await asyncio.create_subprocess_shell(
            COMMAND, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()
        stdout = stdout.decode().split("\n")
        for branch in stdout:
            if branch.startswith("*"):
                return branch
        raise ValueError()

    @check_admin()
    @admin_cmd.command(name="pull")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
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
                embed.description = "Code is up to date."
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

    @check_owner()
    @admin_cmd.command(name="sync")
    # @app_commands.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def sync(self, interaction: discord.Interaction) -> None:
        await interaction.client.tree.sync()
        await interaction.client.tree.sync(guild=OS)
        await interaction.client.tree.sync(guild=OSGYMS)
        await interaction.client.tree.sync(guild=OSAUCTIONS)
        desc = "**Staff Command's Synced to:**\n"
        desc += f"{GREEN}-OS\n"
        desc += f"{GREEN}-OS Gym Server\n"
        desc += f"{GREEN}-OS Auction Server\n"
        desc += f"{GREEN}-VK's Private Server"
        sync_message = discord.Embed(
            title="Global/Guild Sync Status", type="rich", description=desc
        )
        await interaction.response.send_message(embed=sync_message)

    @check_admin()
    @admin_cmd.command(name="error")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def traceback(self, ctx):
        if not ctx.bot.traceback:
            await ctx.send("No exception has occurred yet.")
            return
        public = True

        def paginate(text: str):
            """Simple generator that paginates text."""
            last = 0
            pages = []
            for curr in range(len(text)):
                if curr % 1980 == 0:
                    pages.append(text[last:curr])
                    last = curr
                    appd_index = curr
            if appd_index != len(text) - 1:
                pages.append(text[last:curr])
            return list(filter(lambda a: a != "", pages))

        destination = ctx.channel if public else ctx.author
        for page in paginate(ctx.bot.traceback):
            embed = discord.Embed(
                title="Error Traceback", description=f"```py\n{page}```"
            )
            await destination.send(embed=embed)

    @check_admin()
    @admin_cmd.command(name="boosted_give")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def boostedgive(self, ctx, user: discord.User, *, val1: str):
        with suppress(discord.HTTPException):
            await ctx.message.delete()
        with suppress(Exception):
            guild = await ctx.bot.mongo_find("guilds", {"id": ctx.guild.id})
            guild["delete_spawns"]
        shiny = False
        radiant = False
        val1 = val1.lower().split()
        if "shiny" in val1:
            shiny = True
            ind = val1.index("shiny")
            val1.pop(ind)
        if "radiant" in val1:
            radiant = True
            ind = val1.index("radiant")
            val1.pop(ind)
        val2 = val1[0]
        channel = ctx.channel
        val = val2.lower()
        irul = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        val[0]
        embed = discord.Embed(
            title=f"Congratulations, an admin has given you the following pokemon: `{val}`\n\nShiny: {shiny}!\nRadiant: {radiant}!\n\n`Given by {ctx.author}`",
            color=random.choice(ctx.bot.colors),
        )

        embed.set_footer(text="This is not a spawn message!!!")
        embed.add_field(name="Given to:", value=f"***{user.mention}***")
        embed.set_image(url=irul)
        embedmsg = await channel.send(embed=embed)
        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        pokemon_info = await ctx.bot.db[1].pfile.find_one(
            {"id": form_info["pokemon_id"]}
        )

        try:
            gender_rate = pokemon_info["gender_rate"]
        except:
            print(f"\n\nCould not spawn {form_info['identifier']}\n\n")
        gender_rate = pokemon_info["gender_rate"]
        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        hpiv = random.randint(17, 31)
        atkiv = random.randint(17, 31)
        defiv = random.randint(17, 31)
        spaiv = random.randint(17, 31)
        spdiv = random.randint(17, 31)
        speiv = random.randint(17, 31)
        plevel = random.randint(90, 100)
        nature = random.choice(natlist)
        plevel**2
        if "idoran" in val.lower():
            gender = val[-2:]
        elif val.lower() == "volbeat":
            gender = "-m"
        elif val.lower() == "illumise":
            gender = "-f"
        elif val.lower() == "gallade":
            gender = "-m"
        elif val.lower() == "nidoking":
            gender = "-m"
        elif val.lower() == "nidoqueen":
            gender = "-f"
        elif gender_rate in (8, -1) and val.capitalize() in (
            "Blissey",
            "Bounsweet",
            "Chansey",
            "Cresselia",
            "Flabebe",
            "Floette",
            "Florges",
            "Froslass",
            "Happiny",
            "Illumise",
            "Jynx",
            "Kangaskhan",
            "Lilligant",
            "Mandibuzz",
            "Miltank",
            "Nidoqueen",
            "Nidoran-f",
            "Nidorina",
            "Petilil",
            "Salazzle",
            "Smoochum",
            "Steenee",
            "Tsareena",
            "Vespiquen",
            "Vullaby",
            "Wormadam",
            "Meowstic-f",
        ):
            gender = "-f"
        elif gender_rate in (8, -1, 0) and val.capitalize() not in (
            "Blissey",
            "Bounsweet",
            "Chansey",
            "Cresselia",
            "Flabebe",
            "Floette",
            "Florges",
            "Froslass",
            "Happiny",
            "Illumise",
            "Jynx",
            "Kangaskhan",
            "Lilligant",
            "Mandibuzz",
            "Miltank",
            "Nidoqueen",
            "Nidoran-f",
            "Nidorina",
            "Petilil",
            "Salazzle",
            "Smoochum",
            "Steenee",
            "Tsareena",
            "Vespiquen",
            "Vullaby",
            "Wormadam",
            "Meowstic-f",
        ):
            gender = "-m"
        else:
            gender = "-f" if random.randint(1, 10) == 1 else "-m"
        query2 = """
                INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, moves, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, fav, ability_index, gender, caught_by, radiant, tradable)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29) RETURNING id
                """

        args = (
            val2.capitalize(),
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            ["tackle", "tackle", "tackle", "tackle"],
            "None",
            0,
            nature,
            35,
            "None",
            shiny,
            0,
            False,
            False,
            random.choice(ab_ids),
            gender,
            user.id,
            radiant,
            False,
        )

        async with ctx.bot.db[0].acquire() as pconn:
            pokeid = await pconn.fetchval(query2, *args)
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $2) WHERE u_id = $1",
                user.id,
                pokeid,
            )

        teext = f"Congratulations {user.mention}, an admin has given you the following pokemon: `{val}`!\n"

        await ctx.channel.send(embed=make_embed(title="", description=teext))
        # await asyncio.sleep(5)
        # await msg.delete()
        # if delspawn:
        #   await embedmsg.delete()

    @check_admin()
    @admin_cmd.command(name="shadow_reset")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def _shadow_reset(self, ctx, user_id: discord.User):
        """ADMIN: Resets a users Shadow hunt count."""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET chain = 0 WHERE u_id = $1", user_id.id
            )
        await ctx.send("Users hunt was reset!")

    @check_owner()
    @admin_cmd.command(name="neval")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def _eval(self, ctx):
        """Evaluates python code"""
        await ctx.send(
            "Please click the below button to evaluate your code.",
            view=EvalView(ctx.author.id),
        )

    @check_owner()
    @admin_cmd.command(name="create_custom")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def create_custom(self, ctx, skin: str, *, val):
        """KT: Creation of custom pokes for art stuff."""
        shiny = False
        radiant = False
        val = val.capitalize()
        poke = await ctx.bot.commondb.create_poke(
            ctx.bot,
            ctx.author.id,
            val,
            shiny=shiny,
            radiant=radiant,
            skin=skin.lower(),
            level=100,
        )
        if poke is None:
            await ctx.send(f"`{val}` doesn't seem to be a valid pokemon name...")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET hpiv = 31, atkiv = 31, defiv = 31, spatkiv = 31, spdefiv = 31, speediv = 31 WHERE id = $1",
                poke.id,
            )
        teext = f"{ctx.author.mention} has created a **{skin}** skinned **{val}**!\nIt has been added as your newest pokemon."
        await ctx.channel.send(embed=make_embed(title="", description=teext))

    @check_admin()
    @commands.hybrid_group(name="gib")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def gib_cmds(self, ctx):
        """Top layer of group"""

    @check_admin()
    @gib_cmds.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
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
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def credits(self, ctx, user: discord.User, credits: int):
        """ADMIN: Give a user Credits"""
        # await ctx.send("get out of here....no.")
        # return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                credits,
                user.id,
            )
            await ctx.send(
                f"{user.name} was given {credits} credits by {ctx.author.id}."
            )

    @check_admin()
    @gib_cmds.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
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
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
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
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
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

    @check_admin()
    @admin_cmd.command(name="playgod")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def forcechange(self, ctx, pokeid: int, pokname):
        """ADMIN: Change a pokemon's  species, caution, extremely painful.
        ex. ;forcechange <POKEID> <NEW-POKENAME>"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET pokname = $1 WHERE id = $2", pokname, pokeid
            )

        embed = discord.Embed()
        embed.add_field(
            name=f"{pokeid}",
            value=f"Species change was successful.\nIt is now a {pokname}",
            inline=True,
        )

        embed.add_field(
            name="Warning!",
            value="Pokemon may experience great pain, or even death.",
            inline=False,
        )

        embed.set_footer(text="Enjoy!")
        await ctx.send(embed=embed)

    @check_admin()
    @admin_cmd.command(name="spawn")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def spawn(self, ctx, *, val1: str):
        with suppress(discord.HTTPException):
            await ctx.message.delete()
        try:
            guild = await ctx.bot.mongo_find("guilds", {"id": ctx.guild.id})
            delspawn = guild["delete_spawns"]
        except Exception as e:
            delspawn = False
        shiny = False
        radiant = False
        val1 = val1.lower().split()
        if "shiny" in val1:
            shiny = True
            ind = val1.index("shiny")
            val1.pop(ind)
        if "radiant" in val1:
            radiant = True
            ind = val1.index("radiant")
            val1.pop(ind)
        val2 = val1[0]
        channel = ctx.channel
        val = val2.lower()
        irul = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        start = val[0]
        embed = discord.Embed(
            title="A wild Pokémon has Spawned, Say its name to catch it!",
            color=random.choice(ctx.bot.colors),
        )

        embed.add_field(name="-", value=f"This Pokémons name starts with {start}")
        embed.set_image(url=irul)
        embedmsg = await channel.send(embed=embed)

        def check(m):
            return (
                m.content.lower() in (val.replace("-", " "), val)
                and m.channel == channel
            )

        msg = await ctx.bot.wait_for("message", check=check, timeout=60)
        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        pokemon_info = await ctx.bot.db[1].pfile.find_one(
            {"id": form_info["pokemon_id"]}
        )

        try:
            gender_rate = pokemon_info["gender_rate"]
        except:
            print(f"\n\nCould not spawn {form_info['identifier']}\n\n")
        gender_rate = pokemon_info["gender_rate"]
        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        hpiv = random.randint(0, 31)
        atkiv = random.randint(0, 31)
        defiv = random.randint(0, 31)
        spaiv = random.randint(0, 31)
        spdiv = random.randint(0, 31)
        speiv = random.randint(0, 31)
        plevel = random.randint(99, 100)
        nature = random.choice(natlist)
        plevel**2
        if "idoran" in val.lower():
            gender = val[-2:]
        elif val.lower() == "volbeat":
            gender = "-m"
        elif val.lower() == "illumise":
            gender = "-f"
        elif val.lower() == "gallade":
            gender = "-m"
        elif val.lower() == "nidoking":
            gender = "-m"
        elif val.lower() == "nidoqueen":
            gender = "-f"
        else:
            if gender_rate in (8, -1) and val.capitalize() in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-f"
            elif gender_rate in (8, -1, 0) and val.capitalize() not in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-m"
            else:
                gender = "-f" if random.randint(1, 10) == 1 else "-m"
        query2 = """
                INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, moves, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, fav, ability_index, gender, caught_by, radiant, tradable)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29) RETURNING id
                """

        args = (
            val2.capitalize(),
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            ["tackle", "tackle", "tackle", "tackle"],
            "None",
            0,
            nature,
            35,
            "None",
            shiny,
            0,
            False,
            False,
            random.choice(ab_ids),
            gender,
            msg.author.id,
            radiant,
            False,
        )

        async with ctx.bot.db[0].acquire() as pconn:
            pokeid = await pconn.fetchval(query2, *args)
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $2) WHERE u_id = $1",
                msg.author.id,
                pokeid,
            )

        teext = f"Congratulations {msg.author.mention}, you have caught a {val}!\n"
        await ctx.channel.send(embed=make_embed(title="", description=teext))
        await asyncio.sleep(5)
        await msg.delete()
        if delspawn:
            await embedmsg.delete()

    @check_admin()
    @commands.hybrid_command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def scount(self, ctx):
        await ctx.send(f"{len(bot.guilds)}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(admin(bot))
    # await bot.add_cog(admin(bot), guilds=[OS, OSGYMS, OSAUCTIONS])
