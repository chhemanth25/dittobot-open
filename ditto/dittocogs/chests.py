import random

import discord
from discord.ext import commands
from utils.misc import ConfirmView, ListSelectView
from discord import app_commands
from dittocogs.pokemon_list import LegendList, pList, pseudoList, starterList, ubList
from enum import Enum
import asyncio

Choice = app_commands.Choice
radiant_menu = [
    discord.SelectOption(label="Shiny Multiplier x1",emoji="<:1:1013539737014907030>",description="5 Radiant Gems", value=1),
    discord.SelectOption(label="Battle Multiplier x1",emoji="<:2:1013539739263041618>",description="5 Radiant Gems", value=2),
    discord.SelectOption(label="IV Multiplier x1",emoji="<:3:1013539741502812310>",description="5 Radiant Gems", value=3),
    discord.SelectOption(label="Breeding Multiplier x1",emoji="<:4:1013539744027783208>",description="5 Radiant Gems", value=4),
    discord.SelectOption(label="Legend Chest",emoji="<:5:1013539745692909740>",description="75 Radiant Gems", value=5),
    discord.SelectOption(label="Radiant Pokemon (non-legend)",emoji="<:6:1013539747517444208>",description="100 Radiant Gems", value=6),
    discord.SelectOption(label="Radiant Pokemon (rare)",emoji="<:7:1013539749035786291>",description="200 Radiant Gems", value=7),
    discord.SelectOption(label="Radiant Pokemon (legend)",emoji="<:8:1013539750596071524>",description="300 Radiant Gems", value=8)
]






class RadiantView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.choice = None
        self.event = asyncio.Event()
        self.CURRENTLY_ACTIVE = (
            "Cramorant",
            "Frillish",
            "Solosis",
            "Spearow",
            "Arceus",
            "Zorua-hisui",
        )
        # currently available event radiants, {"Pokemon": "String when they get that poke!\n"}
        self.EVENT_ACTIVE = {}
        # packs that can be bought with ;radiant, (("Pack Desc", <int - Price in radiant gems>))
        self.PACKS = (
            ("Shiny Multiplier x1", 5),
            ("Battle Multiplier x1", 5),
            ("IV Multiplier x1", 5),
            ("Breeding Multiplier x1", 5),
            ("Legend Chest", 75),
            ("Radiant Pokemon (non-legend)", 100),
            ("Radiant Pokemon (rare)", 200),
            ("Radiant Pokemon (legend)", 300),
        )
        self.CREDITS_PER_MULTI = 100000
        legend = set(LegendList + ubList)
        rare = set(starterList + pseudoList)
        common = set(pList) - legend - rare
        self.LEGEND = set(self.CURRENTLY_ACTIVE) & legend
        self.RARE = set(self.CURRENTLY_ACTIVE) & rare
        self.COMMON = set(self.CURRENTLY_ACTIVE) & common


    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
            content="You are not allowed to interact with this button.",
            ephemeral=True,
        )
            return False
        return True

    async def on_timeout(self, interaction):
        with contextlib.suppress(discord.NotFound):
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.select(options=radiant_menu)
    async def radiant_selection(self, interaction, select):
        self.choice = interaction.data["values"][0]
        self.event.set()
        self.choice = int(self.choice)
        pack = self.PACKS[self.choice - 1]

        if not await ConfirmView(
            self.ctx,
            f"Are you sure you want to buy {pack[0]} for <a:radiantgem:1013790990852685955>x{pack[1]}?",
        ).wait():
            await self.ctx.send("Purchase cancelled.")
            return

        choice = ""
        if self.choice in {6, 7, 8}:
            if self.choice == 6:
                options = list(self.COMMON)
            elif self.choice == 7:
                options = list(self.RARE)
            elif self.choice == 8:
                options = list(self.LEGEND)
            if not options:
                await self.ctx.send(
                    "There are currently no valid pokemon in the pool. Please try again later."
                )
                return
            choice = await ListSelectView(
                self.ctx, "Which pokemon do you want?", options
            ).wait()
            if choice is None:
                await self.ctx.send("You did not select in time, cancelling.")
                return
        async with self.ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", self.ctx.author.id
            )
            if inventory is None:
                await self.ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            if inventory.get("radiant gem", 0) < pack[1]:
                await self.ctx.send("You cannot afford that pack!")
                return
            # await self.log_chest(ctx)
            inventory["radiant gem"] = inventory.get("radiant gem", 0) - pack[1]
            if self.choice in {1, 2, 3, 4}:
                if self.choice == 1:
                    item = "shiny-multiplier"
                elif self.choice == 2:
                    item = "battle-multiplier"
                elif self.choice == 3:
                    item = "iv-multiplier"
                elif self.choice == 4:
                    item = "breeding-multiplier"
                if inventory.get(item, 0) >= 50:
                    await self.ctx.send("You have hit the cap for that multiplier!")
                    return
                inventory[item] = min(inventory.get(item, 0) + 1, 50)
            elif self.choice == 5:
                inventory["legend chest"] = inventory.get("legend chest", 0) + 1
            elif self.choice in {6, 7, 8}:
                await self.ctx.bot.commondb.create_poke(
                    self.ctx.bot, self.ctx.author.id, choice, radiant=True, boosted=True
                )
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                self.__annotations__ctx.author.id,
            )
        await self.ctx.send(
            f"You have successfully bought {pack[0]} for <a:radiantgem:1013790990852685955>x{pack[1]}."
        )




