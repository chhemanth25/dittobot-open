import asyncio
import contextlib
import random
import time
from collections import defaultdict

import discord
from discord.ext import commands
from utils.misc import get_file_name

from dittocogs.fishing import is_key
from dittocogs.json_files import *
from dittocogs.json_files import make_embed
from dittocogs.pokemon_list import *


def despawn_embed(e, status):
    e.title = "Despawned!" if status == "despawn" else "Caught!"
    # e.set_image(url=e.image.url)
    return e


class SpawnView(discord.ui.View):
    def __init__(
        self,
        pokemon: str,
        delspawn: bool,
        pinspawn: bool,
        spawn_channel: discord.TextChannel,
        legendchance: int,
        ubchance: int,
        shiny: bool,
    ):
        self.modal = SpawnModal(
            pokemon,
            delspawn,
            pinspawn,
            spawn_channel,
            legendchance,
            ubchance,
            shiny,
            self,
        )
        super().__init__(timeout=360)
        self.msg = None

    def set_message(self, msg: discord.Message):
        self.msg = msg

    async def on_timeout(self):
        if self.msg:
            embed = self.msg.embeds[0]
            embed.title = "Timed out! Better luck next time!"
            await self.msg.edit(embed=embed, view=None)

    @discord.ui.button(label="Catch This Pokemon!", style=discord.ButtonStyle.blurple)
    async def click_here(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(self.modal)


class SpawnModal(discord.ui.Modal, title="Catch!"):
    def __init__(
        self,
        pokemon: str,
        delspawn: bool,
        pinspawn: bool,
        spawn_channel: discord.TextChannel,
        legendchance: int,
        ubchance: int,
        shiny: bool,
        view: discord.ui.View,
    ):
        self.pokemon = pokemon
        self.guessed = False
        self.delspawn = delspawn
        self.pinspawn = pinspawn
        self.spawn_channel = spawn_channel
        self.legendchance = legendchance
        self.ubchance = ubchance
        self.shiny = shiny
        self.view = view
        super().__init__()

    name = discord.ui.TextInput(
        label="Pokemon Name", placeholder="What do you think this pokemon is named?"
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.embedmsg = interaction.message

        await interaction.response.defer()

        pokemon = self.pokemon

        # Check if pokemon name is correct
        if self.guessed:
            return await interaction.followup.send(
                "Someone's already guessed this pokemon!", ephemeral=True
            )

        # Add additional valid names to support variations in naming
        catch_options = [pokemon]
        if pokemon == "mr-mime":
            catch_options.append("mr.-mime")
        elif pokemon == "mime-jr":
            catch_options.append("mime-jr.")
        elif pokemon.endswith("-alola"):
            catch_options.append(f"alola-{pokemon[:-6]}")
            catch_options.append(f"alolan-{pokemon[:-6]}")
        elif pokemon.endswith("-galar"):
            catch_options.append(f"galar-{pokemon[:-6]}")
            catch_options.append(f"galarian-{pokemon[:-6]}")
        elif pokemon.endswith("-hisui"):
            catch_options.append(f"hisui-{pokemon[:-6]}")
            catch_options.append(f"hisuian-{pokemon[:-6]}")

        if str(self.name).lower().replace(
            " ", "-"
        ) not in catch_options or interaction.client.botbanned(interaction.user.id):
            return await interaction.followup.send(
                "Incorrect name! Try again :(", ephemeral=True
            )

        # Someone caught the poke, create it
        async with interaction.client.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json from users WHERE u_id = $1",
                interaction.user.id,
            )
            if inventory is None:
                return await interaction.followup.send(
                    "You have not started!\nStart with `/start` first!", ephemeral=True
                )

        self.guessed = True

        pokemon = pokemon.capitalize()

        ivmulti = inventory.get("iv-multiplier", 0)
        # 0%-10% chance from 0-50 iv multis
        boosted = random.randrange(500) < ivmulti
        plevel = random.randint(1, 60)
        pokedata = await interaction.client.commondb.create_poke(
            interaction.client,
            interaction.user.id,
            pokemon,
            shiny=self.shiny,
            boosted=boosted,
            level=plevel,
        )
        ivpercent = round((pokedata.iv_sum / 186) * 100, 2)
        credits = None

        async with interaction.client.db[0].acquire() as pconn:
            items = await pconn.fetchval(
                "SELECT items::json FROM users WHERE u_id = $1",
                interaction.message.author.id,
            )

            if not items:
                items = {}
            #
            user = await interaction.client.mongo_find(
                "users",
                {"user": interaction.user.id},
                default={"user": interaction.user.id, "progress": {}},
            )
            progress = user["progress"]
            progress["catch-count"] = progress.get("catch-count", 0) + 1
            await interaction.client.mongo_update(
                "users", {"user": interaction.user.id}, {"progress": progress}
            )
            #
            berry_chance = max(1, int(random.random() * 350))
            expensive_chance = max(1, int(random.random() * 25))
            if berry_chance in range(1, 8):
                cheaps = [
                    t["item"]
                    for t in SHOP
                    if t["price"] <= 8000 and not is_key(t["item"])
                ]
                expensives = [
                    t["item"]
                    for t in SHOP
                    if t["price"] in range(8000, 20000) and not is_key(t["item"])
                ]
                if berry_chance == 1:
                    berry = random.choice(cheaps)
                elif berry_chance == expensive_chance:
                    berry = random.choice(expensives)
                else:
                    berry = random.choice(list(berryList))
                # items = user_info["items"]
                items[berry] = items.get(berry, 0) + 1
                await pconn.execute(
                    "UPDATE users SET items = $1::json WHERE u_id = $2",
                    items,
                    interaction.user.id,
                )

            else:
                berry_chance = None
            #
            chest_chance = not random.randint(0, 200)
            if chest_chance:
                inventory = await pconn.fetchval(
                    "SELECT inventory::json FROM users WHERE u_id = $1",
                    interaction.user.id,
                )
                chest = "common chest"
                inventory[chest] = inventory.get(chest, 0) + 1
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json where u_id = $2",
                    inventory,
                    interaction.user.id,
                )
            if interaction.client.premium_server(interaction.message.guild.id):
                credits = random.randint(100, 250)
                await pconn.execute(
                    "UPDATE users SET mewcoins = mewcoins + $1 where u_id = $2",
                    credits,
                    interaction.user.id,
                )
        author = interaction.user.mention
        teext = f"Congratulations {author}, you have caught a {pokedata.emoji}{pokemon} ({ivpercent}% iv)!\n"
        if boosted:
            teext += "It was boosted by your IV multiplier!\n"
        if berry_chance:
            teext += f"It also dropped a {berry}!\n"
        if chest_chance:
            teext += f"It also dropped a {chest}!\n"
        if credits:
            teext += f"You also found {credits} credits!\n"

        await interaction.followup.send(embed=(make_embed(title="", description=teext)))
        with contextlib.suppress(discord.HTTPException):
            if self.delspawn:
                await self.embedmsg.delete()
            else:
                await self.embedmsg.edit(
                    embed=despawn_embed(self.embedmsg.embeds[0], "caught"), view=None
                )
                if (
                    self.pinspawn
                    and self.spawn_channel.permissions_for(
                        interaction.message.guild.me
                    ).manage_messages
                ) and any([self.legendchance < 2, self.ubchance < 2]):
                    await self.embedmsg.pin()
        self.view.stop()

        # Dispatches an event that a poke was spawned.
        # on_poke_spawn(self, channel, user)
        interaction.client.dispatch("poke_spawn", self.spawn_channel, interaction.user)


