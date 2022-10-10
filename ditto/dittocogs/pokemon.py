import asyncio
import random

import discord
from discord.ext import commands
from utils.checks import tradelock
from utils.misc import (
    AsyncIter,
    ConfirmView,
    MenuView,
    get_emoji,
    get_pokemon_image,
    pagify,
)
from pokemon_utils.utils import get_pokemon_info, get_pokemon_qinfo

from dittocogs.json_files import *
from dittocogs.pokemon_list import *

custom_poke = (
    "Onehitmonchan",
    "Xerneas-brad",
    "Lucariosouta",
    "Cubone-freki",
    "Glaceon-glaceon",
    "Scorbunny-sav",
    "Palkia-gompp",
    "Alacatzam",
    "Magearna-curtis",
    "Arceus-tatogod",
    "Enamorus-therian-forme",
    "Kubfu-rapid-strike",
    "Palkia-lord",
    "Dialga-lord",
    "Missingno",
)

hp_display = '<:hp:1012942710870642708>'
atk_display = '<:atk:1012942628922347641><:atk2:1012942631090786395>'
def_display = '<:def:1012942478241972304><:def2:1012942479848394824><:def3:1012942481236697160>'
spa_display = '<:spatk:1012942190743388251><:spatk2:1012942192576299098><:spatk3:1012942194228867102><:spatk4:1012942195889803304>'
spd_display = '<:spdef:1012941983339257898><:spdef2:1012941985331552353><:spdef3:1012941987130900530><:spdef4:1012941988687003710>'
spe_display = '<:speed:1012942353172021280><:speed2:1012942358205181972>'

emoji_dict = {
    "0": "<:0:1013539754756800553>",
    "1": "<:1:1013539737014907030>",
    "2": "<:2:1013539739263041618>",
    "3": "<:3:1013539741502812310>",
    "4": "<:4:1013539744027783208>",
    "5": "<:5:1013539745692909740>",
    "6": "<:6:1013539747517444208>",
    "7": "<:7:1013539749035786291>",
    "8": "<:8:1013539750596071524>",
    "9": "<:9:1013539753221697597> ",
    }

