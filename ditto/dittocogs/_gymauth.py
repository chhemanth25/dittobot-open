from discord import app_commands

import discord
from discord.ext import commands
from utils.checks import check_gymauth

GREEN = "\N{LARGE GREEN CIRCLE}"
YELLOW = "\N{LARGE YELLOW CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"

OS = discord.Object(id=999953429751414784)
OSGYMS = discord.Object(id=857746524259483679)
OSAUCTIONS = discord.Object(id=857745448717516830)
VK_SERVER = discord.Object(id=829791746221277244)


class Gymauth(commands.Cog):
    def __init__(self, bot: commands) -> None:
        self.bot: commands.Bot = bot

    @check_gymauth()
    @commands.hybrid_group(name="gym")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(administrator=True)
    async def _gym(self, ctx):
        """Gym Authority Top-Level group command"""
        # await ctx.send("Affirmative.")

    @check_gymauth()
    @_gym.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def addev(self, ctx, userid: discord.User, evs: int):
        """GYM: Add evs to a user by their ID"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET evpoints = evpoints + $1 WHERE u_id = $2",
                evs,
                userid.id,
            )
        await ctx.send("Successfully added Effort Value points to user")

    @check_gymauth()
    @app_commands.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @app_commands.choices(
        credits=[
            app_commands.Choice(name="All Gyms Cleared", value=300000),
            app_commands.Choice(name="Masters Challenge Cleared", value=750000),
        ]
    )
    async def gym_reward(
        self,
        interaction: discord.Interaction,
        credits: app_commands.Choice[int],
        user: discord.User,
    ):
        """GYM: Gym credits Reward"""
        await interaction.response.defer()
        if app_commands.Choice == "All Gyms Cleared":
            async with interaction.client.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    credits.value,
                    user.id,
                )
                await interaction.client.get_partial_messageable(
                    1004572558655508540
                ).send(
                    f"<:err:997377264511623269> **Gym Authority** - {interaction.author}:\nAwarded {user.name}({user.id}) with {credits.value} for beating **all of the island gym challenges**."
                )
                await interaction.followup.send(
                    f"<@{user.id}> has chosen the {credits.name} option which soon will give {credits.value} credits but....\nThis does not currently do anything but goodjob.\n"
                )
        else:
            async with interaction.client.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    credits.value,
                    user.id,
                )
                await interaction.client.get_partial_messageable(
                    1004572558655508540
                ).send(
                    f"<:err:997377264511623269> **Gym Authority** - {interaction.author}:\nAwarded {user.name} with {credits.value} for beating the **masters challenge**"
                )
                await interaction.followup.send(
                    f"<@{user.id}> has been awarded {credits.value} for a gym challenge.\n"
                )

    @check_gymauth()
    @_gym.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def duelblock(self, ctx, id: discord.User):
        """GYM: Ban a user from duels"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE botbans SET duelban = array_append(duelban, $1)", id.id
            )
            await ctx.send(
                f"```Elm\n- Successflly Duelbanned {await ctx.bot.fetch_user(id.id)}```"
            )

    @check_gymauth()
    @_gym.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def unduelblock(self, ctx, id: discord.User):
        """GYM: UNBan a user from duels"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE botbans SET duelban = array_remove(duelban, $1)", id.id
            )
            await ctx.send(
                f"```Elm\n- Successfully unduelbanned {await ctx.bot.fetch_user(id.id)}```"
            )

    @check_gymauth()
    @_gym.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def tradable(self, ctx, pokeid: int, answer: bool):
        """GYM: Set pokemon trade-able or not"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET tradable = $1 WHERE id = $2",
                answer,
                pokeid,
            )
        await ctx.send(f"Successfully set trade-able to {answer}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Gymauth(bot))
