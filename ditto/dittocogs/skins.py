import asyncio
import random
import time

import discord
from discord.ext import commands
from utils.checks import tradelock
from utils.misc import (
    ConfirmView,
    MenuView,
    get_battle_file_name,
    get_pokemon_image,
    pagify,
)

from dittocogs.pokemon_list import LegendList, pList, pseudoList, starterList, ubList

# Map of skin name -> list[pokemon name]
# Every skin pack must have at least 5 skins in it, or the code must be modified
BUYABLE_SKINS = {
    "glimmer": [
        "staryu",
        "azurill",
        "hoppip",
        "raikou",
        "entei",
        "suicune",
        "ho-oh",
        "luvdisc",
        "buneary",
        "stunky",
        "finneon",
        "phione",
        "manaphy",
        "petilil",
        "skrelp",
        "dedenne",
        "carbink",
        "klefki",
        "yungoos",
    ],
    "sketch": [
        "bulbasaur",
        "charmander",
        "squirtle",
        "igglybuff",
        "zubat",
        "growlithe",
        "geodude",
        "gastly",
        "voltorb",
        "mewtwo",
        "mew",
    ],
    "zodiac": [
        "skiddo",
        "tauros",
        "morpeko",
        "krabby",
        "shinx",
        "audino",
        "baltoy",
        "skorupi",
        "rowlet",
        "wooloo",
        "popplio",
        "wishiwashi",
    ],
}
# Map of skin name -> int release timestamp (time.time() // (60 * 60 * 24 * 7))
# Skins will be excluded from the shop if their release timestamp is greater than the current release timestamp
# When adding a new skin, the value set MUST be greater than the current value, otherwise current shops will shuffle
RELEASE_PERIOD = {
    "glimmer": 0,
    "sketch": 0,
    "zodiac": 0,
}


