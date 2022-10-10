import ast
import random
import re
import time
from datetime import datetime
from math import floor

import discord
import ujson
from discord import Embed
from discord.ext import commands
from utils.checks import tradelock
from utils.misc import ConfirmView, MenuView, get_pokemon_image, pagify

from dittocogs.json_files import *
from dittocogs.market import (
    CRYSTAL_PATREON_SLOT_BONUS,
    GOLD_PATREON_SLOT_BONUS,
    PATREON_SLOT_BONUS,
    SILVER_PATREON_SLOT_BONUS,
)
from dittocogs.pokemon_list import *


def do_health(maxHealth, health, healthDashes=10):
    dashConvert = int(
        maxHealth / healthDashes
    )  # Get the number to divide by to convert health to dashes (being 10)
    currentDashes = int(
        health / dashConvert
    )  # Convert health to dash count: 80/10 => 8 dashes
    remainingHealth = (
        healthDashes - currentDashes
    )  # Get the health remaining to fill as space => 12 spaces
    cur = f"{round(health)}/{maxHealth}"

    healthDisplay = "".join(["▰" for _ in range(currentDashes)])
    remainingDisplay = "".join(["▱" for _ in range(remainingHealth)])
    percent = floor(
        (health / maxHealth) * 100
    )  # Get the percent as a whole number:   40%
    if percent < 1:
        percent = 0
    # Print out textbased healthbar
    return f"{healthDisplay}{remainingDisplay}\n           {cur}"


def calculate_breeding_multiplier(level):
    difference = 0.02
    return f"{round((1 + (level) * difference), 2)}x"


def calculate_iv_multiplier(level):
    difference = 0.5
    return f"{round((level * difference), 1)}%"


