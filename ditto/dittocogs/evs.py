from discord.ext import commands


class Evs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="add_evs")
    async def addevs(self, ctx, amount: int, stat: str):
        stat = stat.lower()
        if stat not in {
            "attack",
            "hp",
            "defense",
            "special attack",
            "special defense",
            "speed",
        }:
            await ctx.send(
                f"Correct usage of this command is: `/add evs <amount> <stat_name>`\n"
                f"Example: `/add evs 252 speed` To add to your __Selected__ Pokemon`"
            )
            return
        if amount > 252:
            await ctx.send("You can not add more than 252 EVs to a stat")
            return
        if amount < 1:
            await ctx.send("You must add at least 1 EV to a stat")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
        if not _id:
            await ctx.send(
                f"You do not have a selected pokemon!\nUse `/select` to select a pokemon."
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            ev_points = await pconn.fetchval(
                "SELECT evpoints FROM users WHERE u_id = $1", ctx.author.id
            )
        if ev_points is None:
            await ctx.send(f"You have not Started!\nStart with `/start` first!")
            return
        if ev_points < amount:
            await ctx.send(f"You do not have {amount} EV Points to add!")
            return
        try:
            async with ctx.bot.db[0].acquire() as pconn:
                if stat == "attack":
                    await pconn.execute(
                        "UPDATE pokes SET atkev = atkev + $1 WHERE id = $2", amount, _id
                    )
                elif stat == "defense":
                    await pconn.execute(
                        "UPDATE pokes SET defev = defev + $1 WHERE id = $2", amount, _id
                    )
                elif stat == "hp":
                    await pconn.execute(
                        "UPDATE pokes SET hpev = hpev + $1 WHERE id = $2", amount, _id
                    )
                elif stat == "special attack":
                    await pconn.execute(
                        "UPDATE pokes SET spatkev = spatkev + $1 WHERE id = $2",
                        amount,
                        _id,
                    )
                elif stat == "special defense":
                    await pconn.execute(
                        "UPDATE pokes SET spdefev = spdefev + $1 WHERE id = $2",
                        amount,
                        _id,
                    )
                elif stat == "speed":
                    await pconn.execute(
                        "UPDATE pokes SET speedev = speedev + $1 WHERE id = $2",
                        amount,
                        _id,
                    )
                await pconn.execute(
                    "UPDATE users SET evpoints = evpoints - $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            await ctx.send(
                f"You have successfully added {amount} EVs to the {stat} Stat of your Selected Pokemon!"
            )
        except Exception:
            await ctx.send("Your Pokemon has maxed all 510 EVs")


async def setup(bot):
    await bot.add_cog(Evs(bot))
