import concurrent
import contextlib
import random
import time
import traceback
from collections import defaultdict
from discord import app_commands
from discord.ui import Modal, TextInput
import discord
from discord.ext import commands
from pokemon_utils.utils import evolve

GUILD_DEFAULT = {
    "prefix": ";",
    "disabled_channels": [],
    "redirects": [],
    "disabled_spawn_channels": [],
    "pin_spawns": False,
    "delete_spawns": False,
    "small_images": False,
    "silence_levels": False,
}

class Feedback(discord.ui.Modal, title='Feedback'):
        # Our modal classes MUST subclass `discord.ui.Modal`,
        # but the title can be whatever you want.

        # This will be a short input, where the user can enter their name
        # It will also have a placeholder, as denoted by the `placeholder` kwarg.
        # By default, it is required and is a short-style input which is exactly
        # what we want.
        name = discord.ui.TextInput(
            label='Short Description',
            placeholder='Short Description',
        )

        feedback = discord.ui.TextInput(
            label='Constructive feedback only please',
            style=discord.TextStyle.long,
            placeholder='Type your feedback here...',
            required=True,
            max_length=1000,
        )

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.send_message(f'Thanks for your feedback, {interaction.user.name}! Anyone who abuses this system will be botbanned.', ephemeral=True)
            embed = discord.Embed(
                    title="Feedback Submission", description=f"{interaction.user.id}-{interaction.user.name} submitted:\n\nShort Description:\n **{self.name.value}**\n\nFeedback:\n **{self.feedback.value}**", color=16758465)
            await interaction.client.get_partial_messageable(1004310910313181325).send(embed=embed)