class Skins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="skin")
    async def skin_group(self, ctx: commands.Context) -> None:
        """group cmd"""

    @skin_group.command(name="apply")
    @tradelock
    async def skin_apply(self, ctx, poke: int, skin: str) -> None:
        """Apply a skin to a pokemon."""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT skins::json, pokes[$1] FROM users WHERE u_id = $2",
                poke,
                ctx.author.id,
            )
            if data is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            skins, pid = data
            data = await pconn.fetchrow(
                "SELECT pokname, skin, shiny, radiant FROM pokes WHERE id = $1", pid
            )
            if data is None:
                await ctx.send("You don't have that many pokemon.")
                return
            pokname, current_skin, shiny, radiant = data
            if current_skin is not None:
                await ctx.send("That pokemon already has a skin.")
                return
            if shiny:
                await ctx.send("Skins cannot be applied to shiny pokemon.")
                return
            if radiant:
                await ctx.send("Skins cannot be applied to radiant pokemon.")
                return

            pokname = pokname.lower()
            skin = skin.lower()
            if skins.get(pokname, {}).get(skin, 0) < 1:
                await ctx.send(f"You do not have any {skin} skins for {pokname}.")
                return

            confirm = (
                f"Are you sure you want to apply your {skin} skin to your {pokname}?\n"
            )
            if skin in BUYABLE_SKINS:
                confirm += f"\N{WARNING SIGN} Doing so will make your {pokname} unable to be traded!"
            if not await ConfirmView(ctx, confirm).wait():
                await ctx.send("Cancelling.")
                return

            data = await pconn.fetchrow(
                "SELECT skins::json, pokes[$1] FROM users WHERE u_id = $2",
                poke,
                ctx.author.id,
            )
            new_skins, new_pid = data
            if skins != new_skins or pid != new_pid:
                await ctx.send("Something got desynced. Please try again.")
                return

            skins[pokname][skin] -= 1
            await pconn.execute(
                "UPDATE users SET skins = $1::json WHERE u_id = $2",
                skins,
                ctx.author.id,
            )
            await pconn.execute("UPDATE pokes SET skin = $1 WHERE id = $2", skin, pid)
            if skin in BUYABLE_SKINS:
                await pconn.execute(
                    "UPDATE pokes SET tradable = false WHERE id = $1", pid
                )
        await ctx.send(f"Applied a {skin} skin to your {pokname}!")

    @skin_group.command(name="list")
    async def skin_list(self, ctx: commands.Context) -> None:
        """List your unapplied skins."""
        async with ctx.bot.db[0].acquire() as pconn:
            skins = await pconn.fetchval(
                "SELECT skins::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if skins is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        desc = ""
        for poke in sorted(skins):
            for skin, count in skins[poke].items():
                if count > 0:
                    desc += f"**{poke.title()}** | {skin} | {count}x\n"
        if not desc:
            await ctx.send("You do not have any skins.")
            return
        embed = discord.Embed(
            title="Your Skins",
            color=ctx.bot.get_random_color(),
        )
        pages = pagify(desc, per_page=20, base_embed=embed)
        await MenuView(ctx, pages).start()

    @skin_group.command(name="preview")
    async def skin_preview(self, ctx, poke: str, skin: str) -> None:
        """Preview a skin on a pokemon."""
        async with ctx.bot.db[0].acquire() as pconn:
            skins = await pconn.fetchval(
                "SELECT skins::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if skins is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        poke = poke.lower().replace(" ", "-")
        skin = skin.lower()
        if skin in BUYABLE_SKINS:
            form_poke = await ctx.bot.db[1].forms.find_one({"identifier": poke})
            if form_poke is None:
                await ctx.send("That pokemon does not exist!")
                return
            search_poke = await ctx.bot.db[1].pfile.find_one(
                {"id": form_poke["base_id"]}
            )
            while search_poke["identifier"] not in BUYABLE_SKINS[skin]:
                if search_poke["evolves_from_species_id"] == "":
                    await ctx.send(f"There is no `{skin}` skin for `{poke}`.")
                    return
                search_poke = await ctx.bot.db[1].pfile.find_one(
                    {"id": search_poke["evolves_from_species_id"]}
                )
        elif skins.get(poke, {}).get(skin, 0) < 1:
            await ctx.send(f"You do not have any {skin} skins for {poke} to preview.")
            return
        poke = poke.capitalize()
        iurl = await get_pokemon_image(poke, ctx.bot, skin=skin)
        embed = discord.Embed(
            title=f"{poke}'s {skin} skin preview",
            color=ctx.bot.get_random_color(),
        )
        embed.set_image(url=iurl)
        await ctx.send(embed=embed)

    def generate_shop(self, ctx):
        """Generates the skins available for a current user."""
        state = random.getstate()
        try:
            current_time = int(time.time() // (60 * 60 * 24 * 7))
            random.seed(ctx.author.id + current_time)
            skins = [
                skin
                for skin, release in RELEASE_PERIOD.items()
                if release <= current_time
            ]

            skins = random.sample(skins, k=3)
            result = {skin: random.sample(BUYABLE_SKINS[skin], k=5) for skin in skins}
        except Exception:
            raise
        else:
            return result
        finally:
            random.setstate(state)

    def skin_price(self, pokemon: str):
        """Returns the price of a particular pokemon in the skin shop."""
        pokemon = pokemon.capitalize()
        legend = set(LegendList + ubList)
        if pokemon in legend:
            return 160
        rare = set(starterList + pseudoList)
        if pokemon in rare:
            return 80
        common = set(pList) - legend - rare
        return 40 if pokemon in common else 404

    @skin_group.command(name="shop")
    async def skin_shop(self, ctx) -> None:
        """View the skins available to you for purchase this week."""
        async with ctx.bot.db[0].acquire() as pconn:
            shards = await pconn.fetchval(
                "SELECT skin_tokens FROM users WHERE u_id = $1", ctx.author.id
            )
        if shards is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        embed = discord.Embed(
            title="Skin Shop",
            color=random.choice(ctx.bot.colors),
            description=f"You have **{shards}** skin shards.\nSkins are available for the listed pokemon and their evolved forms.\nBuy a skin with `/skin buy`.\nApplying a shop skin to a pokemon will make it untradable.",
        )
        skins = self.generate_shop(ctx)
        for skin, pokes in skins.items():
            desc = "".join(
                f"`{poke.capitalize()}` - {self.skin_price(poke)}\n" for poke in pokes
            )

            embed.add_field(name=f'"{skin.capitalize()}" Skin', value=desc, inline=True)
        embed.set_footer(text="Options rotate every Wednesday at 8pm ET.")
        await ctx.send(embed=embed)

    @skin_group.command(name="buy")
    @tradelock
    async def skin_buy(self, ctx, poke: str, skin: str) -> None:
        """Buy a skin from your shop."""
        skin = skin.lower()
        poke = poke.lower().replace(" ", "-")

        skins = self.generate_shop(ctx)
        if skin not in skins:
            await ctx.send(
                f"You don't have the `{skin}` skin in your shop right now! View your shop with `/skin shop`."
            )
            return

        # A skin should be purchasable for a poke if it or a PRIOR EVOLUTION exists in the shop.
        # This is to avoid disincentivize evolving pokemon in order to put a skin on them later.
        search_poke = await ctx.bot.db[1].pfile.find_one({"identifier": poke})
        if search_poke is None:
            await ctx.send("That pokemon does not exist!")
            return
        while search_poke["identifier"] not in skins[skin]:
            if search_poke["evolves_from_species_id"] == "":
                await ctx.send(
                    f"You don't have a `{skin}` skin for `{poke}` in your shop right now! View your shop with `/skin shop`."
                )
                return
            search_poke = await ctx.bot.db[1].pfile.find_one(
                {"id": search_poke["evolves_from_species_id"]}
            )
        search_poke = search_poke["identifier"]

        async with ctx.bot.db[0].acquire() as pconn:
            shards = await pconn.fetchval(
                "SELECT skin_tokens FROM users WHERE u_id = $1", ctx.author.id
            )
        if shards is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        price = self.skin_price(search_poke)
        if shards < price:
            await ctx.send(
                "You do not have enough skin shards to buy that skin!\n"
                f"It costs `{price}` skin shards. You currently have `{shards}` skin shards."
            )
            return

        confirm = (
            f"Are you sure you want to buy a `{skin}` skin for `{poke}`?\n"
            f"It will cost `{price}` skin shards. You currently have `{shards}` skin shards."
        )
        if not await ConfirmView(ctx, confirm).wait():
            await ctx.send("Purchase cancelled.")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT skin_tokens, skins::json FROM users WHERE u_id = $1",
                ctx.author.id,
            )
            shards = data["skin_tokens"]
            skins = data["skins"]
            if shards < price:
                await ctx.send(
                    "You do not have enough skin shards to buy that skin!\n"
                    f"It costs `{price}` skin shards. You currently have `{shards}` skin shards."
                )
                return
            if poke not in skins:
                skins[poke] = {}
            skins[poke][skin] = skins[poke].get(skin, 0) + 1
            await pconn.execute(
                "UPDATE users SET skin_tokens = skin_tokens - $2, skins = $3::json WHERE u_id = $1",
                ctx.author.id,
                price,
                skins,
            )

        await ctx.send(f"Successfully purchased a `{skin}` skin for `{poke}`!")

    @commands.Cog.listener()
    async def on_poke_spawn(self, channel, user):
        if self.bot.botbanned(user.id):
            return
        if random.randrange(15):
            return
        async with self.bot.db[0].acquire() as pconn:
            honey = await pconn.fetchval(
                "SELECT type FROM honey WHERE channel = $1 LIMIT 1",
                channel.id,
            )
        if honey is None:
            return
        await asyncio.sleep(random.randint(30, 90))
        skin = random.choice(list(BUYABLE_SKINS.keys()))
        poke = random.choice(BUYABLE_SKINS[skin])
        await RaidSpawn(self.bot, channel, poke, skin).start()


class RaidSpawn(discord.ui.View):
    """A spawn embed for a raid spawn."""

    def __init__(self, bot, channel, poke: str, skin: str = None):
        super().__init__(timeout=120)
        self.bot = bot
        self.channel = channel
        self.poke = poke
        self.skin = skin
        self.registered = []
        self.attacked = {}
        self.state = "registering"
        self.message = None

    async def interaction_check(self, interaction):
        if self.state == "registering":
            if interaction.user in self.registered:
                await interaction.response.send_message(
                    content="You have already joined!", ephemeral=True
                )
                return False
            return True
        elif self.state == "attacking":
            if interaction.user in self.attacked:
                await interaction.response.send_message(
                    content="You have already attacked!", ephemeral=True
                )
                return False
            if interaction.user not in self.registered:
                await interaction.response.send_message(
                    content="You didn't join the battle! You can't attack this one.",
                    ephemeral=True,
                )
                return False
            return True
        else:
            await interaction.response.send_message(
                content="This battle has already ended!", ephemeral=True
            )
            return False

    async def start(self):
        pokeurl = "https://skylarr1227.github.io/images/" + await get_battle_file_name(
            self.poke, self.bot, skin=self.skin
        )
        guild = await self.bot.mongo_find("guilds", {"id": self.channel.guild.id})
        if guild is None:
            small_images = False
        else:
            small_images = guild["small_images"]
        color = random.choice(self.bot.colors)
        embed = discord.Embed(
            title="An Alpha Pokémon has spawned, join the fight to take it down!",
            color=color,
        )
        embed.add_field(name="-", value="Click the button to join!")
        if small_images:
            embed.set_thumbnail(url=pokeurl)
        else:
            embed.set_image(url=pokeurl)
        self.add_item(RaidJoin())
        self.message = await self.channel.send(embed=embed, view=self)
        await asyncio.sleep(30)
        self.clear_items()

        if not self.registered:
            embed = discord.Embed(
                title="The Alpha Pokémon ran away!",
                color=color,
            )
            if small_images:
                embed.set_thumbnail(url=pokeurl)
            else:
                embed.set_image(url=pokeurl)
            await self.message.edit(embed=embed, view=None)
            return

        # Calculate valid moves of each effectiveness tier
        form_info = await self.bot.db[1].forms.find_one(
            {"identifier": self.poke.lower()}
        )
        type_ids = (
            await self.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]})
        )["types"]
        type_effectiveness = {}
        for te in await self.bot.db[1].type_effectiveness.find({}).to_list(None):
            type_effectiveness[(te["damage_type_id"], te["target_type_id"])] = te[
                "damage_factor"
            ]
        super_types = []
        normal_types = []
        un_types = []
        for attacker_type in range(1, 19):
            effectiveness = 1
            for defender_type in type_ids:
                effectiveness *= (
                    type_effectiveness[(attacker_type, defender_type)] / 100
                )
            if effectiveness > 1:
                super_types.append(attacker_type)
            elif effectiveness < 1:
                un_types.append(attacker_type)
            else:
                normal_types.append(attacker_type)
        super_raw = (
            await self.bot.db[1]
            .moves.find(
                {"type_id": {"$in": super_types}, "damage_class_id": {"$ne": 1}}
            )
            .to_list(None)
        )
        super_moves = [
            x["identifier"].capitalize().replace("-", " ") for x in super_raw
        ]
        normal_raw = (
            await self.bot.db[1]
            .moves.find(
                {"type_id": {"$in": normal_types}, "damage_class_id": {"$ne": 1}}
            )
            .to_list(None)
        )
        normal_moves = [
            x["identifier"].capitalize().replace("-", " ") for x in normal_raw
        ]
        un_raw = (
            await self.bot.db[1]
            .moves.find({"type_id": {"$in": un_types}, "damage_class_id": {"$ne": 1}})
            .to_list(None)
        )
        un_moves = [x["identifier"].capitalize().replace("-", " ") for x in un_raw]

        # Add the moves to the view
        moves = []
        moves.append(RaidMove(random.choice(super_moves), 2))
        moves.append(RaidMove(random.choice(normal_moves), 1))
        for move in random.sample(un_moves, k=2):
            moves.append(RaidMove(move, 0))
        random.shuffle(moves)
        for move in moves:
            self.add_item(move)

        self.max_hp = int(len(self.registered) * 1.33)
        embed = discord.Embed(
            title="An Alpha Pokémon has spawned, attack it with everything you've got!",
            color=color,
        )
        embed.add_field(name="-", value=f"HP = {self.max_hp}/{self.max_hp}")
        if small_images:
            embed.set_thumbnail(url=pokeurl)
        else:
            embed.set_image(url=pokeurl)
        self.state = "attacking"
        await self.message.edit(embed=embed, view=self)

        for i in range(5):
            await asyncio.sleep(3)
            hp = max(self.max_hp - sum(self.attacked.values()), 0)
            embed.clear_fields()
            embed.add_field(name="-", value=f"HP = {hp}/{self.max_hp}")
            await self.message.edit(embed=embed)

        self.state = "ended"
        hp = max(self.max_hp - sum(self.attacked.values()), 0)
        if hp > 0:
            embed = discord.Embed(
                title="The Alpha Pokémon got away!",
                color=color,
            )
            hp = max(self.max_hp - sum(self.attacked.values()), 0)
            embed.add_field(name="-", value=f"HP = {hp}/{self.max_hp}")
            if small_images:
                embed.set_thumbnail(url=pokeurl)
            else:
                embed.set_image(url=pokeurl)
            await self.message.edit(embed=embed, view=None)
            return

        async with self.bot.db[0].acquire() as pconn:
            for attacker, damage in self.attacked.items():
                await pconn.execute(
                    "UPDATE users SET skin_tokens = skin_tokens + $1 WHERE u_id = $2",
                    damage * 2,
                    attacker.id,
                )
        embed = discord.Embed(
            title="The Alpha Pokémon was defeated! Attackers have been awarded skin tokens.",
            color=color,
        )
        if small_images:
            embed.set_thumbnail(url=pokeurl)
        else:
            embed.set_image(url=pokeurl)
        await self.message.edit(embed=embed, view=None)


class RaidJoin(discord.ui.Button):
    """A button to join an alpha pokemon raid."""

    def __init__(self):
        super().__init__(label="Join", style=discord.ButtonStyle.green)

    async def callback(self, interaction):
        self.view.registered.append(interaction.user)
        await interaction.response.send_message(
            content="You have joined the battle!", ephemeral=True
        )


class RaidMove(discord.ui.Button):
    """A move button for attacking an alpha pokemon raid."""

    def __init__(self, move, damage):
        super().__init__(
            label=move,
            style=discord.ButtonStyle.gray,
        )
        self.move = move
        self.damage = damage
        if damage == 2:
            self.effective = (
                "It's super effective! You will get 2x rewards if the poke is defeated."
            )
        elif damage == 1:
            self.effective = "It hits! You will get 1x rewards if the poke is defeated."
        else:
            self.effective = "It shrugged off your attack..."

    async def callback(self, interaction):
        self.view.attacked[interaction.user] = self.damage
        await interaction.response.send_message(
            content=f"You attack the alpha pokemon with {self.move}... {self.effective}",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Skins(bot))
