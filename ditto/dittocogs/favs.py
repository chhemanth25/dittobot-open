import asyncio

from discord.ext import commands


class Favs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="fav")
    async def fav_cmds(self, ctx):
        """Top layer of group"""

    @fav_cmds.command()
    async def list(self, ctx):
        await ctx.send(
            "This command is deprecated, you should use `/f p args:fav` instead. "
            "It has the same functionality, but with a fresh output and the ability to use additional filters.\n"
            "Running that for you now..."
        )
        await asyncio.sleep(3)
        c = ctx.bot.get_cog("Filter")
        if c is None:
            return
        await c.filter_pokemon.callback(c, ctx, args="fav")
        return

    @fav_cmds.command()
    async def add(self, ctx, poke: int = None):
        async with ctx.bot.db[0].acquire() as pconn:
            if poke is None:
                _id = await pconn.fetchval(
                    "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
                )
            else:
                if poke < 1:
                    await ctx.send("You don't have that Pokemon")
                    return
                _id = await pconn.fetchval(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2",
                    poke,
                    ctx.author.id,
                )
            name = await pconn.fetchval("SELECT pokname FROM pokes WHERE id = $1", _id)
            if name is None:
                await ctx.send("You don't have that Pokemon")
                return
            await pconn.execute("UPDATE pokes SET fav = $1 WHERE id = $2", True, _id)
            await ctx.send(
                f"You have successfully added your {name} to your favourite pokemon list!"
            )

    @fav_cmds.command()
    async def remove(self, ctx, poke: int = None):
        async with ctx.bot.db[0].acquire() as pconn:
            if poke is None:
                _id = await pconn.fetchval(
                    "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
                )
            else:
                if poke < 1:
                    await ctx.send("You don't have that Pokemon")
                    return
                _id = await pconn.fetchval(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2",
                    poke,
                    ctx.author.id,
                )
            name = await pconn.fetchval("SELECT pokname FROM pokes WHERE id = $1", _id)
            if name is None:
                await ctx.send("You don't have that Pokemon")
                return
            await pconn.execute("UPDATE pokes SET fav = $1 WHERE id = $2", False, _id)
            await ctx.send(
                f"You have successfully removed your {name} from your favourite pokemon list!"
            )


async def setup(bot):
    await bot.add_cog(Favs(bot))
