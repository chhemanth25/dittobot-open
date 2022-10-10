import time

import discord
from discord.ext import commands
from utils.misc import ConfirmView
from pokemon_utils.utils import evolve

from dittocogs.market import MAX_MARKET_SLOTS
from dittocogs.pokemon_list import activeItemList, berryList, is_formed


class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def prep_item_remove(ctx):
        """Handles ensuring a user can unequip an item. Returns None if they cannot, (held_item, pokname, items) if they can."""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT pokes.hitem, pokes.pokname, users.items::json FROM pokes INNER JOIN users ON pokes.id = (SELECT selected FROM users WHERE u_id = $1) AND users.u_id = $1",
                ctx.author.id,
            )
        if data is None:
            await ctx.send(
                "You do not have a pokemon selected!\nSelect one with `/select` first."
            )
            return None
        held_item, name, items = data
        if held_item in ("None", None, "none"):
            await ctx.send("Your selected Pokemon is not holding any item!")
            return None
        if (
            held_item in ("megastone", "mega-stone", "mega-stone-x", "mega-stone-y")
            and any(name.endswith(x) for x in ("-mega", "-x", "-y"))
            and name.lower() != "rayquaza-mega"
        ):
            await ctx.send("Deform this Pokemon before Unequipping the item!")
            return None
        if is_formed(name) and held_item in (
            "primal-orb",
            "blue-orb",
            "red-orb",
            "griseous-orb",
            "ultranecronium-z",
            "rusty-sword",
            "rusty-shield",
        ):
            await ctx.send("Deform this Pokemon before Unequipping the item!")
            return None
        return (held_item, name, items)

    @commands.hybrid_command()
    async def unequip(self, ctx):
        data = await self.prep_item_remove(ctx)
        if data is None:
            return
        held_item, name, items = data
        async with ctx.bot.db[0].acquire() as pconn:
            items[held_item] = items.get(held_item, 0) + 1
            await pconn.execute(
                "UPDATE users SET items = $1::json WHERE u_id = $2",
                items,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE pokes SET hitem = 'None' WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                ctx.author.id,
            )
        await ctx.send(f"Successfully unequipped a {held_item} from selected Pokemon")

    @commands.hybrid_command()
    async def equip(self, ctx, item_name: str):
        item_name = "-".join(item_name.split()).lower()
        item_info = await ctx.bot.db[1].shop.find_one({"item": item_name})
        if item_name == "nature-capsule":
            await ctx.send(
                "Use `/change nature` to use a nature capsule to change your pokemon's nature."
            )
            return
        if item_name not in berryList and not item_info:
            await ctx.send("That Item does not exist!")
            return
        if item_name in activeItemList:
            await ctx.send(
                f"That item cannot be equiped! Use it on your poke with `/apply {item_name}`."
            )
            return
        async with ctx.bot.db[0].acquire() as conn:
            dets = await conn.fetchval(
                "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if dets.get(item_name, 0) == 0:
            await ctx.send(f"You do not have any {item_name}!")
            return
        dets[item_name] = dets[item_name] - 1
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            data = await pconn.fetchrow(
                "SELECT pokname, hitem FROM pokes WHERE id = $1", _id
            )
            if data is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )
                return
            pokename, hitem = data
            if hitem.lower() != "none":
                await ctx.send(
                    f"Your pokemon is already holding the {hitem}! Unequip it with `/unequip` first!."
                )
                return
            ab_index = await pconn.fetchval(
                "SELECT ability_index FROM pokes WHERE id = $1", _id
            )
            if item_name == "ability-capsule":
                form_info = await ctx.bot.db[1].forms.find_one(
                    {"identifier": pokename.lower()}
                )
                ab_ids = []
                async for ability in ctx.bot.db[1].poke_abilities.find(
                    {"pokemon_id": form_info["pokemon_id"]}
                ):
                    ab_ids.append(ability["ability_id"])

                if len(ab_ids) == 1:
                    await ctx.send("That Pokemon cannot have its ability changed!")
                    return
                try:
                    new_ab = ab_ids[ab_index + 1]
                    new_index = ab_ids.index(new_ab)
                except IndexError:
                    new_index = 0
                await pconn.execute(
                    "UPDATE pokes SET ability_index = $1 WHERE id = $2", new_index, _id
                )
                ab_id = ab_ids[new_index]
                new_ability = await ctx.bot.db[1].abilities.find_one({"id": ab_id})

                await pconn.execute(
                    "UPDATE users SET items = $1::json WHERE u_id = $2",
                    dets,
                    ctx.author.id,
                )
                await ctx.send(
                    f"You have Successfully changed your Pokémons ability to {new_ability['identifier']}"
                )
                return
            if item_name == "daycare-space":
                await pconn.execute(
                    "UPDATE users SET items = $1::json, daycarelimit = daycarelimit + 1 WHERE u_id = $2",
                    dets,
                    ctx.author.id,
                )
                await ctx.send("You have successfully equipped an Extra Daycare Space!")
                return
            if item_name == "ev-reset":
                await pconn.execute(
                    "UPDATE users SET items = $1::json WHERE u_id = $2",
                    dets,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE pokes SET hpev = 0, atkev = 0, defev = 0, spatkev = 0, spdefev = 0, speedev = 0 WHERE id = $1",
                    _id,
                )
                await ctx.send(
                    "You have successfully reset the Effort Values (EVs) of your selected Pokemon!"
                )
                return
            if "-mega" in pokename and pokename != "Rayquaza-mega":
                await ctx.send(
                    "You can not equip an item for a Mega Pokemon. Use `/deform` to de-mega your Pokemon!"
                )
                return
            if item_name in {"zinc", "hp-up", "protein", "calcium", "iron", "carbos"}:
                try:
                    if item_name == "calcium":
                        await pconn.execute(
                            "UPDATE pokes SET spatkev = spatkev + 10 WHERE id = $1", _id
                        )
                    elif item_name == "carbos":
                        await pconn.execute(
                            "UPDATE pokes SET speedev = speedev + 10 WHERE id = $1", _id
                        )
                    elif item_name == "hp-up":
                        await pconn.execute(
                            "UPDATE pokes SET hpev = hpev + 10 WHERE id = $1", _id
                        )
                    elif item_name == "iron":
                        await pconn.execute(
                            "UPDATE pokes SET defev = defev + 10 WHERE id = $1", _id
                        )
                    elif item_name == "protein":
                        await pconn.execute(
                            "UPDATE pokes SET atkev = atkev + 10 WHERE id = $1", _id
                        )
                    elif item_name == "zinc":
                        await pconn.execute(
                            "UPDATE pokes SET spdefev = spdefev + 10 WHERE id = $1", _id
                        )
                    await pconn.execute(
                        "UPDATE users SET items = $1::json WHERE u_id = $2",
                        dets,
                        ctx.author.id,
                    )
                except:
                    await ctx.send("Your Pokemon has maxed all 510 EVs")
                    return
                await ctx.send(f"You have successfully used your {item_name}")
                return
            if item_name.endswith("-rod"):
                await pconn.execute(
                    "UPDATE users SET items = $1::json, held_item = $3 WHERE u_id = $2",
                    dets,
                    ctx.author.id,
                    item_name,
                )
                await ctx.send(f"You have successfully equiped your {item_name}")
                return
            name = await pconn.fetchval("SELECT pokname FROM pokes WHERE id = $1", _id)
            await pconn.execute(
                "UPDATE pokes set hitem = $2 WHERE id = $1", _id, item_name
            )
            await pconn.execute(
                "UPDATE users SET items = $1::json WHERE u_id = $2", dets, ctx.author.id
            )
            await ctx.send(
                f"You have successfully given your selected Pokemon a {item_name}"
            )
            await evolve(
                ctx.bot,
                dict(await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", _id)),
                ctx.author,
                channel=ctx.channel,
            )

    @commands.hybrid_command()
    async def drop(self, ctx):
        data = await self.prep_item_remove(ctx)
        if data is None:
            return
        held_item, name, items = data
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET hitem = $2 WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                ctx.author.id,
                "None",
            )
        await ctx.send(f"Successfully Dropped the {held_item}")

    @commands.hybrid_command()
    async def transfer(self, ctx, pokemon_number: int):
        data = await self.prep_item_remove(ctx)
        if data is None:
            return
        held_item, name, items = data
        async with ctx.bot.db[0].acquire() as pconn:
            poke = await pconn.fetchval(
                "SELECT pokes[$1] FROM users WHERE u_id = $2",
                pokemon_number,
                ctx.author.id,
            )
            if poke is None:
                await ctx.send("You do not have that Pokemon!")
                return
            details = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", poke)
            if details["hitem"].capitalize() != "None":
                await ctx.send("That Pokemon is already holding an item")
                return
            pokename = details["pokname"].capitalize()
            await pconn.execute(
                "UPDATE pokes SET hitem = 'None' WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE pokes SET hitem = $1 WHERE id = $2", held_item, poke
            )
        await ctx.send(
            f"You have successfully transfered the {held_item} from your {name} to your {pokename}!"
        )

    @commands.hybrid_command()
    async def apply(self, ctx, item_name: str):
        """Use an active item to evolve a poke."""
        item_name = "-".join(item_name.split()).lower()
        if item_name == "nature-capsule":
            await ctx.send(
                "Use `/change nature` to use a nature capsule to change your pokemon's nature."
            )
            return
        if item_name not in activeItemList:
            await ctx.send(
                f"That item cannot be used on a poke! Try equiping it with `/equip {item_name}`."
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            dets = await pconn.fetchval(
                "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if dets is None:
            await ctx.send("You have not started!\nStart with `/start first.")
            return
        if dets.get(item_name, 0) == 0:
            await ctx.send(f"You do not have any {item_name}!")
            return
        dets[item_name] = dets[item_name] - 1
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            poke = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", _id)
        if poke is None:
            await ctx.send(
                "You do not have a pokemon selected! Select one with `/select` first."
            )
            return
        evo_result = await evolve(
            ctx.bot,
            dict(poke),
            ctx.author,
            channel=ctx.channel,
            active_item=item_name,
        )
        if evo_result is False or not evo_result.used_active_item():
            await ctx.send(f"The {item_name} had no effect!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET items = $1::json WHERE u_id = $2", dets, ctx.author.id
            )
        await ctx.send(f"Your {item_name} was consumed!")

    @commands.hybrid_group(name="buy")
    async def buy_cmds(self, ctx):
        """Top layer of group"""

    @buy_cmds.command()
    async def item(self, ctx, arg: str):
        arg = arg.replace(" ", "-").lower()
        if arg == "evo-stone":
            await ctx.send("Purchasing that item is currently disabled.")
            return
        if arg == "daycare-space":
            await ctx.send("Use `/buy daycare`, not `/buy item daycare-space`.")
            return
        item = await ctx.bot.db[1].shop.find_one({"item": arg})
        if not item:
            await ctx.send("That Item is not in the market")
            return
        price = item["price"]
        item = item["item"]
        async with ctx.bot.db[0].acquire() as pconn:
            # items, current_creds = await pconn.fetchrow("SELECT  FROM users WHERE u_id = $1", ctx.author.id)
            data = await pconn.fetchrow(
                "SELECT inventory::json, mewcoins, selected FROM users WHERE u_id = $1",
                ctx.author.id,
            )
            if data is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            inventory, current_creds, selected_id = data
            if current_creds < price:
                await ctx.send(f"You don't have {price}ℳ")
                return
            # These items do NOT need the selected pokemon
            if item == "coin-case":
                if item in inventory:
                    await ctx.send("You already have a Coin Case!")
                    return
                inventory["coin-case"] = 0
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json, mewcoins = mewcoins - 1000 WHERE u_id = $2",
                    inventory,
                    ctx.author.id,
                )
                await ctx.send("You have successfully purchased a Coin Case!")
                return
            if item == "market-space":
                if current_creds < 30000:
                    await ctx.send(
                        f"You need 30,000 credits to buy a market space! You only have {current_creds}..."
                    )
                    return
                marketlimit = await pconn.fetchval(
                    "SELECT marketlimit FROM users WHERE u_id = $1", ctx.author.id
                )
                if marketlimit >= MAX_MARKET_SLOTS:
                    await ctx.send(
                        "You already have the maximum number of market spaces!"
                    )
                    return
                await pconn.fetchval(
                    "UPDATE users SET marketlimit = marketlimit + 1, mewcoins = mewcoins - 30000 WHERE u_id = $1",
                    ctx.author.id,
                )
                await ctx.send("You have successfully bought an extra market space!")
                return
            if "-rod" in item:
                await pconn.execute(
                    "UPDATE users set held_item = $1 WHERE u_id = $2",
                    item,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins - $2 WHERE u_id = $1",
                    ctx.author.id,
                    price,
                )
                await ctx.send(f"You have successfully bought the {item}!")
                return
            if item in activeItemList:
                dets = await pconn.fetchval(
                    "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
                )
                dets[item] = dets.get(item, 0) + 1
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins - $1, items = $2::json WHERE u_id = $3",
                    price,
                    dets,
                    ctx.author.id,
                )
                await ctx.send(
                    f"You have successfully bought a {item}! Use it with `/apply {item}`."
                )
                return

            if selected_id:
                _id, pokename, ab_index = await pconn.fetchrow(
                    "SELECT id, pokname, ability_index FROM pokes WHERE id = $1",
                    selected_id,
                )
            else:
                await ctx.send(
                    "You do not have a selected pokemon and the item you are trying to buy requires one!\nUse `/select` to select a pokemon."
                )
                return
            # These items DO need the selected pokemon
            if item == "ability-capsule":
                ab_ids = []
                form_info = await ctx.bot.db[1].forms.find_one(
                    {"identifier": pokename.lower()}
                )
                async for record in ctx.bot.db[1].poke_abilities.find(
                    {"pokemon_id": form_info["pokemon_id"]}
                ):
                    ab_ids.append(record["ability_id"])
                if len(ab_ids) <= 1:
                    await ctx.send("That Pokemon cannot have its ability changed!")
                    return
                ab_index = (ab_index + 1) % len(ab_ids)
                new_ab = ab_ids[ab_index]
                await pconn.execute(
                    "UPDATE pokes SET ability_index = $1 WHERE id = $2", ab_index, _id
                )
                ability = (await ctx.bot.db[1].abilities.find_one({"id": new_ab}))[
                    "identifier"
                ]
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                    price,
                    ctx.author.id,
                )
                await ctx.send(
                    f"You have Successfully changed your Pokémons ability to {ability}"
                )
                return
            if item == "ev-reset":
                await pconn.execute(
                    "UPDATE pokes SET hpev = 0, atkev = 0, defev = 0, spatkev = 0, spdefev = 0, speedev = 0 WHERE id = $1",
                    _id,
                )
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins - $2 WHERE u_id = $1",
                    ctx.author.id,
                    price,
                )
                await ctx.send(
                    "You have successfully reset the Effort Values (EVs) of your selected Pokemon!"
                )
                return
            if is_formed(pokename):
                await ctx.send(
                    "You can not buy an item for a Form. Use `/deform` to de-form your Pokemon!"
                )
                return
            helditem = await pconn.fetchval(
                "SELECT hitem FROM pokes WHERE id = $1", _id
            )
            if helditem.lower() != "none":
                await ctx.send("You already have an item equipped!")
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                price,
                ctx.author.id,
            )
            await pconn.execute("UPDATE pokes SET hitem = $1 WHERE id = $2", item, _id)
            await ctx.send(
                f"You have successfully bought the {item} for your {pokename}"
            )
            evolved = await evolve(
                ctx.bot,
                dict(await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", _id)),
                ctx.author,
                channel=ctx.channel,
            )

    @buy_cmds.command()
    async def daycare(self, ctx, amount: int = 1):
        """Buy daycare spaces."""
        item = await ctx.bot.db[1].shop.find_one({"item": "daycare-space"})
        if not item:
            await ctx.send("That Item is not in the market")
            return
        price = item["price"]
        price *= amount
        async with ctx.bot.db[0].acquire() as pconn:
            bal = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
            )
            if bal is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            if price > bal:
                await ctx.send(
                    f"You cannot afford that many daycare spaces! You need {price} credits, but you only have {bal}."
                )
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $2, daycarelimit = daycarelimit + $3 WHERE u_id = $1",
                ctx.author.id,
                price,
                amount,
            )
        plural = "s" if amount != 1 else ""
        await ctx.send(f"You have successfully bought {amount} daycare space{plural}!")

    @buy_cmds.command()
    async def coins(self, ctx, amount: int):
        amount = max(0, amount)
        if amount % 2 != 0:
            await ctx.send("You must buy Coin amounts divisible by 2!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT inventory::json, mewcoins FROM users WHERE u_id = $1",
                ctx.author.id,
            )
            if details is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            items, creds = details
            total = amount / 2
            if amount / 2 > creds:
                await ctx.send(f"You do not have {total} Credits ({amount} Coins)!")
                return
            if "coin-case" in items:
                items["coin-case"] += amount
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins - $1, inventory = $2::json WHERE u_id = $3",
                    amount / 2,
                    items,
                    ctx.author.id,
                )
                await ctx.send(
                    f"You have Successfully purchased {amount} Coins ({total} Credits)"
                )
            else:
                await ctx.send("You do not have a Coin Case!")

    @buy_cmds.command()
    async def vitamins(self, ctx, item_name, amount: int):
        amount = max(0, amount)
        item_name = item_name.strip()
        item_info = await ctx.bot.db[1].shop.find_one({"item": item_name})
        try:
            item_info["price"]
        except TypeError:
            await ctx.send("That Item is not in the market")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            total_price = amount * 100
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )
            if pokename is None:
                await ctx.send(
                    "You don't have a pokemon selected!\nSelect one with `/select` first."
                )
                return
            async with pconn.transaction():
                try:
                    await pconn.execute(
                        "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                        total_price,
                        ctx.author.id,
                    )
                except:
                    await ctx.send(f"You do not have {total_price} credits!")
                    return
                try:
                    if item_name == "zinc":
                        await pconn.execute(
                            "UPDATE pokes SET spdefev = spdefev + $1 WHERE id = $2",
                            amount,
                            _id,
                        )
                    elif item_name == "hp-up":
                        await pconn.execute(
                            "UPDATE pokes SET hpev = hpev + $1 WHERE id = $2",
                            amount,
                            _id,
                        )
                    elif item_name == "protein":
                        await pconn.execute(
                            "UPDATE pokes SET atkev = atkev + $1 WHERE id = $2",
                            amount,
                            _id,
                        )
                    elif item_name == "calcium":
                        await pconn.execute(
                            "UPDATE pokes SET spatkev = spatkev + $1 WHERE id = $2",
                            amount,
                            _id,
                        )
                    elif item_name == "iron":
                        await pconn.execute(
                            "UPDATE pokes SET defev = defev + $1 WHERE id = $2",
                            amount,
                            _id,
                        )
                    elif item_name == "carbos":
                        await pconn.execute(
                            "UPDATE pokes SET speedev = speedev + $1 WHERE id = $2",
                            amount,
                            _id,
                        )
                    await ctx.send(
                        f"You have successfully bought {amount} {item_name} for your {pokename}"
                    )
                except:
                    await ctx.send(
                        "Your Pokemon has maxed all 510 EVs or 252 EVs for that stat."
                    )

    @buy_cmds.command()
    async def candy(self, ctx, amount: int = 1):
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            if _id is None:
                await ctx.send("You need to select a pokemon first!")
                return
            det = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", _id)
            credits = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
            )
        name = det["pokname"]
        poke_id = det["id"]
        level = det["pokelevel"]
        det["happiness"]
        use_amount = max(0, amount)
        use_amount = min(100 - level, use_amount)
        buy_amount = use_amount
        if buy_amount == 0:
            buy_amount = 1
        price = buy_amount * 100
        string = "candy" if buy_amount == 1 else "candies"
        if price > credits:
            await ctx.send(
                f"You do not have {price} credits for {buy_amount} Rare {string}"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            # This try should not be necessary, but this keeps trying to assign lvl 101 pokes for no reason, and needs debugging
            try:
                await pconn.execute(
                    "UPDATE pokes SET pokelevel = pokelevel + $1 WHERE id = $2",
                    use_amount,
                    poke_id,
                )
            except Exception as e:
                ctx.bot.logger.warning(
                    f"Tried to give more levels than allowed - Poke: {poke_id} | Expected level - {level + use_amount}"
                )
                await ctx.send(
                    "Sorry, I can't do that right now. Try again in a moment."
                )
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                price,
                ctx.author.id,
            )
            pokemon_details = await pconn.fetchrow(
                "SELECT * FROM pokes WHERE id = $1", poke_id
            )
        level_total = level + use_amount
        await ctx.send(
            f"Your {name} has successfully leveled up to Level {level_total}."
        )
        await evolve(
            ctx.bot,
            dict(pokemon_details),
            ctx.author,
            channel=ctx.channel,
            override_lvl_100=True,
        )

    @buy_cmds.command()
    async def chest(self, ctx, chest_type: str, credits_or_redeems: str):
        """Buy a radiant chest."""
        ct = chest_type.lower().strip()
        cor = credits_or_redeems.lower()
        if ct not in ("rare", "mythic", "legend"):
            await ctx.send(
                f'"`{ct}`" is not a valid chest type! Choose one of Rare, Mythic, or Legend.'
            )
            return
        if cor not in ("credits", "redeems"):
            await ctx.send('Specify either "credits" or "redeems"!')
            return
        price = {
            "credits": {"rare": 600000, "mythic": 1250000, "legend": 3000000},
            "redeems": {"rare": 12, "mythic": 25, "legend": 55},
        }[cor][ct]
        if not await ConfirmView(
            ctx, f"Are you sure you want to buy a {ct} chest for {price} {cor}?\n"
        ).wait():
            await ctx.send("Purchase cancelled.")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            if cor == "credits":
                bal = await pconn.fetchval(
                    "SELECT mewcoins FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
                if bal is None:
                    await ctx.send("You have not started!\nStart with `/start` first.")
                    return
                if bal < price:
                    await ctx.send(
                        f"You do not have the {price} credits you need to buy a {ct} chest!"
                    )
                    return

                await pconn.execute(
                    "INSERT INTO cheststore VALUES ($1, 0, 0, 0, 0) ON CONFLICT DO NOTHING",
                    ctx.author.id,
                )
                info = await pconn.fetchrow(
                    "SELECT * FROM cheststore WHERE u_id = $1", ctx.author.id
                )
                info = {
                    "u_id": info["u_id"],
                    "rare": info["rare"],
                    "mythic": info["mythic"],
                    "legend": info["legend"],
                    "restock": int(info["restock"]),
                }

                restock_time = 604800
                if info["restock"] <= int(time.time() // restock_time):
                    await pconn.execute(
                        "UPDATE cheststore SET rare = 0, mythic = 0, legend = 0, restock = $1 WHERE u_id = $2",
                        str(int(time.time() // restock_time) + 1),
                        ctx.author.id,
                    )
                    info = {
                        "u_id": ctx.author.id,
                        "rare": 0,
                        "mythic": 0,
                        "legend": 0,
                        "restock": int(time.time() // restock_time) + 1,
                    }
                max_chests = 5
                if info[ct] + 1 > max_chests:
                    await ctx.send(
                        f"You can't buy more than {max_chests} per week using credits!  You've already bought {info[ct]}."
                    )
                    return
                if ct == "legend":
                    await pconn.execute(
                        "UPDATE cheststore SET legend = legend + 1 WHERE u_id = $1",
                        ctx.author.id,
                    )
                elif ct == "mythic":
                    await pconn.execute(
                        "UPDATE cheststore SET mythic = mythic + 1 WHERE u_id = $1",
                        ctx.author.id,
                    )
                elif ct == "rare":
                    await pconn.execute(
                        "UPDATE cheststore SET rare = rare + 1 WHERE u_id = $1",
                        ctx.author.id,
                    )
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                    price,
                    ctx.author.id,
                )
            elif cor == "redeems":
                bal = await pconn.fetchval(
                    "SELECT redeems FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
                if bal is None:
                    await ctx.send("You have not started!\nStart with `/start` first.")
                    return
                if bal < price:
                    await ctx.send(
                        f"You do not have the {price} redeems you need to buy a {ct} chest!"
                    )
                    return
                await pconn.execute(
                    "UPDATE users SET redeems = redeems - $1 WHERE u_id = $2",
                    price,
                    ctx.author.id,
                )
            else:
                return
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            item = f"{ct} chest"
            inventory[item] = inventory.get(item, 0) + 1
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
        await ctx.send(
            f"You have successfully bought a {ct} chest for {price} {cor}!\n"
            f"You can open it with `/open {ct}`."
        )

    @buy_cmds.command()
    async def redeems(self, ctx, amount: int = None):
        if amount and amount < 1:
            await ctx.send("Nice try...")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if not await pconn.fetchval(
                "SELECT exists(SELECT * from users WHERE u_id = $1)", ctx.author.id
            ):
                await ctx.send("You have not started!\nStart with `/start` first.")
                return

            await pconn.execute(
                "INSERT INTO redeemstore VALUES ($1, 0, 0) ON CONFLICT DO NOTHING",
                ctx.author.id,
            )
            info = await pconn.fetchrow(
                "SELECT * FROM redeemstore WHERE u_id = $1", ctx.author.id
            )

        info = (
            {
                "u_id": info["u_id"],
                "bought": info["bought"],
                "restock": int(info["restock"]),
            }
            if info
            else {"u_id": ctx.author.id, "bought": 0, "restock": 0}
        )

        max_redeems = 15
        restock_time = 604800
        if info["restock"] <= int(time.time() // restock_time):
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE redeemstore SET bought = 0, restock = $1 WHERE u_id = $2",
                    str(int(time.time() // restock_time) + 1),
                    ctx.author.id,
                )
            info = {
                "u_id": ctx.author.id,
                "bought": 0,
                "restock": int(time.time() // restock_time) + 1,
            }

        if not amount:
            if info["restock"] != 0:
                desc = f"You have bought {info['bought']} redeems this week.\n"
                if info["bought"] >= max_redeems:
                    desc += "You cannot buy any more this week."
                else:
                    desc += "Buy more using `/buy redeems <amount>`!"
                embed = discord.Embed(
                    title="Buy redeems",
                    description=desc,
                    color=0xFFB6C1,
                )
                embed.set_footer(text="Redeems restock every Wednesday at 8pm ET.")
            else:
                embed = discord.Embed(
                    title="Buy redeems",
                    description="You haven't bought any redeems yet! Use `/buy redeems <amount>`!",
                    color=0xFFB6C1,
                )

            await ctx.send(embed=embed)
        else:
            if info["bought"] + amount > max_redeems:
                await ctx.send(
                    f"You can't buy more than {max_redeems} per week!  You've already bought {info['bought']}."
                )
                return

            async with ctx.bot.db[0].acquire() as pconn:
                bal = await pconn.fetchval(
                    "SELECT mewcoins FROM users WHERE u_id = $1",
                    ctx.author.id,
                )

            credits_per_redeem = 60000

            price = amount * credits_per_redeem

            if bal < price:
                await ctx.send(
                    f"You do not have the {price} credits to buy those redeems!"
                )
                return

            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1, mewcoins = mewcoins - $2 WHERE u_id = $3",
                    amount,
                    price,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE redeemstore SET bought = bought + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
                if info["restock"] == 0:
                    await pconn.execute(
                        "UPDATE redeemstore SET restock = $1 WHERE u_id = $2",
                        str(int(time.time() // restock_time) + 1),
                        ctx.author.id,
                    )

            await ctx.send(
                f"You have successfully bought {amount} redeems for {price} credits!"
            )

    @commands.hybrid_command()
    async def cashout(self, ctx, amount: int):
        amount = max(0, amount)
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT inventory::json, mewcoins FROM users WHERE u_id = $1",
                ctx.author.id,
            )
            if details is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            items, creds = details
            total = amount / 2
            if "coin-case" not in items:
                await ctx.send("You need a Coin Case.")
                return
            if amount > items["coin-case"]:
                await ctx.send(f"You do not have {amount} Coins in your coin case!")
                return
            if "coin-case" in items:
                items["coin-case"] -= amount
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1, inventory = $2::json WHERE u_id = $3",
                    amount / 2,
                    items,
                    ctx.author.id,
                )
                await ctx.send(
                    f"You have Successfully Cashed out {amount} Coins ({total} Credits)"
                )


async def setup(bot):
    await bot.add_cog(Items(bot))
