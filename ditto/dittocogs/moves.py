import discord
from discord.ext import commands
from utils.misc import MenuView, pagify
from pokemon_utils.utils import evolve

from dittocogs.json_files import *


async def get_moves(ctx, pokemon_name):
    if pokemon_name == "smeargle":
        # Moves which are not coded in the bot
        uncoded_ids = [
            266,
            270,
            476,
            495,
            502,
            511,
            597,
            602,
            603,
            607,
            622,
            623,
            624,
            625,
            626,
            627,
            628,
            629,
            630,
            631,
            632,
            633,
            634,
            635,
            636,
            637,
            638,
            639,
            640,
            641,
            642,
            643,
            644,
            645,
            646,
            647,
            648,
            649,
            650,
            651,
            652,
            653,
            654,
            655,
            656,
            657,
            658,
            671,
            695,
            696,
            697,
            698,
            699,
            700,
            701,
            702,
            703,
            719,
            723,
            724,
            725,
            726,
            727,
            728,
            811,
            10001,
            10002,
            10003,
            10004,
            10005,
            10006,
            10007,
            10008,
            10009,
            10010,
            10011,
            10012,
            10013,
            10014,
            10015,
            10016,
            10017,
            10018,
        ]
        all_moves = (
            await ctx.bot.db[1]
            .moves.find(
                {
                    "id": {"$nin": uncoded_ids},
                }
            )
            .to_list(None)
        )
        return [t["identifier"] for t in all_moves]
    moves = await ctx.bot.db[1].pokemon_moves.find_one({"pokemon": pokemon_name})
    if moves is None:
        return None
    moves = moves["moves"]
    return sorted(set(moves))


class Moves(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def learn(self, ctx, slot: int, move: str):
        if slot > 4 or slot < 1:
            return
        move = move.replace(" ", "-").lower()
        async with ctx.bot.db[0].acquire() as pconn:
            dets = await pconn.fetchrow(
                "SELECT * FROM pokes WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                ctx.author.id,
            )
            if not dets:
                await ctx.send("You do not have that Pokemon!")
                return
            poke = dets["pokname"]
            moves = await get_moves(ctx, poke.lower())
            if moves is None:
                await ctx.send(
                    "That pokemon cannot learn any moves! You might need to `/deform` it first."
                )
                ctx.bot.logger.warning(f"Could not get moves for {poke}")
                return
            if move not in moves:
                await ctx.send(f"Your {poke} can not learn that Move")
                return
            await pconn.execute(
                "UPDATE pokes SET moves[$1] = $2 WHERE id = $3",
                slot,
                move.lower(),
                dets["id"],
            )
            await ctx.send(
                f"You have successfully learnt {move} as your slot {slot} move"
            )
            await evolve(
                ctx.bot,
                dict(
                    await pconn.fetchrow(
                        "SELECT * FROM pokes WHERE id = $1", dets["id"]
                    )
                ),
                ctx.author,
                channel=ctx.channel,
            )

    @commands.hybrid_command()
    async def moves(self, ctx):
        """Show moves your pokemon has learned"""
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT * FROM pokes WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                ctx.author.id,
            )
            if details is None:
                await ctx.send(
                    "You do not have a selected pokemon. Select one with `/select` first."
                )

                return
            details["pokname"]
            m1, m2, m3, m4 = (
                details["moves"][0],
                details["moves"][1],
                details["moves"][2],
                details["moves"][3],
            )
        embed = discord.Embed(title="Moves", color=0xFFB6C1)

        embed.add_field(name="**Move 1**:", value=f"{m1}")
        embed.add_field(name="**Move 2**:", value=f"{m2}")
        embed.add_field(name="**Move 3**:", value=f"{m3}")
        embed.add_field(name="**Move 4**:", value=f"{m4}")

        embed.set_footer(text="See available moves with /moveset")
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def moveset(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = (SELECT selected FROM users WHERE u_id = $1)",
                ctx.author.id,
            )
        if not pokename:
            await ctx.send("You have not selected a Pokemon")
            return
        pokename = pokename.lower()
        if pokename == "egg":
            await ctx.send("There are no available moves for an Egg")
            return
        moves = await get_moves(ctx, pokename)
        if moves is None:
            await ctx.send(
                "That pokemon cannot learn any moves! You might need to `/deform` it first."
            )
            ctx.bot.logger.warning(f"Could not get moves for {pokename}")
            return
        len(moves)
        desc = ""
        for move in moves:
            move = move.capitalize().replace("'", "")
            if ctx.author == ctx.bot.owner:
                print(move)
            move_info = await ctx.bot.db[1].moves.find_one({"identifier": move.lower()})
            if not move_info:
                move_info = await ctx.bot.db[1].moves.find_one(
                    {"identifier": move.lower().rsplit("-", 1)[0]}
                )
            if move_info is None:
                await ctx.send("An error occurred finding moves for that pokemon.")
                ctx.bot.logger.warn(f"A move is not in mongo moves - {move}")
                return
            power = move_info["power"]
            accuracy = move_info["accuracy"]
            type_id = move_info["type_id"]
            damage_class = move_info["damage_class_id"]
            if damage_class == 1:
                damage_class = "<:status1:1013111246121353359><:status2:1013111249095098497>"
            elif damage_class == 2:
                damage_class = "<:phys1:1013111228803059754><:phys2:1013111230937960479>"
            elif damage_class == 3:
                damage_class = "<:special1:1013111240966557706><:special2:1013111242547802183> "
            type = [t["identifier"] for t in TYPES if t["id"] == type_id][
                0
            ].capitalize()
            desc += f"**{damage_class} {move.replace('-', ' ')}** - Power:`{power}` Acc:`{accuracy}` Type:`{type}`\n"
        embed = discord.Embed(
            title="Learnable Move List", colour=random.choice(ctx.bot.colors)
        )
        pages = pagify(desc, base_embed=embed)
        await MenuView(ctx, pages).start()


async def setup(bot):
    await bot.add_cog(Moves(bot))
