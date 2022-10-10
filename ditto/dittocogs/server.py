import discord
from discord.ext import commands
from utils.misc import MenuView, pagify

from dittocogs.json_files import *


def default_factory():
    return {
        "prefix": ";",
        "disabled_channels": [],
        "redirects": [],
        "disabled_spawn_channels": [],
        "pin_spawns": False,
        "delete_spawns": False,
        "small_images": False,
        "silence_levels": False,
    }


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_current(self, ctx):
        current_setting = await ctx.bot.mongo_find("guilds", {"id": ctx.guild.id})
        if not current_setting:
            current_setting = default_factory()
            current_setting["id"] = ctx.guild.id
            await ctx.bot.mongo_update("guilds", {"id": ctx.guild.id}, current_setting)
        return current_setting

    # @commands.hybrid_command()
    # @commands.has_permissions(manage_messages=True)
    async def prefix(self, ctx, val):
        """
        Changes bot prefix server-wide.

        Ex. `;prefix !`
        """

        # Discord auto-strips the sides of messages of whitespace, prevent impossible prefixes.
        val = val.lstrip()
        if not val:
            await ctx.send("That isF not a valid prefix!")
            return
        await ctx.bot.mongo_update("guilds", {"id": ctx.guild.id}, {"prefix": val})
        await ctx.send(f"Prefix has been set to {val}")
        await ctx.bot.load_guild_settings()

    @commands.hybrid_group(name="auto")
    async def auto_cmds(self, ctx):
        """Top layer of group"""

    @auto_cmds.command()
    async def delete(self, ctx):
        """
        Deletes the spawn image when you catch a Pokemon.

        Ex. `;auto delete spawns #channel`
        """
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        current_setting = await self.get_current(ctx)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"delete_spawns": not current_setting["delete_spawns"]},
        )
        await ctx.send(
            f"Spawns will {'not be deleted' if current_setting['delete_spawns'] else 'be deleted'} in all channels"
        )

    @auto_cmds.command()
    async def pin(self, ctx):
        """
        Automatically pins rare spawns.

        Ex. `;auto pin spawns #channel`
        """
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        current_setting = await self.get_current(ctx)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"pin_spawns": not current_setting["pin_spawns"]},
        )
        await ctx.send(
            f"Rare Spawns will {'not be pinned' if current_setting['pin_spawns'] else 'be pinned'} in all channels"
        )

    @commands.hybrid_group()
    async def redirect(self, ctx):
        ...

    @redirect.command()
    async def add(self, ctx, channel: discord.TextChannel = None):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        if not channel:
            channel = ctx.channel
        current_setting = await self.get_current(ctx)
        channels = set(current_setting["redirects"])
        channels.add(channel.id)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"redirects": list(channels)},
        )
        await ctx.send(f"Successfully added {channel} to the spawn redirects list.")

    @redirect.command()
    async def remove(self, ctx, channel: discord.TextChannel = None):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        if not channel:
            channel = ctx.channel
        current_setting = await self.get_current(ctx)
        channels = set(current_setting["redirects"])
        if channel.id not in channels:
            await ctx.send(
                "That channel is not in the redirect list! Use `/redirect clear` to clear all redirects."
            )
            return
        channels.remove(channel.id)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"redirects": list(channels)},
        )
        await ctx.send(f"Successfully removed {channel} from the spawn redirects list.")

    @redirect.command()
    async def clear(self, ctx):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        await self.get_current(ctx)
        await ctx.bot.mongo_update("guilds", {"id": ctx.guild.id}, {"redirects": []})
        await ctx.send("All spawn redirects were removed.")

    @commands.hybrid_group(name="commands")
    async def command(self, ctx):
        ...

    @command.command()
    async def disable(self, ctx, channel: discord.TextChannel = None):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        if not channel:
            channel = ctx.channel
        current_setting = await self.get_current(ctx)
        disabled = set(current_setting["disabled_channels"])
        if channel.id in disabled:
            await ctx.send(f"Commands are already disabled in {channel}.")
            return
        disabled.add(channel.id)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"disabled_channels": list(disabled)},
        )
        await ctx.send(f"Successfully disabled commands in {channel}.")
        await ctx.bot.load_bans()

    @command.command()
    async def enable(self, ctx, channel: discord.TextChannel = None):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        if not channel:
            channel = ctx.channel
        current_setting = await self.get_current(ctx)
        if channel.id not in current_setting["disabled_channels"]:
            await ctx.send(f"{channel} is already enabled.")
            return
        disabled = set(current_setting["disabled_channels"])
        disabled.remove(channel.id)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"disabled_channels": list(disabled)},
        )
        await ctx.send(f"Successfully enabled commands in {channel}.")
        await ctx.bot.load_bans()

    @commands.hybrid_group()
    async def spawns(self, ctx):
        ...

    @spawns.command()
    async def modalview(self, ctx):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return

        guild = await self.bot.mongo_find("guilds", {"id": ctx.guild.id})

        if not guild:
            await ctx.send(
                "This server is not in the database. Please use `;setup` to set up the bot."
            )
            return

        if not guild.get("modal_view"):
            await self.bot.mongo_update(
                "guilds", {"id": ctx.guild.id}, {"modal_view": True}
            )
            await ctx.send("Modal view is now enabled for this server.")
        else:
            await self.bot.mongo_update(
                "guilds", {"id": ctx.guild.id}, {"modal_view": False}
            )
            await ctx.send("Modal view is now disabled for this server.")

        return

    @spawns.command()
    async def disable(self, ctx, channel: discord.TextChannel = None):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        if not channel:
            channel = ctx.channel
        current_setting = await self.get_current(ctx)
        disabled = set(current_setting["disabled_spawn_channels"])
        if channel.id in disabled:
            await ctx.send(f"Spawns are already disabled in {channel}.")
            return
        disabled.add(channel.id)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"disabled_spawn_channels": list(disabled)},
        )
        await ctx.bot.load_bans()
        await ctx.send(f"Successfully disabled spawns in {channel}.")

    @spawns.command()
    async def enable(self, ctx, channel: discord.TextChannel = None):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        if not channel:
            channel = ctx.channel
        current_setting = await self.get_current(ctx)
        if channel.id not in current_setting["disabled_spawn_channels"]:
            await ctx.send(f"Spawns are already enabled in {channel}.")
            return
        disabled = set(current_setting["disabled_spawn_channels"])
        disabled.remove(channel.id)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"disabled_spawn_channels": list(disabled)},
        )
        await ctx.bot.load_bans()
        await ctx.send(f"Successfully enabled spawns in {channel}.")

    @spawns.command()
    async def small(self, ctx):
        """Toggle smaller spawn embeds in this guild."""
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        current_setting = await self.get_current(ctx)
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"small_images": not current_setting["small_images"]},
        )
        await ctx.send(
            f"Spawn messages will now be {'normal sized' if current_setting['small_images'] else 'small'} in this server."
        )

    @spawns.command()
    async def check(self, ctx):
        """Check spawn status for channels in this guild."""
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        current_setting = await self.get_current(ctx)
        disabled_channels = current_setting["disabled_spawn_channels"]
        redirect_channels = current_setting["redirects"]
        any_redirects = bool(redirect_channels)
        msg = ""
        for channel in ctx.guild.text_channels:
            name = channel.name
            if len(name) > 22:
                name = f"{name[:19]}..."
            name = name.ljust(22)
            perms = channel.permissions_for(ctx.guild.me)
            read = perms.read_messages
            send = perms.send_messages
            embeds = perms.embed_links
            enabled = channel.id not in disabled_channels
            redirect = channel.id in redirect_channels
            if not (read and send and embeds and enabled):
                spawns = "\N{CROSS MARK}"
            elif any_redirects and not redirect:
                spawns = "\N{RIGHTWARDS ARROW WITH HOOK}\N{VARIATION SELECTOR-16}"
            else:
                spawns = "\N{WHITE HEAVY CHECK MARK}"
            read = "\N{WHITE HEAVY CHECK MARK}" if read else "\N{CROSS MARK}"
            send = "\N{WHITE HEAVY CHECK MARK}" if send else "\N{CROSS MARK}"
            embeds = "\N{WHITE HEAVY CHECK MARK}" if embeds else "\N{CROSS MARK}"
            enabled = "\N{WHITE HEAVY CHECK MARK}" if enabled else "\N{CROSS MARK}"
            msg += f"{name}|  {spawns}  ||  {read}   |  {send} |  {embeds}   |  {enabled}\n"
        embed = discord.Embed(
            title="Spawn Checker", colour=random.choice(ctx.bot.colors)
        )
        pages = pagify(msg, per_page=25, base_embed=embed)
        for page in pages:
            page.description = f"```\nName                  | Spawn || Read  | Send | Embed |Enable\n{page.description}```"
        await MenuView(ctx, pages).start()

    @commands.hybrid_command()
    async def silenceserver(self, ctx):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send(
                "You are not allowed to manage this setting. You need to have `manage_messages` permission to do so."
            )
            return
        current_setting = await self.get_current(ctx)
        state = not current_setting["silence_levels"]
        await ctx.bot.mongo_update(
            "guilds",
            {"id": ctx.guild.id},
            {"silence_levels": state},
        )
        state = "off" if state else "on"
        await ctx.send(
            f"Successfully toggled {state} level up messages in this server!"
        )


async def setup(bot):
    await bot.add_cog(Settings(bot))