class Extras(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        # This is to make sure the dict exists before we access in the cog check
        await self.bot.redis_manager.redis.execute(
            "HMSET", "resetcooldown", "examplekey", "examplevalue"
        )

    @commands.hybrid_command()
    async def natures(self, ctx):
        natures = "https://media.discordapp.net/attachments/1010539978633252884/1011756228986282065/ZT3XP-image0.jpg"
        await ctx.send(natures)

    @commands.hybrid_group(name="spread")
    async def spread_cmds(self, ctx):
        """Top layer of group"""

    @spread_cmds.command()
    async def honey(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            inv = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
            if not inv:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            honey = await pconn.fetchval(
                "SELECT * FROM honey WHERE channel = $1 LIMIT 1",
                ctx.channel.id,
            )
            if honey is not None:
                await ctx.send(
                    "There is already honey in this channel! You can't add more yet."
                )
                return
            if "honey" in inv and inv["honey"] >= 1:
                inv["honey"] -= 1
            else:
                await ctx.send("You do not have any units of Honey!")
                return
            expires = int(time.time() + (60 * 60))
            await pconn.execute(
                "INSERT INTO honey (channel, expires, owner, type) VALUES ($1, $2, $3, 'honey')",
                ctx.channel.id,
                expires,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE users SET inventory = $1::json WHERE u_id = $2",
                inv,
                ctx.author.id,
            )
            await ctx.send(
                "You have successfully spread some of your honey, rare spawn chance increased by nearly 20 times normal in this channel for the next hour!"
            )

    @commands.hybrid_command()
    async def leaderboard(self, ctx, board: str):
        LEADERBOARD_IMMUNE_USERS = [
            195938951188578304,  # gomp
            3746,  # not a real user, just used to store pokes and such
        ]
        if board.lower() == "vote":
            async with ctx.bot.db[0].acquire() as pconn:
                leaders = await pconn.fetch(
                    "SELECT tnick, vote_streak, u_id, staff FROM users WHERE last_vote >= $1 ORDER BY vote_streak DESC",
                    time.time() - (36 * 60 * 60),
                )
            names = [record["tnick"] for record in leaders]
            votes = [record["vote_streak"] for record in leaders]
            ids = [record["u_id"] for record in leaders]
            staffs = [record["staff"] for record in leaders]
            embed = discord.Embed(title="Upvote Streak Rankings!", color=0xFFB6C1)
            desc = ""
            true_idx = 1
            for idx, vote in enumerate(votes):
                if staffs[idx] == "Developer" or ids[idx] in LEADERBOARD_IMMUNE_USERS:
                    continue
                if names[idx] is not None:
                    name = f"{names[idx]} - ({ids[idx]})"
                else:
                    name = f"Unknown user - ({ids[idx]})"
                desc += f"{true_idx}. {vote:,} votes - {name}\n"
                true_idx += 1
            pages = pagify(desc, base_embed=embed)
            await MenuView(ctx, pages).start()
        elif board.lower() == "servers":
            total = []
            launcher_res = await self.bot.handler("statuses", 1, scope="launcher")
            if not launcher_res:
                await ctx.send(
                    "I can't process that request right now, try again later."
                )
                return
            processes = len(launcher_res[0])
            body = "return {x.name: x.member_count for x in bot.guilds if x.member_count is not None}"
            eval_res = await self.bot.handler(
                "_eval",
                processes,
                args={"body": body, "cluster_id": "-1"},
                scope="bot",
                _timeout=5,
            )
            if not eval_res:
                await ctx.send(
                    "I can't process that request right now, try again later."
                )
                return
            for response in eval_res:
                if response["message"]:
                    total.extend(ast.literal_eval(response["message"]).items())
            total.sort(key=lambda a: a[1], reverse=True)
            embed = discord.Embed(title="Top Servers with DittoBOT!", color=0xFFB6C1)
            desc = ""
            for true_idx, data in enumerate(total, start=1):
                name, count = data
                desc += f"{true_idx}. {count:,} members - {name}\n"
            pages = pagify(desc, base_embed=embed)
            await MenuView(ctx, pages).start()
        elif board.lower() == "pokemon":
            async with ctx.bot.db[0].acquire() as pconn:
                details = await pconn.fetch(
                    """SELECT u_id, cardinality(pokes) as pokenum, staff, tnick FROM users ORDER BY pokenum DESC"""
                )
            pokes = [record["pokenum"] for record in details]
            ids = [record["u_id"] for record in details]
            staffs = [record["staff"] for record in details]
            names = [record["tnick"] for record in details]
            embed = discord.Embed(title="Pokemon Leaderboard!", color=0xFFB6C1)
            desc = ""
            true_idx = 1
            for idx, id in enumerate(ids):
                if staffs[idx] == "Developer" or ids[idx] in LEADERBOARD_IMMUNE_USERS:
                    continue
                pokenum = pokes[idx]
                if names[idx] is not None:
                    name = f"{names[idx]} - ({id})"
                else:
                    name = f"Unknown user - ({id})"
                desc += f"__{true_idx}__. {pokenum:,} Pokemon - {name}\n"
                true_idx += 1
            pages = pagify(desc, base_embed=embed)
            await MenuView(ctx, pages).start()
        elif board.lower() == "fishing":
            async with ctx.bot.db[0].acquire() as pconn:
                details = await pconn.fetch(
                    """SELECT u_id, fishing_exp, fishing_level as pokenum, staff, tnick FROM users ORDER BY fishing_exp DESC"""
                )

            pokes = [record["pokenum"] for record in details]
            exps = [t["fishing_exp"] for t in details]
            ids = [record["u_id"] for record in details]
            staffs = [record["staff"] for record in details]
            names = [record["tnick"] for record in details]
            embed = discord.Embed(title="Fishing Leaderboard!", color=0xFFB6C1)
            desc = ""
            true_idx = 1
            for idx, id in enumerate(ids):
                if staffs[idx] == "Developer" or ids[idx] in LEADERBOARD_IMMUNE_USERS:
                    continue
                pokenum = pokes[idx]
                exp = exps[idx]
                if names[idx] is not None:
                    name = f"{names[idx]} - ({id})"
                else:
                    name = f"Unknown user - ({id})"
                desc += f"__{true_idx}__. `FishEXP` : **{exp}** - `{name}`\n"
                true_idx += 1
            pages = pagify(desc, base_embed=embed)
            await MenuView(ctx, pages).start()

    @commands.hybrid_command()
    async def server(self, ctx):
        embed = Embed(title="Server Stats", color=0xFFBC61)
        embed.add_field(
            name="Official Server",
            value="[Join the Official Server](https://discord.gg/ditto)",
        )
        async with ctx.bot.db[0].acquire() as pconn:
            honeys = await pconn.fetch(
                "SELECT channel, expires, type FROM honey WHERE channel = ANY ($1) ",
                [channel.id for channel in ctx.guild.text_channels],
            )
        desc = ""
        for t in honeys:
            channel = t["channel"]
            expires = t["expires"]
            honey_type = t["type"]
            if honey_type == "honey":
                honey_type = "Honey"
            elif honey_type == "ghost":
                honey_type = "Ghost Detector"
            elif honey_type == "cheer":
                honey_type = "Christmas Cheer"
            # Convert the expire timestamp to 10 minute buckets of time remaining
            # Since the task that clears honey only runs every 10 minutes, it doesn't make much sense to try to be more accurate than that
            minutes = int((expires - time.time()) // 60)
            minutes -= minutes % 10
            minutes = "Less than 10 minutes" if minutes < 0 else f"{minutes} minutes"
            desc += f"{honey_type} Stats for <#{channel}>\n\t**__-__Expires in {minutes}**\n"
        pages = pagify(desc, base_embed=embed)
        await MenuView(ctx, pages).start()

    @commands.hybrid_group(name="nature")
    async def nature_cmds(self, ctx):
        """Top layer of group"""

    @nature_cmds.command()
    async def change(self, ctx, nature: str):
        """
        Uses a nature capsule to change your selected Pokemon's nature.

        Ex. `;change nature adamant`
        """
        if nature.capitalize() not in natlist:
            await ctx.send("That Nature does not exist!")
            return
        nature = nature.capitalize()
        async with ctx.bot.db[0].acquire() as conn:
            dets = await conn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if dets is None:
            await ctx.send(f"You have not Started!\nStart with `/start` first!")
            return
        if dets["nature-capsules"] <= 0 or nature is None:
            await ctx.send(
                "You have no nature capsules! Buy some with `/redeem nature capsules`."
            )
            return
        dets["nature-capsules"] = dets["nature-capsules"] - 1
        async with ctx.bot.db[0].acquire() as pconn:
            _id = await pconn.fetchval(
                "SELECT selected FROM users WHERE u_id = $1", ctx.author.id
            )
            name = await pconn.fetchval("SELECT pokname FROM pokes WHERE id = $1", _id)
            await pconn.execute(
                "UPDATE users SET inventory = $1::json WHERE u_id = $2",
                dets,
                ctx.author.id,
            )
            await pconn.execute(
                "UPDATE pokes SET nature = $1 WHERE id = $2", nature, _id
            )
        await ctx.send(
            f"You have successfully changed your selected Pokemon's nature to {nature}"
        )

    @commands.hybrid_command()
    async def bag(self, ctx):
        """
        Lists your items.
        """
        async with ctx.bot.db[0].acquire() as conn:
            dets = await conn.fetchval(
                "SELECT items::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if dets is None:
            await ctx.send(f"You have not Started!\nStart with `/start` first!")
            return
        desc = "".join(
            f"{item.replace('-', ' ').capitalize()} : {dets[item]}x\n"
            for item in dets
            if dets[item] > 0
        )

        if not desc:
            e = Embed(title="Your Current Bag", color=0xFFB6C1, description="Empty :(")
            await ctx.send(embed=e)
            return

        embed = Embed(title="Your Current Bag", color=0xFFB6C1)
        pages = pagify(desc, per_page=20, base_embed=embed)
        await MenuView(ctx, pages).start()


    @commands.hybrid_group(name="visible")
    async def visible_toggles(self, ctx):
        """Top layer of group"""

    @visible_toggles.command()
    async def bal(self, ctx):
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET visible = NOT visible WHERE u_id = $1", ctx.author.id
            )
        await ctx.send("Toggled trainer card visibility!")

    @visible_toggles.command()
    async def donations(self, ctx, toggle: bool=False):
        if not toggle:
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET show_donations = False WHERE u_id = $1", ctx.author.id
                )
            await ctx.send("Your donations total will no longer show on your balance.")
        else:
            async with ctx.bot.db[0].acquire() as pconn:
                await pconn.execute(
                    "UPDATE users SET show_donations = True WHERE u_id = $1", ctx.author.id
                )
            await ctx.send("Your donations total will now show on your balance.")


    @commands.hybrid_command()
    async def updates(self, ctx):
        """Lists recent updates."""
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetch(
                "SELECT id, dev, update, update_date FROM updates ORDER BY update_date DESC"
            )
        updates = [t["update"] for t in details]
        dates = [t["update_date"] for t in details]
        devs = [t["dev"] for t in details]
        desc = ""
        for idx, date in enumerate(dates):
            month = date.strftime("%B")
            desc += (
                f"**{month} {date.day}, {date.year} - {devs[idx]}**\n{updates[idx]}\n\n"
            )
        embed = discord.Embed(title="Recent Updates", colour=0xFFB6C1)
        pages = pagify(desc, sep="\n\n", per_page=5, base_embed=embed)
        await MenuView(ctx, pages).start()

    @commands.hybrid_command()
    async def silence(self, ctx):
        """Silence level up messages from your pokemon"""
        async with ctx.bot.db[0].acquire() as pconn:
            state = await pconn.fetchval(
                "UPDATE users SET silenced = NOT silenced WHERE u_id = $1 RETURNING silenced",
                ctx.author.id,
            )
        state = "off" if state else "on"
        await ctx.send(
            f"Successfully toggled {state} level up messages for your pokemon!"
        )

    @commands.hybrid_command()
    async def status(self, ctx):
        """Shows bot info, credits and copyright"""
        embed = Embed(color=0xFFB6C1, url="https://mewbot.wiki/")

        clusternum = 1
        shardnum = len(ctx.bot.shards)

        result = await ctx.bot.handler("num_processes", 1, scope="launcher")

        if result:
            clusternum = result[0]["clusters"]
            shardnum = result[0]["shards"]
            process_res = await ctx.bot.handler(
                "_eval",
                clusternum,
                args={"body": "return len(bot.guilds)", "cluster_id": "-1"},
                scope="bot",
            )
            servernum = 0
            for cluster in process_res:
                servernum += int(cluster["message"])
        else:
            clusternum = "1"
            shardnum = len(ctx.bot.shards)
            servernum = len(ctx.bot.guilds)

        embed.add_field(
            name="Bot Information",
            value=(
                f"`Owner/Founders:` **{ctx.bot.owner.name}, Eaaarl#3381, Chichiri12345#6662, Cruithne#1421**\n"
                "`Developers:` **Cruithne#1421, Zak~#0193**\n"
                "`Server Host:` **Krypt**\n"
                "`Artwork Lead:`**PinkDank**\n"
                f"`Server count:` **{servernum:,}**\n"
                f"`Shard count:` **{shardnum}**\n"
                f"`Cluster count:` **{clusternum}**\n"
                "\n"
                f"`Discord version:` **{discord.__version__}**\n"
                f"`Uptime:` **{ctx.bot.uptime}**\n"
                "*A huge THANK YOU goes out to **Flame#2941** and **NeuroA#4779** for all of their help with the bot-without their work, the bot would be nowhere close to what it is today. <3*\n"
            ),
        )

        # give users a link to invite thsi bot to their server
        embed.add_field(
            name="Invite",
            value="[Invite Me](https://discordapp.com/api/oauth2/authorize?client_id=1000125868938633297&permissions=387136&scope=bot)",
            inline=False,
        )
        # embed.add_field(
        #    name="Follow us on Social Media for fun events and rewards!",
        #    value="[`Reddit`](https://www.reddit.com/r/Mewbot/)\n[`Instagram`](https://www.instagram.com/mewbot_official/)\n[`Twitter`](https://twitter.com/MewbotOS)",
        #    inline=False,
        # )
        embed.add_field(
            name="Official Wiki Page",
            value="[Wiki Tutorial](https://dittobot.wiki)",
            inline=False,
        )
        view = discord.ui.View(timeout=60)

        async def check(interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message(
                    content="You are not allowed to interact with this button.",
                    ephemeral=True,
                )
                return False
            return True

        view.interaction_check = check
        creditpage = discord.ui.Button(
            style=discord.ButtonStyle.gray, label="View Credits"
        )

        async def creditcallback(interaction):
            await self.credit_page(ctx)

        creditpage.callback = creditcallback
        view.add_item(creditpage)
        copyright = discord.ui.Button(
            style=discord.ButtonStyle.gray, label="View Copyright Info"
        )

        async def copyrightcallback(interaction):
            await self.copyright_page(interaction)

        copyright.callback = copyrightcallback
        view.add_item(copyright)
        
        self.msg = await ctx.send(embed=embed, view=view)

    async def credit_page(self, ctx):
        """
        Our Contributors
        """
        desc = f"**Contributor Credit:**\n"
        desc += f"\n**Various Artwork/Skins:**"
        desc += f"\n[mcg.mark](https://www.instagram.com/mcg.mark/)"
        desc += f"\n[flippodraws](https://www.instagram.com/filippodraws)"
        desc += f"\n[albert_wlson](https://www.instagram.com/albert_wlson/)"
        desc += f"\n\n**Radiant Artwork:**"
        desc += f"\n**Leads:**"
        # desc += f"\nKT#0302"
        desc += f"\n[Pinkdankk#8560](https://www.deviantart.com/pinkdankk)"
        desc += f"\n\n**Art Team:**"
        desc += f"\nRuwangi Munasinghe#3861"
        desc += f"\nA Fearsome Fox#1337"
        # desc += f"\ncheese#0666"
        desc += f"\nSenpai#6218"
        desc += f"\n៚ᴀsʜ ᐖ🍿™❞#4994"
        desc += f"\nCakeCrusader#5759"
        desc += f"\nRadioactiveRenegade#0823"
        desc += f"\nHELLBOY#6802"
        # desc += f"\nmisfy#0666"
        # desc += f"\nDagger_Mace#5953"
        # desc += f"\nMabs#9126"
        desc += f"\nGrape#6587"
        desc += f"\n\n**Noteworthy Donators:(THANK YOU)**"
        desc += f"\nnah#3933"
        desc += f"\nvKoIIextionz—#5408"
        desc += f"\nKingmaker#0001"
        desc += f"\nฯFa£©¤nฯ#2326"
        desc += f"\nxD#9016"
        desc += f"\nProtoxic#7835"
        desc += f"\n.•°A Snowy Wolf°•."
        desc += f"\nSpeedyfoster"
        desc += f"\n\n***More will be added soon!***"
        desc += f""
        embed = Embed(color=0xFFB6C1, description=desc)
        self.msg.edit(embed=embed)

    async def copyright_page(self, interaction):
        """
        Copyright Information
        """
        desc = f"**Copyright Information**:\n"
        desc += f"\n**Pokémon © 2002-2022 Pokémon.**\n**© 1995-2022 Nintendo/Creatures Inc.**\n**/GAME FREAK inc. TM, ® and Pokémon character names are trademarks of Nintendo.**"
        desc += f"\n*No copyright or trademark infringement is intended in using Pokémon content within DittoBOT.*"
        desc += " "
        embed = Embed(color=0xFFB6C1, description=desc)
        #await interaction.edit_original_response(embed=embed)
        self.msg.edit(embed=embed)

    @commands.hybrid_command()
    async def claim(self, ctx):
        """Claim upvote points!"""
        async with ctx.bot.db[0].acquire() as pconn:
            points = await pconn.fetchval(
                "SELECT upvotepoints FROM users WHERE u_id = $1", ctx.author.id
            )
            if points is None:
                await ctx.send(f"You have not Started!\nStart with `/start` first!")
                return
            if points < 5:
                await ctx.send("You do not have enough Upvote Points for your rewards.")
                return
            await pconn.execute(
                "UPDATE users SET upvotepoints = upvotepoints - 5, redeems = redeems + 1, mewcoins = mewcoins + 15000 WHERE u_id = $1",
                ctx.author.id,
            
            )
        await ctx.send("Upvote Points Claimed!")

    @commands.hybrid_command()
    async def ping(self, ctx):
        embed = Embed(color=0xFFB6C1)
        lat = ctx.bot.latency * 1000
        lat = "Infinity :(" if lat == float("inf") else f"{int(lat)}ms"
        shard_id = ctx.guild.shard_id
        cluster_id = ctx.bot.cluster["id"]
        cluster_name = ctx.bot.cluster["name"]

        embed.title = f"Cluster #{cluster_id} ({cluster_name})"
        embed.description = f"Shard {shard_id} - {lat}"
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def vote(self, ctx):
        async with self.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT vote_streak, last_vote FROM users WHERE u_id = $1",
                ctx.author.id,
            )
            if data is None:
                vote_streak = 0
            elif data["last_vote"] < time.time() - (36 * 60 * 60):
                vote_streak = 0
            else:
                vote_streak = data["vote_streak"]
        embed = Embed(color=0xFFB6C1)
        embed.description = (
            "**Upvote **DittoBOT** on the following websites and earn rewards for each!**\n\n"
            "<a:vote1:1013434144023380078><a:vote2:1013434140877664256> -> [#1 TOP.GG](https://top.gg/bot/1000125868938633297/vote)\n\n"
            "<a:vote1:1013434144023380078><a:vote2:1013434140877664256> -> [#2 BOTLIST.ME](https://botlist.me/bots/1000125868938633297/vote)\n\n"
            "<a:vote1:1013434144023380078><a:vote2:1013434140877664256> -> [#3 DISCORDBOTLIST.COM](https://discordbotlist.com/bots/dittobot/upvote)\n\n"
            "<a:vote1:1013434144023380078><a:vote2:1013434140877664256> -> [#4 FATESLIST.XYZ](https://fateslist.xyz/bot/1000125868938633297)\n\n"
            "<a:vote1:1013434144023380078><a:vote2:1013434140877664256> -> [#5 DISCORDZ.GG](https://discordz.gg/bot/1000125868938633297/vote)\n\n"

            f"\n**Vote Streak:** `{vote_streak}` (only for top.gg)"
            "\n------------------\n"
            # "[#2 fateslist.xyz](https://fateslist.xyz/mewbot/vote)\n"
            "Join the Official Server [here](https://discord.gg/ditto) for support and join our huge community of DittoBOT users!"
        )
        link = ["**[Mewdeko - Multipurpose discord bot](https://discord.gg/4stkEfZ6As)**\n> `A bot with more features to help you run and manage your servers than any of the big Multipurpose bots-and totally 100% free for all.`",]
        final_link = random.choice(link)
        embed.add_field(name="Our Partners (officially recommended):", value=f"{final_link}", inline=False)
        embed.set_footer(
            text="You will receive 1 Upvote Point, 1,500 Credits and 2 Energy Bars automatically after upvoting per site!"
        )
        await ctx.send(embed=embed)
        emoji = random.choice(emotes)
        await ctx.send(emoji)

    @commands.hybrid_command()
    async def predeem(self, ctx):
        """Get your redeems from patreon rewards."""
        date = datetime.now()
        date = f"{date.month}-{date.year}"
        async with ctx.bot.db[0].acquire() as pconn:
            if not await pconn.fetchval(
                "SELECT exists(SELECT * from users WHERE u_id = $1)", ctx.author.id
            ):
                await ctx.send("You have not started!\nStart with `/start` first!")
                return
            last = await pconn.fetchval(
                "SELECT lastdate FROM patreonstore WHERE u_id = $1", ctx.author.id
            )
        if last == date:
            await ctx.send(
                "You have already received your patreon redeems for this month... Come back later!"
            )
            return
        patreon_status = await ctx.bot.patreon_tier(ctx.author.id)
        if patreon_status is None:
            await ctx.send(
                "I do not recognize you as a patron. Please double check that your membership is still active.\n"
                "If you are currently a patron, but I don't recognize you, check the following things:\n\n"
                "**1.** If you subscribed within the last 15 minutes, the bot has not had enough time to process your patronage. "
                "Wait 15 minutes and try again. If waiting does not work, continue with the following steps.\n\n"
                "**2.** Check if you have linked your Discord account on your Patreon account. "
                "Follow this guide to make sure it is linked. "
                "<https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role>\n\n"
                "**3.** Check that you subscribed to Patreon in a tier, instead of donating a custom amount. "
                "If you do not donate in a tier, the bot cannot identify what perks you are supposed to receive. "
                "Follow this guide to make sure you subscribe in a tier. "
                "It will explain how to make sure you are in a tier and explain how to subscribe to a tier with a custom amount. "
                "<https://support.patreon.com/hc/en-us/articles/360000126286-Editing-your-membership>\n\n"
                "If none of the above worked, ask a staff member for further assistance."
            )
            return
        if patreon_status == "Elite Patreon":
            amount = 150
        elif patreon_status == "Crystal Patreon":
            amount = 75
        elif patreon_status == "Gold Patreon":
            amount = 30
        elif patreon_status == "Silver Patreon":
            amount = 15
        elif patreon_status == "dittoBot Patreon":
            amount = 3
        else:
            await ctx.send(
                "Uh oh, you have an invalid patreon tier! The tiers may have been modified without updating this command... Please report this bug!"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            if last is None:
                await pconn.execute(
                    "INSERT INTO patreonstore (u_id, lastdate) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    ctx.author.id,
                    date,
                )
            else:
                await pconn.execute(
                    "UPDATE patreonstore SET lastdate = $2 WHERE u_id = $1",
                    ctx.author.id,
                    date,
                )
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $2 WHERE u_id = $1",
                ctx.author.id,
                amount,
            )
        await ctx.send(
            f"You have received **{amount}** redeems. Thank you for supporting DittoBOT!"
        )

    @commands.hybrid_command()
    async def nick(self, ctx, nick: str = "None"):
        """
        Set or reset your selected pokemon's nickname.

        Ex. `;nick` Resets nickname
            `;nick Frank` Sets nickname to Frank
        """
        if len(nick) > 150:
            await ctx.send("Nickname is too long!")
            return
        if any(
            word in nick
            for word in (
                "@here",
                "@everyone",
                "http",
                "nigger",
                "nigga",
                "gay",
                "fag",
                "kike",
                "jew",
                "faggot",
            )
        ):
            await ctx.send("Nope.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE pokes SET poknick = $1 WHERE id = (SELECT selected FROM users WHERE u_id = $2)",
                nick,
                ctx.author.id,
            )
        if nick == "None":
            await ctx.send("Successfully reset Pokemon nickname.")
            return
        await ctx.send(f"Successfully changed Pokemon nickname to {nick}.")

    @commands.hybrid_command()
    async def stats(self, ctx):
        async with ctx.bot.db[0].acquire() as tconn:
            details = await tconn.fetchrow(
                "SELECT * FROM users WHERE u_id = $1", ctx.author.id
            )
            inv = await tconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", ctx.author.id
            )
        if inv is None:
            await ctx.send(f"You have not Started!\nStart with `/start` first!")
            return
        embed = discord.Embed(title="Your Stats", color=0xFFB6C1)
        fishing_level = details["fishing_level"]
        fishing_exp = details["fishing_exp"]
        fishing_levelcap = details["fishing_level_cap"]
        luck = details["luck"]
        energy = do_health(10, details["energy"])
        embed.add_field(name="Energy", value=energy)
        case = inv["coin-case"] if "coin-case" in inv else "No Coin Case"
        embed.add_field(
            name="Fishing Stats",
            value=f"Fishing Level - {fishing_level}\nFishing Exp - {fishing_exp}/{fishing_levelcap}",
        )
        embed.add_field(
            name="Game Corner Stats",
            value=f"Luck - {luck}\nCoins - {case:,}",
        )
        embed.set_footer(text="If You have some Energy go fishing!")
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def hunt(self, ctx, pokemon: str):
        pokemon = pokemon.capitalize()
        if pokemon not in totalList:
            await ctx.send("You have chosen an invalid Pokemon.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetchrow(
                "SELECT hunt, chain FROM users WHERE u_id = $1", ctx.author.id
            )
        if data is None:
            await ctx.send("You have not started!\nStart with `/start` first.")
            return
        hunt, chain = data
        if hunt == pokemon:
            await ctx.send("You are already hunting that pokemon!")
            return
        add_chain = 0
        if (
            chain > 0
            and hunt
            and not await ConfirmView(
                ctx,
                f"Are you sure you want to abandon your hunt for **{hunt}**?\nYou will lose your streak of **{chain}**.",
            ).wait()
        ):
            return
        elif chain > 0 and not hunt:
            add_chain = 500
            await ctx.send("Binding loose chain to new Pokemon.")
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET hunt = $1, chain = $3 WHERE u_id = $2",
                pokemon,
                ctx.author.id,
                add_chain,
            )
        e = discord.Embed(
            title="Shadow Hunt",
            description=f"Successfully changed shadow hunt selection to **{pokemon}**.",
            color=0xFFB6C1,
        )
        e.set_image(url=await get_pokemon_image(pokemon, ctx.bot, skin="shadow"))
        await ctx.send(embed=e)
        await ctx.bot.get_partial_messageable(1005559143886766121).send(
            f"`{ctx.author.id} - {hunt} @ {chain}x -> {pokemon}`"
        )

    @commands.hybrid_command()
    async def trainer(self, ctx, user: discord.User = None):
        if user is None:
            user = ctx.author
        async with ctx.bot.db[0].acquire() as tconn:
            details = await tconn.fetchrow(
                "SELECT * FROM users WHERE u_id = $1", user.id
            )
            if details is None:
                await ctx.send(f"{user.name} has not started!")
                return
            if (
                not details["visible"]
                and user.id != ctx.author.id
                and ctx.author.id != ctx.bot.owner_id
            ):
                await ctx.send(
                    f"You are not permitted to see the Trainer card of {user.name}"
                )
                return
            pokes = details["pokes"]
            daycared = await tconn.fetchval(
                "SELECT count(*) FROM pokes WHERE id = ANY ($1) AND pokname = 'Egg'",
                pokes,
            )
            usedmarket = await tconn.fetchval(
                "SELECT count(id) FROM market WHERE owner = $1 AND buyer IS NULL",
                user.id,
            )

        details["visible"]
        details["u_id"]
        redeems = details["redeems"]
        tnick = details["tnick"]
        uppoints = details["upvotepoints"]
        mewcoins = details["mewcoins"]
        evpoints = details["evpoints"]
        dlimit = details["daycarelimit"]
        hitem = details["held_item"]
        marketlimit = details["marketlimit"]
        dets = details["inventory"]
        count = len(pokes)
        is_staff = details["staff"]

        embed = Embed(color=0xFFB6C1)
        if is_staff.lower() != "user":
            embed.set_author(
                name=f"{tnick if tnick is not None else user.name} Trainer Card",
                icon_url="https://cdn.discordapp.com/attachments/707730610650873916/773574461474996234/logo_mew.png",
            )
        else:
            embed.set_author(
                name=f"{tnick if tnick is not None else user.name} Trainer Card"
            )
        embed.add_field(name="Redeems", value=f"{redeems:,}", inline=True)
        embed.add_field(name="Upvote Points", value=f"{uppoints}", inline=True)
        embed.add_field(
            name="Credits",
            value=f"{mewcoins:,}<:dittocoin:1010679749212901407>",
            inline=True,
        )
        embed.add_field(name="Pokemon Count", value=f"{count:,}", inline=True)
        embed.add_field(name="EV Points", value=f"{evpoints:,}", inline=True)
        embed.add_field(
            name="Daycare spaces", value=f"{daycared}/{dlimit}", inline=True
        )
        dets = ujson.loads(dets)
        dets.pop("coin-case", None) if "coin-case" in dets else None
        for item in dets:
            embed.add_field(
                name=item.replace("-", " ").capitalize(),
                value=f"{dets[item]}{'%' if 'shiny' in item or 'honey' in item else 'x'}",
                inline=True,
            )
        patreon_status = await ctx.bot.patreon_tier(user.id)
        if patreon_status in ("Crystal Patreon", "Elite Patreon"):
            marketlimitbonus = CRYSTAL_PATREON_SLOT_BONUS
        elif patreon_status == "Gold Patreon":
            marketlimitbonus = GOLD_PATREON_SLOT_BONUS
        elif patreon_status == "Silver Patreon":
            marketlimitbonus = SILVER_PATREON_SLOT_BONUS
        elif patreon_status == "dittoBot Patreon":
            marketlimitbonus = PATREON_SLOT_BONUS
        else:
            marketlimitbonus = 0
        markettext = f"{usedmarket}/{marketlimit}"
        if marketlimitbonus:
            markettext += f" (+ {marketlimitbonus}!)"
        embed.add_field(name="Market spaces", value=markettext, inline=True)
        if is_staff.lower() != "user":
            embed.set_footer(
                text=f"Holding: {hitem.capitalize().replace('-',' ')}",
                icon_url="https://cdn.discordapp.com/attachments/707730610650873916/773574461474996234/logo_mew.png",
            )
        else:
            embed.set_footer(text=f"Holding: {hitem.capitalize().replace('-',' ')}")
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def trainernick(self, ctx, val: str):
        """Sets your trainer nickname."""
        if any(word in val for word in ("@here", "@everyone", "http")):
            await ctx.send("Nope.")
            return
        if len(val) > 18:
            await ctx.send("Trainer nick too long!")
            return
        if re.fullmatch(r"^[ -~]*$", val) is None:
            await ctx.send("Unicode characters cannot be used in your trainer nick.")
            return
        if "|" in val:
            await ctx.send("`|` cannot be used in your trainer nick.")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            nick = await pconn.fetchval(
                "SELECT tnick FROM users WHERE u_id = $1", ctx.author.id
            )
            if nick is not None:
                await ctx.send("You have already set your trainer nick.")
                return
            user = await pconn.fetchval("SELECT u_id FROM users WHERE tnick = $1", val)
            if user is not None:
                await ctx.send("That nick is already taken. Try another one.")
                return
            await pconn.execute(
                "UPDATE users SET tnick = $1 WHERE u_id = $2", val, ctx.author.id
            )
        await ctx.send("Successfully Changed Trainer Nick")

    @commands.hybrid_command()
    @tradelock
    async def resetme(self, ctx):
        cooldown = (
            await ctx.bot.redis_manager.redis.execute(
                "HMGET", "resetcooldown", str(ctx.author.id)
            )
        )[0]

        cooldown = 0 if cooldown is None else float(cooldown.decode("utf-8"))
        if cooldown > time.time():
            reset_in = cooldown - time.time()
            cooldown = f"{round(reset_in)}s"
            await ctx.send(f"Command on cooldown for {cooldown}")
            return
        await ctx.bot.redis_manager.redis.execute(
            "HMSET", "resetcooldown", str(ctx.author.id), str(time.time() + 60 * 60 * 3)
        )

        prompts = [
            "Are you sure you want to reset your account? This cannot be undone.",
            (
                "Are you **absolutely certain**? This will reset **all of your pokemon**, "
                "**all of your credits and redeems**, and anything else you have done on the bot and "
                "**cannot be undone**.\nOnly click `Confirm` if you are **certain** you want this."
            ),
        ]
        for prompt in prompts:
            if not await ConfirmView(ctx, prompt).wait():
                await ctx.send("Canceling reset.")
                return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "DELETE FROM redeemstore WHERE u_id = $1", ctx.author.id
            )
            await pconn.execute("DELETE FROM cheststore WHERE u_id = $1", ctx.author.id)
            await pconn.execute("DELETE FROM users WHERE u_id = $1", ctx.author.id)
        await ctx.send(
            "Your account has been reset. Start the bot again with `/start`."
        )
        await ctx.bot.get_partial_messageable(1005747202242650182).send(
            f"{ctx.author.id} - {ctx.author.name} "
        )

    @commands.hybrid_command()
    async def invite(self, ctx):
        embed = Embed(
            title="Invite Me",
            description="The invite link for DittoBOT",
            color=0xFFB6C1,
        )

        # invite l
        embed.add_field(
            name="Invite",
            value="[Invite DittoBOT!](https://discordapp.com/api/oauth2/authorize?client_id=1000125868938633297&permissions=387136&scope=bot+applications.commands)",
        )
        embed.add_field(
            name="Official Server",
            value="[Join Dittopia (our Official Server)](https://discord.gg/ditto)",
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def region(self, ctx, reg: str):
        if reg not in ("original", "alola", "galar", "hisui"):
            await ctx.send(
                "That isn't a valid region! Select one of `original`, `alola`, `galar`, `hisui`."
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET region = $1 WHERE u_id = $2", reg, ctx.author.id
            )
        await ctx.send(f"Your region has been set to **{reg.title()}**.")

    @commands.hybrid_command()
    async def bal(self, ctx, user: discord.User = None):
        """Lists credits, redeems, EV points, upvote points, and selected fishing rod."""
        if user is None:
            user = ctx.author
        async with ctx.bot.db[0].acquire() as tconn:
            details = await tconn.fetchrow(
                "SELECT * FROM users WHERE u_id = $1", user.id
            )
            donations = await tconn.fetchrow(
                "SELECT sum(amount) as total FROM ditto_donations WHERE u_id = $1", user.id
            )
            if details is None:
                await ctx.send(f"{user.name} has not started!")
                return
            if (
                not details["visible"]
                and user.id != ctx.author.id
                and ctx.author.id != ctx.bot.owner_id
            ):
                await ctx.send(
                    f"You are not permitted to see the Trainer card of {user.name}"
                )
                return
            if details["show_donations"] == False:
                donated_total = "Hidden"
            else:
                donated_total = donations["total"]
            if details["last_vote"] < time.time() - (36 * 60 * 60):
                vote_streak = 0
            else:
                vote_streak = details["vote_streak"]
            pokes = details["pokes"]
            mystery_token = details["mystery_token"]
            details["visible"]
            details["u_id"]
            redeems = details["redeems"]
            tnick = details["tnick"]
            uppoints = details["upvotepoints"]
            mewcoins = details["mewcoins"]
            evpoints = details["evpoints"]
            len(pokes)
            is_staff = details["staff"]
            region = details["region"]
            staffrank = await tconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", user.id
            )
            hitem = details["held_item"]
            desc = f"{tnick if tnick is not None else user.name}'s\n__**Balances**__"
            desc += f"\n<:dittocoin:1010679749212901407>**Credits**: `{mewcoins:,}`"
            desc += f"\n<:rtedee2m:817647281364271144>**Redeems**: `{redeems:,}`"
            desc += f"\n**Mystery Tokens**: `{mystery_token:,}`\n"
            desc += f"\n<:evs:818149979428093983>**EV Points**: `{evpoints:,}`"
            desc += f"\n<:upvote:817898847320801300>**Upvote Points**: `{uppoints}`"
            desc += f"\n<:upvote:817898847320801300>**Vote Streak**: `{vote_streak}`\n"
            desc += f"\n**Holding**: `{hitem.capitalize().replace('-',' ')}`"
            desc += f"\n**Region**: `{region.capitalize()}`"
            if donated_total is None:
                donated_total = "--"
            desc += f"\n\n**Donated**: {donated_total}"
            embed = Embed(color=0xFFB6C1, description=desc)
            if is_staff.lower() != "user":
                embed.set_author(
                    name="Official Staff Member",
                    icon_url="https://cdn.discordapp.com/emojis/1004753524111974420.gif?size=80&quality=lossless",
                )

                embed.add_field(
                    name="Bot Staff Rank",
                    value=f"{staffrank}",
                )
            else:
                embed.set_author(name="Trainer Information")
            view = discord.ui.View(timeout=60)

            async def check(interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        content="You are not allowed to interact with this button.",
                        ephemeral=True,
                    )
                    return False
                return True

            view.interaction_check = check
            chest = discord.ui.Button(
                style=discord.ButtonStyle.gray, label="View chests"
            )

            async def chestcallback(interaction):
                await self.balance_chests(ctx, user)

            chest.callback = chestcallback
            view.add_item(chest)
            misc = discord.ui.Button(style=discord.ButtonStyle.gray, label="View misc")

            async def misccallback(interaction):
                await self.balance_misc(ctx, user)

            misc.callback = misccallback
            view.add_item(misc)
            await ctx.send(embed=embed, view=view)

    async def balance_chests(self, ctx, user: discord.User = None):
        """Lists the current chests you have to open."""
        if user is None:
            user = ctx.author
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT * FROM users WHERE u_id = $1", user.id
            )
            if details is None:
                await ctx.send(f"{user.name} has not started!")
                return
            if (
                not details["visible"]
                and user.id != ctx.author.id
                and ctx.author.id != ctx.bot.owner_id
            ):
                await ctx.send(
                    f"You are not permitted to see how many chests {user.name} has"
                )
                return
            inv = await pconn.fetchval(
                "SELECT inventory::json FROM users WHERE u_id = $1", user.id
            )
        common = inv.get("common chest", 0)
        rare = inv.get("rare chest", 0)
        mythic = inv.get("mythic chest", 0)
        legend = inv.get("legend chest", 0)
        is_staff = details["staff"]
        details["held_item"]
        tnick = details["tnick"]
        desc = "*current totals*"
        desc += f"\n<:l1:817978350042873886><:l2:817978350026227732> `legend`"
        desc += f"\n<:l3:817978349837746198><:l4:817978350194786324>: {legend}"
        desc += f"\n<:m1:817978527286165514><:m2:817978526979457055> `mythic`"
        desc += (
            f"\n<:image_part_003:817978527654871040><:m4:817978527407145030>: {mythic}"
        )
        desc += f"\n<:r1:817974422924427274><:r2:817974423034003476> `rare`"
        desc += f"\n<:r3:817974423121952829><:r4:817974423096131627>: {rare}"
        desc += (
            f"\n<:c1:817978621574119444><:image_part_002:817978621633232916> `common`"
        )
        desc += f"\n<:c3:817978621640704030><:c4:817978621854613554>: {common}"
        embed = Embed(color=0xFFB6C1, description=desc)
        if is_staff.lower() != "user":
            embed.set_author(
                name=f"{tnick if tnick is not None else user.name}'s Chests",
                icon_url="https://cdn.discordapp.com/attachments/707730610650873916/773574461474996234/logo_mew.png",
            )
        else:
            embed.set_author(
                name=f"{tnick if tnick is not None else user.name}'s Chests"
            )
        await ctx.send(embed=embed)

    async def balance_misc(self, ctx, user: discord.User = None):
        """
        Lists other miscellaneous data.

        Includes held item, pokemon owned, market slots, egg slots,
        bicycle, honey, radiant gems, IV mult, nature capsules,
        shiny multi, battle multi, and breeding multi.
        """
        if user is None:
            user = ctx.author
        async with ctx.bot.db[0].acquire() as pconn:
            details = await pconn.fetchrow(
                "SELECT * FROM users WHERE u_id = $1", user.id
            )
            if details is None:
                await ctx.send(f"{user.name} has not started!")
                return
            if (
                not details["visible"]
                and user.id != ctx.author.id
                and ctx.author.id != ctx.bot.owner_id
            ):
                await ctx.send(
                    f"You are not permitted to see how many chests {user.name} has"
                )
                return
            pokes = details["pokes"]
            daycared = await pconn.fetchval(
                "SELECT count(*) FROM pokes WHERE id = ANY ($1) AND pokname = 'Egg'",
                pokes,
            )
            usedmarket = await pconn.fetchval(
                "SELECT count(id) FROM market WHERE owner = $1 AND buyer IS NULL",
                user.id,
            )
        bike = details["bike"]
        details["visible"]
        details["u_id"]
        tnick = details["tnick"]
        dlimit = details["daycarelimit"]
        hitem = details["held_item"]
        marketlimit = details["marketlimit"]
        dets = details["inventory"]
        count = len(pokes)
        is_staff = details["staff"]
        hunt = details["hunt"]
        huntprogress = details["chain"]
        patreon_status = await ctx.bot.patreon_tier(user.id)
        if patreon_status in ("Crystal Patreon", "Elite Patreon"):
            marketlimitbonus = CRYSTAL_PATREON_SLOT_BONUS
        elif patreon_status == "Gold Patreon":
            marketlimitbonus = GOLD_PATREON_SLOT_BONUS
        elif patreon_status == "Silver Patreon":
            marketlimitbonus = SILVER_PATREON_SLOT_BONUS
        elif patreon_status == "dittoBot Patreon":
            marketlimitbonus = PATREON_SLOT_BONUS
        else:
            marketlimitbonus = 0
        markettext = f"{usedmarket}/{marketlimit}"
        if marketlimitbonus:
            markettext += f" (+ {marketlimitbonus}!)"
        desc = f"**Held Item**: `{hitem}`"
        desc += f"\n**Pokemon Owned**: `{count:,}`"
        desc += f"\n**Market Slots**: `{markettext}`"
        desc += f"| **Daycare Slots**: `{daycared}/{dlimit}`"
        if hunt:
            desc += f"\n**Shadow Hunt**: {hunt} ({huntprogress}x)"
        else:
            desc += f"\n**Shadow Hunt**: Select with `/hunt`!"
        desc += f"\n**Bicycle**: {bike}"
        desc += "\n**General Inventory**\n"
        dets = ujson.loads(dets)
        dets.pop("coin-case", None) if "coin-case" in dets else None
        for item in dets:
            if item in ("common chest", "rare chest", "mythic chest", "legend chest"):
                continue
            if "breeding" in item:
                desc += f"{item.replace('-', ' ').capitalize()} `{dets[item]}` `({calculate_breeding_multiplier(dets[item])})`\n"
            elif "iv" in item:
                desc += f"{item.replace('-', ' ').capitalize()} `{dets[item]}` `({calculate_iv_multiplier(dets[item])})`\n"
            else:
                desc += f"{item.replace('-', ' ').capitalize()} `{dets[item]}`x\n"
        embed = Embed(color=0xFFB6C1, description=desc)
        if is_staff.lower() != "user":
            embed.set_author(
                name=f"{tnick if tnick is not None else user.name}'s Miscellaneous Balances",
                # icon_url="https://cdn.discordapp.com/attachments/707730610650873916/773574461474996234/logo_mew.png",
            )
        else:
            embed.set_author(
                name=f"{tnick if tnick is not None else user.name}'s Miscellaneous Balances"
            )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Extras(bot))