class Spawn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spawn_cache = defaultdict(
            int
        )  # This doesn't need to be put in Redis, because it's a cache of Guild ID's, which aren't cross-cluster
        self.always_spawn = False
        self.modal_view = False

    # @check_owner()
    # @commands.hybrid_command(name="lop")
    # async def lop(self, ctx):
    #    if self.always_spawn:
    #        self.always_spawn = False
    #        await ctx.send("Always spawning disabled.")
    #    else:
    #        self.always_spawn = True
    #        await ctx.send("Always spawning enabled.")

    async def get_type(self, type_id):
        data = await self.bot.db[1].ptypes.find({"types": type_id}).to_list(None)
        data = [x["id"] for x in data]
        data = (
            await self.bot.db[1].forms.find({"pokemon_id": {"$in": data}}).to_list(None)
        )
        data = [x["identifier"].title() for x in data]
        return list(set(data) & set(totalList))

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.bot.wait_until_ready()
        if not message.guild:
            return
        if message.author.bot:
            return
        # if self.bot.botbanned(message.author.id):
        # return
        if message.guild.id in (264445053596991498, 446425626988249089):
            return
        if time.time() < self.spawn_cache[message.guild.id]:
            return
        if random.random() >= 0.05 and not self.always_spawn:
            return
        if isinstance(message.channel, discord.threads.Thread):
            return
        if isinstance(message.channel, discord.VoiceChannel):
            return
        self.spawn_cache[message.guild.id] = time.time() + 5
        
        # See if we are allowed to spawn in this channel & get the spawn channel
        try:
            guild = await self.bot.mongo_find("guilds", {"id": message.guild.id})
            (
                redirects,
                delspawn,
                pinspawn,
                disabled_channels,
                small_images,
                modal_view,
            ) = (
                guild["redirects"],
                guild["delete_spawns"],
                guild["pin_spawns"],
                guild["disabled_spawn_channels"],
                guild["small_images"],
                guild.get("modal_view", None),
            )

        except Exception:
            redirects, delspawn, pinspawn, disabled_channels, small_images = (
                [],
                False,
                False,
                [],
                False,
            )
        if message.channel.id in disabled_channels:
            return
        if redirects:
            spawn_channel = message.guild.get_channel(random.choice(redirects))
        else:
            spawn_channel = message.channel
        if spawn_channel is None:
            return
        if isinstance(spawn_channel, discord.CategoryChannel):
            if not spawn_channel.text_channels:
                return
            spawn_channel = random.choice(spawn_channel.text_channels)
        #if #message.guild.id == 999953429751414784:
            #await spawn_channel.send("Join DittoBOT")
        if not isinstance(spawn_channel, discord.TextChannel):
            return
        if not spawn_channel.permissions_for(message.guild.me).send_messages:
            return
        if not spawn_channel.permissions_for(message.guild.me).embed_links:
            return
        # Check the "environment" to determine spawn rates
        override_with_ghost = False
        override_with_ice = False
        async with self.bot.db[0].acquire() as pconn:
            inventory = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1",
                message.author.id,
            )
            threshold = 4000
            if inventory is not None:
                threshold = round(
                    threshold - threshold * (inventory.get("shiny-multiplier", 0) / 100)
                )
            shiny = random.choice([False for i in range(threshold)] + [True])

            honey = await pconn.fetchval(
                "SELECT type FROM honey WHERE channel = $1 LIMIT 1",
                message.channel.id,
            )
            if honey is None:
                honey = 0
            elif honey == "ghost":
                honey = 0
                override_with_ghost = bool(random.randrange(4))
            elif honey == "cheer":
                honey = 0
                override_with_ice = True
            else:
                honey = 50

            legendchance = int(random.random() * (round(4000 - 7600 * honey / 100)))
            ubchance = int(random.random() * (round(3000 - 5700 * honey / 100)))
            pseudochance = int(random.random() * (round(1000 - 1900 * honey / 100)))
            starterchance = int(random.random() * (round(500 - 950 * honey / 100)))

        # Pick which type of pokemon to spawn
        if message.guild.id == 999953429751414784 and False:
            pass
        elif override_with_ghost:
            pokemon = random.choice(await self.get_type(8))
        elif override_with_ice:
            pokemon = random.choice(await self.get_type(15))
        elif legendchance < 2:
            pokemon = random.choice(LegendList)
        elif ubchance < 2:
            pokemon = random.choice(ubList)
        elif pseudochance < 2:
            pokemon = random.choice(pseudoList)
        elif starterchance < 2:
            pokemon = random.choice(starterList)
        else:
            pokemon = random.choice(pList)
        pokemon = pokemon.lower()

        # Get the data for the pokemon that is about to spawn
        form_info = await self.bot.db[1].forms.find_one({"identifier": pokemon})
        if form_info is None:
            raise ValueError(f'Bad pokemon name "{pokemon}" passed to spawn.py')
        pokemon_info = await self.bot.db[1].pfile.find_one(
            {"id": form_info["pokemon_id"]}
        )
        if not pokemon_info and "alola" in pokemon:
            pokemon_info = await self.bot.db[1].pfile.find_one(
                {"identifier": pokemon.lower().split("-")[0]}
            )
        try:
            pokeurl = await get_file_name(pokemon, self.bot, shiny)
        except Exception:
            return

        # Create & send the pokemon spawn embed
        embed = discord.Embed(
            title=f"A wild Pokémon has Spawned, Say its name to catch it!",
            color=random.choice(self.bot.colors),
        )
        embed.add_field(name="-", value=f"This Pokémons name starts with {pokemon[0]}")
        try:
            if small_images:
                embed.set_thumbnail(
                    url="https://skylarr1227.github.io/images/" + pokeurl
                )
            else:
                embed.set_image(url="https://skylarr1227.github.io/images/" + pokeurl)
        except Exception:
            return

        if self.modal_view:
           try:
               view = SpawnView(
                   pokemon=pokemon,
                   delspawn=delspawn,
                   pinspawn=pinspawn,
                   spawn_channel=spawn_channel,
                   legendchance=legendchance,
                   ubchance=ubchance,
                   shiny=shiny,
               )
               msg = await spawn_channel.send(embed=embed, view=view)
    
               view.set_message(msg)
    
           except discord.HTTPException:
               return
        else:
            catch_options = [pokemon]
            if pokemon == "mr-mime":
                catch_options.append("mr.-mime")
            elif pokemon == "mime-jr":
                catch_options.append("mime-jr.")
            elif pokemon.endswith("-alola"):
                catch_options.append("alola-" + pokemon[:-6])
                catch_options.append("alolan-" + pokemon[:-6])
            elif pokemon.endswith("-galar"):
                catch_options.append("galar-" + pokemon[:-6])
                catch_options.append("galarian-" + pokemon[:-6])
            elif pokemon.endswith("-hisui"):
                catch_options.append("hisui-" + pokemon[:-6])
                catch_options.append("hisuian-" + pokemon[:-6])

            embedmsg = await spawn_channel.send(
                embed=embed,
            )

            def check(m):
                if(m.content is None):
                    return False
                return (
                    m.channel.id == spawn_channel.id
                    and any([m.content.lower().replace(" ","-").endswith(catch_option) for catch_option in catch_options]) # The message ends with the pokemon's name
                    and not self.bot.botbanned(m.author.id)
                )

            while True:
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=600)
                except asyncio.TimeoutError:
                    try:
                        await embedmsg.edit(
                            embed=despawn_embed(embedmsg.embeds[0], "despawn")
                        )
                    except discord.HTTPException:
                        pass
                    return
                async with self.bot.db[0].acquire() as pconn:
                    inventory = await pconn.fetchval(
                        "SELECT inventory::json from users WHERE u_id = $1",
                        msg.author.id,
                    )
                    if inventory is None:
                        await spawn_channel.send(
                            "You have not started!\nStart with `/start` first!"
                        )
                    else:
                        break

            pokemon = pokemon.capitalize()

            # Someone caught the poke, create it
            ivmulti = inventory.get("iv-multiplier", 0)
            # 0%-10% chance from 0-50 iv multis
            boosted = random.randrange(500) < ivmulti
            plevel = random.randint(1, 60)
            pokedata = await self.bot.commondb.create_poke(
                self.bot,
                msg.author.id,
                pokemon,
                shiny=shiny,
                boosted=boosted,
                level=plevel,
            )
            ivpercent = round((pokedata.iv_sum / 186) * 100, 2)
            credits = None

            async with self.bot.db[0].acquire() as pconn:
                items = await pconn.fetchval(
                    "SELECT items::json FROM users WHERE u_id = $1", msg.author.id
                )
                #
                user = await self.bot.mongo_find(
                    "users",
                    {"user": msg.author.id},
                    default={"user": msg.author.id, "progress": {}},
                )
                progress = user["progress"]
                progress["catch-count"] = progress.get("catch-count", 0) + 1
                await self.bot.mongo_update(
                    "users", {"user": msg.author.id}, {"progress": progress}
                )
                if shiny:
                    await pconn.execute("UPDATE achievements SET shiny_caught = shiny_caught + 1 WHERE u_id = $1", msg.author.id)
                else:
                    await pconn.execute("UPDATE achievements SET pokemon_caught = pokemon_caught + 1 WHERE u_id = $1", msg.author.id)
                berry_chance = max(1, int(random.random() * 350))
                expensive_chance = max(1, int(random.random() * 25))
                if berry_chance in range(1, 8):
                    cheaps = [
                        t["item"]
                        for t in SHOP
                        if t["price"] <= 8000 and not is_key(t["item"])
                    ]
                    expensives = [
                        t["item"]
                        for t in SHOP
                        if t["price"] in range(8000, 20000) and not is_key(t["item"])
                    ]
                    if berry_chance == 1:
                        berry = random.choice(cheaps)
                    elif berry_chance == expensive_chance:
                        berry = random.choice(expensives)
                    else:
                        berry = random.choice(list(berryList))
                    # items = user_info["items"]
                    items[berry] = items.get(berry, 0) + 1
                    await pconn.execute(
                        f"UPDATE users SET items = $1::json WHERE u_id = $2",
                        items,
                        msg.author.id,
                    )
                else:
                    berry_chance = None
                #
                chest_chance = not random.randint(0, 200)
                if chest_chance:
                    inventory = await pconn.fetchval(
                        "SELECT inventory::json FROM users WHERE u_id = $1",
                        msg.author.id,
                    )
                    chest = "common chest"
                    inventory[chest] = inventory.get(chest, 0) + 1
                    await pconn.execute(
                        "UPDATE users SET inventory = $1::json where u_id = $2",
                        inventory,
                        msg.author.id,
                    )
                if self.bot.premium_server(message.guild.id):
                    credits = random.randint(100, 250)
                    await pconn.execute(
                        "UPDATE users SET mewcoins = mewcoins + $1 where u_id = $2",
                        credits,
                        msg.author.id,
                    )
            author = msg.author.mention
            teext = f"Congratulations {author}, you have caught a {pokedata.emoji}{pokemon} ({ivpercent}% iv)!\n"
            if boosted:
                teext += "It was boosted by your IV multiplier!\n"
            if berry_chance:
                teext += f"It also dropped a {berry}!\n"
            if chest_chance:
                teext += f"It also dropped a {chest}!\n"
            if credits:
                teext += f"You also found {credits} credits!\n"

            await spawn_channel.send(embed=(make_embed(title="", description=teext)))
            try:
                if delspawn:
                    await embedmsg.delete()
                else:
                    await embedmsg.edit(
                        embed=despawn_embed(embedmsg.embeds[0], "caught")
                    )
                    if (
                        pinspawn
                        and spawn_channel.permissions_for(
                            message.guild.me
                        ).manage_messages
                    ):
                        if any([legendchance < 2, ubchance < 2]):
                            await embedmsg.pin()
            except discord.HTTPException:
                pass
            # Dispatches an event that a poke was spawned.
            # on_poke_spawn(self, channel, user)
            self.bot.dispatch("poke_spawn", spawn_channel, msg.author)


async def setup(bot):
    await bot.add_cog(Spawn(bot))