class Pokemon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.forms_cursor = bot.db[1].forms.find()

    async def parse_form(self, form):
        form = form.lower()
        if (
            "-" not in form
            or form.startswith("tapu-")
            or form.startswith("ho-")
            or form.startswith("mr-")
            or form.startswith("nidoran-")
        ):
            return form
        if form in (await self.forms_cursor.distinct("identifier")):
            return form
        if is_formed(form) and form.split("-")[1] in (
            await self.forms_cursor.distinct("form_identifier")
        ):
            return form
        # possible 'mega charizard' 'mega charizard x' expecting 'charizard mega x' or 'charizard mega'
        form = list(form.split("-"))
        form[0], form[1] = form[1], form[0]
        form = "-".join(form)
        return form

    @commands.hybrid_group(name="pokedex")
    async def pokedex_cmds(self, ctx):
        """Top layer of group"""

    @pokedex_cmds.command()
    async def national(self, ctx):
        await self._build_pokedex(ctx, True)

    @pokedex_cmds.command()
    async def unowned(self, ctx):
        await self._build_pokedex(ctx, False)

    async def _build_pokedex(self, ctx, include_owned: bool):
        """Helper func to build & send the pokedex."""
        async with self.bot.db[0].acquire() as pconn:
            pokes = await pconn.fetchval(
                "SELECT pokes FROM users WHERE u_id = $1", ctx.author.id
            )
            if pokes is None:
                return
            owned = await pconn.fetch(
                "SELECT DISTINCT pokname FROM pokes WHERE id = ANY($1) AND pokname != ANY($2)",
                pokes,
                custom_poke,
            )
        allpokes = self.bot.db[1].pfile.find(
            projection={"identifier": True, "_id": False}
        )
        allpokes = await allpokes.to_list(None)
        allpokes = [t["identifier"].capitalize() async for t in AsyncIter(allpokes)]
        total = set(allpokes) - set(custom_poke)
        owned = set([t["pokname"] async for t in AsyncIter(owned)])
        owned &= total
        desc = ""
        async for poke in AsyncIter(allpokes):
            if poke not in total:
                continue
            if poke not in owned:
                desc += f"**{poke}** - <a:cuscross:529192535642603530>\n"
            elif include_owned:
                desc += f"**{poke}** - <a:cuscheck:534740177147396097>\n"
        embed = discord.Embed(
            title=f"You have {len(owned)} out of {len(total)} available Pokemon!",
            colour=random.choice(self.bot.colors),
        )
        if len(owned) == len(total):
            async with self.bot.db[0].acquire() as pconn:
                completed = await pconn.fetchval("SELECT dex_complete from achievements WHERE u_id = $1", ctx.author.id)
                if not completed:
                    await pconn.execute("UPDATE achievements SET dex_complete = true WHERE u_id = $1", ctx.author.id)
                    await ctx.send(f"CONGRATULATIONS! You have completed the entire Pokedex by catching one of each pokemon plus all their forms!!! Join the official server (https://discord.gg/ditto) and ask the staff team about your reward!")
                    await self.bot.get_partial_messageable(1004311737706754088).send(f"{ctx.author} (`{ctx.author.id}`) has completed the entire pokedex!! <@&1004222018310389780>")
        pages = pagify(desc, per_page=20, base_embed=embed)
        await MenuView(ctx, pages).start()

    @commands.hybrid_command()
    async def select(self, ctx, poke_id: str):
        """Select a pokemon by ID number from your pokemon list"""
        async with self.bot.db[0].acquire() as pconn:
            if poke_id in {"newest", "new", "latest"}:
                _id = await pconn.fetchval(
                    "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1",
                    ctx.author.id,
                )
            else:
                try:
                    poke_id = int(poke_id)
                except ValueError:
                    await ctx.send("`/select <pokemon_number>` to select a Pokemon!")
                    return
                if poke_id > 2147483647:
                    await ctx.send("You do not have that many pokemon!")
                    return
                _id = await pconn.fetchval(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2", poke_id, ctx.author.id
                )
            if _id is None:
                await ctx.send("You have not started or that Pokemon does not exist!")
                return
            else:
                name = await pconn.fetchval(
                    "SELECT pokname FROM pokes WHERE id = $1", _id
                )
                await pconn.execute(
                    "UPDATE users SET selected = $1 WHERE u_id = $2", _id, ctx.author.id
                )
            emoji = random.choice(emotes)
            await ctx.send(f"You have selected your {name}\n{emoji}")

    @commands.hybrid_command()
    @tradelock
    async def release(self, ctx, pokemon):
        pokes = []
        if pokemon.lower() in ("new", "latest"):
            async with self.bot.db[0].acquire() as pconn:
                poke = await pconn.fetchval(
                    "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1 AND array_length(pokes, 1) > 1",
                    ctx.author.id,
                )
                if poke is None:
                    await ctx.send("You don't have any pokemon you can release!")
                    return
                pokes.append(poke)
        else:
            async with self.bot.db[0].acquire() as pconn:
                stmt = await pconn.prepare(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2"
                )
                for p in pokemon.split():
                    try:
                        p = int(p)
                        if p <= 1:
                            continue
                        id = await stmt.fetchval(p, ctx.author.id)
                        if not id:
                            continue
                        pokes.append(id)
                    except ValueError:
                        continue
            if not pokes:
                await ctx.send("You did not specify any valid pokemon!")
                return
        async with self.bot.db[0].acquire() as pconn:
            pokenames = []
            favorites = []
            valid_pokes = []
            for p in await pconn.fetch(
                "SELECT id, pokname, fav, COALESCE(atkiv,0) + COALESCE(defiv,0) + COALESCE(spatkiv,0) + COALESCE(spdefiv,0) + COALESCE(speediv,0) + COALESCE(hpiv,0) AS ivs FROM pokes WHERE id = ANY ($1)",
                pokes,
            ):
                if p["fav"]:
                    favorites.append(p["pokname"])
                else:
                    pokenames.append(f'{p["pokname"]} ({p["ivs"]/186:06.2%})')
                    valid_pokes.append(p["id"])
        if favorites:
            await ctx.send(
                f"You cannot release your {', '.join(favorites).capitalize()} as they are favorited.\n"
                f"Unfavorite them first with `/fav remove <poke>`."
            )
        if not pokenames:
            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to release your {', '.join(pokenames).capitalize()}?",
        ).wait():
            await ctx.send("Release cancelled.")
            return
        for poke_id in valid_pokes:
            await self.bot.commondb.remove_poke(ctx.author.id, poke_id, delete=False)
        await ctx.send(
            f"You have successfully released your {', '.join(pokenames).capitalize()}"
        )
        await self.bot.get_partial_messageable(1005805097235775538).send(
            f"{ctx.author} (`{ctx.author.id}`) released **{len(valid_pokes)}** pokes.\n`{valid_pokes}`"
        )
        released_pokes = int(len(valid_pokes))
        async with self.bot.db[0].acquire() as pconn:
            await pconn.execute("UPDATE achievements SET pokemon_released = pokemon_released + $2 WHERE u_id = $1", ctx.author.id, released_pokes)

    @commands.hybrid_command()
    async def cooldowns(self, ctx):
        await ctx.send(
            "This command is deprecated, you should use `/f p args:cooldown` instead. "
            "It has the same functionality, but with a fresh output and the ability to use additional filters.\n"
            "Running that for you now..."
        )
        await asyncio.sleep(3)
        c = ctx.bot.get_cog("Filter")
        if c is None:
            return
        await c.filter_pokemon.callback(c, ctx, args="cooldown")
        return

    @commands.hybrid_command()
    async def p(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            pokes = await pconn.fetchval(
                "SELECT pokes FROM users WHERE u_id = $1", ctx.author.id
            )
            if pokes is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            user_order = await pconn.fetchval(
                "SELECT user_order FROM users WHERE u_id = $1", ctx.author.id
            )

        orders = {
            "iv": "ORDER by ivs DESC",
            "level": "ORDER by pokelevel DESC",
            "ev": "ORDER by evs DESC",
            "name": "order by pokname DESC",
            "kek": "",
        }
        order = orders.get(user_order)
        query = f"""SELECT *, COALESCE(atkiv,0) + COALESCE(defiv,0) + COALESCE(spatkiv,0) + COALESCE(spdefiv,0) + COALESCE(speediv,0) + COALESCE(hpiv,0) AS ivs, COALESCE(atkev,0) + COALESCE(defev,0) + COALESCE(spatkev,0) + COALESCE(spdefev,0) + COALESCE(speedev,0) + COALESCE(hpev,0) AS evs FROM pokes WHERE id = ANY ($1) {order}"""

        async with self.bot.db[0].acquire() as pconn:
            async with pconn.transaction():
                cur = await pconn.cursor(query, pokes)
                records = await cur.fetch(15 * 250)

        desc = ""
        async for record in AsyncIter(records):
            nr = record["pokname"]
            pn = pokes.index(record["id"]) + 1
            record["poknick"]
            iv = record["ivs"]
            shiny = record["shiny"]
            radiant = record["radiant"]
            level = record["pokelevel"]
            emoji = get_emoji(
                blank="<:blank:942623726715936808>",
                shiny=shiny,
                radiant=radiant,
                skin=record["skin"],
            )
            gender = ctx.bot.misc.get_gender_emote(record["gender"])
            desc += f"{emoji}{gender}**{nr.capitalize()}** | **__No.__** - {pn} | **Level** {level} | **IV%** {iv/186:.2%}\n"

        embed = discord.Embed(title="Your Pokemon", color=0xFFB6C1)
        pages = pagify(desc, base_embed=embed)
        await MenuView(ctx, pages).start()

    @commands.hybrid_group(name="tags")
    async def tags_cmds(self, ctx):
        """Top layer of group"""

    @tags_cmds.command()
    async def list(self, ctx, poke: str):
        """View the tags for a pokemon."""
        async with self.bot.db[0].acquire() as pconn:
            if poke.lower() in {"new", "latest"}:
                gid = await pconn.fetchval(
                    "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1 AND array_length(pokes, 1) > 1",
                    ctx.author.id,
                )
            else:
                try:
                    poke = int(poke)
                except ValueError:
                    await ctx.send("You need to provide a valid pokemon number.")
                    return
                gid = await pconn.fetchval(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2", poke, ctx.author.id
                )
            if gid is None:
                await ctx.send("That pokemon does not exist!")
                return
            tags = await pconn.fetchval("SELECT tags FROM pokes WHERE id = $1", gid)
        if not tags:
            await ctx.send(
                f"That pokemon has no tags! Use `/tags add <tag> {poke}` to add one!"
            )
            return
        tags = ", ".join(tags)
        tags = f"**Current tags:** {tags}"
        pages = pagify(tags, sep=", ", per_page=30)
        await MenuView(ctx, pages).start()

    @tags_cmds.command()
    async def add(self, ctx, tag: str, pokes: str):
        """Add a tag to a pokemon."""
        tag = tag.lower().strip()
        pokes = pokes.split(" ")
        if " " in tag:
            await ctx.send("Tags cannot have spaces!")
            return
        if len(tag) > 50:
            await ctx.send("That tag is too long!")
            return
        failed = []
        async with ctx.bot.db[0].acquire() as pconn:
            for poke in pokes:
                if poke.lower() in ("new", "latest"):
                    gid = await pconn.fetchval(
                        "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1 AND array_length(pokes, 1) > 1",
                        ctx.author.id,
                    )
                else:
                    try:
                        poke = int(poke)
                    except ValueError:
                        failed.append(str(poke))
                        continue
                    gid = await pconn.fetchval(
                        "SELECT pokes[$1] FROM users WHERE u_id = $2",
                        poke,
                        ctx.author.id,
                    )
                if gid is None:
                    failed.append(str(poke))
                    continue
                tags = await pconn.fetchval("SELECT tags FROM pokes WHERE id = $1", gid)
                try:
                    tags = set(tags)
                except TypeError:
                    failed.append(str(poke))
                    continue
                tags.add(tag)
                await pconn.execute(
                    "UPDATE pokes SET tags = $1 WHERE id = $2", list(tags), gid
                )
        if len(failed) == len(pokes) == 1:
            await ctx.send("That pokemon does not exist!")
        elif len(failed) == len(pokes):
            await ctx.send("Those pokemon do not exist!")
        elif failed:
            await ctx.send(
                f"Tag successfully added to existing pokemon. The following pokemon I could not find: {', '.join(failed)}"
            )
        else:
            await ctx.send("Tag successfully added.")

    @tags_cmds.command()
    async def remove(self, ctx, tag: str, pokes: str):
        """Remove a tag from a pokemon."""
        tag = tag.lower().strip()
        pokes = pokes.split(" ")
        if " " in tag:
            await ctx.send("Tags cannot have spaces!")
            return
        not_exist = []
        dont_have_tag = []

        async with ctx.bot.db[0].acquire() as pconn:
            for poke in pokes:
                if poke.lower() in ("new", "latest"):
                    gid = await pconn.fetchval(
                        "SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1 AND array_length(pokes, 1) > 1",
                        ctx.author.id,
                    )
                else:
                    try:
                        poke = int(poke)
                    except ValueError:
                        not_exist.append(str(poke))
                        continue
                    gid = await pconn.fetchval(
                        "SELECT pokes[$1] FROM users WHERE u_id = $2",
                        poke,
                        ctx.author.id,
                    )
                if gid is None:
                    not_exist.append(str(poke))
                    continue
                tags = await pconn.fetchval("SELECT tags FROM pokes WHERE id = $1", gid)
                try:
                    tags = set(tags)
                except TypeError:
                    not_exist.append(str(poke))
                    continue
                if tag not in tags:
                    dont_have_tag.append(str(poke))
                    continue
                tags.remove(tag)
                await pconn.execute(
                    "UPDATE pokes SET tags = $1 WHERE id = $2", list(tags), gid
                )
        # I don't know why I did this
        if (len(not_exist) + len(dont_have_tag) == len(pokes)) and (
            not_exist and dont_have_tag
        ):
            await ctx.send(
                f"Failed to remove tags from specified pokemon. The following pokemon could not be found: {', '.join(not_exist)}. "
                f"The following pokemon did not have that tag: {', '.join(dont_have_tag)}."
            )
        elif len(not_exist) == len(pokes) == 1:
            await ctx.send("That pokemon does not exist!")
        elif len(not_exist) == len(pokes):
            await ctx.send("Those pokemon do not exist!")
        elif len(dont_have_tag) == len(pokes) == 1:
            await ctx.send("That pokemon does not have that tag!")
        elif len(dont_have_tag) == len(pokes):
            await ctx.send("Those pokemon do not have that tag!")
        elif not_exist and dont_have_tag:
            await ctx.send(
                f"Tag successfully removed from existing pokemon that had the tag.  The following pokemon could not be found: {', '.join(not_exist)}. "
                f"The following pokemon did not have that tag: {', '.join(dont_have_tag)}."
            )
        elif not_exist:
            await ctx.send(
                f"Tag successfully removed from existing pokemon. The following pokemon could not be found: {', '.join(not_exist)}."
            )
        elif dont_have_tag:
            await ctx.send(
                f"Tag successfully removed from pokemon with that tag.  The following pokemon did not have that tag: {', '.join(dont_have_tag)}."
            )
        else:
            await ctx.send("Tag successfully removed.")

    async def get_reqs(self, poke):
        """Gets a string formatted to be used to display evolution requirements for a particular pokemon."""
        reqs = []
        evoreq = await self.bot.db[1].evofile.find_one({"evolved_species_id": poke})
        if evoreq["trigger_item_id"]:
            item = await self.bot.db[1].items.find_one(
                {"id": evoreq["trigger_item_id"]}
            )
            reqs.append(f"apply `{item['identifier']}`")
        if evoreq["held_item_id"]:
            item = await self.bot.db[1].items.find_one({"id": evoreq["held_item_id"]})
            reqs.append(f"hold `{item['identifier']}`")
        if evoreq["gender_id"]:
            reqs.append(f"is `{'female' if evoreq['gender_id'] == 1 else 'male'}`")
        if evoreq["minimum_level"]:
            reqs.append(f"lvl `{evoreq['minimum_level']}`")
        if evoreq["known_move_id"]:
            move = await self.bot.db[1].moves.find_one({"id": evoreq["known_move_id"]})
            reqs.append(f"knows `{move['identifier']}`")
        if evoreq["minimum_happiness"]:
            reqs.append(f"happiness `{evoreq['minimum_happiness']}`")
        if evoreq["relative_physical_stats"] is not None:
            if evoreq["relative_physical_stats"] == 0:
                reqs.append("atk = def")
            elif evoreq["relative_physical_stats"] == 1:
                reqs.append("atk > def")
            elif evoreq["relative_physical_stats"] == -1:
                reqs.append("atk < def")
        if evoreq["region"]:
            reqs.append(f"region `{evoreq['region']}`")
        reqs = ", ".join(reqs)
        return f"({reqs})"

    async def get_kids(self, raw, species_id, prefix):
        """Recursively build an evolution tree for a particular species."""
        result = ""
        for poke in raw:
            if poke["evolves_from_species_id"] == species_id:
                reqs = ""
                if species_id != "":
                    reqs = await self.get_reqs(poke["id"])
                result += f"{prefix}├─{poke['identifier']} {reqs}\n"
                result += await self.get_kids(raw, poke["id"], f"{prefix}│ ")
        return result

    @commands.hybrid_command(name="i")
    @discord.app_commands.describe(
        poke="The pokemon number, or 'new'. Otherwise selected pokemon is used instead"
    )
    async def info(self, ctx, poke: str = None):
        """Get information about a pokemon."""
        pokemon = poke
        if pokemon is None:
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                    ctx.author.id,
                )
            if records is None:
                await ctx.send(
                    "You do not have a pokemon selected. Use `/select` to select one!"
                )

                return
            await ctx.send(embed=await get_pokemon_info(ctx, records))
            return

        if pokemon in {"newest", "latest", "atest", "ewest", "new"}:
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1)",
                    ctx.author.id,
                )
            if records is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            await ctx.send(embed=await get_pokemon_info(ctx, records))
            return

        try:
            pokemon = int(pokemon)
        except ValueError:
            pass
        else:
            if pokemon < 1:
                await ctx.send("That is not a valid pokemon number!")
                return
            if pokemon > 4000000000:
                await ctx.send("You probably don't have that many pokemon...")
                return
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT pokes[$1] FROM users WHERE u_id = $2)",
                    pokemon,
                    ctx.author.id,
                )
            if records is None:
                await ctx.send(
                    "You do not have that many pokemon. Go catch some more first!"
                )
                return
            await ctx.send(embed=await get_pokemon_info(ctx, records))
            return

        # "pokemon" is *probably* a pokemon name
        pokemon = pokemon.lower().replace("alolan", "alola").split()
        shiny = False
        radiant = False
        skin = None
        if "shiny" in pokemon:
            shiny = True
            pokemon.remove("shiny")
        elif "radiant" in pokemon:
            radiant = True
            pokemon.remove("radiant")
        elif "shadow" in pokemon and pokemon.index("shadow") == 0:
            skin = "shadow"
            pokemon.remove("shadow")
        pokemon = "-".join(pokemon)
        val = pokemon.capitalize()
        try:
            val = await self.parse_form(val)
            iurl = await get_pokemon_image(
                val, ctx.bot, shiny, radiant=radiant, skin=skin
            )
        except ValueError:
            await ctx.send("That Pokemon does not exist!")
            return

        forms = []
        if val.lower() in ("spewpa", "scatterbug", "mew"):
            forms = ["None"]
        else:
            # TODO: This is potentially VERY dangerous since this is user input directed to a regex pattern.
            cursor = ctx.bot.db[1].forms.find({"identifier": {"$regex": f".*{val}.*"}})
            forms = [t.capitalize() for t in await cursor.distinct("form_identifier")]

        if "" in forms:
            forms.remove("")
        if "Galar" in forms:
            forms.remove("Galar")
        if "Alola" in forms:
            forms.remove("Alola")
        if "Hisui" in forms:
            forms.remove("Hisui")
        if not forms:
            forms = ["None"]
        forms = "\n".join(forms)

        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        if not form_info:
            await ctx.send("<:error:1009448089930694766> That Pokemon does not exist! <:error:1009448089930694766>")
            return
        ptypes = await ctx.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]})
        if not ptypes:
            await ctx.send("<:error:1009448089930694766> That Pokemon does not exist! <:error:1009448089930694766>")
            return
        type_ids = ptypes["types"]
        types = [
            str(
                ctx.bot.misc.get_type_emote(
                    (await ctx.bot.db[1].types.find_one({"id": _type}))["identifier"]
                )
            )
            for _type in type_ids
        ]
        try:
            egg_groups_ids = (
                await ctx.bot.db[1].egg_groups.find_one(
                    {"species_id": form_info["pokemon_id"]}
                )
            )["egg_groups"]
        except:
            egg_groups_ids = [15]

        egg_groups = [
            str(
                ctx.bot.misc.get_egg_emote(
                    (
                        await ctx.bot.db[1].egg_groups_info.find_one(
                            {"id": egg_group_id}
                        )
                    )["identifier"]
                )
            )
            for egg_group_id in egg_groups_ids
        ]

        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        ab_ids[0]
        abilities = [
            (await ctx.bot.db[1].abilities.find_one({"id": ab_id}))["identifier"]
            for ab_id in ab_ids
        ]

        # Stats
        pokemon_stats = await ctx.bot.db[1].pokemon_stats.find_one(
            {"pokemon_id": form_info["pokemon_id"]}
        )
        if not pokemon_stats:
            await ctx.send("<:error:1009448089930694766> That Pokemon does not exist! <:error:1009448089930694766>")
            return
        stats = pokemon_stats["stats"]
        pokemonSpeed = stats[5]
        pokemonSpd = stats[4]
        pokemonSpa = stats[3]
        pokemonDef = stats[2]
        pokemonAtk = stats[1]
        pokemonHp = stats[0]
        tlist = ", ".join(types)
        egg_groups = ", ".join(egg_groups)
        stats_str = (
            f"{hp_display} `{pokemonHp}`\n"
            f"{atk_display} `{pokemonAtk}`\n"
            f"{def_display} `{pokemonDef}`\n"
            f"{spa_display} `{pokemonSpa}`\n"
            f"{spd_display} `{pokemonSpd}`\n"
            f"{spe_display} `{pokemonSpeed}`"
        )

        # Evolution line / Catch Rate
        evo_line = ""
        catch_rate = ""
        form_suffix = form_info["form_identifier"]
        if form_suffix in ("alola", "galar", "hisui"):
            form_suffix = ""
        base_name = val.lower().replace(form_suffix, "").strip("-")
        pfile = await ctx.bot.db[1].pfile.find_one({"identifier": base_name})
        if pfile is not None:
            raw_evos = (
                await ctx.bot.db[1]
                .pfile.find({"evolution_chain_id": pfile["evolution_chain_id"]})
                .to_list(None)
            )
            evo_line = await self.get_kids(raw_evos, "", "")
            evo_line = f"**Evolution Line**:\n{evo_line}"
            catch_rate = f"**Catch rate**: {pfile['capture_rate']}\n"

        # Weight
        weight = f'{form_info["weight"] / 10:.1f} kg'

        if "arceus-" in val.lower():
            tlist = val.split("-")[1]
        emoji = get_emoji(
            shiny=shiny,
            radiant=radiant,
            skin=skin,
        )
        val = val.capitalize()
        embed = discord.Embed(
            title=f"{emoji}{val}", description="", color=random.choice(ctx.bot.colors)
        )
        abilities = ", ".join(abilities).capitalize()
        forms = forms.capitalize()
        embed.add_field(
            name="Pokemon information",
            value=(
                f"**Abilities**: {abilities}\n"
                f"**Types**: {tlist}\n"
                f"**Egg Groups**: {egg_groups}\n"
                f"**Weight**: {weight}\n"
                f"{catch_rate}"
                f"**Stats**\n{stats_str}\n"
                f"**Available Forms**:\n{forms}\n"
            ),
        )
        embed.add_field(name="Evolution Line", value=evo_line,)
        embed.set_footer(
            text="Evolve to any of the forms by using /form (form name) - Upvote DittoBOT"
        )

        embed.set_image(url=iurl)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="qi")
    async def qinfo(self, ctx, poke: str = None):
        pokemon = poke
        if pokemon is None:
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                    ctx.author.id,
                )
            if records is None:
                await ctx.send(
                    "You do not have a pokemon selected. Use `/select` to select one!"
                )

                return
            await ctx.send(embed=await get_pokemon_qinfo(ctx, records))
            return

        if pokemon in {"newest", "latest", "atest", "ewest", "new"}:
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1)",
                    ctx.author.id,
                )
            await ctx.send(embed=await get_pokemon_qinfo(ctx, records))
            return

        try:
            pokemon = int(pokemon)
        except ValueError:
            pass
        else:
            if pokemon < 1:
                await ctx.send("That is not a valid pokemon number!")
                return
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT pokes[$1] FROM users WHERE u_id = $2)",
                    pokemon,
                    ctx.author.id,
                )
            if records is None:
                await ctx.send(
                    "You do not have that many pokemon. Go catch some more first!"
                )
                return
            await ctx.send(embed=await get_pokemon_qinfo(ctx, records))
            return

        # "pokemon" is *probably* a pokemon name
        pokemon = pokemon.lower().replace("alolan", "alola").split()
        shiny = "shiny" in pokemon
        radiant = "radiant" in pokemon
        if shiny:
            pokemon.remove("shiny")
        if radiant:
            pokemon.remove("radiant")
        pokemon = "-".join(pokemon)
        val = pokemon.capitalize()
        try:
            val = await self.parse_form(val)
            iurl = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        except ValueError:
            await ctx.send("That Pokemon does not exist!")
            return
        forms = []
        if val.lower() in ("spewpa", "scatterbug"):
            forms = ["None"]
        else:
            # TODO: This is potentially VERY dangerous since this is user input directed to a regex pattern.
            cursor = ctx.bot.db[1].forms.find({"identifier": {"$regex": f".*{val}.*"}})
            forms = [t.capitalize() for t in await cursor.distinct("form_identifier")]
        forms = "\n".join(forms)

        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        if not form_info:
            await ctx.send("That Pokemon does not exist!")
            return
        ptypes = await ctx.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]})
        if not ptypes:
            await ctx.send("That Pokemon does not exist!")
            return
        type_ids = ptypes["types"]
        types = [
            (await ctx.bot.db[1].types.find_one({"id": _type}))["identifier"]
            for _type in type_ids
        ]

        pokemon_stats = await ctx.bot.db[1].pokemon_stats.find_one(
            {"pokemon_id": form_info["pokemon_id"]}
        )
        if not pokemon_stats:
            await ctx.send("That Pokemon does not exist!")
            return
        stats = pokemon_stats["stats"]

        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        ab_ids[0]
        abilities = [
            (await ctx.bot.db[1].abilities.find_one({"id": ab_id}))["identifier"]
            for ab_id in ab_ids
        ]
        pokemonSpeed = stats[5]
        pokemonSpd = stats[4]
        pokemonSpa = stats[3]
        pokemonDef = stats[2]
        pokemonAtk = stats[1]
        pokemonHp = stats[0]
        tlist = ", ".join(types)

        if "arceus-" in val.lower():
            tlist = val.split("-")[1]
        emoji = get_emoji(
            shiny=shiny,
            radiant=radiant,
        )
        val = val.capitalize()
        embed = discord.Embed(
            title=f"{emoji}{val}", description="", color=random.choice(ctx.bot.colors)
        )
        abilities = ", ".join(abilities).capitalize()
        forms = forms.capitalize()
        embed.add_field(name="Types", value=f"`{tlist}`")
        embed.add_field(
            name="Base Stats",
            value=f"**HP:** `{pokemonHp}` | **Atk.:** `{pokemonAtk}` | **Def.:** `{pokemonDef}`\n**Sp.Atk.:** `{pokemonSpa}` | **Sp.Def.:** `{pokemonSpd}` | **Speed:** `{pokemonSpeed}`",
        )
        embed.set_footer(text="Quick information - Use /i for full info")
        # embed.set_image(url=iurl)
        await ctx.send(embed=embed)


    @commands.hybrid_command(name="qi2")
    async def qinfo2(self, ctx, poke: str = None):
        pokemon = poke
        if pokemon is None:
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                    ctx.author.id,
                )
            if records is None:
                await ctx.send(
                    "You do not have a pokemon selected. Use `/select` to select one!"
                )

                return
            await ctx.send(embed=await get_pokemon_qinfo(ctx, records))
            return

        if pokemon in {"newest", "latest", "atest", "ewest", "new"}:
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT pokes[array_upper(pokes, 1)] FROM users WHERE u_id = $1)",
                    ctx.author.id,
                )
            await ctx.send(embed=await get_pokemon_qinfo(ctx, records))
            return

        try:
            pokemon = int(pokemon)
        except ValueError:
            pass
        else:
            if pokemon < 1:
                await ctx.send("That is not a valid pokemon number!")
                return
            async with ctx.bot.db[0].acquire() as pconn:
                records = await pconn.fetchrow(
                    "SELECT * FROM pokes WHERE id = (SELECT pokes[$1] FROM users WHERE u_id = $2)",
                    pokemon,
                    ctx.author.id,
                )
            if records is None:
                await ctx.send(
                    "You do not have that many pokemon. Go catch some more first!"
                )
                return
            await ctx.send(embed=await get_pokemon_qinfo(ctx, records))
            return

        # "pokemon" is *probably* a pokemon name
        pokemon = pokemon.lower().replace("alolan", "alola").split()
        shiny = "shiny" in pokemon
        radiant = "radiant" in pokemon
        if shiny:
            pokemon.remove("shiny")
        if radiant:
            pokemon.remove("radiant")
        pokemon = "-".join(pokemon)
        val = pokemon.capitalize()
        try:
            val = await self.parse_form(val)
            iurl = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        except ValueError:
            await ctx.send("That Pokemon does not exist!")
            return
        forms = []
        if val.lower() in ("spewpa", "scatterbug"):
            forms = ["None"]
        else:
            # TODO: This is potentially VERY dangerous since this is user input directed to a regex pattern.
            cursor = ctx.bot.db[1].forms.find({"identifier": {"$regex": f".*{val}.*"}})
            forms = [t.capitalize() for t in await cursor.distinct("form_identifier")]
        forms = "\n".join(forms)

        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        if not form_info:
            await ctx.send("That Pokemon does not exist!")
            return
        ptypes = await ctx.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]})
        if not ptypes:
            await ctx.send("That Pokemon does not exist!")
            return
        type_ids = ptypes["types"]
        types = [
            (await ctx.bot.db[1].types.find_one({"id": _type}))["identifier"]
            for _type in type_ids
        ]

        pokemon_stats = await ctx.bot.db[1].pokemon_stats.find_one(
            {"pokemon_id": form_info["pokemon_id"]}
        )
        if not pokemon_stats:
            await ctx.send("That Pokemon does not exist!")
            return
        stats = pokemon_stats["stats"]

        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        ab_ids[0]
        abilities = [
            (await ctx.bot.db[1].abilities.find_one({"id": ab_id}))["identifier"]
            for ab_id in ab_ids
        ]
        pokemonSpeed = stats[5]
        pokemonSpd = stats[4]
        pokemonSpa = stats[3]
        pokemonDef = stats[2]
        pokemonAtk = stats[1]
        pokemonHp = stats[0]
        tlist = ", ".join(types)

        if "arceus-" in val.lower():
            tlist = val.split("-")[1]
        emoji = get_emoji(
            shiny=shiny,
            radiant=radiant,
        )
        val = val.capitalize()
        embed = discord.Embed(
            title=f"{emoji}{val}", description="", color=random.choice(ctx.bot.colors)
        )
        abilities = ", ".join(abilities).capitalize()
        forms = forms.capitalize()
        speed_emoji = ""
        atk_emoji = ""
        def_emoji = ""
        spdef_emoji = ""
        spatk_emoji = ""
        hp_emoji = ""
        for char in str(pokemonSpeed):
            speed_emoji += emoji_dict[char]
        for char in str(pokemonSpd):
            spdef_emoji += emoji_dict[char]
        for char in str(pokemonSpa):
            spatk_emoji += emoji_dict[char]
        for char in str(pokemonDef):
            def_emoji += emoji_dict[char]
        for char in str(pokemonAtk):
            atk_emoji += emoji_dict[char]
        for char in str(pokemonHp):
            hp_emoji += emoji_dict[char]
        embed.add_field(name="Types", value=f"`{tlist}`")
        embed.add_field(
            name="Base Stats",
            value=f"**HP:** {hp_emoji} | **Atk.:** {atk_emoji} | **Def.:** {def_emoji}\n**Sp.Atk.:** {spatk_emoji} | **Sp.Def.:** {spdef_emoji} | **Speed:** {speed_emoji}",
        )
        embed.set_footer(text="Quick information - Use /i for full info")
        # embed.set_image(url=iurl)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pokemon(bot))
