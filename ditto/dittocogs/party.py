import discord
from discord.ext import commands
from utils.misc import ConfirmView, MenuView, pagify


class Party(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="party")
    async def party_base(self, ctx: commands.Context) -> None:
        """Commands for loading, registering, and deleting partys"""

    @party_base.command(name="view")
    async def party_view(self, ctx) -> None:
        """View your loaded party"""
        embed = discord.Embed(title="Your Current Party!", color=0xEEE647)
        async with ctx.bot.db[0].acquire() as pconn:
            party_nums = await pconn.fetchval(
                "SELECT party FROM users WHERE u_id = $1", ctx.author.id
            )
            if party_nums is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            for idx, _id in enumerate(party_nums):
                t_name = await pconn.fetchval(
                    "SELECT pokname FROM pokes WHERE id = $1", _id
                )
                if t_name is None:
                    t_name = "None"
                else:
                    num = await pconn.fetchval(
                        "SELECT array_position(pokes, $1) FROM users WHERE u_id = $2",
                        _id,
                        ctx.author.id,
                    )
                    t_name = f"{t_name} [{num}]"
                embed.add_field(name=(f"Slot {idx+1} Pokemon"), value=(f"{t_name}"))
        embed.set_footer(
            text="Your Current Pokemon Party | use /party add <slot_number> to add a selected Pokemon"
        )

        await ctx.send(embed=embed)

    @party_base.command(name="add")
    async def party_add(self, ctx, slot: int, poke: int = None) -> None:
        """Add a pokemon to a slot in your party"""
        if slot < 1 or slot > 6:
            await ctx.send("You only add a Pokemon to a slot between 1 and 6!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            ids = await pconn.fetchval(
                "SELECT party FROM users WHERE u_id = $1", ctx.author.id
            )
            if ids is None:
                await ctx.send(f"You have not started!\nStart with `/start` first!")
                return
            if poke is not None:
                _id = await pconn.fetchval(
                    "SELECT pokes[$1] FROM users WHERE u_id = $2", poke, ctx.author.id
                )
            else:
                _id = await pconn.fetchval(
                    "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
                )
            if ids.count(_id) >= 1:
                await ctx.send("That Pokemon already occupies a Team Slot!")
                return
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )
            if pokename is None:
                await ctx.send("You do not have that Pokemon!")
                return
            pokename = pokename.capitalize()
            ids[slot - 1] = _id
            await pconn.execute(
                "UPDATE users SET party = $1 WHERE u_id = $2", ids[:6], ctx.author.id
            )
        await ctx.send(f"Your {pokename} is now on your party, Slot number {slot}")

    @party_base.command(name="remove")
    async def party_remove(self, ctx, slot: int) -> None:
        """Remove a pokemon from a slot in your party"""
        if slot < 1 or slot > 6:
            await ctx.send("Slot must be between 1 and 6!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            ids = await pconn.fetchval(
                "SELECT party FROM users WHERE u_id = $1", ctx.author.id
            )
            if ids is None:
                await ctx.send(f"You have not started!\nStart with `/start` first!")
                return
            _id = ids[slot - 1]
            ids[slot - 1] = 0
            await pconn.execute(
                "UPDATE users SET party = $2 WHERE u_id = $1", ctx.author.id, ids
            )
            pokename = await pconn.fetchval(
                "SELECT pokname FROM pokes WHERE id = $1", _id
            )
        if not pokename:
            await ctx.send("You do not have that Pokemon!")
            return
        pokename = pokename.capitalize()
        await ctx.send(
            f"You have successfully removed {pokename} from Pokemon Number {slot} In your Party!"
        )

    @party_base.command(name="register")
    async def party_register(self, ctx, party_name: str) -> None:
        """Register your current party with a name"""
        party_name = party_name.lower()
        if len(party_name) > 20:
            await ctx.send("That party name is too long. Please choose a shorter one.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            # Pull names of current parties
            party_names = await pconn.fetch(
                "SELECT name FROM partys WHERE u_id = $1", ctx.author.id
            )

            party_names = [record["name"] for record in party_names]

            # Pull their currently used party
            current_party = await pconn.fetchval(
                "SELECT party FROM users WHERE u_id = $1", ctx.author.id
            )
            if current_party is None:
                await ctx.send("You have not started!\nStart with `/start` first.")
                return

            # This is for updating an existing save
            if party_name in party_names:
                await pconn.execute(
                    "UPDATE partys SET slot1=$1, slot2=$2, slot3=$3, slot4=$4, slot5=$5, slot6=$6 WHERE name = $7 AND u_id = $8",
                    *(current_party),
                    party_name,
                    ctx.author.id,
                )

                await ctx.send(f"Successfully updated party save {party_name.title()}")
                return

            # Then we insert this into the party table
            query = """INSERT INTO partys (u_id, name, slot1, slot2, slot3, slot4, slot5, slot6)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"""

            args = (
                ctx.author.id,
                party_name,
                current_party[0],
                current_party[1],
                current_party[2],
                current_party[3],
                current_party[4],
                current_party[5],
            )

            await pconn.execute(query, *args)
        await ctx.send("Successfully created a new party save.")

    @party_base.command(name="deregister")
    async def party_deregister(self, ctx, party_name: str) -> None:
        """Deregister a Party from your saved partys"""
        party_name = party_name.lower()
        async with ctx.bot.db[0].acquire() as pconn:
            # Pull names of current parties
            party_names = await pconn.fetch(
                "SELECT name FROM partys WHERE u_id = $1", ctx.author.id
            )

            party_names = [record["name"] for record in party_names]

            # No party exists with that name
            if party_name not in party_names:
                await ctx.send(f"You do not have a party with the name `{party_name}`.")
                return

            if not await ConfirmView(
                ctx, f"Are you sure you want to deregister party `{party_name}`?"
            ).wait():
                await ctx.send("Party deletion canceled.")
                return

            await pconn.execute(
                "DELETE FROM partys WHERE u_id = $1 AND name = $2",
                ctx.author.id,
                party_name,
            )
        await ctx.send(f"Successfully deregistered party `{party_name}`.")

    @party_base.command(name="load")
    async def party_load(self, ctx, party_name: str) -> None:
        """Load a registered party save by name"""
        party_name = party_name.lower()
        async with ctx.bot.db[0].acquire() as pconn:
            # Pull the party that was saved in database.
            party_data = await pconn.fetchrow(
                "SELECT slot1, slot2, slot3, slot4, slot5, slot6 FROM partys WHERE name = $1 AND u_id = $2",
                party_name,
                ctx.author.id,
            )

            if party_data is None:
                await ctx.send("You don't have a party registered with that name.")
                return

            # Pulls current party
            ids = await pconn.fetchval(
                "SELECT party FROM users WHERE u_id = $1", ctx.author.id
            )

            # Override current party with the new IDs.
            for i in range(6):
                new_id = party_data[i]
                ids[i] = new_id

            await pconn.execute(
                "UPDATE users SET party = $1 WHERE u_id = $2", ids[:6], ctx.author.id
            )

        await ctx.send("Successfully, updated current party from saved data.")

    @party_base.command(name="list")
    async def party_list(self, ctx) -> None:
        """List your saved partys"""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "SELECT name FROM partys WHERE u_id = $1", ctx.author.id
            )
        if data is None:
            await ctx.send(
                "You do not have any saved parties. Register one with `/party register` first."
            )

            return

        raw = "".join(f'{p["name"]}\n' for p in data)
        pages = pagify(
            raw, base_embed=discord.Embed(title="Your Saved Parties", color=0xDD00DD)
        )

        await MenuView(ctx, pages).start()


async def setup(bot) -> None:
    await bot.add_cog(Party(bot))
