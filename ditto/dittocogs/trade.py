from typing import List, Optional
import discord
from discord.ext import commands

from dittocogs.json_files import *
from utils.checks import tradelock
from utils.misc import ConfirmView
import asyncio
from datetime import datetime


class Poke:
    def __init__(self, sender: int, poke_id: int):
        self.sender = sender
        self.poke_id = poke_id
        self.time = datetime.now()
        self.cached_info = None

    def __eq__(self, other):
        if isinstance(other, int):
            return self.poke_id == other

        if not isinstance(other, Poke):
            return False
        return (self.poke_id == other.poke_id) and (self.sender == other.sender)


class Credit:
    def __init__(self):
        self.p1 = 0
        self.p2 = 0


class TradeList:
    def __init__(self, val: List[Poke]):
        self.val = val

    def sender(self, sender: int):
        """Returns the sender's poke list"""
        return [poke for poke in self.val if poke.sender == sender]

    def iter(self, sender: int):
        """Iterates over the poke list"""
        for poke in self.val:
            if poke.sender == sender:
                yield poke


class PokeAddModal(discord.ui.Modal, title="Add A Pokemon!"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.event = asyncio.Event()
        self.output = None
        self.out_interaction = None
        super().__init__()

    poke_id = discord.ui.TextInput(
        label="Pokemon ID", placeholder="ID of the pokemon you want to add"
    )

    async def on_submit(self, interaction: discord.Interaction):
        id = str(self.poke_id).replace(" ", "")

        ids = []

        for id in id.replace(" ", ",").split(","):
            if not id.isdigit() or id in ids:
                continue
            ids.append(int(id))

        if not ids:
            self.output = None
            await interaction.response.send_message(
                f"Please enter a valid pokemon ID", ephemeral=True
            )
            self.event.set()
            return

        self.output = ids

        self.out_interaction = interaction
        self.event.set()


class PokeRemoveModal(discord.ui.Modal, title="Remove A Pokemon!"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.event = asyncio.Event()
        self.output = None
        self.out_interaction = None
        super().__init__()

    poke_id = discord.ui.TextInput(
        label="Pokemon ID", placeholder="ID's of the pokemon you want to remove"
    )

    async def on_submit(self, interaction: discord.Interaction):
        id = str(self.poke_id).replace(" ", "")

        ids = []

        for id in id.replace(" ", ",").split(","):
            if not id.isdigit() or id in ids:
                continue
            ids.append(int(id))

        if not ids:
            self.output = None
            await interaction.response.send_message(
                f"Please enter only valid pokemon ID's, seperated by commas with no spaces",
                ephemeral=True,
            )
            self.event.set()
            return

        self.output = ids

        self.out_interaction = interaction
        self.event.set()


class CreditsSetModal(discord.ui.Modal, title="Add Credits!"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.event = asyncio.Event()
        self.output = None
        self.out_interaction = None
        super().__init__()

    credits = discord.ui.TextInput(
        label="Credit Number", placeholder="Number of credits to trade"
    )

    async def on_submit(self, interaction: discord.Interaction):
        id = (
            str(self.credits)
            .lower()
            .replace(" ", "")
            .replace("k", "000")
            .replace("m", "000000")
        )
        if not id.isdigit():
            self.output = None
            await interaction.response.send_message(
                f"Please enter a valid number of credits: {id}", ephemeral=True
            )
            self.event.set()
            return

        self.output = int(id)

        if self.output < 0:
            self.output = None
            await interaction.response.send_message(
                "You can't trade negative credits!", ephemeral=True
            )
            self.event.set()
            return

        self.out_interaction = interaction
        self.event.set()


ATTEMPT_TRADE = "Confirm Trade"


class TradeMainView(discord.ui.View):
    def __init__(self, ctx, p1: int, p2: int):
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.can_trade = False
        self.attempting = False
        self.cancelled = False
        super().__init__(timeout=360)
        self.msg: Optional[discord.Message] = None

        # Trade values
        self.pokes: List[Poke] = []
        self.credits: Credit = Credit()

    def set_message(self, msg: discord.Message):
        self.msg = msg

    async def interaction_check(self, interaction):
        if interaction.user.id not in (self.p1, self.p2):
            return False
        return True

    async def on_error(self, interaction, error, item):
        await interaction.response.send_message(
            f"Something went wrong: {error} in item {item}", ephemeral=True
        )

    async def on_timeout(self):
        await self.unlock_trade()
        if self.msg:
            await self.msg.edit(
                content=f"**Trade between <@{self.p1}> and <@{self.p2}> cancelled**",
                view=None,
            )
        self.cancelled = True

    async def _attrs(self, pconn, poke):
        if poke.cached_info:
            name = poke.cached_info
        else:
            name = await pconn.fetchrow(
                "SELECT pokname, tradable, shiny, radiant FROM pokes WHERE id = $1",
                poke.poke_id,
            )
            poke.cached_info = name

        attrs = []

        if name["shiny"]:
            attrs.append("Shiny")
        if name["radiant"]:
            attrs.append("Radiant")

        return name, attrs

    async def _trade_evo(self, p, interaction, _id):
        """
        p - The user of said pokemon
        interaction - The interaction
        _id - The id of the pokemon
        """
        async with self.ctx.bot.db[0].acquire() as pconn:
            try:
                pokename = await pconn.fetchval(
                    "SELECT pokname FROM pokes WHERE id = $1",
                    _id,
                )
                helditem = await pconn.fetchval(
                    "SELECT hitem FROM pokes WHERE id = $1", _id
                )
                pokename = pokename.lower()
                try:
                    pid = [t["id"] for t in PFILE if t["identifier"] == pokename][0]
                except:
                    return

                eids = [t["id"] for t in PFILE if t["evolves_from_species_id"] == pid]

                for eid in eids:
                    hitem = [
                        t["held_item_id"]
                        for t in EVOFILE
                        if t["evolved_species_id"] == eid
                    ][0]
                    evo_trigger = [
                        t["evolution_trigger_id"]
                        for t in EVOFILE
                        if t["evolved_species_id"] == eid
                    ][0]

                    if hitem:
                        item = [t["identifier"] for t in ITEMS if t["id"] == hitem]
                        item = item[0]
                        if not helditem.lower() == item.lower():
                            continue

                        else:
                            evoname = [t["identifier"] for t in PFILE if t["id"] == eid]
                            evoname = evoname[0]
                            await pconn.execute(
                                "UPDATE pokes SET pokname = $1 WHERE id = $2",
                                evoname.capitalize(),
                                _id,
                            )
                            await interaction.followup.send(
                                embed=make_embed(
                                    title="Congratulations!!!",
                                    description=f"<@{p}>, your {pokename.capitalize()} has evolved into {evoname.capitalize()}!",
                                )
                            )
                    elif evo_trigger == 2:
                        evoname = [t["identifier"] for t in PFILE if t["id"] == eid]
                        evoname = evoname[0]
                        await pconn.execute(
                            "UPDATE pokes SET pokname = $1 WHERE id = $2",
                            evoname.capitalize(),
                            _id,
                        )
                        await interaction.followup.send(
                            embed=make_embed(
                                title="Congratulations!!!",
                                description=f"<@{p}>, your {pokename.capitalize()} has evolved into {evoname.capitalize()}!",
                            )
                        )
                    else:
                        continue
            except:
                pass

    async def _to_trade_msg(self) -> str:
        msg = []

        poke_trade = TradeList(self.pokes)

        async with self.ctx.bot.db[0].acquire() as pconn:
            msg.append(f"**(<@{self.p1}>)**\n*Pokemon*")

            flag = False
            p1_has = False

            for poke in poke_trade.iter(self.p1):
                flag = True
                p1_has = True

                name, attrs = await self._attrs(pconn, poke)

                msg.append(f"{name['pokname']} ({poke.poke_id})({id}) {attrs}")

            if not p1_has:
                msg.append("No pokemon added to trade")

            if self.credits.p1 > 0:
                msg.append(f"*Credits*\n{self.credits.p1} credits")
                flag = True

            p2_has = False

            msg.append(f"\n**(<@{self.p2}>)**\n*Pokemon*")
            for poke in poke_trade.iter(self.p2):
                flag = True
                p2_has = True

                name, attrs = await self._attrs(pconn, poke)

                msg.append(f"{name['pokname']} ({poke.poke_id})({id}) {attrs}")

            if not p2_has:
                msg.append("No pokemon added to trade")

            if self.credits.p2 > 0:
                msg.append(f"*Credits*\n{self.credits.p2} credits")
                flag = True

        self.can_trade = flag

        return "\n".join(msg)

    async def update_msg(self):
        trade_msg = await self._to_trade_msg()

        for child in self.children:
            if child.label == ATTEMPT_TRADE:
                child.disabled = not self.can_trade

        if self.msg:
            await self.msg.edit(content=f"**Trade Summary**\n{trade_msg}", view=self)

    @discord.ui.button(
        label="Add Pokemon",
        emoji="<a:plus:1008763677509431446>",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def add_poke(self, interaction, button):
        modal = PokeAddModal(self)
        await interaction.response.send_modal(modal)

        await modal.event.wait()

        if not modal.output:
            return

        for poke in modal.output:
            if poke == 1:
                await modal.out_interaction.response.send_message(
                    "You can not give off your Number 1 Pokemon", ephemeral=True
                )
                return

            if poke in self.pokes:
                await modal.out_interaction.response.send_message(
                    "You already have this pokemon in your trade", ephemeral=True
                )
                return

            async with self.ctx.bot.db[0].acquire() as pconn:
                details = await pconn.fetchrow(
                    "SELECT id, pokname, pokelevel, shiny, radiant, tradable FROM pokes WHERE id = (SELECT pokes[$1] FROM users WHERE u_id = $2)",
                    poke,
                    interaction.user.id,
                )

                if not details:
                    await modal.out_interaction.response.send_message(
                        "You do not have that Pokemon or that Pokemon is currently in the market!",
                        ephemeral=True,
                    )
                    return

            if details["id"] in self.pokes:
                await modal.out_interaction.response.send_message(
                    "You already have this pokemon in your trade", ephemeral=True
                )
                return

            if details["pokname"] == "Egg":
                await modal.out_interaction.response.send_message(
                    "You cannot trade eggs!", ephemeral=True
                )
                return

            if not details["tradable"]:
                await modal.out_interaction.response.send_message(
                    "This pokemon is not tradable", ephemeral=True
                )
                return

            self.pokes.append(Poke(interaction.user.id, details["id"]))

        await modal.out_interaction.response.send_message(
            f"Added {modal.output} to your trade list (message will update in a second or two!)",
            ephemeral=True,
        )

        await self.update_msg()

    @discord.ui.button(
        label="Remove Pokemon",
        emoji="<a:minus:1008763512652304555>",
        style=discord.ButtonStyle.danger,
        row=1,
    )
    async def remove_poke(self, interaction, button):
        modal = PokeRemoveModal(self)
        await interaction.response.send_modal(modal)

        await modal.event.wait()

        if not modal.output:
            return

        flag = False

        ext_check = None

        for poke in modal.output:
            async with self.ctx.bot.db[0].acquire() as pconn:
                details = await pconn.fetchrow(
                    "SELECT id, pokname, pokelevel, shiny, radiant, tradable FROM pokes WHERE id = (SELECT pokes[$1] FROM users WHERE u_id = $2)",
                    poke,
                    interaction.user.id,
                )

                if details:
                    ext_check = details["id"]

            for poke in TradeList(self.pokes).iter(interaction.user.id):
                if poke.poke_id == poke or poke.poke_id == ext_check:
                    flag = True
                    self.pokes.remove(poke)

            if flag:
                await modal.out_interaction.response.send_message(
                    f"Removed {poke} from your trade!", ephemeral=True
                )
            else:
                await modal.out_interaction.response.send_message(
                    f"You do not have {poke} in your trade list!\n**Hint:** Are you using the ID next to the name",
                    ephemeral=True,
                )

        await self.update_msg()

    @discord.ui.button(
        label="Add Credits",
        emoji="<:dittocoin:1010679749212901407>",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def set_credits(self, interaction, button):
        modal = CreditsSetModal(self)
        await interaction.response.send_modal(modal)

        await modal.event.wait()

        if modal.output is None:
            return

        async with self.ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", interaction.user.id
            )
            if modal.output > curcreds:
                await modal.out_interaction.response.send_message(
                    "You don't have that many credits at this time..."
                )
                return

        if interaction.user.id == self.p1:
            self.credits.p1 = modal.output
            await modal.out_interaction.response.send_message(
                f"Set {modal.output} credits for Player 1", ephemeral=True
            )
        if interaction.user.id == self.p2:
            self.credits.p2 = modal.output
            await modal.out_interaction.response.send_message(
                f"Set {modal.output} credits for Player 2", ephemeral=True
            )

        await self.update_msg()

    async def unlock_trade(self):
        await self.ctx.bot.redis_manager.redis.execute(
            "LREM", "tradelock", "1", str(self.p1)
        )
        await self.ctx.bot.redis_manager.redis.execute(
            "LREM", "tradelock", "1", str(self.p2)
        )

    @discord.ui.button(
        label=ATTEMPT_TRADE, style=discord.ButtonStyle.primary, row=2, disabled=True
    )
    async def attempt_trade(self, interaction, button):
        if not self.can_trade:
            await interaction.response.send_message(
                "You can not attempt a trade with this trade list", ephemeral=True
            )
            return

        if self.attempting:
            await interaction.response.send_message(
                "You are already attempting a trade", ephemeral=True
            )
            return

        if self.cancelled:
            await interaction.response.send_message(
                "You have cancelled this trade", ephemeral=True
            )
            return

        self.attempting = True

        async def _unlock(ctx, msg):
            await self.unlock_trade()
            self.attempting = False
            await msg.edit(
                content="Trade attempt timed out. Try attempting a trade again using the 'Attempt Trade' button"
            )
            return

        await interaction.response.defer(ephemeral=True)

        CONTENT = "To confirm this trade, both traders must click the Confirm button."

        wait_on = [self.p1, self.p2]

        async def _confirm(i, msg):
            if not wait_on:
                return

            if i.user.id == self.p1:
                wait_on.remove(self.p1)

                if not wait_on:
                    return

                await msg.edit(
                    content=CONTENT + f"\n*Waiting for <@{self.p2}> to confirm trade*"
                )
            else:
                wait_on.remove(self.p2)

                if not wait_on:
                    return

                await msg.edit(
                    content=CONTENT + f"\n*Waiting for <@{self.p1}> to confirm trade*"
                )

        confirm_view = ConfirmView(
            self.ctx,
            CONTENT + f"\n*Waiting for <@{self.p1}> and <@{self.p2}> to confirm trade*",
            on_timeout=_unlock,
            on_confirm=_confirm,
            allowed_interactors=[self.p1, self.p2],
            interaction=interaction,
        )

        if not await confirm_view.wait():
            await self.unlock_trade()
            await self.ctx.send("Trade Rejected!")
            self.attempting = False
            return

        if self.cancelled:
            await interaction.response.send_message(
                "You have cancelled this trade", ephemeral=True
            )
            return

        await confirm_view.message.edit(content="Trade being processed. Please wait")

        # Recheck pokes
        async with self.ctx.bot.db[0].acquire() as pconn:
            for poke in TradeList(self.pokes).iter(self.p1):
                is_owner = await pconn.fetchval(
                    "SELECT u_id FROM users WHERE pokes @> $1",
                    [poke.poke_id],
                )
                if is_owner != self.p1:
                    await interaction.followup.send(
                        f"<@{self.p1}> no longer owns one or more of the pokemon they were trading, canceling trade!"
                    )
                    await self.on_timeout()
                    self.stop()
                    return

            for poke in TradeList(self.pokes).iter(self.p2):
                is_owner = await pconn.fetchval(
                    "SELECT u_id FROM users WHERE pokes @> $1",
                    [poke.poke_id],
                )
                if is_owner != self.p2:
                    await interaction.followup.send(
                        f"<@{self.p2}> no longer owns one or more of the pokemon they were trading, canceling trade!"
                    )
                    await self.on_timeout()
                    self.stop()
                    return

            p1_info = await pconn.fetchrow(
                "SELECT selected, mewcoins FROM users WHERE u_id = $1", self.p1
            )

            if p1_info["selected"] in TradeList(self.pokes).sender(self.p1):
                await interaction.followup.send(
                    f"<@{self.p1}> has selected one or more of the pokemon they were trading, canceling trade!"
                )
                await self.on_timeout()
                self.stop()
                return

            if self.credits.p1 and self.credits.p1 > p1_info["mewcoins"]:
                await interaction.followup.send(
                    f"<@{self.p1}> does not have enough credits to complete this trade, canceling trade!"
                )
                await self.on_timeout()
                self.stop()
                return

            p2_info = await pconn.fetchrow(
                "SELECT selected, mewcoins FROM users WHERE u_id = $1", self.p2
            )

            if p2_info["selected"] in TradeList(self.pokes).sender(self.p2):
                await interaction.followup.send(
                    f"<@{self.p2}> has selected one or more of the pokemon they were trading, canceling trade!"
                )
                await self.on_timeout()
                self.stop()
                return

            if self.credits.p2 and self.credits.p2 > p2_info["mewcoins"]:
                await interaction.followup.send(
                    f"<@{self.p2}> does not have enough credits to complete this trade, canceling trade!"
                )
                await self.on_timeout()
                self.stop()
                return

            # Begin the trade

            # Mewcoins
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                self.credits.p2,  # Credits p2 is giving to p1
                self.p1,
            )

            # Remove credits from p2
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                self.credits.p2,
                self.p2,
            )

            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                self.credits.p1,  # Credits p1 is giving to p2
                self.p2,
            )

            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                self.credits.p1,
                self.p1,
            )

            # Pokemon
            for poke in TradeList(self.pokes).iter(self.p1):
                # Remove pokemon from player 1 and give to player 2
                await pconn.execute(
                    "UPDATE users set pokes = array_remove(pokes, $1) WHERE u_id = $2",
                    poke.poke_id,
                    self.p1,
                )
                await pconn.execute(
                    "UPDATE users set pokes = array_append(pokes, $1) WHERE u_id = $2",
                    poke.poke_id,
                    self.p2,
                )
                await pconn.execute(
                    "UPDATE pokes SET market_enlist = false WHERE id = $1",
                    poke.poke_id,
                )

            for poke in TradeList(self.pokes).iter(self.p2):
                # Remove pokemon from player 2 and give to player 1
                await pconn.execute(
                    "UPDATE users set pokes = array_remove(pokes, $1) WHERE u_id = $2",
                    poke.poke_id,
                    self.p2,
                )
                await pconn.execute(
                    "UPDATE users set pokes = array_append(pokes, $1) WHERE u_id = $2",
                    poke.poke_id,
                    self.p1,
                )
                await pconn.execute(
                    "UPDATE pokes SET market_enlist = false WHERE id = $1",
                    poke.poke_id,
                )

            # Just in case
            await self.unlock_trade()
            self.stop()

            await interaction.followup.send("Checking for trade evolutions...")

            # Check for trade evolutions
            for poke in self.pokes:
                await self._trade_evo(poke.sender, interaction, poke.poke_id)

            await interaction.followup.send("Trade Complete!")

    @discord.ui.button(
        label="Cancel Trade", emoji="❌", style=discord.ButtonStyle.danger, row=2
    )
    async def cancel_trade(self, interaction, button):
        await self.on_timeout()
        self.stop()
        await interaction.response.send_message("Trade cancelled", ephemeral=True)


