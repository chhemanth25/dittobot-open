from __future__ import annotations

import os
import pathlib

import discord
import psutil
from discord.ext import commands
from utils.checks import *

OS = discord.Object(id=999953429751414784)


class motz(commands.Cog):
    """Motz stuff"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.process = psutil.Process(os.getpid())

    def bytesto(self, bytes, to, bsize=1024):
        """convert bytes to megabytes, etc.
        sample code:
                print('mb= ' + str(bytesto(314575262000000, 'm')))
        sample output:
                mb= 300002347.946
        """

        a = {"k": 1, "m": 2, "g": 3, "t": 4, "p": 5, "e": 6}
        r = float(bytes)
        for _ in range(a[to]):
            r = r / bsize

        return r

    @check_admin()
    @discord.app_commands.guilds(OS)
    @commands.hybrid_command()
    async def botstats(self, ctx, ephemeral: bool = True) -> None:
        """Get some information about the bot"""
        await ctx.typing(ephemeral=ephemeral)
        fetching = await ctx.send("Fetching stats...", ephemeral=ephemeral)
        num = 0
        for guild in self.bot.guilds:
            for channel in guild.channels:
                num += 1
        discord_version = discord.__version__
        amount_of_app_cmds = await self.bot.tree.fetch_commands()
        chunked = []
        for guild in self.bot.guilds:
            if guild.chunked:
                chunked.append(guild)
        ramUsage = self.process.memory_full_info().rss / 1024**2
        intervals = (
            ("w", 604800),  # 60 * 60 * 24 * 7
            ("d", 86400),  # 60 * 60 * 24
            ("h", 3600),  # 60 * 60
            ("m", 60),
            ("s", 1),
        )

        def draw_box(usage, active, inactive):
            usage = int(usage)
            if usage < 20:
                return f"{active}{inactive * 9}"
            elif usage == 100:
                return active * 10

            activec = usage // 10
            black = 10 - activec
            return f"{active * activec}{inactive * black}"

        def commify(n):
            n = str(n)
            return n if len(n) <= 3 else f"{commify(n[:-3])},{n[-3:]}"

        def display_time(seconds, granularity=2):
            result = []

            for name, count in intervals:
                if value := seconds // count:
                    seconds -= value * count
                    if value == 1:
                        name = name.rstrip("s")
                    result.append(f"{value}{name}")
            return " ".join(result[:granularity])

        async def line_count(self):
            await ctx.channel.typing()
            total = 0
            file_amount = 0
            ENV = "env"

            for path, _, files in os.walk("."):
                for name in files:
                    file_dir = str(pathlib.PurePath(path, name))
                    # ignore env folder and not python files.
                    if not name.endswith(".py") or ENV in file_dir:
                        continue
                    if "__pycache__" in file_dir:
                        continue
                    if ".git" in file_dir:
                        continue
                    if ".local" in file_dir:
                        continue
                    if ".config" in file_dir:
                        continue
                    if "?" in file_dir:
                        continue
                    if ".cache" in file_dir:
                        continue
                    file_amount += 1
                    with open(file_dir, "r", encoding="utf-8") as file:
                        for line in file:
                            if not line.strip().startswith("#") or not line.strip():
                                total += 1
            return f"{total:,} lines, {file_amount:,} files"

        if len(chunked) == len(self.bot.guilds):
            all_chunked = "All servers are cached!"
        else:
            all_chunked = f"{len(chunked)} / {len(self.bot.guilds)} servers are cached"
        if self.bot.shard_count == 1:
            shards = "1 shard"
        else:
            shards = f"{self.bot.shard_count:,} shards"
        made = discord.utils.format_dt(self.bot.user.created_at, style="R")
        cpu = psutil.cpu_percent()
        cpu_box = draw_box(round(cpu), ":blue_square:", ":black_large_square:")
        ramlol = round(ramUsage) // 10
        ram_box = draw_box(ramlol, ":blue_square:", ":black_large_square:")
        GUILD_MODAL = f"""{len(self.bot.guilds)} Guilds are seen,\n{commify(num)} channels,\nand {commify(len(self.bot.users))} users."""
        PERFORMANCE_MODAL = f"""
        `RAM Usage: {ramUsage:.2f}MB / 1GB scale`
        {ram_box}
        `CPU Usage: {cpu}%`
        {cpu_box}"""
        BOT_INFO = f"""{all_chunked}\nLatency: {round(self.bot.latency * 1000, 2)}ms\nShard count: {shards}\nLoaded CMDs: {len([x.name for x in self.bot.commands])} and {len(amount_of_app_cmds)} slash commands\nMade: {made}\n{await line_count(self)}"""
        embed = discord.Embed(
            color=0xFFB6C1,
        )
        embed.set_thumbnail(url=self.bot.user.avatar)
        embed.add_field(
            name="Performance Overview", value=PERFORMANCE_MODAL, inline=False
        )
        embed.add_field(
            name="Guild Information",
            value=GUILD_MODAL,
            inline=False,
        )

        embed.add_field(name="Bot Information", value=BOT_INFO, inline=False)
        embed.set_footer(
            text=f"Made with ❤️. Library used: Discord.py{discord_version}"
        )
        await fetching.edit(content="Almost done...")
        await fetching.edit(
            content=f"Stats about **{self.bot.user}**",
            embed=embed,
        )

    @check_admin()
    @discord.app_commands.guilds(OS)
    @commands.hybrid_command()
    async def serverinfo(self, ctx):
        """Check info about current server"""

        def commify(n):
            n = str(n)
            return n if len(n) <= 3 else f"{commify(n[:-3])},{n[-3:]}"

        fetching = await ctx.send("Fetching info...")
        embed = discord.Embed(
            title=f"{self.bot.user.name}",
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
        )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon)
        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner)

        embed.add_field(name="Server Name", value=f"`{ctx.guild.name}`", inline=True)
        embed.add_field(name="Server ID", value=f"`{ctx.guild.id}`", inline=True)
        embed.add_field(
            name="Bots", value=f"`{len([bot for bot in ctx.guild.members if bot.bot])}`"
        )
        if len(ctx.guild.text_channels) == 69:
            embed.add_field(
                name="Text channels",
                value=f"`{len(ctx.guild.text_channels)}` Nice",
                inline=True,
            )
        else:
            embed.add_field(
                name="Text channels",
                value=f"`{len(ctx.guild.text_channels)}`",
                inline=True,
            )
        embed.add_field(
            name="Voice channels",
            value=f"`{len(ctx.guild.voice_channels)}`",
            inline=True,
        )
        embed.add_field(
            name="Server on shard", value=f"`{ctx.guild.shard_id}`", inline=True
        )
        embed.add_field(
            name="Members", value=f"`{ctx.guild.member_count}`", inline=True
        )
        if len(ctx.guild.roles) == 69:
            embed.add_field(
                name="Roles", value=(f"`{len(ctx.guild.roles)}` Nice"), inline=True
            )
        else:
            embed.add_field(
                name="Roles", value=(f"`{len(ctx.guild.roles)}`"), inline=True
            )
        embed.add_field(
            name="Emoji Count", value=f"`{len(ctx.guild.emojis)}`", inline=True
        )
        embed.add_field(
            name="Emoji Limit", value=f"`{ctx.guild.emoji_limit}` Emojis", inline=True
        )
        embed.add_field(
            name="Filesize Limit",
            value=f"`{str(self.bytesto(ctx.guild.filesize_limit, 'm'))}` mb",
        )
        embed.add_field(
            name="Bitrate Limit",
            value=f"`{str(ctx.guild.bitrate_limit / 1000).split('.', 1)[0]}` Kbps",
        )
        embed.add_field(
            name="Security Level",
            value=f"`{ctx.guild.verification_level}`",
            inline=True,
        )
        try:
            embed.add_field(
                name="Owner/ID",
                value=f"**Name**:`{ctx.guild.owner}`\n**ID**:`{ctx.guild.owner.id}`",
                inline=False,
            )
        except Exception:
            embed.add_field(
                name="Owner/ID",
                value=f"**Name**:`Unable to fetch.`\n**ID**:`Unable to fetch.`",
                inline=False,
            )
        time_guild_existed = discord.utils.utcnow() - ctx.guild.created_at
        time_created = discord.utils.format_dt(ctx.guild.created_at, style="R")
        embed.add_field(
            name="Created",
            value=f"`{ctx.guild.created_at:%b %d, %Y - %H:%M:%S}`\nThat was `{commify(time_guild_existed.days)}` days ago or {time_created}",
            inline=True,
        )
        embed.set_footer(text=f" {ctx.author}", icon_url=ctx.author.avatar)
        await fetching.edit(
            content=None,
            embed=embed,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(motz(bot))
