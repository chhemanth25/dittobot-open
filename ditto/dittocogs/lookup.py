import contextlib
from collections import defaultdict

import aiohttp
import discord
from discord.ext import commands

ELEMENTS = {
    "normal": 0xA9A87A,
    "fire": 0xEE7D39,
    "water": 0x6A91ED,
    "grass": 0x7BC856,
    "electric": 0xF7CF41,
    "ice": 0x9AD8D8,
    "fighting": 0xBE2C2D,
    "poison": 0x9E409F,
    "ground": 0xDFBF6E,
    "flying": 0xA891EE,
    "psychic": 0xF65689,
    "bug": 0xA8B831,
    "rock": 0xB69F40,
    "ghost": 0x705796,
    "dragon": 0x6F3CF5,
    "dark": 0x6E5849,
    "steel": 0xB8B8CF,
    "fairy": 0xF6C9E3,
}


class AbilityView(discord.ui.View):
    def __init__(self, ctx, base_embed, poke_embed):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.base_embed = base_embed
        self.poke_embed = poke_embed

    async def on_timeout(self):
        with contextlib.suppress(discord.NotFound):
            await self.message.edit(view=None)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                content="You are not allowed to interact with this button.",
                ephemeral=True,
            )
            return False
        return True

    async def on_error(self, error, item, interaction):
        await self.ctx.bot.misc.log_error(self.ctx, error)

    async def start(self):
        self.message = await self.ctx.send(embed=self.base_embed, view=self)
        return self.message

    @discord.ui.button(label="View Pokemon")
    async def view_pokes(self, button, interaction):
        await interaction.response.edit_message(embed=self.poke_embed, view=None)


class Lookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="lookup")
    async def lookup_cmds(self, ctx):
        """Top layer of group"""

    @lookup_cmds.command()
    async def move(self, ctx, move: str):
        move = move.lower().replace(" ", "-")

        # Validate the move exists, to make the API happy and to prevent injections
        exists = await ctx.bot.db[1].moves.find_one({"identifier": move})
        if exists is None:
            await ctx.send("That move does not exist!")
            return

        # Call the API to fetch the data for the move
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://pokeapi.co/api/v2/move/{move}"
            ) as response:
                if response.status != 200:
                    await ctx.send("That move does not exist!")
                    return
                data = await response.json()

        # Build the embed
        prio = data["priority"]
        pp = data["pp"]
        type = data["type"]["name"].title()
        acc = data["accuracy"]
        power = data["power"]
        dclass = data["damage_class"]["name"].title()
        desc = ""
        desc += f"**Damage Class:** `{dclass}` "
        if power:
            desc += f"| **Power:** `{power}`"
        desc += f"\n**Accuracy:** `{acc}` "
        desc += f"| **Type:** `{type}` "
        desc += f"| **PP:** `{pp}` "
        if prio:
            desc += f"\n**Priority:** `{prio}`"

        embed = discord.Embed(
            title=move.title().replace("-", " "),
            color=ELEMENTS.get(data["type"]["name"], 0x000001),
            description=desc,
        )
        effects = "".join(
            "- " + effect["short_effect"] + "\n"
            for effect in data["effect_entries"]
            if effect["language"]["name"] == "en"
        )

        if data["effect_chance"]:
            effects = effects.replace("$effect_chance", str(data["effect_chance"]))
        if effects:
            embed.add_field(name="Effect", value=effects, inline=False)

        await ctx.send(embed=embed)

    @lookup_cmds.command()
    async def ability(self, ctx, ability: str):
        ability = ability.lower().replace(" ", "-")

        # Validate the ability exists, to make the API happy and to prevent injections
        exists = await ctx.bot.db[1].abilities.find_one({"identifier": ability})
        if exists is None:
            await ctx.send("That ability does not exist!")
            return

        # Call the API to fetch the data for the ability
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://pokeapi.co/api/v2/ability/{ability}"
            ) as response:
                if response.status != 200:
                    await ctx.send("That ability does not exist!")
                    return
                data = await response.json()

        # Build the base embed
        desc = ""
        embed = discord.Embed(
            title=ability.title().replace("-", " "),
            color=0xF699CD,
            description=desc,
        )
        effects = "".join(
            "- " + effect["short_effect"] + "\n"
            for effect in data["effect_entries"]
            if effect["language"]["name"] == "en"
        )

        if not effects:
            for effect in data["flavor_text_entries"]:
                if effect["language"]["name"] == "en":
                    effects += effect["flavor_text"] + "\n"
        if effects:
            embed.add_field(name="Effect", value=effects, inline=False)

        # Build the embed of pokemon
        desc = "".join(
            pokemon["pokemon"]["name"].title() + "\n" for pokemon in data["pokemon"]
        )

        poke_embed = discord.Embed(
            title="Pokemon with " + ability.title().replace("-", " "),
            color=0xF699CD,
            description=desc,
        )

        await AbilityView(ctx, embed, poke_embed).start()

    @lookup_cmds.command()
    async def type(self, ctx, type1: str, type2: str = None):
        type_ids = {
            1: "Normal",
            2: "Fighting",
            3: "Flying",
            4: "Poison",
            5: "Ground",
            6: "Rock",
            7: "Bug",
            8: "Ghost",
            9: "Steel",
            10: "Fire",
            11: "Water",
            12: "Grass",
            13: "Electric",
            14: "Psychic",
            15: "Ice",
            16: "Dragon",
            17: "Dark",
            18: "Fairy",
        }
        type_effectiveness = {}
        for te in await ctx.bot.db[1].type_effectiveness.find({}).to_list(None):
            if te["damage_type_id"] in type_ids and te["target_type_id"] in type_ids:
                type_effectiveness[
                    (type_ids[te["damage_type_id"]], type_ids[te["target_type_id"]])
                ] = (te["damage_factor"] / 100)
        type1 = type1.title()
        types = [type1]
        if type2:
            types.append(type2.title())

        for t in types:
            if t not in type_ids.values():
                await ctx.send(f"{t} is not a valid type.")
                return

        atk_effs = defaultdict(list)
        if not type2:
            for d in type_ids.values():
                eff = 1
                eff *= type_effectiveness[(type1, d)]
                atk_effs[eff].append(d)

        def_effs = defaultdict(list)
        for a in type_ids.values():
            eff = 1
            for d in types:
                eff *= type_effectiveness[(a, d)]
            def_effs[eff].append(a)

        desc = ""

        if 4 in def_effs:
            formatted = ", ".join(def_effs[4])
            desc += f"**x4 damage from:** `{formatted}`\n"
        if 2 in def_effs:
            formatted = ", ".join(def_effs[2])
            desc += f"**x2 damage from:** `{formatted}`\n"
        if 1 in def_effs:
            formatted = ", ".join(def_effs[1])
            desc += f"**x1 damage from:** `{formatted}`\n"
        if 1 / 2 in def_effs:
            formatted = ", ".join(def_effs[1 / 2])
            desc += f"**x1/2 damage from:** `{formatted}`\n"
        if 1 / 4 in def_effs:
            formatted = ", ".join(def_effs[1 / 4])
            desc += f"**x1/4 damage from:** `{formatted}`\n"
        if 0 in def_effs:
            formatted = ", ".join(def_effs[0])
            desc += f"**Immune to damage from:** `{formatted}`\n"

        desc += "\n"

        if 2 in atk_effs:
            formatted = ", ".join(atk_effs[2])
            desc += f"**x2 damage to:** `{formatted}`\n"
        if 1 in atk_effs:
            formatted = ", ".join(atk_effs[1])
            desc += f"**x1 damage to:** `{formatted}`\n"
        if 1 / 2 in atk_effs:
            formatted = ", ".join(atk_effs[1 / 2])
            desc += f"**x1/2 damage to:** `{formatted}`\n"
        if 0 in atk_effs:
            formatted = ", ".join(atk_effs[0])
            desc += f"**Does nothing to:** `{formatted}`\n"

        embed = discord.Embed(
            title=", ".join(types),
            color=0xF699CD,
            description=desc,
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Lookup(bot))
