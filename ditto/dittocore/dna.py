#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
import asyncio
import contextlib
import json
import logging
import os
import random
import time
import warnings
from collections import defaultdict
from datetime import timedelta

import aiohttp
import aioredis
import asyncpg
import discord
import dittocogs
import pybrake
import ujson
import uvloop
from discord.ext import commands
from utils.checks import OWNER_IDS, OWNER_ID_LIST
from utils.misc import EnableCommandsView, get_prefix
from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient

from dittocore.commondb import CommonDB
from dittocore.dna_misc import DittoMisc
from dittocore.redis_handler import RedisHandler

warnings.filterwarnings("ignore", category=DeprecationWarning)

DATABASE_URL = os.environ["DATABASE_URL"]

notifier = pybrake.Notifier(
        project_id=your-project-id,
        project_key="your-airbrake-key-here",
        environment="production",
    )


class Ditto(commands.AutoShardedBot):
    def __init__(self, cluster_info, *args, **kwargs):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        # =yield loop
        # loop.close()
        AgnosticClient.get_io_loop = asyncio.get_running_loop
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        # To be removed once the bot is ready, or september, whichever comes first :P
        intents.message_content = False
        super().__init__(
            command_prefix=get_prefix,
            max_messages=None,
            intents=intents,
            heartbeat_timeout=120,
            owner_ids=OWNER_ID_LIST,
            guild_ready_timeout=10,
            shard_ids=cluster_info["shards"],
            shard_count=cluster_info["total_shards"],
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
            enable_debug_events=True,
            chunk_guilds_at_startup=False,
            *args,
            **kwargs,
        )
        self.misc = DittoMisc(self)
        self.commondb = CommonDB(self)
        airbrake_handler = pybrake.LoggingHandler(notifier=notifier, level=logging.WARN)
        self.logger = logging.getLogger("dittobot")
        self.logger.addHandler(airbrake_handler)
        self.notifier = notifier
        self.db = [None, None, None]
        self.started_at = time.monotonic()
        self.pokemon_names = {}
        self.loaded_extensions = False
        self.remove_command("help")
        self.guildcount = len(self.guilds)
        self.usercount = len(self.users)
        self.colors = (16711888, 0xFFB6C1, 0xFF69B4, 0xFFC0CB, 0xC71585, 0xDB7093)
        self.linecount = 0
        self.commands_used = defaultdict(int)
        self.debug = kwargs.pop("debug", False)
        self.token = os.environ["MTOKEN"]
        self.will_restart = False
        self.app_directory = cluster_info["ad"]
        self.command_cooldown = defaultdict(int)
        self.emote_server = None
        self.is_maintenance = False
        self.is_discord_issue = False
        self.msg_maintenance = (
            "The bot is currently undergoing maintenance.\n"
            # "For updates and more information, check the #bot-announcements channel of the Official Server."
        )
        self.msg_discord_issue = (
            "There is currently an issue on discord's end that is preventing normal usage of the bot.\n"
            # "For updates and more information, check the #bot-announcements channel of the Official Server."
        )

        # Testing
        self.cluster = cluster_info

        for i in os.listdir(self.app_directory / "shared" / "data" / "pokemon_names"):
            self.pokemon_names[i[:2]] = ujson.load(
                open(self.app_directory / "shared" / "data" / "pokemon_names" / f"{i}")
            )
        self.mongo_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        self.mongo_pokemon_db = self.mongo_client.pokemon
        self.db[1] = self.mongo_pokemon_db
        self.redis_manager = RedisHandler(self)
        self.handler = self.redis_manager.handler

        # missions
        self.primaries = {
            # "redeem-poke": ["Redeem a {x}", 1],
            # "chat-general": ["**Send {x} messages in <#519466243342991362> ({done})**", 100],
            "catch-count": ["**Catch {x} pokemon ({done})**", 50],
            "redeem": ["**Use {x} redeem(s) ({done})**", 5],
            "npc-win": ["**Win {x} NPC Duel(s) ({done})**", 25],
            "hatch": ["**Hatch {x} egg(s) ({done})**", 5],
        }

        self.secondaries = {
            "upvote": ["**Upvote the Bot ({done})**", 1],
            "duel-win": ["**Win {x} duel(s) ({done})**", 5],
            "fish": ["**Catch {x} fish ({done})**", 10],
        }

        # self.logger.info(f'[Cluster#{self.cluster_name}] {kwargs["shard_ids"]}, {kwargs["shard_count"]}')
        self.traceback = None

        self.owner = None

        self.initial_launch = True
        self._clusters_ready = asyncio.Event()

        self.official_server = None

    async def on_connect(self):
        self.logger.info(
            f"Shard ID - {list(self.shards.keys())[-1]} has connected to Discord"
        )

        if not self.owner:
            self.owner = await self.fetch_user(790722073248661525)
        if not self.official_server:
            self.official_server = await self.fetch_guild(999953429751414784)
        if not self.emote_server:
            self.emote_server = await self.fetch_guild(878766711598366741)

    async def before_identify_hook(self, shard_id: int, *, initial: bool = False):
        self.logger.info("Before identify hook fired.  Requesting gateway queue")

        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get("http://178.28.0.12:5000")
                if resp.status != 200:
                    self.logger.error(
                        f"Gateway queue returned non-200 status code: {resp.status}"
                    )
        except aiohttp.ClientConnectionError:
            self.logger.error("Gateway queue unreachable, please ensure it is running")
            if not initial:
                await asyncio.sleep(5)

    async def on_shard_connect(self, shard_id):
        self.logger.info("On shard connect called")
        if not self.initial_launch:
            with contextlib.suppress(discord.HTTPException):
                embed = discord.Embed(
                    title=f"Shard {shard_id} reconnected to gateway",
                    color=0x008800,
                )
                await self.get_partial_messageable(1005561909870870529).send(
                    embed=embed
                )

    async def on_ready(self):
        self.logger.info(
            f"Successfully launched shards {self.cluster['shards'][0]}-{self.cluster['shards'][-1]}"
        )
        payload = {
            "scope": "launcher",
            "action": "launch_next",
            "args": {"id": self.cluster["id"], "pid": os.getpid()},
        }
        await self.db[2].execute("PUBLISH", "dittobot_clusters", json.dumps(payload))
        if self.initial_launch:
            with contextlib.suppress(discord.HTTPException):
                embed = discord.Embed(
                    title=f"[Cluster #{self.cluster['id']} ({self.cluster['name']})] Started successfully",
                    color=0x008800,
                )
                await self.get_partial_messageable(1005561909870870529).send(
                    embed=embed
                )
        self.initial_launch = False

    async def check(self, ctx):
        # TODO
        interaction = ctx.interaction

        # Filter out non-slash command interactions
        if (
            interaction
            and interaction.type != discord.InteractionType.application_command
        ):
            return True

        interaction = ctx.interaction or ctx

        # Only accept interactions that occurred in a guild, so we don't break half our code
        if not interaction.guild:
            await interaction.response.send_message(
                content="Commands cannot be used in DMs."
            )
            return False

        # Don't send commands where they are not supposed to work
        channel_disabled = ctx.channel.id in self.disabled_channels
        # is_old_os = ctx.guild.id == 999953429751414784
        botbanned = ctx.author.id in self.banned_users
        serverbanned = ctx.guild.id in self.banned_guilds
        if (botbanned or serverbanned) and ctx.author.id not in OWNER_IDS:
            await ctx.send("You are not allowed to use commands.", ephemeral=True)
            return False
        if channel_disabled and ctx.author.id not in OWNER_IDS:
            if ctx.author.guild_permissions.manage_messages:
                await ctx.send(
                    "Commands have been disabled in this channel.",
                    ephemeral=True,
                    view=EnableCommandsView(ctx),
                )
            else:
                await ctx.send(
                    "Commands have been disabled in this channel.", ephemeral=True
                )
            return False
        # Cluster-wide command disables for emergencies
        if self.is_maintenance and ctx.author.id not in OWNER_IDS:
            await ctx.send(self.msg_maintenance, ephemeral=True)
            return False
        if self.is_discord_issue and ctx.author.id not in OWNER_IDS:
            await ctx.send(self.msg_discord_issue, ephemeral=True)
            return False

        # Cluster-wide command cooldown
        if (
            self.command_cooldown[ctx.author.id] + 3 > time.time()
            and ctx.author.id not in OWNER_IDS
        ):
            await ctx.send("You're using commands too fast!", ephemeral=True)
            return False
        self.command_cooldown[ctx.author.id] = time.time()

        # Just in case
        await ctx.defer()

        return True

    def are_clusters_ready(self):
        return self._clusters_ready.is_set()

    async def wait_until_clusters_ready(self):
        await self._clusters_ready.wait()

    async def init_pg(self, con):
        await con.set_type_codec(
            typename="json",
            encoder=ujson.dumps,
            decoder=ujson.loads,
            schema="pg_catalog",
        )

    async def load_jsk(self):
        try:
            await self.load_extension("jishaku")
            self.logger.info("Loaded JSK.")
        except Exception as e:
            self.logger.warning(f"Failed to load jsk\n{e}")

    async def _setup_hook(self):
        self.logger.info("Initializing Setup Hook...")
        self.logger.info("Initializing Cogs & DB Connection...")
        self.logger.info("Initializing JSK...")
        await self.load_jsk()
        self.db[0] = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=10,
            max_size=15,
            command_timeout=30,
            init=self.init_pg,
        )
        self.db[2] = await aioredis.create_pool(
            "redis://178.28.0.13", minsize=10, maxsize=20
        )
        # self.oxidb = await asyncpg.create_pool(
        #    OXI_DATABASE_URL, min_size=2, max_size=10, command_timeout=10, init=self.init
        # )
        await self.redis_manager.start()
        await self.load_guild_settings()
        # await self.load_extensions()
        await self.load_bans()
        self.logger.info("Initialization Completed!")
        return await super().setup_hook()

    async def _async_del(self):
        # This is done to stop the on_message listener, so it stops
        # attempting to connect to postgres after db is closed
        self.logger.info("Destroying conns")
        try:
            await self.unload_extension("dittocogs.spawn")
        except:
            pass

        try:
            await self.unload_extension("dittocogs.misc")
        except:
            pass

        if self.db[0]:
            await self.db[0].close()
        if self.db[2]:
            self.db[2].close()
            await self.db[2].wait_closed()

    async def logout(self):
        await self._async_del()
        await super().close()

    async def log(self, channel, content):
        await self.get_partial_messageable(channel).send(content)

    async def patreon_tier(self, user_id: int):
        """
        Returns the patreon tier, or None, for a user id.

        Tier will be one of
        - "dittoBot Patreon"
        - "Silver Patreon"
        - "Gold Patreon"
        - "Crystal Patreon"
        - "Elite Patreon"
        """
        expired = await self.redis_manager.redis.execute("GET", "patreonreset")
        if expired is None or time.time() > float(expired):
            await self.redis_manager.redis.execute(
                "SET", "patreonreset", time.time() + (60 * 15)
            )
            try:
                data = await self._fetch_patreons()
            except RuntimeError:
                return None
            # Expand the dict, since redis doesn't like dicts
            result = []
            for k, v in data.items():
                result += [k, v]
            await self.redis_manager.redis.execute("DEL", "patreontier")
            await self.redis_manager.redis.execute("HMSET", "patreontier", *result)
        tier = await self.redis_manager.redis.execute("HGET", "patreontier", user_id)
        # Don't return a string None
        return None if tier is None else str(tier, "utf-8")

    async def _fetch_patreons(self):
        """
        Fetches the patreon data.

        Returns a dict mapping {userid (int): tier (str)}
        WARNING: This API is evil, modify this code at your own risk!
        """
        headers = {"Authorization": f"Bearer {os.environ['PATREON_TOKEN']}"}
        api_url = ""
        users_tiers = []
        members = []
        RED = "{LARGE RED CIRCLE}"
        async with aiohttp.ClientSession() as session:
            # Loop through the pages returned from the API, stop at 25 to prevent an infinte loop
            for _ in range(25):
                async with session.get(api_url, headers=headers) as r:
                    if r.status != 200:
                        data = await r.text()
                        self.logger.warning(
                            f"Got a non 200 status code from the patreon API.{RED}\n\n{data}\n"
                        )
                        await self.get_partial_messageable(1005563356985442415).send(
                            f"Got a `{r.status}` status code from the patreon API."
                        )
                        raise RuntimeError(
                            "Got a non 200 status code from the patreon API."
                        )
                    data = await r.json()
                # Two sets of data are returned from the API, "data" and "included".
                # "data" is of type patreon.Member and allows us to check their patreon status and get their patreon.User.id.
                # "included" is anything after "?include=" in the api url.
                # Currently it includes the objects for any patreon.User and patreon.Tier that shows up in "data".
                # Discord UIDs can be acquired from patreon.User and display names can be acquired from patreon.Tier
                members += data["data"]
                users_tiers += data["included"]
                # If there are no more links, we have reached the last page, so break out
                if "links" not in data:
                    break
                api_url = data["links"]["next"]

        # Mapping of {patreon user id: patreon tier id}
        active_patrons = {}
        for member in members:
            if "attributes" not in member:
                continue
            if "patron_status" not in member["attributes"]:
                continue
            # Member is either an old patreon, or their payment was declined
            if member["attributes"]["patron_status"] != "active_patron":
                continue
            # Member is subscribed to patreon, but did not select a tier, so they do not get a role or explicit perks
            if not member["relationships"]["currently_entitled_tiers"]["data"]:
                continue
            active_patrons[member["relationships"]["user"]["data"]["id"]] = member[
                "relationships"
            ]["currently_entitled_tiers"]["data"][0]["id"]

        # Mapping of {discord user id: patreon tier id}
        userids = {}
        # Mapping of {patreon tier id: tier name}
        tiers = {}
        # Since data from "included" can be either a patreon.User or patreon.Tier, both are handled in this loop
        for item in users_tiers:
            # Item is a patreon.Tier, get its {id: name}
            if item["type"] == "tier":
                tiers[item["id"]] = item["attributes"]["title"]
                continue
            # Item is a patreon.User, get its discord id & cross reference the tier id from the equivalent patreon.Member
            if item["id"] not in active_patrons:
                continue
            if "attributes" not in item:
                continue
            if "social_connections" not in item["attributes"]:
                continue
            if "discord" not in item["attributes"]["social_connections"]:
                continue
            if not item["attributes"]["social_connections"]["discord"]:
                continue
            if "user_id" not in item["attributes"]["social_connections"]["discord"]:
                continue
            userids[
                int(item["attributes"]["social_connections"]["discord"]["user_id"])
            ] = active_patrons[item["id"]]

        # Mapping of {discord user id: tier name}
        result = {uid: tiers[userids[uid]] for uid in userids}
        # Overrides
        async with self.db[0].acquire() as pconn:
            overrides = await pconn.fetch(
                "SELECT u_id, patreon_override FROM users WHERE patreon_override IS NOT NULL"
            )
        for override in overrides:
            result[override["u_id"]] = override["patreon_override"]

        return result

    def premium_server(self, guild_id: int):
        return guild_id in {
            692412843370348615,
            422495634172542986,
            624217127540359188,
            694472115428261888,
            432763481289261077,
            999953429751414784,
        }

    def get_random_color(self):
        return random.choice(self.colors)

    def make_linecount(self):
        """Generates a total linecount of all python files"""
        for root, dirs, files in os.walk(os.getcwd()):
            for file_ in files:
                if file_.endswith(".py"):
                    with open(os.sep.join([root, file_]), "r", encoding="utf-8") as f:
                        self.linecount += len(f.readlines())

    async def load_bans(self):
        pipeline = [
            {"$unwind": "$disabled_channels"},
            {"$group": {"_id": None, "clrs": {"$push": "$disabled_channels"}}},
            {"$project": {"_id": 0, "disabled_channels": "$clrs"}},
        ]
        async for doc in self.db[1].guilds.aggregate(pipeline):
            self.disabled_channels = doc["disabled_channels"]

        self.banned_users = (await self.db[1].blacklist.find_one())["users"]
        self.banned_guilds = (await self.db[1].blacklist.find_one())["guilds"]


    def botbanned(self, id):
        return id in self.banned_users  # and (id not in (790722073248661525))

    async def load_guild_settings(self):
        self.guild_settings = {}
        cursor = self.mongo_pokemon_db.guilds.find()
        async for document in cursor:
            self.guild_settings[document.pop("id")] = document

    async def pubsub_request(self, target_shard="all", **kwargs):
        if self.db[2]:
            request = {"target_shard": target_shard} | kwargs
            await self.db[2].publish(self.pubsub_id, ujson.dumps(request))

    async def mongo_find(self, collection, query, default=None):
        result = await self.db[1][collection].find_one(query)
        return result or default

    async def mongo_update(self, collection, filter, update):
        result = await self.db[1][collection].find_one(filter)
        if not result:
            await self.db[1][collection].insert_one({**filter, **update})
        result = await self.db[1][collection].update_one(filter, {"$set": update})
        return result



    async def load_extensions(self):
        cogs = [
            "boost",
            "botlist",
            "breeding",
            "chests",
            "cooldown",
            "duel",
            "events",
            "evs",
            "extras",
            "favs",
            "filter",
            "fishing",
            "forms",
            "helpcog",
            "items",
            "lookup",
            "market",
            "misc",
            "missions",
            "moves",
            "orders",
            "party",
            "pokemon",
            "redeem",
            "responses",
            "sell",
            "server",
            "shop",
            "spawn",
            "staff",
            "skins",
            "start",
            "tasks",
            "trade",
            "tutorial",
        ]
        for cog in cogs:
            if "_" in cog:
                continue
            async with self:
                await self.load_extension(f"dittocogs.{cog}")
        self.logger.debug("Cogs successfully loaded")
        self.loaded_extensions = True

    async def unload_extensions(self, ctx):
        txt = ""
        for cog in dir(dittocogs):
            if "_" not in cog and cog not in ("dylee", "staff"):
                try:
                    await self.unload_extension(f"dittocogs.{cog}")
                    txt += "\n" + f"Unloaded cog.{cog}"
                except Exception as e:
                    txt += "\n" + f"Error unloading cog.{cog} - {str(e)}"
        await ctx.send(f"```css\n{txt}```", delete_after=5)

    async def _run(self):
        self.logger.info("Launching...")
        # self.logger.info(f"Shards - {self.shards}\n{[self.get_shard(shard_id) for shard_id in self.shard_ids]}")
        try:
            # Start the client
            async with self:
                await self._setup_hook()

                safe_to_load = [
                    "boost",
                    "botlist",
                    "breeding",
                    "chests",
                    "cooldown",
                    "duel",
                    "events",
                    "evs",
                    "extras",
                    "favs",
                    "filter",
                    "fishing",
                    "forms",
                    "helpcog",
                    "items",
                    "lookup",
                    "market",
                    "misc",
                    "missions",
                    "moves",
                    "orders",
                    "party",
                    "pokemon",
                    "redeem",
                    "responses",
                    "sell",
                    "server",
                    "shop",
                    "spawn",
                    "staff",
                    "skins",
                    "start",
                    "tasks",
                    "trade",
                    "tutorial",
                ]

                for cog in safe_to_load:
                    await self.load_extension(f"dittocogs.{cog}")
                self.loaded_extensions = True

                async def check(ctx):
                    return await ctx.bot.check(ctx)

                self.add_check(check)

                self.logger.info(
                    "Initializing Discord Connection..."
                )  # Actually say Connecting to Discord WHEN it's connecting.
                await self.start(self.token)
        except BaseException as e:
            self.logger.error(f"Error - {str(e)}")
            raise e
        
    

    @property
    def uptime(self):
        return timedelta(seconds=time.monotonic() - self.started_at)


os.environ.setdefault("JISHAKU_HIDE", "1")
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
