from discord.ext import commands

from dittocogs.json_files import *
from dittocogs.pokemon_list import *


class Forms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.XYS = ("charizard", "mewtwo")
        self.MEGAS = (
            "venusaur",
            "blastoise",
            "alakazam",
            "gengar",
            "kangaskhan",
            "pinsir",
            "gyarados",
            "aerodactyl",
            "ampharos",
            "scizor",
            "heracross",
            "houndoom",
            "tyranitar",
            "blaziken",
            "gardevoir",
            "mawile",
            "aggron",
            "medicham",
            "manectric",
            "banette",
            "absol",
            "latias",
            "latios",
            "garchomp",
            "lucario",
            "abomasnow",
            "beedrill",
            "pidgeot",
            "slowbro",
            "steelix",
            "sceptile",
            "swampert",
            "sableye",
            "sharpedo",
            "camerupt",
            "altaria",
            "glalie",
            "salamence",
            "metagross",
            "rayquaza",
            "lopunny",
            "gallade",
            "audino",
            "diancie",
            "lucariosouta",
        )

    @commands.hybrid_command()
    async def lunarize(self, ctx, val: int):
        """
        Lunarizes the selected Necrozma into Necrozma-dawn form.

        Ex. `;lunarize 12` (12 being lunala #)
        """
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )

            if _id is None:
                await ctx.send("You need to select a Necrozma first!")
                return
            selected_pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )

            selected_pokename = selected_pokename.lower()
            if selected_pokename != "necrozma":
                await ctx.send(f"You can not Lunarize a {selected_pokename}")
                return
            helditem = await pconn.fetchval(
                "SELECT hitem FROM pokes WHERE id = $1", _id
            )
            if helditem != "n-lunarizer":
                await ctx.send(
                    "Your Necrozma is not holding a N-lunarizer.\nYou need to buy it from the Shop."
                )

                return
            num = await pconn.fetchval(
                "SELECT pokes[$1] FROM users WHERE u_id = $2", val, ctx.author.id
            )

            lunala = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", num
            )
            if lunala is None:
                await ctx.send("You do not have that many pokes!")
                return
            lunala = lunala.lower()
            if lunala != "lunala":
                await ctx.send(
                    "That is not a Lunala, please use `/lunarize <lunala_number>` to Lunarize"
                )

                return
            await ctx.send("You have fused your Necrozma with your Lunala!")
            await pconn.execute(
                "UPDATE pokes SET pokname = $1 WHERE id = $2", "Necrozma-dawn", _id
            )

    @commands.hybrid_command()
    async def solarize(self, ctx, val: int):
        """
        Solarizes your Necrozma into Necrozma-Dusk form.

        Ex. `;solarize 12` (12 being the solgaleo #)
        """
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )

            num = await pconn.fetchval(
                "SELECT pokes[$1] FROM users WHERE u_id = $2", val, ctx.author.id
            )

            details = await pconn.fetchrow(
                "SELECT pokname, hitem FROM pokes WHERE id = $1", _id
            )

            if details is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )

                return
            pokename, helditem = details
            pokename = pokename.lower()
            if pokename != "necrozma":
                await ctx.send(f"You can not Solarize a {pokename}")
                return
            details = await pconn.fetchrow(
                "SELECT pokname, pokelevel FROM pokes WHERE id = $1", num
            )

            if details is None:
                await ctx.send("You do not have that many pokes!")
                return
            if pokename is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )

                return
            lunala, lunalev = details
            lunala = lunala.lower()
            if lunalev is None:
                await ctx.send("That Pokemon Does not exist in your List")
            if lunala.lower() != "solgaleo":
                await ctx.send(
                    "That is not a Solgaleo, please use `/solarize <solgaleo_number>` to Solarize"
                )

                return
            if helditem != "n-solarizer":
                await ctx.send(
                    "Your Necrozma is not holding a N-solarizer\nYou need to buy it from the Shop"
                )

                return
            msg = await ctx.send("Fusing")
            await ctx.send(
                f"You have Fused your Necrozma with your Solgaleo Level {lunalev}"
            )

            await pconn.execute(
                "UPDATE pokes SET pokname = $1 WHERE id = $2", "Necrozma-dusk", _id
            )

            await msg.edit(content="Fusion Complete")

    @commands.hybrid_command()
    async def fuse(self, ctx, form, val: int):
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT selected, pokes[$2] FROM users WHERE u_id = $1",
                ctx.author.id,
                val,
            )
            
            if data is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return
            _id, num = data
            details = await pconn.fetchrow(
                "SELECT pokname, hitem FROM pokes WHERE id = $1", _id
            )
            data = await pconn.fetchrow(
                "SELECT pokname, hitem FROM pokes WHERE id = $1", _id
            )

            if data is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )

                return
            pokename, helditem = data
            pokename = pokename.lower()
            data = await pconn.fetchrow(
                "SELECT pokname, pokelevel FROM pokes WHERE id = $1", num
            )

            if data is None:
                await ctx.send("That is not a valid lunala!")
                return
            othername, otherlevel = data
            othername = othername.lower()
            if form == "white":
                if pokename != "kyurem":
                    await ctx.send(f"You can not Fuse a {pokename} with Reshiram")
                    return
                if othername != "reshiram":
                    await ctx.send(
                        "That is not a Reshiram, please use `/fuse white <reshiram_number>` to Fuse Kyurem with Reshiram"
                    )

                    return
                if helditem != "light-stone":
                    await ctx.send(
                        "Your Kyurem is not holding a Light stone\nYou need to buy it from the Shop"
                    )

                    return
                msg = await ctx.send("Fusing")
                await ctx.send(
                    f"You have Fused your Kyurem with your Reshiram Level {otherlevel}"
                )

                await pconn.execute(
                    "UPDATE pokes SET pokname = $1 WHERE id = $2", "Kyurem-white", _id
                )

                await msg.edit(content="Fusion Complete")
            elif form == "black":
                if pokename != "kyurem":
                    await ctx.send(f"You can not Fuse a {pokename} with Zekrom")
                    return
                if othername != "zekrom":
                    await ctx.send(
                        "That is not a Zekrom, please use `/fuse black <zekrom_number>` to Fuse Kyurem with Zekrom"
                    )

                    return
                if helditem != "dark-stone":
                    await ctx.send(
                        "Your Kyurem is not holding a Dark stone\nYou need to buy it from the Shop"
                    )

                    return
                msg = await ctx.send("Fusing")
                await ctx.send(
                    f"You have Fused your Kyurem with your Zekrom Level {otherlevel}"
                )

                await pconn.execute(
                    "UPDATE pokes SET pokname = $1 WHERE id = $2", "Kyurem-black", _id
                )

                await msg.edit(content="Fusion Complete")
            elif form == "ice":
                if pokename != "calyrex":
                    await ctx.send(f"You can not Fuse a {pokename} with Glastrier")
                    return
                if othername != "glastrier":
                    await ctx.send(
                        "That is not a Glastrier, please use `/fuse ice <glastrier_number>` to Fuse Calyrex with Glastrier"
                    )

                    return
                if helditem != "reins-of-unity":
                    await ctx.send(
                        "Your Calyrex is not holding the Reins of Unity\nYou need to buy it from the Shop"
                    )

                    return
                msg = await ctx.send("Fusing")
                await ctx.send(
                    f"You have Fused your Calyrex with your Glastrier Level {otherlevel}"
                )

                await pconn.execute(
                    "UPDATE pokes SET pokname = $1 WHERE id = $2",
                    "Calyrex-ice-rider",
                    _id,
                )

                await msg.edit(content="Fusion Complete")
            elif form == "shadow":
                if pokename != "calyrex":
                    await ctx.send(f"You can not Fuse a {pokename} with Spectrier")
                    return
                if othername != "spectrier":
                    await ctx.send(
                        "That is not a Spectrier, please use `/fuse ice <spectrier_number>` to Fuse Calyrex with Spectrier"
                    )
                    return
                if helditem != "reins-of-unity":
                    await ctx.send(
                        "Your Calyrex is not holding the Reins of Unity\nYou need to buy it from the Shop"
                    )
                    return
                lunala, lunalev = details
                lunala = lunala.lower()
                if lunalev is None:
                    await ctx.send("That Pokemon Does not exist in your List")
                if lunala.lower() != "solgaleo":
                    await ctx.send(
                        "That is not a Solgaleo, please use `/solarize <solgaleo_number>` to Solarize"
                    )

                msg = await ctx.send("Fusing")
                await ctx.send(
                    f"You have Fused your Calyrex with your Spectrier Level {lunalev}"
                )

                await pconn.execute(
                    "UPDATE pokes SET pokname = $1 WHERE id = $2",
                    "Calyrex-shadow-rider",
                    _id,
                )

                await msg.edit(content="Fusion Complete")
            else:
                await ctx.send("That isn't a valid form!")

    @commands.hybrid_command()
    async def deform(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )
            if pokename is None:
                await ctx.send("You have no Pokemon Selected")
                return
            if not is_formed(pokename) or pokename.endswith("-alola"):
                await ctx.send("This Pokemon is not a form!")
                return
            pokename = pokename.split("-")
            newname = pokename[0].capitalize()
            if pokename[-1] == "galar":
                newname += "-galar"
            await pconn.execute(
                "UPDATE pokes SET pokname = $1 WHERE id = $2", newname, _id
            )
            await ctx.send("Your Pokemon has successfully reset forms")

    @commands.hybrid_command()
    async def form(self, ctx, val: str):
        val = val.lower()
        if any(
            val.lower().endswith(x)
            for x in ("alola", "galar", "hisui", "misfit", "skylarr")
        ):
            await ctx.send("You cannot form your pokemon to a regional form!")
            return
        if val.lower().endswith("lord"):
            await ctx.send("That form is not available yet!")
            return
        if "mega" in val.lower():
            await ctx.send(f"Use `/mega` for mega evolutions.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )
            happiness = await pconn.fetchval(
                "SELECT happiness FROM pokes WHERE id = $1", _id
            )
            level = await pconn.fetchval(
                "SELECT pokelevel FROM pokes WHERE id = $1", _id
            )
            helditem = await pconn.fetchval(
                "SELECT hitem FROM pokes WHERE id = $1", _id
            )
            moves = await pconn.fetchval("SELECT moves FROM pokes WHERE id = $1", _id)
            if pokename is None:
                await ctx.send("No Pokemon Selected")
                return
            pokename = pokename.lower()
            conditions = pokename == "kyurem"
            if conditions:
                await ctx.send(
                    f"Please use `/fuse` for Kyurem and `/lunarize` /  `/solarize` for Lunala/Solgaleo"
                )
                return
            weathevo = ("thundurus", "tornadus", "landorus")
            if pokename == "arceus":
                required_item = {
                    "electric": "zap",
                    "poison": "toxic",
                    "rock": "stone",
                    "ghost": "spooky",
                    "water": "splash",
                    "flying": "sky",
                    "fairy": "pixie",
                    "psychic": "mind",
                    "grass": "meadow",
                    "steel": "iron",
                    "bug": "insect",
                    "ice": "icicle",
                    "fighting": "fist",
                    "dragon": "draco",
                    "fire": "flame",
                    "dark": "dread",
                    "ground": "earth",
                }.get(val, None)
                if not required_item:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                required_item += "-plate"
            else:
                required_item = {
                    "necrozma": "ultranecronium-z",
                    "lugia": "shadow Stone",
                    "shaymin": "gracidea flower",
                    "kyogre": "blue orb",
                    "groudon": "red orb",
                    "hoopa": "prison bottle",
                    "giratina": "griseous orb",
                    "deoxys": "meteorite",
                    "thundurus": "reveal glass",
                    "landorus": "reveal glass",
                    "tornadus": "reveal glass",
                    "zygarde": "zygarde cell",
                    "dialga": "adamant orb",
                    "palkia": "lustrous orb",
                    "zacian": "rusty sword",
                    "zamazenta": "rusty shield",
                }.get(pokename, None)

            if pokename in ("eevee", "pikachu"):
                if level == 100 and happiness >= 252:
                    form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                    cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                    form_identifier = await cursor.distinct("form_identifier")
                    if not form_identifier:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    form_identifier = form_identifier[0]
                    if form_identifier != val:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    else:
                        await pconn.execute(
                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                            form_to_evolve.capitalize(),
                            _id,
                        )
                        await ctx.send(
                            embed=make_embed(
                                title="Congratulations!!!",
                                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                            )
                        )
                        return
                else:
                    await ctx.send(
                        f"Your {pokename} needs to be level 100 and have maximum happiness!"
                    )
                    return
            elif pokename == "necrozma":
                if helditem != "ultranecronium-z":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "lugia":
                if helditem != "shadow-stone":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return

            elif pokename == "shaymin":
                if helditem != "gracidea-flower":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "kyogre":
                if helditem != "blue-orb":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "groudon":
                if helditem != "red-orb":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "hoopa":
                if helditem != "prison-bottle":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "giratina":
                if helditem != "griseous-orb":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "keldeo":
                if "secret-sword" in moves:
                    form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                    cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                    form_identifier = await cursor.distinct("form_identifier")
                    if not form_identifier:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    form_identifier = form_identifier[0]
                    if form_identifier != val:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    else:
                        await pconn.execute(
                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                            form_to_evolve.capitalize(),
                            _id,
                        )
                        await ctx.send(
                            embed=make_embed(
                                title="Congratulations!!!",
                                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                            )
                        )
                        return

                else:
                    await ctx.send("Your Keldeo does not know Secret Sword Move")
            elif pokename == "meloetta":
                if "relic-song" in moves:
                    form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                    cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                    form_identifier = await cursor.distinct("form_identifier")
                    if not form_identifier:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    form_identifier = form_identifier[0]
                    if form_identifier != val:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    else:
                        await pconn.execute(
                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                            form_to_evolve.capitalize(),
                            _id,
                        )
                        await ctx.send(
                            embed=make_embed(
                                title="Congratulations!!!",
                                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                            )
                        )
                else:
                    await ctx.send("Your Meloetta does not know Relic Song Move")
            elif pokename == "deoxys":
                if helditem != "meteorite":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename in weathevo:
                if helditem != "reveal-glass":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "zygarde":
                if helditem != "zygarde-cell":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "arceus":
                if helditem != required_item:
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
                    return
            elif pokename == "dialga":
                if val.lower() == "origin":
                    if helditem != "adamant-orb":
                        await ctx.send(
                            f"Your {pokename} is not holding the {required_item}"
                        )
                        return
                elif val.lower() == "primal":
                    if helditem != "primal-orb":
                        await ctx.send(f"Your {pokename} is not holding the primal orb")
                        return
                else:
                    await ctx.send("Invalid form form for that Pokemon!")
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
            elif pokename == "palkia":
                if helditem != "lustrous-orb":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
            elif pokename == "zacian":
                if helditem != "rusty-sword":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
            elif pokename == "zamazenta":
                if helditem != "rusty-shield":
                    await ctx.send(
                        f"Your {pokename} is not holding the {required_item}"
                    )
                    return
                form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                form_identifier = await cursor.distinct("form_identifier")
                if not form_identifier:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                form_identifier = form_identifier[0]
                if form_identifier != val:
                    await ctx.send("Invalid form for that Pokemon!")
                    return
                else:
                    await pconn.execute(
                        "UPDATE pokes SET pokname = $1 WHERE id = $2",
                        form_to_evolve.capitalize(),
                        _id,
                    )
                    await ctx.send(
                        embed=make_embed(
                            title="Congratulations!!!",
                            description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                        )
                    )
            else:
                try:
                    if pokename.endswith("-galar"):
                        base = pokename.rstrip("-galar")
                        form_to_evolve = f"{base.lower()}-{val.lower()}-galar"
                    else:
                        form_to_evolve = f"{pokename.lower()}-{val.lower()}"
                    cursor = ctx.bot.db[1].forms.find({"identifier": form_to_evolve})
                    form_identifier = await cursor.distinct("form_identifier")
                    if not form_identifier:
                        await ctx.send("That form does not exist!")
                        return
                    form_identifier = form_identifier[0]
                    if form_identifier != val:
                        await ctx.send("Invalid form for that Pokemon!")
                        return
                    else:
                        await pconn.execute(
                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                            form_to_evolve.capitalize(),
                            _id,
                        )
                        await ctx.send(
                            embed=make_embed(
                                title="Congratulations!!!",
                                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {form_to_evolve.capitalize()}!",
                            )
                        )
                        return
                except Exception as e:
                    if "-" in pokename:
                        await ctx.send(f"`/deform` Your Pokemon first!")
                    else:
                        await ctx.send("Invalid form! OR holding wrong item")
                    raise e

    @commands.hybrid_group(name="mega")
    async def mega_cmds(self, ctx):
        """Top layer of group"""

    @mega_cmds.command()
    async def evolve(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            details = await pconn.fetchrow("SELECT * FROM pokes WHERE id = $1", _id)
            if details is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )
                return
            pokename = details["pokname"]
            helditem = details["hitem"]
            moves = details["moves"]
            if pokename.lower() not in self.MEGAS:
                await ctx.send("That pokemon cannot be mega evolved!")
                return
            if pokename == "Rayquaza":
                if "dragon-ascent" not in moves:
                    await ctx.send("Your Rayquaza Needs to know Dragon Ascent!")
                    return
            if "-" in helditem:
                helditem = helditem.replace("-", " ")
            if helditem != "mega stone":
                await ctx.send("This Pokemon Is not holding a Mega Stone!")

                return
            if pokename is None:
                await ctx.send("No Pokemon Selected")

                return
            pokemon_info = await ctx.bot.db[1].forms.find_one(
                {"identifier": pokename.lower()}
            )
            if pokemon_info is None:
                await ctx.send("This Pokemon cannot Mega Evolve!")
                return
            order = pokemon_info["order"] + 1
            evolution = await ctx.bot.db[1].forms.find_one({"order": order})
            if evolution is None:
                await ctx.send("This Pokemon cannot Mega Evolve!")
                return
            pokemon = evolution["identifier"]
            await pconn.execute(
                "UPDATE pokes SET pokname = $1 WHERE id = $2",
                pokemon.capitalize(),
                _id,
            )
        await ctx.send(
            embed=make_embed(
                title="Congratulations!!!",
                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {pokemon.capitalize()}!",
            )
        )

    @mega_cmds.command()
    async def devolve(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )
            if pokename is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )
                return
            pokename = pokename.lower()
            if "mega" not in pokename:
                await ctx.send("This Pokemon is not a Mega Pokemon!")
                return
            if pokename is None:
                await ctx.send("No Pokemon Selected")
                return
            order = [t["order"] for t in FORMS if t["identifier"] == pokename.lower()]
            formnum = order[0]
            formnum -= 1
            pokemon = [t["identifier"] for t in FORMS if t["order"] == formnum]
            megaable = [t["is_mega"] for t in FORMS if t["identifier"] == pokemon[0]]
            mega = pokemon[0]
            megaable = megaable[0]
            if megaable == 1:
                await ctx.send("This Pokemon cannot Mega Devolve!")
                return
            await pconn.execute(
                "UPDATE pokes SET pokname = $1 WHERE id = $2",
                mega.capitalize(),
                _id,
            )
        await ctx.send(
            embed=make_embed(
                title="Congratulations!!!",
                description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {mega.capitalize()}!",
            )
        )

    @mega_cmds.command()
    async def x(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            details = await pconn.fetchrow(
                "SELECT pokname, hitem FROM pokes WHERE id = $1", _id
            )
            if details is None:
                await ctx.send(
                    "You do not have a pokemon selected!\nSelect one with `/select` first."
                )
                return
            pokename, helditem = details
            if pokename.lower() not in self.XYS:
                await ctx.send("That pokemon cannot be mega evolved into an x form!")
                return
            if "-" in helditem:
                helditem = helditem.replace("-", " ")
            if helditem != "mega stone x":
                await ctx.send("This Pokemon Is not holding a Mega Stone X!")
                return
            if pokename is None:
                await ctx.send("No Pokemon Selected")
                return

            pokemon_info = await ctx.bot.db[1].forms.find_one(
                {"identifier": pokename.lower()}
            )
            order_number = pokemon_info["order"] + 1
            evolution = await ctx.bot.db[1].forms.find_one({"order": order_number})
            mega = evolution["identifier"]

            if pokemon_info["is_mega"]:
                await ctx.send("This Pokemon cannot Mega Evolve!")
                return

            if mega.startswith(pokename.lower()):
                await pconn.execute(
                    "UPDATE pokes SET pokname = $1 WHERE id = $2",
                    mega.capitalize(),
                    _id,
                )

                await ctx.send(
                    embed=make_embed(
                        title="Congratulations!!!",
                        description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {mega.capitalize()}!",
                    )
                )

    @mega_cmds.command()
    async def y(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            details = await pconn.fetchrow(
                "SELECT pokname, hitem FROM pokes WHERE id = $1", _id
            )
            if details is None:
                await ctx.send(
                    "You don't have a pokemon selected!\nSelect one with `/select` first."
                )
                return
            pokename, helditem = details
            if pokename.lower() not in self.XYS:
                await ctx.send("That pokemon cannot be mega evolved into a y form!")
                return
            if helditem is None:
                await ctx.send("Your Pokemon is not holding any Item!")
                return

            if "-" in helditem:
                helditem = helditem.replace("-", " ")

            if helditem != "mega stone y":
                await ctx.send("This Pokemon Is not holding a Mega Stone Y!")

                return

            if pokename is None:
                await ctx.send("No Pokemon Selected")
                return

            pokemon_info = await ctx.bot.db[1].forms.find_one(
                {"identifier": pokename.lower()}
            )
            order_number = pokemon_info["order"] + 2
            evolution = await ctx.bot.db[1].forms.find_one({"order": order_number})
            mega = evolution["identifier"]

            if pokemon_info["is_mega"]:
                await ctx.send("This Pokemon cannot Mega Evolve!")
                return

            if mega.startswith(pokename.lower()):
                await pconn.execute(
                    "UPDATE pokes SET pokname = $1 WHERE id = $2",
                    mega.capitalize(),
                    _id,
                )

                await ctx.send(
                    embed=make_embed(
                        title="Congratulations!!!",
                        description=f"{ctx.author.name} Your {pokename.capitalize()} has evolved into {mega.capitalize()}!",
                    )
                )


async def setup(bot):
    await bot.add_cog(Forms(bot))
