import asyncio
import pathlib
import time
from copy import copy

import discord
from discord.ext import commands, tasks
from utils.misc import MenuView
from pokemon_utils.classes import *

from dittocogs.json_files import *
from dittocogs.pokemon_list import *

IMG_SERVER_BASE_SKIN = "https://skylarr1227.github.io/images/skins"
IMG_SERVER_BASE_RAD = "https://skylarr1227.github.io/images/radiant"
SKIN_BASE = "/home/kittycat/mewbot/shared/duel/sprites/skins/"
RAD_BASE = "/home/kittycat/mewbot/shared/duel/sprites/radiant/"

GREEN = "\N{LARGE GREEN CIRCLE}"
YELLOW = "\N{LARGE YELLOW CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"


class Sky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        self.safe_edb = ""
        self.cleanup_sessions.start()
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

    @tasks.loop(seconds=60)
    async def cleanup_sessions(self):
        for channel in self.sessions:
            for user in list(self.sessions[channel]):
                if (time.time() - self.sessions[channel][user]["last"]) >= (60 * 5):
                    del self.sessions[channel][user]
                    c = self.bot.get_channel(channel)
                    await c.send(f"Mock session ended for mocker {user}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.sessions:
            return

        if message.channel.id not in self.sessions:
            return

        entry = None
        try:
            entry = self.sessions[message.channel.id][message.author.id]
        except KeyError:
            return

        if not entry:
            return

        if message.content.startswith(":"):
            self.sessions[message.channel.id][message.author.id]["last"] = time.time()

            msg = copy(message)
            msg.author = entry["mocking"]
            msg.content = f";{message.content[1:]}"

            fake_ctx = await self.bot.get_context(msg)
            await self.bot.invoke(fake_ctx)
        elif message.content.startswith("m:"):
            self.sessions[message.channel.id][message.author.id]["last"] = time.time()

            msg = copy(message)
            msg.author = entry["mocking"]
            msg.content = message.content[2:]

            self.bot.dispatch("message", msg)

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

    @commands.hybrid_command(aliases=["pride_skins"])
    async def view_skins_pride(self, ctx):
        """PUBLIC: View Pride 2022 Skins"""
        pages = []
        SERVER_BASE_PRIDE_SKIN = "https://mewbot.xyz/sprites/skins/pride2022/"
        PRIDE_BASE = "/home/dylee/clustered/shared/duel/sprites/skins/pride2022/"
        pages = []
        skins = list(pathlib.Path(PRIDE_BASE).glob("*-*-.png"))
        total = len(skins)
        for idx, path in enumerate(skins, 1):
            pokeid = int(path.name.split("-")[0])
            pokename = (await ctx.bot.db[1].forms.find_one({"pokemon_id": pokeid}))[
                "identifier"
            ]
            embed = discord.Embed(
                title=f"{pokename} - PRIDE EVENT 2022 ",
                color=0xDD22DD,
            )
            embed.set_image(url=SERVER_BASE_PRIDE_SKIN + path.name)
            embed.set_footer(text=f"Page {idx}/{total}")
            pages.append(embed)
        await MenuView(ctx, pages).start()

    @commands.hybrid_command(aliases=["skins"])
    async def view_skins(self, ctx, *, skin_name=None):
        """PUBLIC: View ALL Skins (not functional currently)"""
        pages = []
        skins = list(pathlib.Path(SKIN_BASE).glob("*-*-.png"))
        if skin_name is not None:
            skins = [x for x in skins if x.name.split("_")[1][:-4] == skin_name]
        total = len(skins)
        for idx, path in enumerate(skins, 1):
            # skin = path.name.split("_")[1][:-4]
            pokeid = int(path.name.split("-")[0])
            pokename = (await ctx.bot.db[1].forms.find_one({"pokemon_id": pokeid}))[
                "identifier"
            ]
            embed = discord.Embed(
                title=f"{pokename} - {skin}",
                color=0xDD22DD,
            )
            embed.set_image(url=IMG_SERVER_BASE_SKIN + path.name)
            embed.set_footer(text=f"Page {idx}/{total}")
            pages.append(embed)
        await MenuView(ctx, pages).start()

    @commands.hybrid_command(aliases=["radiants"])
    async def view_rads(self, ctx):
        """PUBLIC: View All released radiants"""
        pages = []
        skins = list(pathlib.Path(RAD_BASE).glob("*-*-.png"))
        total = len(skins)
        for idx, path in enumerate(skins, 1):
            pokeid = int(path.name.split("-")[0])
            pokename = (await ctx.bot.db[1].forms.find_one({"pokemon_id": pokeid}))[
                "identifier"
            ]
            embed = discord.Embed(
                title=f"{pokename}",
                color=0xDD22DD,
            )
            embed.set_image(url=IMG_SERVER_BASE_RAD + path.name)
            embed.set_footer(text=f"Page {idx}/{total}")
            pages.append(embed)
        await MenuView(ctx, pages).start()


async def setup(bot):
    await bot.add_cog(Sky(bot))
