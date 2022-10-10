import ast
import datetime

import discord
from discord.ext import commands
from mewcore import commondb
from utils.misc import ConfirmView, MenuView
from utils.checks import (
    check_investigator,
)
from utils.misc import MenuView


OS = discord.Object(id=999953429751414784)
OSGYMS = discord.Object(id=857746524259483679)
OSAUCTIONS = discord.Object(id=857745448717516830)
VK_SERVER = discord.Object(id=829791746221277244)


class investigator(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.safe_edb = ""

    async def load_bans_cross_cluster(self):
        launcher_res = await self.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            return
        processes = len(launcher_res[0])
        body = "await bot.load_bans()"
        await self.bot.handler(
            "_eval",
            processes,
            args={"body": body, "cluster_id": "-1"},
            scope="bot",
            _timeout=10,
        )

    @check_investigator()
    @commands.hybrid_group(name="invest")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def invest_cmd(self, ctx):
        # await ctx_send("Affirmative.")
        ...

    @check_investigator()
    @invest_cmd.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def mostcommonchests(self, ctx):
        """Shows the users who have the most common chests in their inv."""
        async with ctx.bot.db[0].acquire() as pconn:
            data = await pconn.fetch(
                "SELECT u_id, (inventory::json->>'common chest')::int as cc FROM users WHERE (inventory::json->>'common chest')::int IS NOT NULL ORDER BY cc DESC LIMIT 10"
            )

        result = "".join(f"`{row['u_id']}` - `{row['cc']}`\n" for row in data)
        await ctx.send(embed=discord.Embed(description=result, color=14483677))

    @invest_cmd.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def donations(self, ctx, userid: discord.Member):
        """INVESTIGATOR: Shows a users total recorded donations from ;donate command only"""
        async with ctx.bot.db[0].acquire() as pconn:
            money = await pconn.fetchval(
                "select sum(amount) from donations where u_id = $1", userid.id
            )
        await ctx.send(money or "0")

    @check_investigator()
    @invest_cmd.command(name="addpoke")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def addpoke(self, ctx, userid: discord.Member, poke: int):
        """INVESTIGATOR: Add a pokemon by its ID to a user by their userID
        ex. ;addpoke <USERID> <POKEID>"""
        async with ctx.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET pokes = array_append(pokes, $1) WHERE u_id = $2",
                poke,
                userid.id,
            )
        await ctx.send("Successfully added the pokemon to the user specified.")

    @check_investigator()
    @invest_cmd.command(name="removepoke")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def removepoke(self, ctx, userid: discord.Member, poke: int):
        """INVESTIGATOR: Remove a pokemon by its ID to a user by their userID
        ex. ;addpoke <USERID> <POKEID>"""
        try:
            await ctx.bot.commondb.remove_poke(userid.id, poke)
        except commondb.UserNotStartedError:
            await ctx.send("That user has not started!")
            return
        await ctx.send("Successfully removed the pokemon from users pokemon array")

    @check_investigator()
    @invest_cmd.command(name="serverban")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def banserver(self, ctx, id: int):
        """INVESTIGATOR: Ban a server"""
        sbans = set(ctx.bot.banned_guilds)
        if id in sbans:
            await ctx.send("That server is already banned.")
            return
        sbans.add(id)
        await ctx.bot.mongo_update("blacklist", {}, {"guilds": list(sbans)})
        await ctx.send(
            f"```Elm\n-Successfully Banned {await ctx.bot.fetch_guild(id)}```"
        )
        await self.load_bans_cross_cluster()

    @check_investigator()
    @invest_cmd.command(name="unbanserver")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def unbanserver(self, ctx, id: int):
        """INVESTIGATOR: UNBan a server"""
        sbans = set(ctx.bot.banned_guilds)
        if id not in sbans:
            await ctx.send("That server is not banned.")
            return
        sbans.remove(id)
        await ctx.bot.mongo_update("blacklist", {}, {"guilds": list(sbans)})
        await ctx.send(
            f"```Elm\n- Successfully Unbanned {await ctx.bot.fetch_guild(id)}```"
        )
        await self.load_bans_cross_cluster()

    @check_investigator()
    @commands.hybrid_group(name="tl")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def tradelog(self, ctx):
        """INVESTIGATOR: Tradelog command"""

    @check_investigator()
    @tradelog.command(name="user")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def tradelog_user(self, ctx, u_id: int):
        async with ctx.bot.db[0].acquire() as pconn:
            trade_sender = await pconn.fetch(
                "SELECT * FROM trade_logs WHERE $1 = sender ORDER BY t_id ASC", u_id
            )
            trade_receiver = await pconn.fetch(
                "SELECT * FROM trade_logs WHERE $1 = receiver ORDER BY t_id ASC",
                u_id,
            )
        # List[Tuple] -> (T_ID, Optional[DateTime], Traded With, Sent Creds, Sent Redeems, # Sent Pokes, Rec Creds, Rec Redeems, # Rec Pokes)
        trade = []
        t_s = trade_sender.pop(0) if trade_sender else None
        t_r = trade_receiver.pop(0) if trade_receiver else None
        while t_s or t_r:
            if t_s is None or t_r is not None and t_s["t_id"] > t_r["t_id"]:
                trade.append(
                    (
                        t_r["t_id"],
                        t_r["time"],
                        t_r["sender"],
                        t_r["receiver_credits"],
                        t_r["receiver_redeems"],
                        len(t_r["receiver_pokes"]),
                        t_r["sender_credits"],
                        t_r["sender_redeems"],
                        len(t_r["sender_pokes"]),
                    )
                )
                t_r = trade_receiver.pop(0) if trade_receiver else None
            else:
                trade.append(
                    (
                        t_s["t_id"],
                        t_s["time"],
                        t_s["receiver"],
                        t_s["sender_credits"],
                        t_s["sender_redeems"],
                        len(t_s["sender_pokes"]),
                        t_s["receiver_credits"],
                        t_s["receiver_redeems"],
                        len(t_s["receiver_pokes"]),
                    )
                )
                t_s = trade_sender.pop(0) if trade_sender else None
        if not trade:
            await ctx.send("That user has not traded!")
            return
        raw = ""
        now = datetime.datetime.now(datetime.timezone.utc)
        name_map = {}
        for t in trade:
            if t[1] is None:
                time = "?"
            else:
                d = t[1]
                d = now - d
                if d.days:
                    time = f"{str(d.days)}d"
                elif d.seconds // 3600:
                    time = f"{str(d.seconds // 3600)}h"
                elif d.seconds // 60:
                    time = f"{str(d.seconds // 60)}m"
                elif d.seconds:
                    time = f"{str(d.seconds)}s"
                else:
                    time = "?"
            if t[2] in name_map:
                un = name_map[t[2]]
            else:
                try:
                    un = f"{await ctx.bot.fetch_user(int(t[2]))} ({t[2]})"
                except discord.HTTPException:
                    un = t[2]
                name_map[t[2]] = un
            raw += f"__**{t[0]}** - {un}__ ({time} ago)\n"
            raw += f"Gave: {t[3]} creds + {t[4]} redeems + {t[5]} pokes\n"
            raw += f"Got: {t[6]} creds + {t[7]} redeems + {t[8]} pokes\n\n"
        PER_PAGE = 15
        page = ""
        pages = []
        raw = raw.strip().split("\n\n")
        total_pages = ((len(raw) - 1) // PER_PAGE) + 1
        for idx, part in enumerate(raw):
            page += part + "\n\n"
            if idx % PER_PAGE == PER_PAGE - 1 or idx == len(raw) - 1:
                embed = discord.Embed(
                    title=f"Trade history of user {u_id}",
                    description=page,
                    color=0xDD00DD,
                )
                embed.set_footer(text=f"Page {(idx // PER_PAGE) + 1}/{total_pages}")
                pages.append(embed)
                page = ""
        await MenuView(ctx, pages).start()

    @tradelog.command(name="poke")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def tradelog_poke(self, ctx, p_id: int):
        async with ctx.bot.db[0].acquire() as pconn:
            trade_sender = await pconn.fetch(
                "SELECT * FROM trade_logs WHERE $1 = any(sender_pokes) ORDER BY t_id ASC",
                p_id,
            )

            trade_receiver = await pconn.fetch(
                "SELECT * FROM trade_logs WHERE $1 = any(receiver_pokes) ORDER BY t_id ASC",
                p_id,
            )

        trade = []
        t_s = trade_sender.pop(0) if trade_sender else None
        t_r = trade_receiver.pop(0) if trade_receiver else None
        while t_s or t_r:
            if t_s is None or t_r is not None and t_s["t_id"] > t_r["t_id"]:
                trade.append((t_r["t_id"], t_r["time"], t_r["receiver"], t_r["sender"]))
                t_r = trade_receiver.pop(0) if trade_receiver else None
            else:
                trade.append((t_s["t_id"], t_s["time"], t_s["sender"], t_s["receiver"]))
                t_s = trade_sender.pop(0) if trade_sender else None
        if not trade:
            await ctx.send("That pokemon has not been traded!")
            return
        raw = ""
        now = datetime.datetime.now(datetime.timezone.utc)
        for t in trade:
            if t[1] is None:
                time = "?"
            else:
                d = t[1]
                d = now - d
                if d.days:
                    time = f"{str(d.days)}d"
                elif d.seconds // 3600:
                    time = f"{str(d.seconds // 3600)}h"
                elif d.seconds // 60:
                    time = f"{str(d.seconds // 60)}m"
                elif d.seconds:
                    time = f"{str(d.seconds)}s"
                else:
                    time = "?"
            raw += f"**{t[0]}**: {t[2]} -> {t[3]} ({time} ago)\n"
        PER_PAGE = 15
        page = ""
        pages = []
        raw = raw.strip().split("\n")
        total_pages = (len(raw) - 1) // PER_PAGE + 1
        for idx, part in enumerate(raw):
            page += part + "\n"
            if idx % PER_PAGE == PER_PAGE - 1 or idx == len(raw) - 1:
                embed = discord.Embed(
                    title=f"Trade history of poke {p_id}",
                    description=page,
                    color=14483677,
                )

                embed.set_footer(text=f"Page {idx // PER_PAGE + 1}/{total_pages}")
                pages.append(embed)
                page = ""
        await MenuView(ctx, pages).start()

    @check_investigator()
    @tradelog.command(name="info")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def tradelog_info(self, ctx, t_id: int):
        """Get information on a specific trade by transaction id."""
        async with ctx.bot.db[0].acquire() as pconn:
            trade = await pconn.fetchrow(
                "SELECT * FROM trade_logs WHERE t_id = $1", t_id
            )
        if trade is None:
            await ctx.send("That transaction id does not exist!")
            return
        desc = ""
        if trade["sender_credits"] or trade["sender_pokes"] or trade["sender_redeems"]:
            desc += f"**{trade['receiver']} received:**\n"
            if trade["sender_credits"]:
                desc += f"__Credits:__ {trade['sender_credits']}\n"
            if trade["sender_redeems"]:
                desc += f"__Redeems:__ {trade['sender_redeems']}\n"
            if trade["sender_pokes"]:
                desc += f"__Pokes:__ {trade['sender_pokes']}\n"
            desc += "\n"
        if (
            trade["receiver_credits"]
            or trade["receiver_pokes"]
            or trade["receiver_redeems"]
        ):
            desc += f"**{trade['sender']} received:**\n"
        if trade["receiver_credits"]:
            desc += f"__Credits:__ {trade['receiver_credits']}\n"
        if trade["receiver_redeems"]:
            desc += f"__Redeems:__ {trade['receiver_redeems']}\n"
        if trade["receiver_pokes"]:
            desc += f"__Pokes:__ {trade['receiver_pokes']}\n"
        embed = discord.Embed(
            title=f"Trade ID {t_id}", description=desc, color=14483677
        )

        if trade["time"] is not None:
            embed.set_footer(text=trade["time"].isoformat(" "))
        await ctx.send(embed=embed)

    @check_investigator()
    @invest_cmd.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def ownedservers(self, ctx, u_id: int):
        """INVEST: View the servers shared with DittoBOT that a user is the owner in."""
        launcher_res = await self.bot.handler("statuses", 1, scope="launcher")
        if not launcher_res:
            await ctx.send("I can't process that request right now, try again later.")
            return
        processes = len(launcher_res[0])
        body = (
            "result = []\n"
            "for guild in bot.guilds:\n"
            f"  if guild.owner_id == {u_id}:\n"
            "    result.append({'name': guild.name, 'id': guild.id, 'members': guild.member_count})\n"
            "return result"
        )
        eval_res = await self.bot.handler(
            "_eval",
            processes,
            args={"body": body, "cluster_id": "-1"},
            scope="bot",
            _timeout=5,
        )
        if not eval_res:
            await ctx.send("I can't process that request right now, try again later.")
            return
        data = []
        for response in eval_res:
            if response["message"]:
                data.extend(ast.literal_eval(response["message"]))
        pages = []
        for guild_data in data:
            msg = (
                f"Guild Name:   {guild_data['name']}\n"
                f"Guild ID:     {guild_data['id']}\n"
                f"Member Count: {guild_data['members']}\n"
            )
            pages.append(f"```\n{msg}```")
        await MenuView(ctx, pages).start()

    @check_investigator()
    @commands.hybrid_group(name="r")
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def repossess(self, ctx):
        """INVESTIGATOR: COMMANDS FOR REPOSSESSING THINGS FROM OFFENDERS"""

    @check_investigator()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @repossess.command(name="credits")
    async def credits(self, ctx, user: discord.Member, val: int):
        """INVESTIGATOR: REPOSSESS CREDITS"""
        if ctx.author.id == user.id:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou cant take your own credits!"
            )
            return
        if val <= 0:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou need to transfer at least 1 credit!"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            giver_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = 123"
            )

        if getter_creds is None:
            await ctx.send(f"<:err:997377264511623269>!:\nIssue with fake UserID (123)")
            return
        if giver_creds is None:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) has not started."
            )
            return
        if val > giver_creds:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) does not have that many credits!"
            )
            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to move **{val}** credits from **{user.name}**({user.id}) to **DittoBOT's Central Bank?**",
        ).wait():
            await ctx.send("<:err:997377264511623269>!:\nTransfer **Cancelled.**")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )
            if val > curcreds:
                await ctx.send(
                    "<:err:997377264511623269>!:\nUser does not have that many credits anymore..."
                )
                return
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins - $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await pconn.execute(
                "UPDATE users SET mewcoins = mewcoins + $1 WHERE u_id = 123",
                val,
            )
            await ctx.send(
                f"{val} Credits taken from {user.name}({user.id}), added to fake u_id `123`."
            )
            await ctx.bot.get_partial_messageable(997378673214754827).send(
                f"<:err:997377264511623269>-Staff Member: {ctx.author.name}-``{ctx.author.id}``\nCredits Taken From: {user.name}-`{user.id}`\nAmount: ```{val} credits```\n"
            )
            # await pconn.execute(
            #    "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
            #    ctx.author.id, user.id, val, "repo", datetime.now()
            # )

    @check_investigator()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @repossess.command(name="redeems")
    async def redeems(self, ctx, user: discord.Member, val: int):
        """INVESTIGATOR: REPOSSESS REDEEMS"""
        if ctx.author.id == user.id:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou cant take your own Redeems!"
            )
            return
        if val <= 0:
            await ctx.send(
                "<:err:997377264511623269>!:\nYou need to transfer at least 1 Redeem!"
            )
            return
        async with ctx.bot.db[0].acquire() as pconn:
            giver_creds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", user.id
            )
            getter_creds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = 123"
            )

        if getter_creds is None:
            await ctx.send(f"<:err:997377264511623269>!:\nIssue with fake UserID (123)")
            return
        if giver_creds is None:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) has not started."
            )
            return
        if val > giver_creds:
            await ctx.send(
                f"<:err:997377264511623269>!:\n{user.name}({user.id}) does not have that many redeems!!"
            )
            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to move **{val}** redeems from\n**{user.name}**({user.id})\nto **DittoBot's Central Bank?**",
        ).wait():
            await ctx.send("<:err:997377264511623269>!:\nTransfer **Cancelled.**")
            return

        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchval(
                "SELECT redeems FROM users WHERE u_id = $1", user.id
            )
            if val > curcreds:
                await ctx.send(
                    "<:err:997377264511623269>!:\nUser does not have that many redeems anymore..."
                )
                return
            await pconn.execute(
                "UPDATE users SET redeems = redeems - $1 WHERE u_id = $2",
                val,
                user.id,
            )
            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1 WHERE u_id = 123",
                val,
            )
            await ctx.send(
                f"{val} redeems taken from {user.name}({user.id}), added to fake u_id `123`."
            )
            await ctx.bot.get_partial_messageable(997378673214754827).send(
                f"<:err:997377264511623269>-Staff Member: {ctx.author.name}-``{ctx.author.id}``\nredeems Taken From: {user.name}-`{user.id}`\nAmount: ```{val} redeems```\n"
            )
            # await pconn.execute(
            #    "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
            #    ctx.author.id, user.id, val, "repo", datetime.now()
            # )

    @check_investigator()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @repossess.command(name="everything")
    async def all(self, ctx, user: discord.Member):
        """INVESTIGATOR: REPOSSESS EVERYTHING"""
        if ctx.author.id == user.id:
            await ctx.send("<:err:997377264511623269>!: You cant take your own stuff!")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            giver_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = $1", user.id
            )

            getter_creds = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = 123"
            )

        if getter_creds is None:
            await ctx.send("<:err:997377264511623269>!: Issue with fake UserID (123)")
            return
        if giver_creds is None:
            await ctx.send(
                f"<:err:997377264511623269>!: {user.name}({user.id}) has not started."
            )

            return
        if not await ConfirmView(
            ctx,
            f"Are you sure you want to move all **REDEEMS AND CREDITS** from\n**{user.name}**({user.id})\nto **DittoBOT's Central Bank?**",
        ).wait():
            await ctx.send("<:err:997377264511623269>!:\nTransfer **Cancelled.**")
            return
        async with ctx.bot.db[0].acquire() as pconn:
            curcreds = await pconn.fetchrow(
                "SELECT mewcoins, redeems FROM users WHERE u_id = $1", user.id
            )

            credits = curcreds["mewcoins"]
            redeems = curcreds["redeems"]
            await pconn.execute(
                "UPDATE users SET redeems = redeems = 0, mewcoins = 0 WHERE u_id = $1",
                user.id,
            )

            await pconn.execute(
                "UPDATE users SET redeems = redeems + $1, mewcoins = mewcoins + $2 WHERE u_id = 123",
                redeems,
                credits,
            )

            await ctx.send(
                f"{redeems} redeems\n{credits} credits\ntaken from {user.name}({user.id}), added to fake u_id `123`."
            )

            await ctx.bot.get_partial_messageable(997378673214754827).send(
                f"<:err:997377264511623269>-Staff Member: {ctx.author.name}-``{ctx.author.id}``\nEVERYTHING Taken From: {user.name}-`{user.id}`\nAmount: ```{credits} credits\n{redeems} redeems```\n"
            )
            await pconn.execute(
                "INSERT INTO trade_logs (sender, receiver, sender_credits, command, time) VALUES ($1, $2, $3, $4, $5) ",
                ctx.author.id,
                user.id,
                val,
                "repo",
                datetime.now(),
            )

    @check_investigator()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @repossess.command(name="bank")
    async def bank(self, ctx):
        """INVESTIGATOR: BANK BALANCES"""
        async with ctx.bot.db[0].acquire() as pconn:
            redeems = await pconn.fetchval("SELECT redeems FROM users WHERE u_id = 123")
            mewcoins = await pconn.fetchval(
                "SELECT mewcoins FROM users WHERE u_id = 123"
            )
        embed = discord.Embed(title="Balances", color=0xFF0000)
        embed.set_author(
            name="DittoBOT Central Bank",
            url="https://cdn.discordapp.com/attachments/1004311737706754088/1005804309029593098/shime19-moshed-07-29-11-05-16_-_Copy.gif",
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1004311737706754088/1005804309029593098/shime19-moshed-07-29-11-05-16_-_Copy.gif"
        )
        embed.add_field(name="Total Credits:", value=f"{mewcoins}", inline=False)
        embed.add_field(name="Total Redeems:", value=f"{redeems}", inline=False)
        embed.set_footer(text="All credits/redeems are from Bot-banned Users")
        await ctx.send(embed=embed)

    @check_investigator()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @repossess.command(name="help")
    async def help(self, ctx):
        """INVESTIGATOR: COMMANDS"""
        embed = discord.Embed(
            title="Repossess Command",
            description="**Base Command:** `;repossess <sub-command>`\n**Aliases:** `;r`",
            color=0xFF0000,
        )
        embed.set_author(
            name="Investigation Team Only",
            url="https://discord.com/channels/999953429751414784/793744327746519081/",
            icon_url="https://static.thenounproject.com/png/3022281-200.png",
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1004311737706754088/1005804309029593098/shime19-moshed-07-29-11-05-16_-_Copy.gif"
        )
        embed.add_field(
            name=";r redeems <user id> <amount>",
            value="Moves redeems to bank\n**Aliases**: `r, d, deems`",
            inline=False,
        )
        embed.add_field(
            name=";r credits <user id> <amount>",
            value="Moves credits to bank\n**Aliases**: `c, bread, cheese`",
            inline=False,
        )
        embed.add_field(
            name=";r everything <user id>",
            value="Moves all redeems and credits to bank\n**Aliases**: `r, d, deems`",
            inline=True,
        )
        embed.set_footer(text="All commands are logged in support bot server!")
        await ctx.send(embed=embed)

    @check_investigator()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    @invest_cmd.command()
    async def addbb(self, ctx, id: discord.User):
        """INVESTIGATOR: Ban specified user from using the bot in any server."""
        banned = set(ctx.bot.banned_users)
        if id.id in banned:
            await ctx.send("That user is already botbanned!")
            return
        banned.add(id.id)
        await ctx.bot.mongo_update("blacklist", {}, {"users": list(banned)})
        await ctx.send(
            f"```Elm\n-Successfully Botbanned {await ctx.bot.fetch_user(id.id)}```"
        )
        await self.load_bans_cross_cluster()

    @check_investigator()
    @invest_cmd.command()
    @discord.app_commands.guilds(OS, OSGYMS, OSAUCTIONS, VK_SERVER)
    @discord.app_commands.default_permissions(ban_members=True)
    async def removebb(self, ctx, id: discord.User):
        """INVESTIGATOR: Unban specified user from the bot, allowing use of commands again"""
        banned = set(ctx.bot.banned_users)
        if id.id not in banned:
            await ctx.send("That user is not botbanned!")
            return
        banned.remove(id.id)
        await ctx.bot.mongo_update("blacklist", {}, {"users": list(banned)})
        await ctx.send(
            f"```Elm\n- Successfully Unbotbanned {await ctx.bot.fetch_user(id.id)}```"
        )
        await self.load_bans_cross_cluster()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(investigator(bot))
