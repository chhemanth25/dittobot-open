from discord.ext import commands
from utils.checks import tradelock
from utils.misc import ConfirmView

UNSELLABLE = [
    "coin-case",
    "daycare-space",
    "market-space",
    "radiant gem",
    "legend",
    "mythic",
    "rare",
    "common",
    "iv-multiplier",
    "nature-capsule",
    "shiny-multiplier",
    "battle-multiplier",
    "breeding-multiplier",
    "honey",
    "ultranecronium-z",
    "adamant-orb",
    "shadow-stone",
]


class Sell(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="sell")
    @tradelock
    async def sell(self, ctx: commands.Context) -> None:
        """Commands for selling various things"""

    # Only using shop items to start

    @sell.command(name="item")
    @tradelock
    async def sell_item(self, ctx, item_name: str, amount_sold: int = 1) -> None:
        """Sell items from your inventory for credits"""
        if amount_sold < 1:
            await ctx.send("You cannot sell less than 1 of an item!")
            return
        item_name = item_name.replace(" ", "-").lower()
        if item_name in UNSELLABLE:
            await ctx.send(f"`{item_name}` can't be sold.")
            return

        item = await ctx.bot.db[1].shop.find_one({"item": item_name})
        if item is None:
            await ctx.send(f"`{item_name}` isn't a valid item.")
            return

        shop_price = item["price"]

        # Pull their current bag and process sell
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if inventory is None:
                await ctx.send("You have not started!\nStart with `/start` first!")
                return

            # Check if they even have it
            if inventory.get(item_name, 0) < amount_sold:
                await ctx.send(f"You don't have enough `{item_name}`s!")
                return

            inventory[item_name] -= amount_sold
            credits_gained = round((shop_price * 0.65) * amount_sold)

            await pconn.execute(
                "UPDATE users SET items = $1::json, mewcoins = mewcoins + $2 WHERE u_id = $3",
                inventory,
                credits_gained,
                ctx.author.id,
            )
        await ctx.send(
            f"You have successfully sold `{amount_sold}x {item_name}` for {credits_gained:,} credits!"
        )

    @sell.command(name="egg")
    @tradelock
    async def sell_egg(self, ctx, egg_num: str) -> None:
        """Sell eggs from your daycare"""
        async with ctx.bot.db[0].acquire() as pconn:
            if egg_num in {"newest", "new", "latest"}:
                egg_id = await pconn.fetchval(
                    "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
            else:
                try:
                    egg_num = int(egg_num)
                except ValueError:
                    await ctx.send("That isn't a valid pokemon number.")
                    return
                if egg_num <= 1:
                    await ctx.send("That isn't a valid pokemon number.")
                    return
                # Check for num entered
                egg_id = await pconn.fetchval(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2",
                    egg_num,
                    ctx.author.id,
                )
            if egg_id is None:
                await ctx.send("You do not have that many pokemon.")
                return

            # Add check for eggs under 100 step count
            data = await pconn.fetchrow(
                "SELECT counter, pokname, name, fav, COALESCE(hpiv, 0) + COALESCE(atkiv, 0) + COALESCE(spatkiv, 0) + COALESCE(defiv, 0) + COALESCE(spdefiv, 0) + COALESCE(speediv, 0) as ivs FROM pokes WHERE id = $1",
                egg_id,
            )
            if data is None:
                await ctx.send("That pokemon doesn't exist.")
                return

            step_count = data["counter"]
            name = data["pokname"]
            iv_total = data["ivs"]
            fav = data["fav"]
            becomes = data["name"]

            if name != "Egg":
                await ctx.send(f"That's a {name}, not an egg!")
                return
            if step_count <= 100:
                await ctx.send(
                    "That egg is too close to hatching, go hatch it instead!"
                )
                return
            if fav:
                await ctx.send("That egg is favorited! Unfavorite it first.")
                return
            if becomes == "Magikarp":
                await ctx.send("You cannot sell an egg that will hatch into Magikarp!")
                return

            # Passed checks so total IV and calc credits gained
            if iv_total <= 111:
                credits_gained = 1000
            elif iv_total <= 149:
                credits_gained = 2000
            elif iv_total <= 176:
                credits_gained = 3000
            else:
                credits_gained = 10000

            # Display amount to user
            if not await ConfirmView(
                ctx,
                f"Are you sure you want to sell your egg for {credits_gained:,} credits?",
            ).wait():
                await ctx.send("Sale canceled")
                return

            # Remove Pokemon and give credits to user
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $2 WHERE u_id = $1",
                ctx.author.id,
                credits_gained,
            )
        await ctx.bot.commondb.remove_poke(ctx.author.id, egg_id)
        await ctx.send(f"Successfully sold your egg for {credits_gained:,} credits.")


async def setup(bot):
    await bot.add_cog(Sell(bot))