class Chests(commands.Cog):
    """Open and view info on Radiant Chests."""

    def __init__(self, bot):
        self.bot = bot
        # currently available radiant pokemon, ("Pokemon")
        self.CURRENTLY_ACTIVE = (
            "Cramorant",
            "Frillish",
            "Solosis",
            "Spearow",
            "Arceus",
            "Zorua-hisui",
        )
        # currently available event radiants, {"Pokemon": "String when they get that poke!\n"}
        self.EVENT_ACTIVE = {}
        # packs that can be bought with ;radiant, (("Pack Desc", <int - Price in radiant gems>))
        self.PACKS = (
            ("Shiny Multiplier x1", 5),
            ("Battle Multiplier x1", 5),
            ("IV Multiplier x1", 5),
            ("Breeding Multiplier x1", 5),
            ("Legend Chest", 75),
            ("Radiant Pokemon (non-legend)", 100),
            ("Radiant Pokemon (rare)", 200),
            ("Radiant Pokemon (legend)", 300),
        )
        self.CREDITS_PER_MULTI = 100000
        legend = set(LegendList + ubList)
        rare = set(starterList + pseudoList)
        common = set(pList) - legend - rare
        self.LEGEND = set(self.CURRENTLY_ACTIVE) & legend
        self.RARE = set(self.CURRENTLY_ACTIVE) & rare
        self.COMMON = set(self.CURRENTLY_ACTIVE) & common

    async def log_chest(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "INSERT INTO skylog (u_id, command, args, jump, time) VALUES ($1, $2, $3, $4, $5)",
                ctx.author.id,
                ctx.command.qualified_name,
                " ".join([str(x) for x in ctx.args]),
                #ctx.jump_url,
                ctx.created_at.replace(tzinfo=None),
            )

    async def _maybe_spawn_event(self, ctx, chance):
        """
        Temporary method for spawning additional event pokemon.
        Spawns an event radiant for users who do not have one.

        Returns a string for user facing output.
        """
        if random.random() > chance:
            return ""
        if not self.EVENT_ACTIVE:
            return ""
        options = []
        async with ctx.bot.db[0].acquire() as pconn:
            for p in self.EVENT_ACTIVE:
                if not await pconn.fetchval(
                    "SELECT count(id) FROM pokes WHERE id in (select unnest(u.pokes) from users u where u.u_id = $1) AND radiant = true AND pokname = $2",
                    ctx.author.id,
                    p,
                ):
                    options.append(p)
        if not options:
            return ""
        poke = random.choice(options)
        await ctx.bot.commondb.create_poke(ctx.bot, ctx.author.id, poke, radiant=True)
        return self.EVENT_ACTIVE[poke]

    @commands.hybrid_group(name="open")
    async def open_cmds(self, ctx):
        """Top layer of group"""

    @open_cmds.command()
    async def common(self, ctx):
        """Open a common chest."""
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if inventory is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            if "common chest" not in inventory or inventory["common chest"] <= 0:
                await ctx.send("You do not have any Common Chests!")
                return
            # await self.log_chest(ctx)
            inventory["common chest"] = inventory.get("common chest", 0) - 1
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
            await pconn.execute("UPDATE achievements SET chests_common = chests_common + 1 WHERE u_id = $1", ctx.author.id)
        reward = random.choices(
            ("radiant", "chest", "ev", "poke", "redeem", "cred"),
            weights=(0.005, 0.015, 0.1, 0.2, 0.25, 0.43),
        )[0]
        if reward == "radiant":
            pokemon = random.choice(self.CURRENTLY_ACTIVE)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, radiant=True
            )
            msg = f"<a:slowpokeclap:1004716068599758848> **Congratulations! You received a radiant {pokemon}!**\n"
        elif reward == "chest":
            async with ctx.bot.db[0].acquire() as pconn:
                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inventory["rare chest"] = inventory.get("rare chest", 0) + 1
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    ctx.author.id,
                )
            msg = "You received a Rare Chest!\n"
        elif reward == "redeem":
            amount = 1
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            msg = "You received 1 redeem!\n"
        elif reward == "ev":
            amount = 250
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET evpoints = evpoints + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            msg = f"You received {amount} ev points!\n"
        elif reward == "cred":
            amount = random.randint(10, 25) * 1000
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            msg = f"You received {amount} credits!\n"
        elif reward == "poke":
            pokemon = random.choice(pList)
            pokedata = await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon
            )
            msg = f"You received a {pokedata.emoji}{pokemon}!\n"
        if gems := 1:
            async with ctx.bot.db[0].acquire() as pconn:
                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inventory["radiant gem"] = inventory.get("radiant gem", 0) + gems
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    ctx.author.id,
                )
            msg += f"You also received {gems} Radiant Gems <a:radiantgem:1013790990852685955>!\n"
        msg += await self._maybe_spawn_event(ctx, 0.15)
        await ctx.send(msg)

    @open_cmds.command()
    async def rare(self, ctx):
        """Open a rare chest."""
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if inventory is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            if "rare chest" not in inventory or inventory["rare chest"] <= 0:
                await ctx.send("You do not have any Rare Chests!")
                return
            # await self.log_chest(ctx)
            inventory["rare chest"] = inventory.get("rare chest", 0) - 1
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
            await pconn.execute("UPDATE achievements SET chests_rare = chests_rare + 1 WHERE u_id = $1", ctx.author.id)
        reward = random.choices(
            ("radiant", "redeem", "chest", "boostedshiny", "shiny"),
            weights=(0.02, 0.175, 0.20, 0.15, 0.455),
        )[0]
        if reward == "radiant":
            pokemon = random.choice(self.CURRENTLY_ACTIVE)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, radiant=True
            )
            msg = f"<a:slowpokeclap:1004716068599758848> **Congratulations! You received a radiant {pokemon}!**\n"
        elif reward == "redeem":
            amount = random.randint(4, 6)
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            msg = f"You received {amount} redeems!\n"
        elif reward == "chest":
            async with ctx.bot.db[0].acquire() as pconn:
                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inventory["mythic chest"] = inventory.get("mythic chest", 0) + 1
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    ctx.author.id,
                )
            msg = "You received a Mythic Chest!\n"
        elif reward == "shiny":
            pokemon = random.choice(pList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, shiny=True
            )
            msg = f"You received a shiny {pokemon}!\n"
        elif reward == "boostedshiny":
            pokemon = random.choice(pList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, shiny=True, boosted=True
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        gems = random.randint(1, 2)
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            inventory["radiant gem"] = inventory.get("radiant gem", 0) + gems
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
        msg += f"You also received {gems} Radiant Gems <a:radiantgem:1013790990852685955>!\n"
        msg += await self._maybe_spawn_event(ctx, 0.20)
        await ctx.send(msg)

    @open_cmds.command()
    async def mythic(self, ctx):
        """Open a mythic chest."""
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if inventory is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            if "mythic chest" not in inventory or inventory["mythic chest"] <= 0:
                await ctx.send("You do not have any Mythic Chests!")
                return
            # await self.log_chest(ctx)
            inventory["mythic chest"] = inventory.get("mythic chest", 0) - 1
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
            await pconn.execute("UPDATE achievements SET chests_mythic = chests_mythic + 1 WHERE u_id = $1", ctx.author.id)
        reward = random.choices(
            ("radiant", "boostedleg", "redeem", "chest", "shiny", "boostedshiny"),
            weights=(0.12, 0.04, 0.22, 0.20, 0.15, 0.27),
        )[0]
        if reward == "redeem":
            amount = random.randint(7, 15)
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            msg = f"You received {amount} redeems!\n"
        elif reward == "chest":
            async with ctx.bot.db[0].acquire() as pconn:
                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
                )
                inventory["legend chest"] = inventory.get("legend chest", 0) + 1
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    ctx.author.id,
                )
            msg = "You received a Legend Chest!\n"
        elif reward == "boostedleg":
            pokemon = random.choice(LegendList)
            pokedata = await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, boosted=True
            )
            msg = f"You received a boosted IV {pokedata.emoji}{pokemon}!\n"
        elif reward == "radiant":
            pokemon = random.choice(self.CURRENTLY_ACTIVE)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, radiant=True
            )
            msg = f"<a:slowpokeclap:1004716068599758848> **Congratulations! You received a radiant {pokemon}!**\n"
        elif reward == "shiny":
            pokemon = random.choice(pList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, shiny=True
            )
            msg = f"You received a shiny {pokemon}!\n"
        elif reward == "boostedshiny":
            pokemon = random.choice(pList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, shiny=True, boosted=True
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        gems = random.randint(8, 11)
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            inventory["radiant gem"] = inventory.get("radiant gem", 0) + gems
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
        msg += f"You also received {gems} Radiant Gems <a:radiantgem:1013790990852685955>!\n"
        msg += await self._maybe_spawn_event(ctx, 0.25)
        await ctx.send(msg)

    @open_cmds.command()
    async def legend(self, ctx):
        """Open a legend chest."""
        async with ctx.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if inventory is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            if "legend chest" not in inventory or inventory["legend chest"] <= 0:
                await ctx.send("You do not have any Legend Chests!")
                return
            # await self.log_chest(ctx)
            inventory["legend chest"] = inventory.get("legend chest", 0) - 1
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inventory,
                ctx.author.id,
            )
            await pconn.execute("UPDATE achievements SET chests_legend = chests_legend + 1 WHERE u_id = $1", ctx.author.id)
        voucher_chance = 0 if ctx.author.id in (399855039130238986,) else 0.001
        reward = random.choices(
            (
                "custom",
                "boostedshinylegendary",
                "boostedshinyub",
                "redeem",
                "radiant",
                "boostedshinypseudo",
                "boostedshinystarter",
                "boostedshiny",
            ),
            weights=(
                voucher_chance,
                0.012,
                0.012,
                0.275,
                0.275,
                0.025,
                0.025,
                0.375,
            ),
        )[0]
        if reward == "custom":
            msg = "You have received a public voucher that allows you to submit your own recolor with background for any unreleased radiant pokemon, and it will be added to the following months lineup for everyone to obtain! Message Sky in the official server for more information!\nAlso, you of course get the one you design guaranteed. "
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<@631840748924436490> USER ID `{ctx.author.id}` HAS WON A 'Totally Custom Pokemon skin PUBLIC voucher'!"
            )
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute("UPDATE achievements SET chests_voucher = chests_voucher + 1 WHERE u_id = $1", ctx.author.id)
        elif reward == "boostedshinylegendary":
            pokemon = random.choice(LegendList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, boosted=True, shiny=True
            )
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<:b:1005742997876510800><:s:1005742996655972352><:L:1005742994093264916>:\n **User**-`{ctx.author.id}`\nobtained a **boosted shiny legendary** - `{pokemon}`!"
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        elif reward == "boostedshiny":
            pokemon = random.choice(pList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, boosted=True, shiny=True
            )
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<:b:1005742997876510800><:s:1005742996655972352>:\n **User**-`{ctx.author.id}`\nobtained a **boosted shiny** - `{pokemon}`!"
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        elif reward == "redeem":
            amount = random.randint(30, 50)
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                    amount,
                    ctx.author.id,
                )
            msg = f"You received {amount} redeems!\n"
        elif reward == "radiant":
            pokemon = random.choice(self.CURRENTLY_ACTIVE)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, radiant=True, boosted=True
            )
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<:b:1005742997876510800><:RAD:1005743326235988069>:\n **User**-`{ctx.author.id}`\nobtained a boosted **radiant** - `{pokemon}`!"
            )
            msg = f"<a:slowpokeclap:1004716068599758848> **Congratulations! You received a boosted radiant {pokemon}!**\n"
        elif reward == "boostedshinypseudo":
            pokemon = random.choice(pseudoList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, boosted=True, shiny=True
            )
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<:b:1005742997876510800><:s:1005742996655972352><:p:1005742995271843930>:\n **User**-`{ctx.author.id}`\nobtained a **boosted shiny pseudo** - `{pokemon}`!"
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        elif reward == "boostedshinystarter":
            pokemon = random.choice(starterList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, boosted=True, shiny=True
            )
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<:b:1005742997876510800><:s:1005742996655972352><:s:1005742996655972352>:\n **User**-`{ctx.author.id}`\nobtained a **boosted shiny starter** - `{pokemon}`!"
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        elif reward == "boostedshinyub":
            pokemon = random.choice(ubList)
            await ctx.bot.commondb.create_poke(
                ctx.bot, ctx.author.id, pokemon, boosted=True, shiny=True
            )
            await ctx.bot.get_partial_messageable(1005740622805729370).send(
                f"<:b:1005742997876510800><:s:1005742996655972352><:UB:1005742992822390824>:\n **User**-`{ctx.author.id}`\nobtained a **boosted shiny ultra beast** - `{pokemon}`!"
            )
            msg = f"You received a shiny boosted IV {pokemon}!\n"
        gems = random.randint(10, 15)
        async with ctx.bot.db[0].acquire() as pconn:
            inv = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            inv["radiant gem"] = inv.get("radiant gem", 0) + gems
            await pconn.execute(
                "UPDATE users SET inventory = $1::json where u_id = $2",
                inv,
                ctx.author.id,
            )
        msg += f"You also received {gems} Radiant Gems <a:radiantgem:1013790990852685955>!\n"
        msg += await self._maybe_spawn_event(ctx, 0.33)
        await ctx.send(msg)

    #@commands.hybrid_command()
    #async def radiant(self, ctx, packnum: int = None):
    #    """Spend your radiant gems."""
    #    if packnum is None:
    #        desc = ""
    #        for idx, pack in enumerate(self.PACKS, start=1):
    #            desc += f"**{idx}.** __{pack[0]}__ - <a:radiantgem:1013790990852685955>x{pack[1]}\n"
    #        desc += f"\nUse `/radiant` with the number you want to buy."
    #        e = discord.Embed(
    #            title="Radiant Gem Shop",
    #            description=desc,
    #            color=ctx.bot.get_random_color(),
    #        )
    #        await ctx.send(embed=e)
    #        return
    #    if packnum < 1 or packnum > len(self.PACKS):
    #        await ctx.send("That is not a valid pack number.")
    #        return
    #    pack = self.PACKS[packnum - 1]
