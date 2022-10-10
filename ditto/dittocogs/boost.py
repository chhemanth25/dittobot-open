import asyncio
import discord
import random

from discord.ui import Modal, TextInput
from discord.ext import commands
from discord import app_commands

from utils.misc import ConfirmView, ListSelectView2
from utils.checks import check_admin, check_owner, check_helper


class Boost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.NITRO_RWDS = (
            "Rare chest - x1",
            "Battle/shiny multi - x5 Breed/IV multi - x3",
            "Credits - 150,000 + Redeems - x3",
            "(Temp.) Redeems - x6",
            "(Temp.) Shadow Chain Boost (up to +40)",
            "(???) Mystery Token (currently no use)"
        )
        

    async def initialize(self):
        await self.bot.redis_manager.redis.execute("LPUSH", "nitrorace", "123")

    @commands.hybrid_group()
    async def nitro(self, _):
        ...
    
    
    @nitro.command()
    async def claim(self, ctx):
        """Command for Claiming Nitro Boost rewards."""
        if ctx.guild.id != 999953429751414784:
            await ctx.send(f"You can only use this command in the {self.bot.user.name} Official Server.")
            return
        if 1004342763803914261 not in [x.id for x in ctx.author.roles]:
            await ctx.send("You can only use this command if you have nitro boosted this server.")
            return
        boosters = (await ctx.bot.db[1].boosters.find_one())["boosters"]
        in_process = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "nitrorace", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if ctx.author.id in boosters:
            await ctx.send("You have already claimed Nitro Boost!")
            await self.bot.redis_manager.redis.execute("LREM", "nitrorace", "1", str(ctx.author.id))
            return
        if ctx.author.id in in_process:
            await ctx.send("You are already in the process of claiming your Nitro Boost!")
            return
        await self.bot.redis_manager.redis.execute("LPUSH", "nitrorace", str(ctx.author.id))
        async with ctx.bot.db[0].acquire() as pconn:
            u_id = await pconn.fetchval("SELECT u_id FROM users WHERE u_id = $1", ctx.author.id)
        if u_id is None:
            await ctx.send(f"You have not Started!\nStart with `/start` first!")
            await self.bot.redis_manager.redis.execute("LREM", "nitrorace", "1", str(ctx.author.id))
            return

        # Choosing reward finally
        choice = ""
        # choice = int(choice.content)
        
        options = list(self.NITRO_RWDS)
        if not options:
            await ctx.send("Nitro Rewards are currently Disabled, try again at another time.")
            await self.bot.redis_manager.redis.execute("LREM", "nitrorace", "1", str(ctx.author.id))
            return
        choice, context = await ListSelectView2(ctx,
                                               "Which reward would you like for boosting the server?\nOptions marked with (Temp.) are temporary and will only be available for a limited time!\nMystery Tokens do not expire, but currently have no use. <3",
                                               options).wait()
        if choice is None:
            await ctx.send(
                "You did not select in time, cancelling.\n**Please try the command again when you are ready to choose.**")
            await self.bot.redis_manager.redis.execute("LPUSH", "nitrorace", str(ctx.author.id))
            return
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if inventory is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                await self.bot.redis_manager.redis.execute("LREM", "nitrorace", "1", str(ctx.author.id))
                return
            if "Rare chest - x1" in choice:
                inventory["rare chest"] = inventory.get("rare chest", 0) + 1

            elif "Battle/shiny multi - x5 Breed/IV multi - x3" in choice:
                inventory["battle-multiplier"] = min(
                    50, inventory.get("battle-multiplier", 0) + 5
                )
                inventory["shiny-multiplier"] = min(
                    50, inventory.get("shiny-multiplier", 0) + 5
                )
                inventory["iv-multiplier"] = min(
                    50, inventory.get("iv-multiplier", 0) + 3
                )
                inventory["breeding-multiplier"] = min(
                    50, inventory.get("breeding-multiplier", 0) + 3
                )

            elif "Credits - 150,000 + Redeems - x3" in choice:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + 3, mewcoins = mewcoins + 150000 WHERE u_id = $1",
                    ctx.author.id,
                )

            elif "(Temp.) Redeems - x6" in choice:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + 6 WHERE u_id = $1",
                    ctx.author.id,
                )
            
            elif "(Temp.) Shadow Chain Boost (up to +40)" in choice:
                shadow_boost = int(random.randint(1, 41))
                await pconn.execute(
                    "UPDATE users SET chain = chain + $2 WHERE u_id = $1",
                    ctx.author.id,
                    shadow_boost)
                await ctx.send(f"Your chain increased by = {shadow_boost}")
            elif "(???) Mystery Token (currently no use)" in choice:
                await pconn.execute(
                    "UPDATE users SET mystery_token = mystery_token + 1 WHERE u_id = $1",
                    ctx.author.id,
                )

            await pconn.execute(
                "UPDATE users SET inventory = $1::json WHERE u_id = $2",
                inventory,
                ctx.author.id,
            )
            
            await ctx.send(f"You chose and have been given - `{choice}`\nThank you for boosting the server!.",
                               view=None)
            await ctx.bot.db[1].boosters.update_one({}, {"$push": {"boosters": ctx.author.id}})
            await self.bot.redis_manager.redis.execute("LREM", "nitrorace", "1", str(ctx.author.id))
        
    @discord.app_commands.default_permissions(administrator=True)
    @nitro.command()
    async def rmv(self, ctx, id: int):
        """Remove a Nitro Boost from the list"""
        # Dont touch this shit if you seeing this
        if ctx.author.id not in (790722073248661525):
            await ctx.send("no")
            return
        boosters_collection = ctx.bot.db[1].boosters
        boosters = (await boosters_collection.find_one())["boosters"]
        boosters.remove(id)
        await ctx.bot.db[1].boosters.update_one(
            {"key": "boosters"}, {"$set": {"boosters": boosters}}
        )
        await ctx.send(f"Reset boost for {id}")


    @discord.app_commands.default_permissions(administrator=True)
    @nitro.command()
    async def reset(self, ctx):
        """Reset all Nitro Boosts"""
        if ctx.author.id != 790722073248661525:
            await ctx.send("no")
            return
        ctx.bot.db[1].boosters
        (await ctx.bot.db[1].boosters.find_one())["boosters"]
        await ctx.bot.db[1].boosters.update_one(
            {"key": "boosters"}, {"$set": {"boosters": []}}
        )
        await ctx.send("Reset Boosts for this month")


async def setup(bot):
    await bot.add_cog(Boost(bot))
