import asyncio
import inspect
import os
import random
import re
import subprocess
import typing

import discord
import orjson
from discord.ext import commands
from dotenv import load_dotenv
from utils.checks import OWNER_IDS
from utils.misc import get_pokemon_image

from dittocogs.json_files import *
from dittocogs.pokemon_list import *


def hasNumber(inputString):
    return any(char.isdigit() for char in inputString)


GREEN = "\N{LARGE GREEN CIRCLE}"
YELLOW = "\N{LARGE YELLOW CIRCLE}"
RED = "\N{LARGE RED CIRCLE}"


class Dylee(commands.Cog):
    def __init__(self):
        self.safe_edb = ""

    async def _restart_bot(self, bot):
        try:
            await aiosession.close()
        except:
            pass
        await bot.logout()
        subprocess.call([sys.executable, "-m", "mew"])

    async def cog_check(self, ctx):
        return ctx.author.id in OWNER_IDS

    def get_insert_query(self, val, ivs, evs, level, shiny, gender):
        hpiv = ivs[0]
        atkiv = ivs[1]
        defiv = ivs[2]
        spaiv = ivs[3]
        spdiv = ivs[4]
        speiv = ivs[5]
        rnat = random.choice(natlist)

        if shiny is not True:
            shiny_chance = random.randint(1, 8000)
            shiny_chance2 = random.randint(1, 41)
            if shiny_chance == shiny_chance2:
                shiny = True
            else:
                shiny = False
        try:
            pkid = [i["pokemon_id"] for i in FORMS if i["identifier"] == val.lower()][0]
            tids = [i["type_id"] for i in PTYPES[str(pkid)]]
            ab_ids = [
                t["ability_id"] for t in POKE_ABILITIES if t["pokemon_id"] == int(pkid)
            ]
            if len(tids) == 2:
                id1 = [i["identifier"] for i in TYPES if i["id"] == tids[0]][0]
                id2 = [i["identifier"] for i in TYPES if i["id"] == tids[1]][0]
            else:
                id1 = [i["identifier"] for i in TYPES if i["id"] == tids[0]][0]
                id2 = "None"
        except:
            id1 = "None"
            id2 = "None"
            ab_ids = [0]
        query2 = """
            INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, move1, move2, move3, move4, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, happiness, fav, type1, type2, ability_index, gender)

            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32) RETURNING id
            """

        args = (
            val,
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            evs[0],
            evs[1],
            evs[2],
            evs[3],
            evs[4],
            evs[5],
            level,
            "tackle",
            "tackle",
            "tackle",
            "tackle",
            "None",
            0,
            rnat,
            35,
            "None",
            shiny,
            0,
            False,
            0,
            False,
            id1.capitalize(),
            id2.capitalize(),
            ab_ids.index(random.choice(ab_ids)),
            gender,
        )
        return query2, args

    def get_stats(self, msg):
        msg = (
            msg.replace("|0", "| 0")
            .replace("|2", "| 2")
            .replace("|1", "| 1")
            .replace("|3", "| 3")
            .replace("|3", "| 3")
            .replace("|4", "| 4")
            .replace("|5", "| 5")
            .replace("|6", "| 6")
            .replace("|7", "| 7")
            .replace("|8", "| 8")
            .replace("|9", "| 9")
        )
        msg = msg.split()
        result = []

        for lt in msg:
            if lt.isdigit():
                result.append(int(lt))

        counter = 0
        ivs = []
        evs = []

        for res in result:
            if counter in (0, 3, 6, 9, 12, 15):
                pass
            elif counter in (1, 4, 7, 10, 13, 16):
                ivs.append(res)
            elif counter in (2, 5, 8, 11, 14, 17):
                evs.append(res)
            counter += 1

        return (ivs, evs)

    def get_name(self, msg):
        msg = msg.replace("**", "")
        levels = []
        shiny = False
        if "<:sparkless:506398917475434496>" in msg:
            shiny = True

        if "<:male:1011932024438800464>" in msg:
            gender = "-m"
        elif "<:female:1011935234067021834>" in msg:
            gender = "-f"
        else:
            gender = "-m"
        msg = (
            msg.replace("Level", "")
            .replace("<:sparkless:506398917475434496>", "")
            .split()
        )
        for lt in msg:
            if lt.isdigit():
                levels.append(int(lt))
                msg.remove(lt)
        return msg[0], shiny, levels[0], gender

    def get_check_string(self, ivs, name, shiny, gender):
        string = f"SELECT * FROM pokes WHERE pokname = '{name}' AND hpiv = {ivs[0]} AND atkiv = {ivs[1]} AND defiv = {ivs[2]} AND spatkiv = {ivs[3]} AND spdefiv = {ivs[4]} AND speediv = {ivs[5]} AND shiny = {shiny} AND gender = '{gender}'"
        return string

    def check_desc_conditions(self, embed):
        return "**Nature**" in embed.description

    def check_title_conditions(self, embed):
        return not "Market" in embed.title and "Level" in embed.title

    @commands.hybrid_command()
    async def additem(self, ctx, id: int, item, amount: int):
        async with ctx.bot.db[0].acquire() as pconn:
            items = await pconn.fetchval(
                "SELECT items::json FROM users WHERE u_id = $1", id
            )
            if item in items:
                items[item] += amount
            else:
                items[item] = amount
            await pconn.execute(
                "UPDATE users SET items = $1::json WHERE u_id = $2", items, id
            )
            (await ctx.bot.fetch_user(id)).name
            await ctx.send(f".")

    @commands.hybrid_command()
    async def addinv(self, ctx, id: int, item, amount: int):
        async with ctx.bot.db[0].acquire() as pconn:
            items = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", id
            )
            if item in items:
                items[item] += amount
            else:
                items[item] = amount
            await pconn.execute(
                "UPDATE users SET inventory = $1::json WHERE u_id = $2", items, id
            )
            (await ctx.bot.fetch_user(id)).name
            await ctx.send(f".")

    @commands.hybrid_command()
    async def max(self, ctx, command: str = None):
        async with ctx.bot.db[0].acquire() as pconn:
            ivs = 31
            if not command or command.lower() == "all":
                await pconn.execute(
                    "UPDATE pokes SET atkiv = $1, defiv = $1, hpiv = $1, speediv = $1, spdefiv = $1, spatkiv = $1 WHERE id = (SELECT selected FROM users WHERE u_id = $2)",
                    ivs,
                    ctx.author.id,
                )
            else:
                await pconn.execute(
                    f"UPDATE pokes SET {command} = $1 WHERE id = (SELECT selected FROM users WHERE u_id = $2)",
                    ivs,
                    ctx.author.id,
                )

    @commands.hybrid_command()
    async def stupidmax(self, ctx, command: str = None):
        async with ctx.bot.db[0].acquire() as pconn:
            ivs = random.randint(10000, 15000)
            if not command or command.lower() == "all":
                await pconn.execute(
                    "UPDATE pokes SET atkiv = $1, defiv = $1, hpiv = $1, speediv = $1, spdefiv = $1, spatkiv = $1 WHERE id = (SELECT selected FROM users WHERE u_id = $2)",
                    ivs,
                    ctx.author.id,
                )
            else:
                await pconn.execute(
                    f"UPDATE pokes SET {command} = $1 WHERE id = (SELECT selected FROM users WHERE u_id = $2)",
                    ivs,
                    ctx.author.id,
                )

    @commands.hybrid_command(aliases=["edb"])
    async def executedb(self, ctx, type, *, execution: str):
        """Run SQL commands directly"""
        try:
            await ctx.bot.log(
                527031932110897152,
                f"{ctx.author.name} used edb - Execution = `{execution}`",
            )
        except:
            pass

        # Sanity checks
        low_exe = execution.lower()
        if low_exe != self.safe_edb:
            self.safe_edb = low_exe
            if "update" in low_exe and "where" not in low_exe:
                await ctx.send(
                    "**WARNING**: You attempted to run an `UPDATE` without a `WHERE` clause. If you are **absolutely sure** this action is safe, run this command again."
                )
                return
            if "drop" in low_exe:
                await ctx.send(
                    "**WARNING**: You attempted to run a `DROP`. If you are **absolutely sure** this action is safe, run this command again."
                )
                return
            if "delete from" in low_exe:
                await ctx.send(
                    "**WARNING**: You attempted to run a `DELETE FROM`. If you are **absolutely sure** this action is safe, run this command again."
                )
                return

        try:
            async with ctx.bot.db[0].acquire() as pconn:
                if type == "row":
                    result = await pconn.fetchrow(execution)
                elif type == "fetch":
                    result = await pconn.fetch(execution)
                elif type == "val":
                    result = await pconn.fetchval(execution)
                elif type == "execute":
                    result = await pconn.execute(execution)
        except Exception as e:
            await ctx.send(f"```py\n{e}```")
            raise

        result = str(result)
        if len(result) > 1950:
            result = result[:1950] + "\n\n..."
        await ctx.send(f"```py\n{result}```")

    @commands.hybrid_command()
    async def wipe(self, ctx, id: int):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                f"DELETE FROM pokes WHERE id = ANY ( SELECT unnest(pokes) FROM users WHERE u_id = $1 )",
                id,
            )
            await pconn.execute("DELETE FROM users WHERE u_id = $1", id)
            await ctx.send("User's data has been erased")

    @commands.hybrid_command()
    async def shiny(self, ctx, user: discord.Member, poke: int):
        async with ctx.bot.db[0].acquire() as conn:
            await conn.execute(
                "UPDATE pokes SET shiny = $1 WHERE id = (SELECT pokes[$2] FROM users WHERE u_id = $3)",
                True,
                poke,
                user.id,
            )
        await ctx.send("Successfully changed Pokemon to Shiny")

    @commands.hybrid_command()
    async def deshiny(self, ctx, user: discord.Member, poke: int):
        async with ctx.bot.db[0].acquire() as conn:
            await conn.execute(
                "UPDATE pokes SET shiny = $1 WHERE id = (SELECT pokes[$2] FROM users WHERE u_id = $3)",
                False,
                poke,
                user.id,
            )
            await ctx.send("Successfully changed Pokemon to Non-shiny")

    @commands.hybrid_command()
    async def swap(self, ctx, id1: int, id2: int):
        await ctx.send(
            f"Are you sure you want to move all trainer data from {id2} to {id1}?"
        )

        def check(m):
            return m.author.id == ctx.author.id and m.content.lower() in (
                "yes",
                "no",
                "y",
                "n",
            )

        try:
            m = await ctx.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Request timed out.")
            return
        if m.content.lower().startswith("n"):
            await ctx.send("Cancelled.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute("DELETE FROM redeemstore WHERE u_id = $1", id1)
            await pconn.execute("DELETE FROM redeemstore WHERE u_id = $1", id2)
            await pconn.execute("UPDATE users SET u_id = $1 WHERE u_id = $2", id1, id2)
            await ctx.send("Get rekt")

    @commands.hybrid_command()
    async def forcebal(self, ctx, user: discord.User = None):
        if not user:
            user = ctx.author
        async with ctx.bot.db[0].acquire() as tconn:
            pokes = await tconn.fetchval(
                "SELECT pokes FROM users WHERE u_id = $1", user.id
            )
            if not pokes:
                await ctx.send(f"{user.mention} has not started!")
                return
            daycared = await tconn.fetchval(
                "SELECT count(*) FROM pokes WHERE id = ANY ($1) AND pokname = 'Egg'",
                pokes,
            )
            dets = await tconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", user.id
            )
            count = await tconn.fetchval(
                "SELECT array_length(pokes, 1) FROM users WHERE u_id = $1", user.id
            )
            details = await tconn.fetchrow(
                "SELECT * FROM users WHERE u_id = $1", user.id
            )
        details["u_id"]
        redeems = details["redeems"]
        tnick = details["tnick"]
        uppoints = details["upvotepoints"]
        mewcoins = details["mewcoins"]
        evpoints = details["evpoints"]
        dlimit = details["daycarelimit"]
        details["held_item"]
        embed = Embed(
            title=f"{tnick if tnick.lower() != 'none' else user.name} Trainer Card",
            color=0xFFB6C1,
        )
        # embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Redeems", value=f"{redeems}", inline=True)
        embed.add_field(name="Upvote Points", value=f"{uppoints}", inline=True)
        embed.add_field(
            name="Credits",
            value=f"{mewcoins}<:dittocoin:1010679749212901407>",
            inline=True,
        )
        embed.add_field(name="Pokemon Count", value=f"{count}", inline=True)
        embed.add_field(name="EV Points", value=f"{evpoints}", inline=True)
        embed.add_field(
            name="Daycare spaces", value=f"{daycared}/{dlimit}", inline=True
        )
        # dets.pop('coin-case', None) if 'coin-case' in dets else None
        for item in dets:
            embed.add_field(
                name=item.replace("-", " ").capitalize(),
                value=f"{dets[item]}{'%' if 'shiny' in item or 'honey' in item else 'x'}",
                inline=True,
            )
        embed.set_footer(text=f"You thought you could hide your trainer card?")
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def boostedspwn(self, ctx, *, val1):
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        try:
            guild = await ctx.bot.mongo_find("guilds", {"id": ctx.guild.id})
            delspawn = guild["delete_spawns"]
        except Exception as e:
            delspawn = False
        shiny = False
        radiant = False
        val1 = val1.lower().split()
        if "shiny" in val1:
            shiny = True
            ind = val1.index("shiny")
            val1.pop(ind)
        if "radiant" in val1:
            radiant = True
            ind = val1.index("radiant")
            val1.pop(ind)
        val2 = val1[0]
        channel = ctx.channel
        val = val2.lower()
        irul = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        start = val[0]
        embed = discord.Embed(
            title="A wild Pokémon has Spawned, Say its name to catch it!",
            color=random.choice(ctx.bot.colors),
        )
        embed.add_field(name="-", value=f"This Pokémons name starts with {start}")
        embed.set_image(url=irul)
        embedmsg = await channel.send(embed=embed)

        def check(m):
            return (
                m.content.lower() in (val.replace("-", " "), val)
                and m.channel == channel
            )

        msg = await ctx.bot.wait_for("message", check=check, timeout=60)

        # db code starts here

        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        pokemon_info = await ctx.bot.db[1].pfile.find_one(
            {"id": form_info["pokemon_id"]}
        )
        try:
            gender_rate = pokemon_info["gender_rate"]
        except:
            print(f"\n\nCould not spawn {form_info['identifier']}\n\n")

        gender_rate = pokemon_info["gender_rate"]
        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])

        hpiv = random.randint(17, 31)
        atkiv = random.randint(17, 31)
        defiv = random.randint(17, 31)
        spaiv = random.randint(17, 31)
        spdiv = random.randint(17, 31)
        speiv = random.randint(17, 31)
        plevel = random.randint(90, 100)
        nature = random.choice(natlist)
        plevel**2
        if "idoran" in val.lower():
            gender = val[-2:]
        elif val.lower() == "volbeat":
            gender = "-m"
        elif val.lower() == "illumise":
            gender = "-f"
        elif val.lower() == "gallade":
            gender = "-m"
        elif val.lower() == "nidoking":
            gender = "-m"
        elif val.lower() == "nidoqueen":
            gender = "-f"
        else:
            if gender_rate in (8, -1) and val.capitalize() in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-f"
            elif gender_rate in (8, -1, 0) and not val.capitalize() in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-m"
            else:
                gender = "-f" if random.randint(1, 10) == 1 else "-m"
        query2 = """
                INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, moves, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, fav, ability_index, gender, caught_by, radiant)

                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28) RETURNING id
                """
        args = (
            val2.capitalize(),
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            ["tackle", "tackle", "tackle", "tackle"],
            "None",
            0,
            nature,
            35,
            "None",
            shiny,
            0,
            False,
            False,
            random.choice(ab_ids),
            gender,
            msg.author.id,
            radiant,
        )
        async with ctx.bot.db[0].acquire() as pconn:
            pokeid = await pconn.fetchval(query2, *args)
            # a = await pconn.fetchval("SELECT currval('pokes_id_seq');")
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $2) WHERE u_id = $1",
                msg.author.id,
                pokeid,
            )
        teext = f"Congratulations {msg.author.mention}, you have caught a {val}!\n"
        await ctx.channel.send(embed=make_embed(title="", description=teext))
        await asyncio.sleep(5)
        await msg.delete()
        if delspawn:
            await embedmsg.delete()

    @commands.hybrid_command()
    async def newspawn(self, ctx, *, val1):
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        try:
            guild = await ctx.bot.mongo_find("guilds", {"id": ctx.guild.id})
            delspawn = guild["delete_spawns"]
        except Exception as e:
            delspawn = False
        shiny = False
        radiant = False
        val1 = val1.lower().split()
        if "shiny" in val1:
            shiny = True
            ind = val1.index("shiny")
            val1.pop(ind)
        if "radiant" in val1:
            radiant = True
            ind = val1.index("radiant")
            val1.pop(ind)
        val2 = val1[0]
        channel = ctx.channel
        val = val2.lower()
        irul = await get_pokemon_image(val, ctx.bot, shiny, radiant=radiant)
        start = val[0]
        embed = discord.Embed(
            title="A wild Pokémon has Spawned, Say its name to catch it!",
            color=random.choice(ctx.bot.colors),
        )
        embed.add_field(name="-", value=f"This Pokémons name starts with {start}")
        embed.set_image(url=irul)
        embedmsg = await channel.send(embed=embed)

        def check(m):
            return (
                m.content.lower() in (val.replace("-", " "), val)
                and m.channel == channel
            )

        msg = await ctx.bot.wait_for("message", check=check, timeout=60)

        # db code starts here

        form_info = await ctx.bot.db[1].forms.find_one({"identifier": val.lower()})
        pokemon_info = await ctx.bot.db[1].pfile.find_one(
            {"id": form_info["pokemon_id"]}
        )
        try:
            gender_rate = pokemon_info["gender_rate"]
        except:
            print(f"\n\nCould not spawn {form_info['identifier']}\n\n")

        gender_rate = pokemon_info["gender_rate"]
        types = (await ctx.bot.db[1].ptypes.find_one({"id": form_info["pokemon_id"]}))[
            "types"
        ]
        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])

        hpiv = random.randint(1, 31)
        atkiv = random.randint(1, 31)
        defiv = random.randint(1, 31)
        spaiv = random.randint(1, 31)
        spdiv = random.randint(1, 31)
        speiv = random.randint(1, 31)
        plevel = random.randint(1, 100)
        nature = random.choice(natlist)
        plevel**2
        if "idoran" in val.lower():
            gender = val[-2:]
        elif val.lower() == "volbeat":
            gender = "-m"
        elif val.lower() == "illumise":
            gender = "-f"
        elif val.lower() == "gallade":
            gender = "-m"
        elif val.lower() == "nidoking":
            gender = "-m"
        elif val.lower() == "nidoqueen":
            gender = "-f"
        else:
            if gender_rate in (8, -1) and val.capitalize() in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-f"
            elif gender_rate in (8, -1, 0) and not val.capitalize() in (
                "Blissey",
                "Bounsweet",
                "Chansey",
                "Cresselia",
                "Flabebe",
                "Floette",
                "Florges",
                "Froslass",
                "Happiny",
                "Illumise",
                "Jynx",
                "Kangaskhan",
                "Lilligant",
                "Mandibuzz",
                "Miltank",
                "Nidoqueen",
                "Nidoran-f",
                "Nidorina",
                "Petilil",
                "Salazzle",
                "Smoochum",
                "Steenee",
                "Tsareena",
                "Vespiquen",
                "Vullaby",
                "Wormadam",
                "Meowstic-f",
            ):
                gender = "-m"
            else:
                gender = "-f" if random.randint(1, 10) == 1 else "-m"
        query2 = """
                INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, moves, hitem, exp, nature, expcap, poknick, shiny, price, market_enlist, fav, ability_index, gender, caught_by, radiant)

                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28) RETURNING id
                """
        args = (
            val2.capitalize(),
            hpiv,
            atkiv,
            defiv,
            spaiv,
            spdiv,
            speiv,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            ["tackle", "tackle", "tackle", "tackle"],
            "None",
            0,
            nature,
            35,
            "None",
            shiny,
            0,
            False,
            False,
            random.choice(ab_ids),
            gender,
            msg.author.id,
            radiant,
        )
        async with ctx.bot.db[0].acquire() as pconn:
            pokeid = await pconn.fetchval(query2, *args)
            # a = await pconn.fetchval("SELECT currval('pokes_id_seq');")
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $2) WHERE u_id = $1",
                msg.author.id,
                pokeid,
            )
        teext = f"Congratulations {msg.author.mention}, you have caught a {val}! <3\n"
        await ctx.channel.send(embed=make_embed(title="", description=teext))
        await asyncio.sleep(5)
        await msg.delete()
        if delspawn:
            await embedmsg.delete()

    # @commands.hybrid_command()
    # async def createpoke(self, ctx, *, args):
    #    """Creates a new poke and gives it to the author."""
    #    args = args.lower().split()
    #    extras = ""
    #    shiny = "shiny" in args
    #    radiant = "radiant" in args
    #    boosted = "boosted" in args
    #    if shiny:
    #        extras += "shiny "
    #        args.remove("shiny")
    #    if radiant:
    #        extras += "radiant "
    #        args.remove("radiant")
    #    if boosted:
    #        extras += "boosted "
    #        args.remove("boosted")
    #    poke = "-".join(args).capitalize()
    #    await ctx.bot.commondb.create_poke(ctx.bot, ctx.author.id, poke, shiny=shiny, radiant=radiant, boosted=boosted)
    #    await ctx.send(f"Gave you a {extras}{poke}!")

    #   db code goes here
    @commands.hybrid_command()
    async def evalc(
        self, ctx, cluster_id: int, wait: typing.Optional[int] = 5, *, body
    ):
        def cleanup_code(content):
            """Automatically removes code blocks from the code."""
            # remove ```py\n```
            if content.startswith("```") and content.endswith("```"):
                return "\n".join(content.split("\n")[1:-1])

            # remove `foo`
            return content.strip("` \n")

        body = cleanup_code(body)

        eval_res = await ctx.bot.handler(
            "_eval",
            1,
            args={"body": body, "cluster_id": cluster_id},
            scope="bot",
            _timeout=wait,
        )

        if not eval_res:
            await ctx.send(
                "No response from cluster or it timed out after 5 seconds.  Ensure the cluster is running and that the wait is long enough for your eval."
            )
            return

        async def paginate_send(ctx, text: str):
            """Paginates arbatrary length text & sends."""
            last = 0
            pages = []
            for curr in range(0, len(text), 1980):
                pages.append(text[last:curr])
                last = curr
            pages.append(text[last : len(text)])
            pages = list(filter(lambda a: a != "", pages))
            for page in pages:
                await ctx.send(f"```py\n{page}```")

        result = eval_res[0]
        if result["message"]:
            await paginate_send(ctx, result["message"])
        else:
            await ctx.send("Cluster returned no message")

        if result["type"] == "success":
            await ctx.message.add_reaction("\u2705")
        else:
            await ctx.message.add_reaction("\u2049")

    @commands.hybrid_command(aliases=["evalmany", "evalall"])
    async def evall(self, ctx, wait: typing.Optional[int] = 5, *, body):
        def cleanup_code(content):
            """Automatically removes code blocks from the code."""
            # remove ```py\n```
            if content.startswith("```") and content.endswith("```"):
                return "\n".join(content.split("\n")[1:-1])

            # remove `foo`
            return content.strip("` \n")

        launcher_res = await ctx.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return await ctx.send(
                "Launcher did not respond.  Please start with the launcher to use this command."
            )
        processes = len(launcher_res[0])

        body = cleanup_code(body)

        eval_res = await ctx.bot.handler(
            "_eval",
            processes,
            args={"body": body, "cluster_id": "-1"},
            scope="bot",
            _timeout=wait,
        )

        if not eval_res:
            await ctx.send(
                "No response from cluster or it timed out after 5 seconds.  Ensure the cluster is running and that the wait is long enough for your eval."
            )
            return

        async def paginate_send(ctx, text: str):
            """Paginates arbatrary length text & sends."""
            last = 0
            pages = []
            for curr in range(0, len(text), 1980):
                pages.append(text[last:curr])
                last = curr
            pages.append(text[last:])
            pages = list(filter(lambda a: a != "", pages))
            for page in pages:
                await ctx.send(f"```py\n{page}```")

        eval_res.sort(key=lambda x: x["cluster_id"])
        message = ""

        for response in eval_res:
            if not response["message"]:
                response["message"] = "No message returned"
            message += f"[Cluster {response['cluster_id']}]: {response['message']}\n"

        await paginate_send(ctx, message)

    # @commands.hybrid_group()
    # async def demote(self, ctx):
    #    """Demote users."""
    #    pass
    #
    # @demote.command(name="staff")
    # async def _demote_staff(self, ctx, member: discord.Member):
    #    """Demote a user from Staff."""
    #    async with ctx.bot.db[0].acquire() as pconn:
    #        await pconn.execute("UPDATE users SET staff = 'User' WHERE u_id = $1", member.id)
    #
    #    msg = f"{GREEN} Removed bot permissions.\n"
    #    if ctx.guild.id != 999953429751414784:
    #        msg += f"{RED} Could not remove OS roles, as this command was not run in OS.\n"
    #        await ctx.send(msg)
    #        return
    #
    #    ranks = {
    #        "Support": ctx.guild.get_role(544630193449598986),
    #        "Helper": ctx.guild.get_role(728937101285916772),
    #        "Mod": ctx.guild.get_role(519468261780357141),
    #        "Investigator": ctx.guild.get_role(781716697500614686),
    #        "Gymauth": ctx.guild.get_role(758853378515140679),
    #        "Admin": ctx.guild.get_role(519470089318301696),
    #    }
    #    removeset = set(ranks.values())
    #    currentset = set(member.roles)
    #    removeset &= currentset
    #    if not removeset:
    #        msg += f"{YELLOW} User had no rank roles to remove.\n"
    #    else:
    #        removelist = list(removeset)
    #        await member.remove_roles(*removelist, reason=f'Staff demotion - {ctx.author}')
    #        removelist = [str(x) for x in removelist]
    #        msg += f"{GREEN} Removed existing rank role(s) **{', '.join(removelist)}.**\n"
    #
    #    staff_role = ctx.guild.get_role(764870105741393942)
    #    if staff_role not in member.roles:
    #        msg += f"{YELLOW} User did not have the **{staff_role}** role.\n"
    #    else:
    #        await member.remove_roles(staff_role, reason=f'Staff demotion - {ctx.author}')
    #        msg += f"{GREEN} Removed the **{staff_role}** role.\n"
    #
    #    await ctx.send(msg)
    #
    # @demote.command(name="gym")
    # async def _demote_gym(self, ctx, user_id: int):
    #    """Demote a user from Gym Leader."""
    #    async with ctx.bot.db[0].acquire() as pconn:
    #        await pconn.execute("UPDATE users SET gym_leader = false WHERE u_id = $1", user_id)
    #    await ctx.send("Done.")

    @commands.hybrid_command()
    async def makeradiant(self, ctx, user: discord.Member, poke: int):
        async with ctx.bot.db[0].acquire() as conn:
            await conn.execute(
                "UPDATE pokes SET radiant = $1 WHERE id = (SELECT pokes[$2] FROM users WHERE u_id = $3)",
                True,
                poke,
                user.id,
            )
        await ctx.send("RADIANT POKEMON Successfully created. Enjoy.")

    @commands.hybrid_command()
    async def findcog(self, ctx, *, command: str):
        cmd = ctx.bot.get_command(command)
        if not cmd:
            await ctx.send("That command does not exist!")
            return
        await ctx.send(f"{cmd.cog.__module__} - class {cmd.cog.__cog_name__}")

    @commands.hybrid_command(aliases=["sourcecode"])
    async def source(self, ctx, *, command: str):
        command = ctx.bot.get_command(command)
        if not command:
            await ctx.send("That command does not exist!")
            return

        try:
            source_code = inspect.getsource(command.callback)
        except OSError:
            await ctx.send("Failed to get source of command.")
            return

        temp_pages = []
        pages = []

        def paginate(text: str):
            """Paginates arbatrary length text."""
            last = 0
            pages = []
            for curr in range(0, len(text), 1900):
                pages.append(text[last:curr])
                last = curr
            pages.append(text[last : len(text)])
            pages = list(filter(lambda a: a != "", pages))
            return pages

        for page in paginate(source_code):
            temp_pages.append(f"```py\n{page}```")
        max_i = len(temp_pages)
        i = 1
        for page in temp_pages:
            pages.append(f"`Page {i}/{max_i}`\n" + page)
            i += 1
        await menu(ctx, pages, controls=DEFAULT_CONTROLS)

    @commands.hybrid_command()
    async def redis(self, ctx, call: str, expected: int, scope: str, *, args: str):
        try:
            args = orjson.loads(args or "{}")
        except orjson.JSONDecodeError:
            return await ctx.send("Malformed args argument")

        process_res = await ctx.bot.handler(call, expected, args, scope=scope)
        await ctx.send(f"```py\n{process_res}```")

    @commands.hybrid_command()
    async def refreshenv(self, ctx, *env):
        if env is None or not len(env):
            env = (
                x
                for x in os.listdir(ctx.bot.app_directory / "env")
                if x.endswith(".env")
            )

        for env_file in env:
            load_dotenv(
                ctx.bot.app_directory
                / "env"
                / (env_file if env_file.endswith(".env") else f"{env_file}.env"),
                override=True,
            )

        await ctx.send("Successfully refreshed environment variables.")

    @commands.hybrid_command()
    async def duelupload(
        self, ctx, confirmed: typing.Optional[bool] = False, *, filename: str = None
    ):
        if not filename:
            await ctx.send("A filename must be provided.")
            return

        if (
            len(ctx.message.attachments) != 1
            or not ctx.message.attachments[0].url.endswith(".png")
            or ctx.message.attachments[0].width + ctx.message.attachments[0].height
            != 1024
        ):
            await ctx.send(
                "You must send only one attachment with the PNG extension with size 512x512."
            )
            return

        # I love regex
        r = re.compile(
            r"^(?:radiant/|)(?:shiny/|)(?:skins/|)\d{1,4}-\d{1,2}-(?:_\w+|)$"
        )
        if not r.match(filename):
            await ctx.send(
                "Your given filename does not match the set regex `^(?:radiant/|)(?:shiny/|)(?:skins/|)\d{1,4}-\d{1,2}-(?:_\w+|)$`.  Something must be improperly typed, try again."
            )
            return

        filename += ".png"
        savepath = ctx.bot.app_directory / "shared" / "duel" / "sprites" / filename
        if savepath.exists() and not confirmed:
            await ctx.send(
                "An image already exists in this directory.  If you wish to replace it, please run this command with a `True` before the filename."
            )
            return

        await ctx.message.attachments[0].save(savepath)
        await ctx.send("Successfully saved attachment to the specified directory.")

    @commands.hybrid_command()
    async def create_custom(self, ctx, skin: str, *, val):
        shiny = False
        radiant = False
        val = val.capitalize()
        poke = await ctx.bot.commondb.create_poke(
            ctx.bot,
            ctx.author.id,
            val,
            shiny=shiny,
            radiant=radiant,
            skin=skin.lower(),
            level=100,
        )
        if poke is None:
            await ctx.send(f"`{val}` doesn't seem to be a valid pokemon name...")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET hpiv = 31, atkiv = 31, defiv = 31, spatkiv = 31, spdefiv = 31, speediv = 31 WHERE id = $1",
                poke.id,
            )
        teext = f"{ctx.author.mention} has created a **{skin}** skinned **{val}**!\nIt has been added as your newest pokemon."
        await ctx.channel.send(embed=make_embed(title="", description=teext))


async def setup(bot):
    await bot.add_cog(Dylee())
