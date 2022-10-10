import asyncio
import random
from enum import Enum, IntEnum
from math import ceil, floor
from typing import Optional

import discord
from discord.ext import commands
from utils.checks import check_helper


# old
def generate(luck):
    luck = min(luck, 10)
    return max(1, int(random.random() * int(35 - (luck - 1) * 0.75)))


# old
def all_equal(iterator):
    return len(set(iterator)) <= 1


# old
def two_equal(iterator):
    first = iterator[1:]
    second = iterator[:-1]
    last = iterator[:1] + iterator[-1:]
    return any([all_equal(first), all_equal(second), all_equal(last)])


slot_gif = (
    "http://images.dittobot.me/Lychee/uploads/big/7634c78a96f38b892db08cf68c25d0b8.gif"
)

# New
spin_emoji = "<:Poke:844434416935108630>"


class RewardsEnum(IntEnum):
    FILLER1 = 0
    FILLER2 = 1
    FILLER3 = 2
    FILLER4 = 3
    FILLER5 = 4
    FILLER6 = 5
    BREED = 6
    LOSE = 7
    FREE_SPIN = 8
    BET_50 = 9
    SECOND_TIER = 10
    FIRST_TIER = 11
    JACKPOT = 12


class Reroll(IntEnum):
    OFF = 0
    ON = 1
    ON_JACKPOT = 2


# I initially had no idea what to internally call the bet tiers.
# So I named them after warrior cats because I like them.
# Please keep the names warrior cats related and keep them
# like this since I want something warrior cats related in
# the source code.


class BetTiers:
    """Stores all tier metadata types (maybe could be a debug command or smth), but def useful for development
    Types:

    range - anything with begin and end ONLY as keys

    Devs should add other tier metadata types as they add stuff
    """

    _metadata_types = {
        "breed": "range",
    }
    _tiers = [
        {
            "min": 100,  # Minimum coins needed
            "max": 1000,  # Maximum coins for tier, set last tier to None to mean no maximum
            "tierName": "Bronze",
            # Just to make it easier to debug/Give unique names that aren't used everywhere and can never change unlike tier names which may change
            "internalName": "Shadowsight",
            "metadata": {  # Metadata for a tier, if the reward of the particular metadata does not exist, omit its group entirely.
                "_groups": (
                    "breed",
                ),  # All groups, this key is very important and can be relied upon existing. WARNING: DO NOT CHANGE GROUP NAMES EVER
                "breed": {
                    "start": 1,  # Breed multiplier starts
                    "end": 5,  # Breed multiplier ends
                },
            },
        },
        {
            "min": 1000,
            "max": 10000,
            "tierName": "Silver",
            "internalName": "Bristlefrost",
            "metadata": {
                "_groups": ("breed",),
                "breed": {"start": 10, "end": 20},
            },
        },
        {
            "min": 10000,
            "max": 100000,
            "tierName": "Gold",
            "internalName": "Ashfur",
            "metadata": {
                "_groups": ("breed",),
                "breed": {"start": 30, "end": 50},
            },
        },
        {
            "min": 100000,
            "max": 200000,
            "tierName": "Platinum",
            "internalName": "Squirrelflight",
            "metadata": {
                "_groups": ("breed",),
                "breed": {"start": 70, "end": 90},
            },
        },
        {
            "min": 200000,
            "max": None,
            "tierName": "Diamond",
            "internalName": "Snowtuft",
            "metadata": {
                "_groups": ("breed",),
                "breed": {"start": 110, "end": 150},
            },
        },
    ]

    def __init__(self, tier):
        self.tier = tier

    @staticmethod
    def get_tier(coins):
        # Gets the tier given a number of coins
        for t in BetTiers._tiers:
            if coins >= t["min"] and (not t["max"] or coins < t["max"]):
                return BetTiers(t)
        raise ValueError(f"No bet tier found for {coins} coins")

    def next_tier(self):
        return BetTiers(self._tiers[self._tiers.index(self.tier) + 1])

    def __eq__(self, other):
        if isinstance(other, BetTiers):
            return (
                self.tier["internalName"].upper() == other.tier["internalName"].upper()
            )
        elif isinstance(other, dict):
            return self.tier["internalName"].upper() == other["internalName"].upper()
        elif isinstance(other, str):
            return (
                self.tier["internalName"].upper() == other.upper()
            )  # Handle string compare as well to make comparing easier
        elif isinstance(other, Enum):
            return (
                self.tier["internalName"].upper() == other.name.upper()
            )  # Also handle our old enum code as well
        return False

    def coins(self, tier=None):
        """Given tier is the tier class itself"""
        if not tier:
            tier = self.tier
        if isinstance(tier, BetTiers):
            tier = tier.tier
        return "{:,} coins".format(tier["min"])

    def friendly(self):
        """Returns the friendly string for the tier modifier"""
        try:
            next_tier = self.next_tier()
            modifier = (
                f"The next tier is {next_tier.tier['tierName']} at {next_tier.coins()}"
            )
            try:
                next_next_tier = next_tier.next_tier()
                modifier += f" to {next_next_tier.coins()}"
            except IndexError:
                modifier += "."
        except IndexError:
            modifier = "This is the final tier"
        return f"{self.tier['tierName']} ({self.coins()} tier).", modifier

    # Base Getters
    def _base_range_getter(self, group):
        """
        Metadata Checking Methods

        NOTE: All methods here must check _groups if the thing they are looking for is supported. raise NotImplementedError if so. Callers should handle the error correctly (mostly just pass and/or sending the str of the exception as these rewards are tier specific). If in doubt, use the base getter for your metadata type (see _metadata_types dictionary)
        """
        if group not in self.tier["metadata"]["_groups"]:
            raise NotImplementedError(
                f"This tier does not support the reward '{group}'!"
            )
        return (
            self.tier["metadata"][group]["start"],
            self.tier["metadata"][group]["end"],
        )

    # Range Getters
    def get_breed_multi(self):
        return self._base_range_getter("breed")