#
    #    if not await ConfirmView(
    #        ctx,
    #        f"Are you sure you want to buy {pack[0]} for <a:radiantgem:1013790990852685955>x{pack[1]}?",
    #    ).wait():
    #        await ctx.send("Purchase cancelled.")
    #        return
#
    #    choice = ""
    #    if packnum in {6, 7, 8}:
    #        if packnum == 6:
    #            options = list(self.COMMON)
    #        elif packnum == 7:
    #            options = list(self.RARE)
    #        elif packnum == 8:
    #            options = list(self.LEGEND)
    #        if not options:
    #            await ctx.send(
    #                "There are currently no valid pokemon in the pool. Please try again later."
    #            )
    #            return
    #        choice = await ListSelectView(
    #            ctx, "Which pokemon do you want?", options
    #        ).wait()
    #        if choice is None:
    #            await ctx.send("You did not select in time, cancelling.")
    #            return
    #    async with ctx.bot.db[0].acquire() as pconn:
    #        inventory = await pconn.fetchval(
    #            "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
    #        )
    #        if inventory is None:
    #            await ctx.send(f"You have not Started!\nStart with `/start` first!")
    #            return
    #        if inventory.get("radiant gem", 0) < pack[1]:
    #            await ctx.send("You cannot afford that pack!")
    #            return
    #        # await self.log_chest(ctx)
    #        inventory["radiant gem"] = inventory.get("radiant gem", 0) - pack[1]
    #        if packnum in {1, 2, 3, 4}:
    #            if packnum == 1:
    #                item = "shiny-multiplier"
    #            elif packnum == 2:
    #                item = "battle-multiplier"
    #            elif packnum == 3:
    #                item = "iv-multiplier"
    #            elif packnum == 4:
    #                item = "breeding-multiplier"
    #            if inventory.get(item, 0) >= 50:
    #                await ctx.send("You have hit the cap for that multiplier!")
    #                return
    #            inventory[item] = min(inventory.get(item, 0) + 1, 50)
    #        elif packnum == 5:
    #            inventory["legend chest"] = inventory.get("legend chest", 0) + 1
    #        elif packnum in {6, 7, 8}:
    #            await ctx.bot.commondb.create_poke(
    #                ctx.bot, ctx.author.id, choice, radiant=True, boosted=True
    #            )
    #        await pconn.execute(
    #            "UPDATE users SET inventory = $1::json where u_id = $2",
    #            inventory,
    #            ctx.author.id,
    #        )
    #    await ctx.send(
    #        f"You have successfully bought {pack[0]} for <a:radiantgem:1013790990852685955>x{pack[1]}."
    #    )


    class RadiantChoice(Enum):
        one = 1
        two = 2
        three = 3
        four = 4
        five = 5
        six = 6
        seven = 7
        eight = 8



    @commands.hybrid_command()
    async def radiant(self, ctx):
        """Spend your radiant gems."""
        desc = ""
        desc += f"\nSelect which item to buy from the radiant shop!"
        e = discord.Embed(
            title="Radiant Gem Shop",
            description=desc,
            color=ctx.bot.get_random_color(),
        )
        await ctx.send(embed=e, view=RadiantView(ctx))




    

async def setup(bot):
    await bot.add_cog(Chests(bot))
