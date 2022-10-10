import asyncio
import contextlib

import discord
from discord.ext import commands
from utils.checks import tradelock
from utils.misc import ConfirmView
from pokemon_utils.utils import get_pokemon_info

# PostgreSQL database table `market`:
# bigserial id  : Primary key, a unique number that represents the listing id.
# integer poke  : The poke id (primary key of the the `pokes` table) of the pokemon this listing is for.
# bigint owner  : The user id of the owner of this pokemon.
# integer price : The listing price of this pokemon.
# bigint buyer  : One of `null`, `0`, or a user id.
#                   If `null`, this pokemon is currently listed.
#                   If `0`, this pokemon was removed from the market.
#                   If a user id, this pokemon was purchased by that user id.
MAX_MARKET_SLOTS = 10
PATREON_SLOT_BONUS = 1
SILVER_PATREON_SLOT_BONUS = 2
GOLD_PATREON_SLOT_BONUS = 5
CRYSTAL_PATREON_SLOT_BONUS = 10
DEPOSIT_RATE = 0.15


class Market(commands.Cog):
    """List pokemon on the market."""

    def __init__(self, bot):
        self.bot = bot
        self.init_task = asyncio.create_task(self.initialize())

    async def initialize(self):
        await self.bot.redis_manager.redis.execute(
            "LPUSH",
            "marketlock",
            # I don't think we'll get to a market listing this high
            "1231231346546515131351351351315",
        )

    @commands.hybrid_group()
    async def m(self, ctx):
        ...

    @m.command()
    @tradelock
    async def market_add(self, ctx, poke: int, price: int):
        """Add a pokemon to the market."""
        price = max(price, 0)
        if price > 2147483647:
            await ctx.send("Haha, no.")
            return
        if poke == 1:
            await ctx.send("You can not enlist your first Pokemon in the market.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT pokes[$1], marketlimit, mewcoins, tradelock FROM users WHERE u_id = $2",
                poke,
                ctx.author.id,
            )
            if data is None:
                await ctx.send(f"You have not started!\nStart with `/start`")
                return
            poke_id, marketlimit, credits, tradeban = data
            if tradeban:
                await ctx.send("You are not allowed to trade.")
                return
            if poke_id is None:
                await ctx.send("You don't have that Pokemon.")
                return
            deposit = int(price * DEPOSIT_RATE)
            if credits < deposit:
                await ctx.send(
                    f"Listing this pokemon for {price} credits requires a {deposit} credit deposit, which you cannot afford."
                )
                return
            patreon_status = await ctx.bot.patreon_tier(ctx.author.id)
            if patreon_status in ("Crystal Patreon", "Elite Patreon"):
                marketlimit += CRYSTAL_PATREON_SLOT_BONUS
            elif patreon_status == "Gold Patreon":
                marketlimit += GOLD_PATREON_SLOT_BONUS
            elif patreon_status == "Silver Patreon":
                marketlimit += SILVER_PATREON_SLOT_BONUS
            elif patreon_status == "MewBot Patreon":
                marketlimit += PATREON_SLOT_BONUS
            current_listings = await pconn.fetchval(
                "SELECT count(id) FROM market WHERE owner = $1 AND buyer IS NULL",
                ctx.author.id,
            )
            if current_listings >= marketlimit:
                await ctx.send(
                    f"You are only allowed to list {marketlimit} pokemon on the market at once.\n"
                    f"You can buy more with `/buy item market-space`.\n"
                    f"Patreons get more slots. Use `/donate` to learn more!"
                )
                return
            details = await pconn.fetchrow(
                "SELECT pokname, pokelevel, radiant, fav, tradable FROM pokes WHERE id = $1",
                poke_id,
            )
            if details is None:
                await ctx.send("You don't have that Pokemon.")
                return
            pokename, pokelevel, radiant, fav, tradable = details
            if pokename == "Egg":
                await ctx.send("You can't market an Egg!")
                return
            if not tradable:
                await ctx.send("That pokemon cannot be listed on the market!")
                return
            # if radiant:
            #    await ctx.send("You can't market radiant pokemon!")
            #    return
            if fav:
                await ctx.send(
                    f"You cannot market your {pokename} as it is favorited.\n"
                    f"Unfavorite it first with `/fav remove {poke}`."
                )
                return
            if not await ConfirmView(
                ctx,
                (
                    f"Are you sure you want to list your level {pokelevel} {pokename} to the market for {price} credits?\n"
                    f"Listing it will require a {deposit} deposit, which you will only get back if it is sold."
                ),
            ).wait():
                await ctx.send("Cancelling.")
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                deposit,
                ctx.author.id,
            )
            listing_id = await pconn.fetchval(
                "INSERT INTO market (poke, owner, price) VALUES ($1, $2, $3) RETURNING id",
                poke_id,
                ctx.author.id,
                price,
            )
        await ctx.bot.commondb.remove_poke(ctx.author.id, poke_id)
        await ctx.send(
            f"You have added your {pokename} to the market! It is market listing #{listing_id}."
        )
        await ctx.bot.log(
            1008748026799587408,
            f"**ID** - `{listing_id}`\n<a:plus:1008763677509431446> : {ctx.author.name}(`{ctx.author.id}`) **ADDED** **{pokename}**.\n-----------------------------",
        )

    @m.command()
    @tradelock
    async def market_buy(self, ctx, listing_id: int):
        """Buy a pokemon currently listed on the market."""
        in_lock = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "marketlock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if listing_id in in_lock:
            await ctx.send(
                "Someone is already in the process of buying that pokemon. You can try again later."
            )
            return
        await self.bot.redis_manager.redis.execute(
            "LPUSH", "marketlock", str(listing_id)
        )
        try:
            async with ctx.bot.db[0].acquire() as pconn:
                details = await pconn.fetchrow(
                    "SELECT poke, owner, price, buyer FROM market WHERE id = $1",
                    listing_id,
                )
                if not details:
                    await ctx.send("That listing does not exist.")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "marketlock", "1", str(listing_id)
                    )
                    return
                poke, owner, price, buyer = details
                if owner == ctx.author.id:
                    await ctx.send("You can not buy your own pokemon.")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "marketlock", "1", str(listing_id)
                    )
                    return
                if buyer is not None:
                    await ctx.send("That listing has already ended.")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "marketlock", "1", str(listing_id)
                    )
                    return
                details = await pconn.fetchrow(
                    "SELECT pokname, pokelevel FROM pokes WHERE id = $1", poke
                )
            if not details:
                await ctx.send("That pokemon does not exist?")
                await self.bot.redis_manager.redis.execute(
                    "LREM", "marketlock", "1", str(listing_id)
                )
                raise ValueError(
                    f"Poke id {poke} is open market listing {listing_id} but does not exist."
                )
            pokename, pokelevel = details
            pokename = pokename.capitalize()
            if not await ConfirmView(
                ctx,
                f"Are you sure you want to buy a level {pokelevel} {pokename} for {price} credits?",
            ).wait():
                await ctx.send("Purchase cancelled.")
                return
            async with ctx.bot.db[0].acquire() as pconn:
                
                data = await pconn.fetchrow(
                    "SELECT mewcoins, tradelock FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
                if data is None:
                    await ctx.send("You have not started!\nStart with `/start` first.")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "marketlock", "1", str(listing_id)
                    )
                    return
                credits, tradeban = data
                if tradeban:
                    await ctx.send("You are not allowed to trade.")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "marketlock", "1", str(listing_id)
                    )
                    return
                if price > credits:
                    await ctx.send("You don't have enough credits to buy that pokemon.")
                    await self.bot.redis_manager.redis.execute(
                        "LREM", "marketlock", "1", str(listing_id)
                    )
                    return
                await pconn.execute(
                    "UPDATE market SET buyer = $1 WHERE id = $2",
                    ctx.author.id,
                    listing_id,
                )
                await pconn.execute(
                    "UPDATE users SET pokes = array_append(pokes, $1), mewcoins = mewcoins - $2 WHERE u_id = $3",
                    poke,
                    price,
                    ctx.author.id,
                )
                deposit = int(price * DEPOSIT_RATE)
                gain = price + deposit
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    gain,
                    owner,
                )
                await pconn.execute("UPDATE achievements SET market_purchased = market_purchased + 1 WHERE u_id = $1", ctx.author.id)
                await pconn.execute("UPDATE achievements SET market_sold = market_sold + 1 WHERE u_id = $1", owner)
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.send(
                    f"You have Successfully Bought A {pokename} for {price} credits."
                )
            await ctx.send(
                f"You have Successfully Bought A {pokename} for {price} credits."
            )
            with contextlib.suppress(discord.HTTPException):
                user = await ctx.bot.fetch_user(owner)
                await user.send(
                    f"<@{owner}> Your {pokename} has been sold for {price} credits.\n"
                    f"You received your {deposit} credit deposit back as well."
                )
            await ctx.bot.log(
                1008748026799587408,
                f"**ID** - `{listing_id}`\n<a:plus:1008763677509431446> : {ctx.author.name}(`{ctx.author.id}`) **BOUGHT** a **{pokename}**. Seller - (<@{owner}>)`{owner}`.\n-----------------------------",
            )
        except Exception:
            raise
        finally:
            await self.bot.redis_manager.redis.execute(
                "LREM", "marketlock", "1", str(listing_id)
            )  # As a just in case
            


    @m.command()
    async def market_remove(self, ctx, listing_id: int):
        """Remove a pokemon from the market."""
        in_lock = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "marketlock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if listing_id in in_lock:
            await ctx.send(
                "Someone is already in the process of buying that pokemon. You can try again later."
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT poke, owner, buyer FROM market WHERE id = $1", listing_id
            )
            if not details:
                await ctx.send("That listing does not exist.")
                return
            poke, owner, buyer = details
            if owner != ctx.author.id:
                await ctx.send("You do not own that listing.")
                return
            if buyer is not None:
                await ctx.send("That listing has already ended.")
                return
            await pconn.execute(
                "UPDATE market SET buyer = $1 WHERE id = $2", 0, listing_id
            )
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = $2",
                poke,
                ctx.author.id,
            )
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", poke
            )
        await ctx.send(f"You have removed your {pokename} from the market")
        await ctx.bot.log(
            1008748026799587408,
            f"**ID** - `{listing_id}`\n<a:minus:1008763512652304555> : {ctx.author.name}(`{ctx.author.id}`) **REMOVED** {pokename} from the market.\n-----------------------------",
        )

    @m.command()
    async def market_info(self, ctx, listing_id: int):
        """View the info of a marketed pokemon."""
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT poke, buyer FROM market WHERE id = $1", listing_id
            )
            if not details:
                await ctx.send("That listing does not exist.")
                return
            poke, buyer = details
            if buyer is not None:
                await ctx.send("That listing has already ended.")
                return
            records = await pconn.fetchrow(
                "SELECT pokes.*, market.price as pokeprice, market.id as mid FROM pokes INNER JOIN market ON pokes.id = market.poke WHERE pokes.id = $1 AND market.buyer IS NULL",
                poke,
            )
            await ctx.send(
                embed=await get_pokemon_info(ctx, records, info_type="market")
            )


async def setup(bot):
    await bot.add_cog(Market(bot))