# New
slot_dict = {
    # Filler (IMPLEMENTED)
    RewardsEnum.FILLER1: "<:wailmer:844434417246142514>",
    RewardsEnum.FILLER2: "<:urs:844434418398527508>",  # Filler (IMPLEMENTED)
    RewardsEnum.FILLER3: "<:star:844434418172559370>",  # Filler (IMPLEMENTED)
    RewardsEnum.FILLER4: "<:poli:844434417933221909>",  # Filler (IMPLEMENTED)
    RewardsEnum.FILLER5: "<:sudo:844434417660329984>",  # Filler (IMPLEMENTED)
    # Filler (IMPLEMENTED)
    RewardsEnum.FILLER6: "<:star_wars_copy_2_cartoon_charact:844434418281218058>",
    RewardsEnum.BREED: "<:egg:844434416200712193>",  # Breeding (IMPLEMENTED)
    RewardsEnum.LOSE: "<:gas:844434417816829972>",  # Lose Coins (IMPLEMENTED)
    # Free spin (IMPLEMENTED)
    RewardsEnum.FREE_SPIN: "<:ball5:844434418135203870>",
    # Get 50% Bet (IMPLEMENTED)
    RewardsEnum.BET_50: "<:Poke:844434416935108630>",
    # Second Tier (IMPLEMENTED)
    RewardsEnum.SECOND_TIER: "<:bal3:844434417958256671>",
    # First tier (IMPLEMENTED)
    RewardsEnum.FIRST_TIER: "<:ball6:844434418197594122>",
    # Jackpot (IMPLEMENTED)
    RewardsEnum.JACKPOT: "<:Crown:844434416856203294>",
}