class Trade(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_task = asyncio.create_task(self.initialize())
        # 2 different users could make a trade to the same person, who does `;accept` and gets both before either notices the other started.
        # Since this issue only happens in a single guild, a cluster-local tradelock can prevent it.
        self.start_tradelock = []

    async def initialize(self):
        await self.bot.redis_manager.redis.execute("LPUSH", "tradelock", "123")

    # @commands.hybrid_command()
    # async def tradediag(self, ctx):
    #    """Diagnoses trading"""
    #    await ctx.bot.redis_manager.redis.execute(
    #        "LREM", "tradelock", "1", str(ctx.author.id)
    #    )

    # @commands.hybrid_command()
    # async def test_trade_view(self, ctx, p2: discord.User):
    #    view = TradeMainView(ctx, ctx.author.id, p2.id)
    #    msg = await ctx.send("Test trade view up", view=view)
    #    view.set_message(msg)

    @commands.hybrid_group()
    @tradelock
    async def gift(self, ctx):
        ...

    @gift.command(aliases=["redeem"])
    @discord.app_commands.describe(
        user="The User to gift Redeems",
        amount="The amount of redeems you want to gift.",
    )
    @tradelock
    async def redeems(self, ctx, user: discord.Member, amount: int):
        """Gift redeems to another user."""
        val = amount
        if ctx.guild != ctx.bot.official_server:
            await ctx.send(
                "This command can only be used in the Dittobot Official Server."
            )
            return
        if ctx.author.id == user.id:
            await ctx.send("You can not give yourself redeems.")
            return
        if val <= 0:
            await ctx.send("You need to give at least 1 redeem!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if any(
                [
                    i["tradelock"]
                    for i in (
                        await pconn.fetch(
                            "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                            [user.id, ctx.author.id],
                        )
                    )
                ]
            ):
                await ctx.send("A user is not allowed to trade")
                return
            giver_deems = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", ctx.author.id
            )
            getter_deems = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", user.id
            )
        if getter_deems is None:
            await ctx.send(f"{user.name} has not started... Start with `/start` first!")
            return
        if giver_deems is None:
            await ctx.send(
                f"{ctx.author.name} has not started... Start with `/start` first!"
            )
            return
        if val > giver_deems:
            await ctx.send("You don't have that many redeems!")
            return
        if not await ConfirmView(
            ctx, f"Are you sure you want to give {val} redeems to {user.name}?"
        ).wait():
            await ctx.send("Trade Canceled")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", ctx.author.id
            )
            if val > curcreds:
                await ctx.send("You don't have that many redeems anymore...")
                return
            await pconn.execute(
                "UPDATE users SET redeems = redeems - $1 WHERE u_id = $2",
                val,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await ctx.send(f"{ctx.author.name} has given {user.name} {val} redeems.")
            await ctx.bot.get_partial_messageable(1004190550678831214).send(
                f"\N{SMALL BLUE DIAMOND}- {ctx.author.name} - ``{ctx.author.id}`` has given \n{user.name} - `{user.id}`\n```{val} redeems```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_redeems, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                val,
                "gift_redeems",
                datetime.now(),
            )

    @gift.command(aliases=["credit"])
    @discord.app_commands.describe(
        user="The User to gift Credits",
        amount="The amount of credits you want to gift.",
    )
    @tradelock
    async def credits(self, ctx, user: discord.Member, amount: int):
        """Gift credits to another user."""
        val = amount
        if ctx.author.id == user.id:
            await ctx.send("You can not give yourself credits.")
            return
        if val <= 0:
            await ctx.send("You need to give at least 1 credit!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if any(
                [
                    i["tradelock"]
                    for i in (
                        await pconn.fetch(
                            "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                            [user.id, ctx.author.id],
                        )
                    )
                ]
            ):
                await ctx.send("A user is not allowed to Trade")
                return
            giver_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )

        if getter_creds is None:
            await ctx.send(f"{user.name} has not started... Start with `/start` first!")
            return
        if giver_creds is None:
            await ctx.send(
                f"{ctx.author.name} has not started... Start with `/start` first!"
            )
            return
        if val > giver_creds:
            await ctx.send("You don't have that many credits!")
            return
        if not await ConfirmView(
            ctx, f"Are you sure you want to give {val} credits to {user.name}?"
        ).wait():
            await ctx.send("Trade Canceled")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", ctx.author.id
            )
            if val > curcreds:
                await ctx.send("You don't have that many credits anymore...")
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                val,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await ctx.send(f"{ctx.author.name} has given {user.name} {val} credits.")
            await ctx.bot.get_partial_messageable(1004571710323957830).send(
                f"\N{SMALL BLUE DIAMOND}- {ctx.author.name} - ``{ctx.author.id}`` has gifted \n{user.name} - `{user.id}`\n```{val} credits```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                val,
                "gift",
                datetime.now(),
            )

    @gift.command(aliases=["poke"])
    @discord.app_commands.describe(
        user="The User to receive the Pokémon",
        pokemon="The number of the Pokémon you want to gift.",
    )
    @tradelock
    async def pokemon(self, ctx, user: discord.Member, pokemon: int):
        """Gift a Pokémon to another user."""
        val = pokemon
        if ctx.author == user:
            await ctx.send("You cannot give a Pokemon to yourself.")
            return
        if val <= 1:
            await ctx.send("You can not give away that Pokemon")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            for u in (ctx.author, user):
                id_ = await pconn.fetchval(
                    "SELECT u_id FROM users WHERE u_id = $1", u.id
                )
                if id_ is None:
                    await ctx.send(f"{u.name} has not started!")
                    return
            if any(
                [
                    i["tradelock"]
                    for i in (
                        await pconn.fetch(
                            "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                            [user.id, ctx.author.id],
                        )
                    )
                ]
            ):
                await ctx.send("A user is not allowed to Trade")
                return
            poke_id = await pconn.fetchval(
                "SELECT pokes[$1] FROM users WHERE u_id = $2", val, ctx.author.id
            )
            name = await pconn.fetchrow(
                "SELECT market_enlist, pokname, shiny, radiant, fav, tradable FROM pokes WHERE id = $1",
                poke_id,
            )
        if not name:
            await ctx.send("Invalid Pokemon Number")
            return
        shine = ""
        if name["shiny"]:
            shine += "Shiny "
        if name["radiant"]:
            shine += "Radiant "
        if name["fav"]:
            await ctx.send(
                "You can't give away a favorited pokemon. Unfavorite it first!"
            )
            return
        if not name["tradable"]:
            await ctx.send("That pokemon is not tradable.")
            return
        name = name["pokname"]
        if name == "Egg":
            await ctx.send("You can not give Eggs!")
            return

        if not await ConfirmView(
            ctx, f"Are you sure you want to give a {name} to {user.name}?"
        ).wait():
            await ctx.send("Trade Canceled")
            return

        await ctx.bot.commondb.remove_poke(ctx.author.id, poke_id)
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = $2",
                poke_id,
                user.id,
            )
            await ctx.send(f"{ctx.author.name} has given {user.name} a {name}")
            await ctx.bot.get_partial_messageable(1004571710323957830).send(
                f"\N{SMALL BLUE DIAMOND}- {ctx.author.name} - ``{ctx.author.id}`` has given \n{user.name} - `{user.id}`\n```{poke_id} {name}```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_pokes, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                [poke_id],
                "give",
                datetime.now(),
            )

    @commands.hybrid_command()
    @discord.app_commands.describe(user="The User to begin the trade with.")
    async def trade(self, ctx, user: discord.Member):
        """Begin a trade with another user!"""
        # SETUP
        if ctx.author.id == user.id:
            await ctx.send("You cannot trade with yourself!")
            return
        current_traders = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if ctx.author.id in current_traders:
            await ctx.send(f"{ctx.author.name} is currently in a trade!")
            return
        if user.id in current_traders:
            await ctx.send(f"{user.name} is currently in a trade!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if any(
                [
                    i["tradelock"]
                    for i in (
                        await pconn.fetch(
                            "SELECT tradelock FROM users WHERE u_id = ANY($1)",
                            [user.id, ctx.author.id],
                        )
                    )
                ]
            ):
                await ctx.send(f"A user is not allowed to Trade")
                return
            if (
                await pconn.fetchval(
                    "SELECT 1 FROM users WHERE u_id = $1", ctx.author.id
                )
                is None
            ):
                await ctx.send(
                    f"{ctx.author.display_name} has not started!\nStart with `/start` first!"
                )
                return
            if (
                await pconn.fetchval("SELECT 1 FROM users WHERE u_id = $1", user.id)
                is None
            ):
                await ctx.send(
                    f"{user.display_name} has not started!\nStart with `/start` first!"
                )
                return
        await self.bot.redis_manager.redis.execute(
            "LPUSH", "tradelock", str(ctx.author.id)
        )
        #prefix = "/"

        async def _unlock(ctx, msg):
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await msg.edit(
                content=f"{user.mention} took too long to accept the trade..."
            )
            return

        cview = ConfirmView(
            ctx,
            f"{ctx.author.mention} has requested a trade with {user.mention}!\n*Waiting for {user.mention} to confirm...*",
            on_timeout=_unlock,
            allowed_interactors=[user.id],
        )

        if not await cview.wait():
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await cview.message.edit(content="Trade Rejected!")
            return

        await ctx.send(
            f"Trade between {ctx.author.mention} and {user.mention}!", ephemeral=True
        )

        if user.id in self.start_tradelock:
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await ctx.send(f"{user.name} is currently in a trade!")
            return
        self.start_tradelock.append(user.id)
        current_traders = [
            int(id_)
            for id_ in await self.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if user.id in current_traders:
            await self.bot.redis_manager.redis.execute(
                "LREM", "tradelock", "1", str(ctx.author.id)
            )
            await ctx.send(f"{user.name} is currently in a Trade!")
            return
        await self.bot.redis_manager.redis.execute("LPUSH", "tradelock", str(user.id))
        self.start_tradelock.remove(user.id)
        view = TradeMainView(ctx, ctx.author.id, user.id)
        msg = await ctx.send(
            "Use the buttons to add pokemon/credits/redeems to the current trade. Multiple ID's can be added at once-seperated by spaces.",
            view=view,
        )
        view.set_message(msg)


async def setup(bot):
    await bot.add_cog(Trade(bot))
