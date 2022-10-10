import contextlib
import random
import string

import discord
import numpy as np
from discord.ext import commands

from dittocogs.json_files import *
from dittocogs.pokemon_list import *

starters = np.array([k["starters"] for k in REGION_STARTERS]).ravel()


def replace_value_with_definition(key_to_find, definition, dictionary):
    for key in dictionary.keys():
        if key == key_to_find:
            dictionary[key] = definition


class Start(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def start(self, ctx, starter: str = None):
        async with ctx.bot.db[0].acquire() as pconn:
            if await pconn.fetchval(
                "SELECT exists(SELECT * from users WHERE u_id = $1)", ctx.author.id
            ):
                await ctx.send("You have already registered")
                return
        """
        async with ctx.bot.db[0].acquire() as pconn:
            language = await pconn.fetchval(
                "SELECT language FROM servers WHERE serverid = $1", ctx.guild.id
            )
        """
        language = "en"
        if starter is None or starter.capitalize() not in starters:
            embed = discord.Embed(
                title="Begin by choosing your starter!",
                color=random.choice(ctx.bot.colors),
            )
            embed.add_field(
                name="🍃",
                value="Bulbasaur, Chikorita, Treecko, Turtwig, Snivy, Chespin, Rowlet, Grookey",
                inline=True,
            )
            embed.add_field(
                name="🔥",
                value="Charmander, Cyndaquil, Torchic, Chimchar, Tepig, Fennekin, Litten, Scorbunny",
                inline=True,
            )
            embed.add_field(
                name="💧",
                value="Squirtle, Totodile, Mudkip, Piplup, Oshawott, Froakie, Popplio, Sobble",
                inline=True,
            )
            embed.set_image(url="https://i.imgur.com/kFlj6ke.jpg")
            embed.set_footer(text="Run /start <starter> to begin!")
            await ctx.send(embed=embed)
            return
        starter = starter.capitalize()
        if language in ctx.bot.pokemon_names:
            # again, why is this undefined? - Motzumoto
            starter = starters[translated_starters.index(starter)]

        emoji = random.choice(emotes)
        await ctx.send(f"You have selected {starter} as your starter! {emoji}")

        user_query = (
            "INSERT INTO users (u_id, redeems, evpoints, tnick, upvotepoints, mewcoins, user_order, pokes, visible, inventory, comp) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)"
        )
        user_args = (
            ctx.author.id,
            0,
            0,
            None,
            0,
            0,
            "kek",
            [],
            True,
            '{"coin-case": 0, "nature-capsules" : 5, "honey" : 1, "battle-multiplier": 1, "shiny-multiplier": 0 }',
            True,
        )
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(user_query, *user_args)
            await pconn.execute(
                    "INSERT INTO achievements (u_id) VALUES ($1) ON CONFLICT DO NOTHING",
                    ctx.author.id,
                )
        await ctx.bot.commondb.create_poke(
            ctx.bot, ctx.author.id, starter, boosted=True
        )
        

        new_embed = discord.Embed(
            title="Welcome to DittoBOT", color=ctx.bot.get_random_color()
        )
        new_embed.description = f"""See your owned Pokemon using `/p`\nSelect your starter with `/select 1`\n
        Go through the DittoBOT tutorial - `/tutorial` for detailed instructions!\n
        **Now begin your adventure!**"""
        await ctx.send(embed=new_embed)
        message = (
            "Don't hesitate to [Join the Official Server](https://discord.gg/ditto) for upcoming Events/Tournaments\n"
            "Know what's epic? If you haven't, add DittoBOT to your server or recommend DittoBOT to your friends server and spread the fun!!"
        )
        embed = discord.Embed(
            title="Thank you for registering!", description=message, color=0xFFB6C1
        )
        # embed.add_field(
        #     name="Follow us on Social Media for fun events and rewards!",
        #     value="`Reddit`: https://www.reddit.com/r/Mewbot/\n`Instagram`: https://www.instagram.com/mewbot_official/\n`Twitter`: https://twitter.com/MewbotOS",
        # )
        embed.add_field(
            name="How to get Redeems",
            value="Get 1 Redeem and 15,000 Credits for 5 Upvote Points!",
        )
        embed.add_field(
            name="The most unique Pokemon experience on discord!",
            value="We are the only Pokemon Bot with Status, Weather, Setup Moves, Secondary effects and Every Pokemon **Form** working in 6v6 player vs player duels!",
        )
        embed.set_image(
            url="http://images.mewbot.me/Lychee/uploads/big/1013506636007cf754eb26d32a91a312.png"
        )
        await self.bot.get_partial_messageable(1024348479067279390).send(
            f"{ctx.author} (`{ctx.author.id}`) has started **DittoBOT** using `/start` (**{starter}**)"
        )
        with contextlib.suppress(discord.Forbidden):
            await ctx.author.send(embed=embed)

    # @start.autocomplete(name="starter")
    # async def start_autocomplete(self, interaction, starter: str):
    #     """Autocomplete to show the list of pokemon for user easy selection"""
    #     return [k for k in starters if k.startswith(starter)]

    # @commands.hybrid_command(name="promo-start")
    async def start_journey2(self, ctx, starter=None):
        async with ctx.bot.db[0].acquire() as pconn:
            if await pconn.fetchval(
                "SELECT exists(SELECT * from users WHERE u_id = $1)", ctx.author.id
            ):
                await ctx.send("You have already registered with ';start'")
                return
        initial_message = None
        """
        async with ctx.bot.db[0].acquire() as pconn:
            language = await pconn.fetchval(
                "SELECT language FROM servers WHERE serverid = $1", ctx.guild.id
            )
        """
        language = "en"
        if starter is None or starter.capitalize() not in starters:
            ctx.prefix
            embed = discord.Embed(
                title="Say the Starter you want!",
                description="Begin by choosing your starter!",
                color=random.choice(ctx.bot.colors),
            )
            embed.add_field(
                name="🍃",
                value="Bulbasaur, Chikorita, Treecko, Turtwig, Snivy, Chespin, Rowlet, Grookey",
                inline=True,
            )
            embed.add_field(
                name="🔥",
                value="Charmander, Cyndaquil, Torchic, Chimchar, Tepig, Fennekin, Litten, Scorbunny",
                inline=True,
            )
            embed.add_field(
                name="💧",
                value="Squirtle, Totodile, Mudkip, Piplup, Oshawott, Froakie, Popplio, Sobble",
                inline=True,
            )
            embed.set_image(url="https://i.imgur.com/kFlj6ke.jpg")
            embed.set_footer(
                text="Say the Pokemon's name without the prefix! Pokemon names are from left to right."
            )
            initial_message = await ctx.send(embed=embed)
            if language in ctx.bot.pokemon_names:
                # ids = [[i['pokemon_id'] for i in FORMS if i['identifier'] == word.lower()][0] for word in starters]
                translated_starters = []
                for starter in starters:
                    _id = (await ctx.bot.db[1].forms.find_one({"identifier": starter}))[
                        "pokemon_id"
                    ]
                    try:
                        translated_name = ctx.bot.pokemon_names.get(language)[_id - 1]
                    except:
                        translated_name = starter
                    translated_starters.append(translated_name)
            else:
                translated_starters = starters
                # [prefix + starter.capitalize() for starter in translated_starters]

            def predicate(m):
                return (
                    m.author.id == ctx.author.id
                    and m.channel.id == ctx.channel.id
                    and m.content.capitalize() in translated_starters
                )

            try:
                starter = await ctx.bot.wait_for("message", check=predicate, timeout=60)
            except:
                await ctx.send("You took too long to pick a Starter!")
                return
            starter = starter.content.capitalize()
        else:
            starter = starter.capitalize()
        if language in ctx.bot.pokemon_names:
            starter = starters[translated_starters.index(starter)]

        emoji = random.choice(emotes)
        await ctx.send(f"You have selected {starter} as your starter! {emoji}")

        form_info = await ctx.bot.db[1].forms.find_one({"identifier": starter.lower()})
        ab_ids = []
        async for record in ctx.bot.db[1].poke_abilities.find(
            {"pokemon_id": form_info["pokemon_id"]}
        ):
            ab_ids.append(record["ability_id"])
        async with ctx.bot.db[0].acquire() as pconn:
            if await pconn.fetchval(
                "SELECT exists(SELECT * from users WHERE u_id = $1)", ctx.author.id
            ):
                await ctx.send("You have already started with `;start`")
                return
            hpiv = random.randint(20, 30)
            atkiv = random.randint(20, 30)
            defiv = random.randint(20, 30)
            spaiv = random.randint(20, 30)
            spdiv = random.randint(20, 30)
            speiv = random.randint(20, 30)
            nature = random.choice(natlist)
            moves = ["tackle", "tackle", "tackle", "tackle"]

            query2 = """
            INSERT INTO pokes (pokname, hpiv, atkiv, defiv, spatkiv, spdefiv, speediv, hpev, atkev, defev, spatkev, spdefev, speedev, pokelevel, moves, hitem, exp, nature, expcap, poknick, price, market_enlist, happiness, fav, ability_index, gender, caught_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27)"""

            args = (
                starter,
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
                5,
                moves,
                "None",
                1,
                nature,
                35,
                "None",
                0,
                False,
                0,
                False,
                ab_ids.index(random.choice(ab_ids)),
                random.choice(("-m", "-f")),
                ctx.author.id,
            )
            await pconn.execute(query2, *args)
            the_id = await pconn.fetchval("SELECT currval('pokes_id_seq');")
            code1 = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(8)
            )
            query3 = """
            INSERT INTO users (u_id, redeems, evpoints, tnick, upvotepoints, mewcoins, user_order, pokes, visible, inventory, comp)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """

            args2 = (
                ctx.author.id,
                0,
                0,
                "None",
                0,
                0,
                "kek",
                {the_id},
                True,
                '{"coin-case": 0, "nature-capsules" : 10, "honey" : 0, "battle-multiplier": 5, "shiny-multiplier": 5 }',
                True,
            )

            await pconn.execute(query3, *args2)
            new_embed = discord.Embed(
                title="Welcome to DittoBOT", color=ctx.bot.get_random_color()
            )
            new_embed.description = f"""See your owned Pokemon using `{ctx.prefix}pokemon`\nSelect your starter with `{ctx.prefix}select 1`
            Go through the DittoBOT tutorial - `{ctx.prefix}tutorial`\nSee all commands in the help section - `{ctx.prefix}help`
            **Now begin your adventure!**"""
            if initial_message:
                await initial_message.edit(embed=new_embed)
            else:
                await ctx.send(embed=new_embed)
            message = (
                "Don't hesitate to [Join the Official Server](https://discord.gg/ditto) for upcoming Events/Tournaments\n"
                "If you haven't, add DittoBOT to your server or recommend DittoBOT to your friends server to spread the fun!!"
            )
            embed = discord.Embed(
                title="Thank you for registering!", description=message, color=0xFFB6C1
            )
            embed.add_field(
                name="How to get Redeems",
                value="Get 1 Redeem and 15,000 Credits for 5 Upvote Points! or donate 1$ = 2 redeems using the ;donate command",
            )
            embed.add_field(
                name="Play the Best Pokemon bot at the moment!",
                value="Spoiler: We were the first Pokemon Bot with Status, Weather, Setup Moves and Every Pokemon **Form** __This distinguishes DittoBOT from every other Bot!__! (And our amazing dev team!)",
            )
            embed.set_image(
                url="http://images.mewbot.me/Lychee/uploads/big/1013506636007cf754eb26d32a91a312.png"
            )
            await pconn.execute(
                "INSERT INTO skylog (u_id, command, args, jump, time) VALUES ($1, $2, $3, $4, $5)",
                ctx.author.id,
                ctx.command.qualified_name,
                ctx.message.content,
                ctx.message.jump_url,
                ctx.message.created_at,
            )
            await ctx.author.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Start(bot))