class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # This might be better in Redis, but eh if someone wants to get .01% better rates by spam switching channels, let them
        self.user_cache = defaultdict(int)


    @app_commands.command()
    async def feedback(self, interaction: discord.Interaction):
        """Command to provide constructive feedback directly to our team from your server."""
        await interaction.response.send_modal(Feedback())

    @commands.hybrid_command()
    async def slashinvite(self, ctx):
        """Command to allow users to reinvite the bot w/ slash command perms."""
        await ctx.send(
            "If you cannot see slash commands, kick me and reinvite me with the following invite link:\n"
            "<https://discordapp.com/api/oauth2/authorize?client_id=1000125868938633297&permissions=387136&scope=bot+applications.commands>"
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.bot.wait_until_ready()
        if not message.guild or not message.guild.me:
            return
        if message.author.bot:
            return
        if self.bot.botbanned(message.author.id):
            return
        if message.guild.id in (264445053596991498, 446425626988249089):
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if not message.channel.permissions_for(message.guild.me).embed_links:
            return

        if message.channel.id == 1004266790949486724:
            #
            user = await self.bot.mongo_find(
                "users",
                {"user": message.author.id},
                default={"user": message.author.id, "progress": {}},
            )
            progress = user["progress"]
            progress["chat-general"] = progress.get("chat-general", 0) + 1
            await self.bot.mongo_update(
                "users", {"user": message.author.id}, {"progress": progress}
            )
            #
        if time.time() < self.user_cache[message.author.id]:
            return
        self.user_cache[message.author.id] = time.time() + 5
        async with self.bot.db[0].acquire() as pconn:
            try:
                if (
                    await pconn.fetchval(
                        "SELECT true FROM users WHERE u_id = $1", message.author.id
                    )
                    is None
                ):
                    return
                (
                    hatched_party_pokemon,
                    hatched_pokemon,
                    level_pokemon,
                ) = await pconn.fetchrow(
                    "SELECT party_counter($1), selected_counter($1), level_pokemon($1)",
                    message.author.id,
                )
            except Exception:
                return
            response = ""
            if hatched_party_pokemon:
                for egg_name in hatched_party_pokemon:
                    #
                    user = await self.bot.mongo_find(
                        "users",
                        {"user": message.author.id},
                        default={"user": message.author.id, "progress": {}},
                    )
                    progress = user["progress"]
                    progress["hatch"] = progress.get("hatch", 0) + 1
                    await self.bot.mongo_update(
                        "users", {"user": message.author.id}, {"progress": progress}
                    )
                    #
                    response += f"Congratulations!\nYour {egg_name} Egg has hatched!\n"
                    chest_chance = not random.randint(0, 200)
                    if chest_chance:
                        inventory = await pconn.fetchval(
                            "SELECT inventory::json FROM users WHERE u_id = $1",
                            message.author.id,
                        )
                        item = "common chest"
                        inventory[item] = inventory.get(item, 0) + 1
                        await pconn.execute(
                            "UPDATE users SET inventory = $1::json where u_id = $2",
                            inventory,
                            message.author.id,
                        )
                        response += "It was holding a common chest!\n"
            if hatched_pokemon:
                #
                user = await self.bot.mongo_find(
                    "users",
                    {"user": message.author.id},
                    default={"user": message.author.id, "progress": {}},
                )
                progress = user["progress"]
                progress["hatch"] = progress.get("hatch", 0) + 1
                await self.bot.mongo_update(
                    "users", {"user": message.author.id}, {"progress": progress}
                )
                #
                response += (
                    f"Congratulations!\nYour {hatched_pokemon} Egg has hatched!\n"
                )
                chest_chance = not random.randint(0, 200)
                if chest_chance:
                    inventory = await pconn.fetchval(
                        "SELECT inventory::json FROM users WHERE u_id = $1",
                        message.author.id,
                    )
                    item = "common chest"
                    inventory[item] = inventory.get(item, 0) + 1
                    await pconn.execute(
                        "UPDATE users SET inventory = $1::json where u_id = $2",
                        inventory,
                        message.author.id,
                    )
                    response += "It was holding a common chest!\n"
            if level_pokemon:
                pokemon_details = await pconn.fetchrow(
                    "SELECT users.silenced, pokes.* FROM users INNER JOIN pokes on pokes.id = (SELECT selected FROM users WHERE u_id = $1) AND users.u_id = $1",
                    message.author.id,
                )
                silenced = pokemon_details.get("silenced")
                guild_details = await self.bot.db[1].guilds.find_one(
                    {"id": message.guild.id}
                )
                if guild_details:
                    silenced = silenced or guild_details["silence_levels"]
                if not silenced:
                    response += f"{message.author.mention} Your {level_pokemon} has leveled up!\n"
                try:
                    await evolve(
                        self.bot,
                        pokemon_details,
                        message.author,
                        channel=message.channel,
                    )
                except Exception as e:
                    self.bot.logger.exception("Error in evolve", exc_info=e)
            if response:
                with contextlib.suppress(discord.HTTPException):
                    await message.channel.send(
                        embed=discord.Embed(description=response, color=0xFF49E6)
                    )
                return

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if self.bot.user.id != 1000125868938633297:
            return
        guild_data = GUILD_DEFAULT.copy()
        guild_data["id"] = guild.id
        await self.bot.db[1].guilds.insert_one(guild_data)
        owner = await self.bot.fetch_user(guild.owner_id)
        guild_name = guild.name
        owner_id = owner.id
        owner_name = owner.name
        member_count = "??"
        e = discord.Embed(
            title="Thank you for adding me to your server!!", color=0xEDD5ED
        )
        e.add_field(
            name="Tutorial",
            value="Get a tutorial of how to use DittoBOT by using `/tutorial`.",
        )
        e.add_field(
            name="Manage Spawns",
            value="Manage spawns in your server by using `/spawns disable` to disable spawns in a channel, or `/spawns redirect` to redirect spawns to a specific channel.",
        )
        e.add_field(
            name="Help",
            value="If you need any more help, join the official server with the link in `/invite` and ask for help in #questions!",
        )
        with contextlib.suppress(Exception):
            await owner.send(embed=(e))
        await self.bot.log(
            1004571626366587022,
            f"**New Join:**\n**Server Name** = `{guild_name}`\n**Ownerid id** = `{owner_id}`\n**Owner name** = `{owner_name}`\n**Members** = `{member_count}`",
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if self.bot.user.id == 1000125868938633297:
            await self.bot.db[1].guilds.delete_one({"id": guild.id})

    @commands.hybrid_command()
    async def donate(self, ctx):
        name = ctx.author.name
        if " " in name:
            name = name.replace(" ", "")
        e = discord.Embed(title="Donate to the Bot Here!", color=0xFFB6C1)
        donation_url = f"https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=sky@pokepla.net&lc=US&item_name=DittoBOT-Donation-from-{ctx.author.id}&no_note=1&no_shipping=1&rm=1&currency_code=USD&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted&custom={ctx.author.id}&notify_url=http://37.187.250.140:15211/paypal"

        payload = {"user_name": ctx.author.name, "user_id": ctx.author.id}
       
        e.add_field(name="Donation Link", value=f"[Donate Here!]({donation_url})\n")
        e.add_field(
            name="Patreon",
            value=f"**[Become a Patreon and benefit from some awesome rewards.](https://www.patreon.com/mewbotofficial?fan_landing=true)**\n*Patreon is not the same as standard donations, and has totally unique benefits and rewards-see the link above for information on the tiers available.",
            inline=False,
        )
        e.set_footer(
            text="You will receive 3 Redeems + 2,000 credits for every USD donated."
        )
        await ctx.send(embed=e)

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        self.bot.logger.error(
            "Error in event or general bot (found in on_error)", exc_info=True
        )

    @commands.Cog.listener()
    async def on_command(self, ctx):
        # await ctx.bot.cmds_file.write(f"Command used => {ctx.command} - User -> {ctx.author.name}({ctx.author.id})\n")
        # await ctx.bot.cmds_file.flush()
        ctx.bot.commands_used[ctx.command.name] = (
            ctx.bot.commands_used.get(ctx.command.name, 0) + 1
        )

        if ctx.command.cog_name in {"Mod", "Gymauth", "Investigator", "Admin"}:
            await ctx.bot.log(
                1004571779886501969,
                f"{ctx.author.name} - {ctx.author.id} used {ctx.command.name} command\nArguments - {ctx.args}\n{ctx.kwargs}",
            )
        if ctx.command.cog_name == "Settings":
            await self.bot.load_guild_settings()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # TODO: This listener overrides the default command error handler.
        # While that is fine right now, since exceptions are re-raised (as an exception in this listener)
        # when they are unhandled, in the future error handling currently covered by this listener
        # should be a part of the code causing that error. Once that is done, this listener should probably
        # be removed or swapped to have better handling.
        ignored_errors = (
            commands.errors.CommandNotFound,
            commands.errors.MissingPermissions,
            concurrent.futures._base.TimeoutError,
            commands.CheckFailure,
            commands.DisabledCommand,
            commands.MaxConcurrencyReached,
        )
        if isinstance(error, ignored_errors):
            return
        if isinstance(error, discord.errors.Forbidden):
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.send(
                    f"I do not have Permissions to use in {ctx.channel}"
                )
            return
        if isinstance(error, commands.CommandOnCooldown):
            cooldown = f"{error.retry_after:.2f}s"
            with contextlib.suppress(Exception):
                await ctx.channel.send(f"Command on cooldown for {cooldown}")
            return
        help_errors = (
            commands.errors.MissingRequiredArgument,
            commands.errors.BadArgument,
        )
        if isinstance(error, help_errors):
            command = ctx.command
            try:
                await ctx.send(
                    f"That command doesn't look quite right...\n"
                    f"Syntax: `{ctx.prefix}{command.qualified_name} {command.signature}`\n\n"
                )
            except:
                pass
            return
        if isinstance(error, commands.errors.CommandInvokeError):
            # This should get the actual error behind the CommandInvokeError
            error = error.__cause__ or error
            if "TimeoutError" in str(error) or "Forbidden" in str(error):
                return
            if ctx.command.cog_name in ("battle", "duel"):
                try:
                    await ctx.send(
                        "Please make sure you have selected a Pokemon, no eggs are in your party, your party is full, and the same for your opponent"
                    )
                except:
                    pass
                return
            #if ctx.command.qualified_name == None
                #ctx.command.qualified_name = "ERROR GETTING COMMAND NAME"
            ctx.bot.traceback = (
                f"Exception in command '{ctx.command.qualified_name}'\n"
                + "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
            )
        # Since this overrides the default command listener, this raise sends this error to the
        # listener error handler as an exception in the "on_command_error" listener so it can be
        # printed to console.
        ctx.bot.logger.exception(type(error).__name__, exc_info=error)
        await ctx.bot.misc.log_error(ctx, error)


async def setup(bot):
    await bot.add_cog(Misc(bot))