class RerollView(discord.ui.View):
    def __init__(self, callback, timeout, uid):
        """Where callback is the asyncio coroutine to be called"""
        self.callback = callback
        self.timeout_fn = timeout
        self.uid = uid
        super().__init__(timeout=180)

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.green)
    async def reroll(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.uid:
            return
        await self.callback

    async def on_timeout(self):
        await self.timeout_fn


# Begin actual cog code (finally)
class GameCorner(commands.Cog):
    # New
    def _get_bet(self, bet: str) -> int:
        try:
            bet = bet.lower().replace(" ", "").replace(",", "")
            if bet.endswith("k"):
                return int(bet.replace("k", "")) * 1000
            elif bet.endswith("l") or bet.endswith("ht"):
                return int(bet.replace("ht", "").replace("l", "")) * 100000
            return int(bet) if bet.isdigit() else None
        except:
            return None

    @commands.hybrid_command()
    async def dreamslots(
        self,
        ctx: commands.Context,
        bet: str,
        s1: int,
        s2: int,
        s3: int,
        embed: bool = True,
    ):
        bet = self._get_bet(bet)
        if not bet:
            await ctx.send(
                "Bet must be a number. Youcan use k for 1,000 and ht/l for 100,000 (2k etc.)"
            )
            return
        if ctx.author.id not in (
            563808552288780322,
            455277032625012737,
            790722073248661525,
            473541068378341376,
        ):
            return await ctx.send(
                "Your dreams died! You aren't a whitelisted developer or a whitelisted developer helper and as such you can't use this command, so ha! If you *are* a developer, please DM skylarr#6666 for access to this debug command!"
            )
        try:
            slot_results = [RewardsEnum(s1), RewardsEnum(s2), RewardsEnum(s3)]
        except Exception as exc:
            await ctx.send(
                f"DEBUG: Internal Error Occurred **WARNING:** We couldn't kill your dreams because of the following error:\n\n{type(exc).__name__}: {exc}"
            )  # Give an error
            raise exc
        await ctx.send(
            f"DEBUG: Dreamslots called with {slot_results}.\n**WARNING:** This is where your dreams go to die..."
        )
        return await self._slotsnew(
            ctx=ctx, bet=bet, dbg_slot_results=slot_results, embed=embed
        )

    @check_helper()
    @commands.hybrid_command()
    async def slotsnew(self, ctx: commands.Context, bet: str, embed: bool = True):
        bet = self._get_bet(bet)
        if not bet:
            await ctx.send(
                "Bet must be a number.\n**Tip:** You can use k for one thousand and 'ht' or 'l' for hundred thousand (or lakh)"
            )
            return
        if embed in {0, 1}:
            return await self._slotsnew(ctx=ctx, bet=bet, embed=embed)
        else:
            return await ctx.send("You can only give 0 or 1 for embed/no embed")

    async def _slotsnew(
        self,
        ctx: commands.Context,
        bet: int,  # How much to bet?
        embed: bool,
        # Should be None unless in dreamslots
        dbg_slot_results: Optional[list] = None,
        reroll: Optional[Reroll] = None,  # Reroll state for previous reroll
        reroll_reward: Optional[dict] = None,  # Reward for reroll currently
        prev_slot_results: Optional[list] = None,  # Previous reroll results
        # Whether we are currently in a reroll
        in_reroll: Optional[bool] = False,
        # Our reroll luck for previous round
        reroll_luck: Optional[int] = None,
    ):

        if in_reroll and reroll.OFF:
            return

        MIN_COINS = 100
        MAX_COINS = 250000
        if bet < MIN_COINS or bet > MAX_COINS:
            await ctx.send(
                f"You must bet a minimum of {MIN_COINS} coins and a maximum of {MAX_COINS} coins <:Vapocry:800374886496337920>!"
            )
            return

        tier = BetTiers.get_tier(bet)
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT energy, luck, inventory::json FROM users WHERE u_id = $1",
                ctx.author.id,
            )

        if not data:
            await ctx.send(
                f"You have not started yet!\nStart with `{ctx.prefix}start` first!"
            )
            return

        luck = reroll_luck if in_reroll else data["luck"]
        energy = data["energy"]
        items = data["inventory"]
        if not in_reroll and energy == 0:
            await ctx.send("Please wait for your energy to be replenished!")
            return

        # User does not have a coin case
        if "coin-case" not in items:
            await ctx.send(
                f"You do not have a coin case yet!\nBuy one with `{ctx.prefix}buy coin case`."
            )
            return
        coins = items["coin-case"]

        # If not in reroll, check bet amount to make sure it isn't invalid
        if not in_reroll:
            if coins < bet:
                await ctx.send("You don't have enough coins")
                return
            elif bet <= 0:
                await ctx.send("Invalid coins amount!")
                return

        if not in_reroll:
            tier.friendly()
            e = discord.Embed(title="Slots", color=0xFFB6C1)
        else:
            e = discord.Embed(title="Slots Reroll", color=0xFFBC61)

        msg = [":white_circle:", ":white_circle:", ":white_circle:"]
        e.description = " ".join(msg)
        dmsg = await ctx.send(embed=e) if embed else await ctx.send(e.description)
        # We use predetermined weights here to make things slightly easier for users
        slot_results = random.choices(
            list(RewardsEnum),
            #        F1   F2   F3   F4   F5   F6   BR LO FS  B5  ST  FT  JP
            weights=(1.2, 1.2, 1.3, 1.2, 1.1, 1.0, 5, 9, 10, 12, 11, 9, 7),
            k=3,
        )

        try:
            for i in range(3):
                if dbg_slot_results:
                    slot_results[i] = dbg_slot_results[i]

                await asyncio.sleep(0.6)

                # Note to self: Slot dict is a dict defined above that defines all the emojis
                msg[i] = slot_dict[slot_results[i]]
                msg_str = " ".join(msg)
                if embed:
                    e.description = msg_str
                    await dmsg.edit(embed=e)
                else:
                    await dmsg.edit(msg_str)
        except Exception as exc:
            return await ctx.send(str(exc))

        def most_frequent(List):
            """From programiz"""
            return max(set(List), key=List.count)

        result = RewardsEnum(most_frequent(slot_results))

        # Reroll state to start with always starts with OFF
        reroll_new = Reroll.OFF

        # This is the reroll state of the previous roll if in a reroll
        # that we have to account for. It should not be modified in code
        reroll_curr = reroll if in_reroll else Reroll.OFF

        # The amount of good/matching slots
        total_good = slot_results.count(result)
        reward = reroll_reward if reroll_curr == Reroll.ON_JACKPOT else {"coin-case": 0}

        async def _error(ctx, bet, luck):
            coin_case = -bet * 0.974
            luck -= 2
            luck = max(luck, 0)
            return coin_case, luck

        if result.name.startswith("FILLER") or (
            result == RewardsEnum.JACKPOT and total_good < 2
        ):
            reward["coin-case"], luck = await _error(ctx, bet, luck)

        elif result == RewardsEnum.LOSE:
            if total_good == 2:
                # 2 coins
                reward["coin-case"] = ceil(-1 * bet * 1.5)
            else:
                # 3 coins
                reward["coin-case"] = ceil(-1 * bet * 2.5)
            e = discord.Embed(
                title="You Lose!",
                description=f"Say good bye to {abs(reward['coin-case'])} coins!",
                color=discord.Color.red(),
            )
            await ctx.send(embed=e)

        elif result == RewardsEnum.FREE_SPIN and total_good == 3:
            await ctx.send("**Free Spin!**")
            # Set new reroll state to ON
            reroll_new = Reroll.ON

        elif result == RewardsEnum.SECOND_TIER and total_good == 3:
            reward["coin-case"] += 2 * bet
            luck += 2
            e = discord.Embed(
                title="Second Tier Spin!",
                description="Way to go! You got x2 of your bet and your luck increased by 2!",
                color=discord.Color.light_grey(),
            )
            await ctx.send(embed=e)

        elif result == RewardsEnum.FIRST_TIER and total_good == 3:
            reward["coin-case"] += 3 * bet
            luck += 4
            e = discord.Embed(
                title="First Tier Spin!",
                description="Congratulations! You got x3 of your bet and your luck increased by 4!",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=e)

        elif result == RewardsEnum.BET_50 and total_good == 3:
            reward["coin-case"] += 0.5 * bet
            luck += 1
            e = discord.Embed(
                title="50% Bet",
                description="You got 50% of your bet back!",
                color=discord.Color.magenta(),
            )
            await ctx.send(embed=e)

        elif result == RewardsEnum.JACKPOT and total_good == 3:
            if reroll_curr == Reroll.ON_JACKPOT:
                reward["coin-case"] *= 3  # Triple payout
                luck += 4
                e = discord.Embed(
                    title="Reroll Paid Off!",
                    description="That reroll paid off. You win x3 of your bet and your luck has increased by 4",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=e)
            else:
                reward["coin-case"] = ceil(
                    (bet + (bet * (random.uniform(1, 1.5)) + 100)) * 1.15
                )
                e = discord.Embed(
                    title="Jackpot!",
                    description=f"**Congratulations!**\nYou hit the jackpot! You have won {reward['coin-case']} and your luck increased by 7. You can reroll to get triple the money and some luck.",
                    color=discord.Color.gold(),
                )
                await ctx.send(embed=e)
                reroll_new = Reroll.ON_JACKPOT
                luck += 7

        elif result == RewardsEnum.JACKPOT and total_good == 2:
            # Always make sure they gain (with balancing)
            luck = ceil(min(luck, 100) * 0.5)
            coins = ceil(bet + (bet * (random.uniform(1, 1.5)) * 100) * (luck / 101))
            reward["coin-case"] += coins  # Anyways will be floored

            # Drop luck by 6 for only getting 2 crowns
            luck -= 6
            luck = max(luck, 0)
            color = discord.Color.blurple()
            e = discord.Embed(
                title="2 Crowns",
                description=f"You got {abs(coins)} coins since you got 2 crowns.",
                color=color,
            )
            await ctx.send(embed=e)

        elif result == RewardsEnum.BREED and total_good == 3:
            start, end = tier.get_breed_multi()
            steps_lost = floor(bet * random.uniform(start, end) * 0.245)
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE pokes SET counter = (SELECT MAX(steps) FROM (VALUES (pokes.counter - $2), (1)) AS stepoptions(steps)) WHERE id = ANY(SELECT unnest(party) FROM users WHERE u_id = $1) AND counter > 0",
                    ctx.author.id,
                    steps_lost,
                )
            if dbg_slot_results:
                await ctx.send(f"DEBUG: Breeding steps lost = {steps_lost}")
            luck += 1
        else:
            reward["coin-case"], luck = await _error(ctx, bet, luck)

        # Helper function to give rewards
        async def give_reward(ctx, items, reward, luck):
            async with ctx.bot.db[0].acquire() as pconn:
                items["coin-case"] += reward["coin-case"]
                items["coin-case"] = max(items["coin-case"], 0)
                items["coin-case"] = ceil(items["coin-case"])
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json WHERE u_id = $2",
                    items,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET energy = energy - 1 WHERE u_id = $1",
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET luck = $1 WHERE u_id = $2",
                    floor(luck),
                    ctx.author.id,
                )

        if reroll_new == Reroll.OFF:
            await give_reward(ctx, items, reward, luck)
            if energy <= 1:
                await ctx.send(
                    "You have used up all of your energy!\nYou will get an energy bar every 20 Minutes or you can also upvote DittoBOT if you haven't done it yet to get an energy bar"
                )
                upvote = ctx.bot.get_command("upvote")
                if command is not None:  # why is this undefined? - Motzumoto
                    return await ctx.invoke(upvote)
            return

        try:
            if reroll_new == Reroll.ON:
                await ctx.send(
                    "You can reroll again :)",
                    view=RerollView(
                        self._slotsnew(
                            ctx=ctx,
                            bet=bet,
                            embed=embed,
                            dbg_slot_results=dbg_slot_results,
                            reroll=reroll_new,
                            reroll_reward=reward,
                            prev_slot_results=slot_results,
                            in_reroll=True,
                            reroll_luck=luck,
                        ),
                        give_reward(
                            ctx, items, reward, luck
                        ),  # Give them the reward on timeout
                        ctx.author.id,
                    ),
                )
            elif reroll_new == Reroll.ON_JACKPOT:
                await ctx.send(
                    "Do you want to try rerolling for a chance to triple the money you got?",
                    view=RerollView(
                        self._slotsnew(
                            ctx=ctx,
                            bet=bet,
                            embed=embed,
                            dbg_slot_results=dbg_slot_results,
                            reroll=reroll_new,
                            reroll_reward=reward,
                            prev_slot_results=slot_results,
                            in_reroll=True,
                            reroll_luck=luck,
                        ),
                        give_reward(
                            ctx, items, reward, luck
                        ),  # Give them the reward on timeout
                        ctx.author.id,
                    ),
                )
        except Exception as exc:
            await ctx.send(str(exc))
            return

    # Old
    @commands.hybrid_command()
    async def slots(self, ctx, bet=None):
        async with ctx.bot.db[0].acquire() as pconn:
            items = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            energy = await pconn.fetchrow(
                "SELECT energy, luck FROM users WHERE u_id = $1", ctx.author.id
            )
            if not energy:
                await ctx.send(
                    f"You have not Started!\nStart with `{ctx.prefix}start` first!"
                )
                return

            luck = energy["luck"]
            energy = energy["energy"]
            if energy == 0:
                await ctx.send("Please wait for your energy to be replenished!")
                return
            if "coin-case" not in items:
                await ctx.send("You do not have a Coin Case!")
                return
        if not bet:
            await ctx.send("Bet how many coins?")

            def check(m):
                return all([m.author == ctx.author, m.channel == ctx.channel])

            try:
                msg = await ctx.bot.wait_for("message", check=check, timeout=60)
            except:
                await ctx.send("You took too long!")
                return
            msg.content = msg.content.replace("k", "000").replace("m", "000000")
            try:
                bet = int(msg.content)
            except:
                await ctx.send("Invalid bet amount!")
                return
        try:
            bet = max(0, int(bet))
        except:
            await ctx.send("Invalid bet amount!")
            return
        coins = items["coin-case"]

        if coins < bet:
            await ctx.send("You don't have enough coins")
            return
        elif bet <= 0:
            await ctx.send("Invalid coins amount!")
            return
        payout = max(90, int(random.random() * 100))
        e = discord.Embed(
            title="Welcome To DittoBOT Game Corner!\nRolling the Slots!",
            description=f"Your Payout % is {payout} %, hitting the Jackpot doubles the Payout %!",
            color=0xFFB6C1,
        )
        e.set_footer(
            text=f"You can also specify bet amount automatically with `{ctx.prefix}slots <bet_amount>`"
        )
        e.add_field(name="Bet Amount", value=f"{bet} Coins")
        # e.set_image(url=slot_gif)
        await ctx.send(embed=e)
        slot_results = []
        for idx, i in enumerate(range(3), start=1):
            await asyncio.sleep(1)
            row = generate(luck)
            slot_results.append(row)
            await ctx.send(f"Row {idx} Generated - {row}")
        winnings = floor(bet + (bet * payout / 100))
        if all_equal(slot_results):
            jackpot_winnings = floor(bet + (bet * (2 * payout) / 100))
            await ctx.send("Congratulations!\nYou hit the jackpot!")
            await ctx.send(
                f"Your winnings before hitting Jackpot - {winnings}\nTotal winnings after hitting Jackpot {jackpot_winnings}!!!"
            )
            async with ctx.bot.db[0].acquire() as pconn:
                items["coin-case"] += jackpot_winnings
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json WHERE u_id = $2",
                    items,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET energy = energy - 1 WHERE u_id = $1",
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET luck = luck + 2 WHERE u_id = $1",
                    ctx.author.id,
                )
        elif two_equal(slot_results):
            await ctx.send("Congratulations!\nYou hit two rows!")
            await ctx.send(f"Your Total winnings! {winnings}")
            async with ctx.bot.db[0].acquire() as pconn:
                items["coin-case"] += winnings
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json wHERE u_id = $2",
                    items,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET energy = energy - 1 WHERE u_id = $1",
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET luck = luck + 1 WHERE u_id = $1", ctx.author.id
                )
        else:
            async with ctx.bot.db[0].acquire() as pconn:
                items["coin-case"] -= bet
                await pconn.execute(
                    "UPDATE users SET inventory = $1::json wHERE u_id = $2",
                    items,
                    ctx.author.id,
                )
                await pconn.execute(
                    "UPDATE users SET energy = energy - 1 WHERE u_id = $1",
                    ctx.author.id,
                )
            await ctx.send(
                "Oh no, you missed it this time!, play again, win and increase your luck!\nMore luck = Higher Chance to hit Jackpot!:wink:"
            )
        if energy <= 1:
            await ctx.send(
                "You have used up all your Energy!\nYou will get An Energy bar after every 20 Minutes or Upvote DittoBOT if you haven't to get an energy bar"
            )


async def setup(bot):
    await bot.add_cog(GameCorner())
