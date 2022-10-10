from typing import Optional
import os
import aiohttp
from discord.ext import commands, tasks
import discord
from discord import app_commands
from utils.checks import check_admin
import discordlists
from botlistpy import BotClient
from botlistpy.helpers import AutoPoster

client_id = 1000125868938633297
api_token = {os.environ['BOTLISTME']}
botlist_client = BotClient(client_id,api_token)

class BotList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = discordlists.Client(self.bot)  # Create a Client instance
        self.api.set_auth("discordz.gg", f"{os.environ['DISCORDZGG']}") # Set authorisation token for a bot list
        self.api.set_auth("fateslist.xyz", f"{os.environ['FATESLIST']}")
        self.api.set_auth("top.gg", f"{os.environ['TOPGG']}") # Set authorisation token for a bot list
        self.api.start_loop()  # Posts the server count automatically every 30 minutes
        poster = AutoPoster(botlist_client,bot,interval=360)
        

    async def _guild_count(self) -> Optional[int]:
        """Handle clustering (this code was made by flame and was just made a function). If this returns None, ignore the whole guild count post"""
        launcher_res = await self.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return None  # Ignore this round
        processes = len(launcher_res[0])
        body = "return len(bot.guilds)"
        eval_res = await self.bot.handler(
            "_eval",
            processes,
            args={"body": body, "cluster_id": "-1"},
            scope="bot",
            _timeout=5,
        )
        return (
            sum(
                int(response["message"]) for response in eval_res if response["message"]
            )
            if eval_res
            else None
        )

    async def _shard_count(self) -> Optional[int]:
        """Return shard count. In case clustering solution changes, you can just change this"""
        return self.bot.shard_count

    async def _botblock_poster(self):
        if self.bot.user.id != 1000125868938633297:
            return False, "Not running on DittoBOT"
        guild_count = await self._guild_count()
        if not guild_count:
            return False, "Failed to get guild count"  # Wait

        shard_count = await self._shard_count()
        if not shard_count:
            return False, "Failed to get shard count"  # Wait

        botblock_base_json = {
            "bot_id": str(self.bot.user.id),
            "server_count": guild_count,
            "shard_count": shard_count,
        }
        botblock_json = {
            **botblock_base_json,
            **botlist_tokens,
        }  # Copy all botlist tokens to botblack base JSON
        self.bot.logger.debug(
            f"Posting botblock stats with JSON {botblock_base_json} and full JSON of {botblock_json}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(self.botblock_url, json=botblock_json) as res:
                response = await res.json()
                if res.status != 200:
                    msg = f"Got a non 200 status code trying to post to BotBlock.\n\nResponse: {response}\n\nStatus: {res.status}"
                    #if res.ratelimit_reset:
                       # msg += f"\n<t:{res.ratelimit_reset}:R>"
                    self.bot.logger.warn(msg)
                    return False, msg
                self.bot.logger.info(
                    "SUCCESS: Successfully posted to BotBlock. Should be propogating to all lists now"
                )
                return True, response

    @tasks.loop(seconds=60 * 45)
    async def botblock(self):
        await self.bot.wait_until_clusters_ready()
        await self._botblock_poster()
        servercount = self._guild_count()
        shardcount = self._shard_count()
        await botlist_client.setStats(servercount, shardcount)

    @check_admin()
    @commands.hybrid_group(name="botblock")
    @discord.app_commands.default_permissions(administrator=True)
    async def botblock(self, ctx):
        await ctx_send("Affirmative.")
        """Botblock Top-Level group command"""

    @check_admin()
    @botblock.command()
    @discord.app_commands.default_permissions(administrator=True)
    async def embed_gen(self, ctx: commands.Context):
        img = await botlist_client.generate_embed()
        with open("embed.png","wb") as f:
            f.write(img)
        await ctx.send(file=discord.File(img))

    @check_admin()
    @botblock.command()
    @discord.app_commands.default_permissions(administrator=True)
    async def poststats(self, ctx: commands.Context):
        """
        Manually posts guild count using BotBlock
        """
        try:
            result = await self.api.post_count()
        except Exception as e:
            await ctx.send("Request failed: `{}`".format(e))
            return
        poster = AutoPoster(botlist_client,bot,interval=360)
        await poster.start()
        await ctx.send("Successfully manually posted server count ({:,}) to {:,} lists."
                       "\nFailed to post server count to {:,} lists.".format(self.api.server_count,
                                                                             len(result["success"].keys()),
                                                                             len(result["failure"].keys())))

    @check_admin()
    @botblock.command()
    @discord.app_commands.default_permissions(administrator=True)
    async def get(self, ctx: commands.Context, bot_id: int = None):
        """
        Gets a bot using BotBlock
        """
        if bot_id is None:
            bot_id = self.bot.user.id
        try:
            result = (await self.api.get_bot_info(bot_id))[1]
        except Exception as e:
            await ctx.send("Request failed: `{}`".format(e))
            return

        await ctx.send("Bot: {}{} ({})\nOwners: {}\nServer Count: {}".format(
            result['username'], result['discriminator'], result['id'],
            ", ".join(result['owners']) if result['owners'] else "Unknown",
            "{:,}".format(result['server_count']) if result['server_count'] else "Unknown"
        ))


async def setup(bot):
    await bot.add_cog(BotList(bot))


