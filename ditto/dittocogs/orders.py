from discord.ext import commands


class Orders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="order")
    async def order_cmds(self, ctx):
        """Top layer of group"""

    @order_cmds.command()
    async def ivs(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET user_order = $1 WHERE u_id = $2", "iv", ctx.author.id
            )
        await ctx.send("Your Pokemon will now be ordered by their IVs!")

    @order_cmds.command()
    async def default(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET user_order = $1 WHERE u_id = $2", "kek", ctx.author.id
            )
        await ctx.send("Your Pokemon orders have been reset!")

    @order_cmds.command()
    async def evs(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET user_order = $1 WHERE u_id = $2", "ev", ctx.author.id
            )
        await ctx.send("Your Pokemon will now be ordered by their EVs!")

    @order_cmds.command()
    async def name(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET user_order = $1 WHERE u_id = $2",
                "name",
                ctx.author.id,
            )
        await ctx.send("Your Pokemon will now be ordered by their Names!")

    @order_cmds.command()
    async def level(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET user_order = $1 WHERE u_id = $2",
                "level",
                ctx.author.id,
            )
        await ctx.send("Your Pokemon will now be ordered by their Level!")


async def setup(bot):
    await bot.add_cog(Orders(bot))
