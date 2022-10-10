from enum import IntEnum
from functools import wraps

import discord
from discord.ext import commands

# This file holds checks that can be used to limit access to certain functions.

# Staff checks will allow any user of at least that rank to use the command.
# The hierarchy is Admin > Investigator > Mod > Helper.
# This Enum outlines the hierarchy. Higher values indicate more access.
# These numbers can be safely modified WITHOUT touching the rest of the file in order to add or remove ranks without changing current access.


class Rank(IntEnum):
    USER = 0
    SUPPORT = 1
    GYM = 2
    HELPER = 3
    MOD = 4
    GYMAUTH = 5
    INVESTIGATOR = 6
    ADMIN = 7
    DEVELOPER = 8


# In order to prevent developers from being locked out, this variable holds the user ids of developers.
# Any ID in this tuple will always be able to use commands, regardless of rank or DB status.
# Be careful adding IDs to this tuple, as they get access to a large number of commands.
OWNER_IDS = (
    790722073248661525,
    #101118549958877184,
    318844987464876034,
    749299865334448249,
    150319814836092928,
    104265011714592768,
)
OWNER_ID_LIST = [
    790722073248661525,
    #101118549958877184,
    318844987464876034,
    749299865334448249,
    150319814836092928,
    104265011714592768,
]
# Sky, KT, Earl, Cru, Chi, Motzumoto#9773


def check_owner():
    async def predicate(ctx):
        return ctx.author.id in OWNER_IDS

    return commands.check(predicate)


def check_admin():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", ctx.author.id
            )
        if rank is None:
            return False
        rank = Rank[rank.upper()]
        return rank >= Rank.ADMIN

    return commands.check(predicate)


def check_investigator():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", ctx.author.id
            )
        if rank is None:
            return False
        rank = Rank[rank.upper()]
        # ONLY allow EXACTLY invest (or higher) to use
        return rank >= Rank.INVESTIGATOR

    return commands.check(predicate)


def check_gymauth():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", ctx.author.id
            )
        if rank is None:
            return False
        rank = Rank[rank.upper()]
        # ONLY allow EXACTLY gym auth (or higher) to use
        return rank >= Rank.GYMAUTH

    return commands.check(predicate)


def check_mod():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", ctx.author.id
            )
        if rank is None:
            return False
        rank = Rank[rank.upper()]
        return rank >= Rank.MOD

    return commands.check(predicate)


def check_helper():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", ctx.author.id
            )
        if rank is None:
            return False
        rank = Rank[rank.upper()]
        return rank >= Rank.HELPER

    return commands.check(predicate)


def check_support():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        async with ctx.bot.db[0].acquire() as pconn:
            rank = await pconn.fetchval(
                "SELECT staff FROM users WHERE u_id = $1", ctx.author.id
            )
        if rank is None:
            return False
        rank = Rank[rank.upper()]
        return rank >= Rank.SUPPORT

    return commands.check(predicate)


def tradelock(coro_or_command):
    """
    A decorator that prevents a command from being run if the author is tradelocked,
    and tradelocks the author for the entire runtime of the command.
    If used with slash commands, this MUST be below the slash decorator.

    Usage
    -----
    @commands.hybrid_command()
    @tradelock
    async def command(self, ctx):
        ...
    """
    is_command = isinstance(coro_or_command, commands.Command)
    coro = coro_or_command.callback if is_command else coro_or_command

    @wraps(coro)
    async def wrapped(self, ctx, *args, **kwargs):
        current_traders = [
            int(id_)
            for id_ in await ctx.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if ctx.author.id in current_traders:
            await ctx.send(f"{ctx.author.name} is currently in a trade!")
            return
        async with ctx.bot.commondb.TradeLock(ctx.bot, ctx.author):
            await coro(self, ctx, *args, **kwargs)

    if not is_command:
        return wrapped
    wrapped.__module__ = coro_or_command.callback.__module__
    coro_or_command.callback = wrapped
    return coro_or_command


def tradelock_with_receiver(coro_or_command):
    """
    A decorator that prevents a command from being run if the author OR the provided `member` is tradelocked,
    and tradelocks the author AND the provided `member` for the entire runtime of the command.
    If used with slash commands, this MUST be below the slash decorator.

    Usage
    -----
    @commands.hybrid_command()
    @tradelock_with_receiver
    async def command(self, ctx, member: discord.Member):
        ...
    """
    is_command = isinstance(coro_or_command, commands.Command)
    coro = coro_or_command.callback if is_command else coro_or_command

    @wraps(coro)
    async def wrapped(self, ctx, member, *args, **kwargs):
        if not isinstance(member, discord.Member):
            raise RuntimeError(
                "The first argument for a command decorated with tradelock_with_receiver must be a discord.Member."
            )
        current_traders = [
            int(id_)
            for id_ in await ctx.bot.redis_manager.redis.execute(
                "LRANGE", "tradelock", "0", "-1"
            )
            if id_.decode("utf-8").isdigit()
        ]
        if ctx.author.id in current_traders:
            await ctx.send(f"{ctx.author.name} is currently in a trade!")
            return
        if member.id in current_traders:
            await ctx.send(f"{member.name} is currently in a trade!")
            return
        async with ctx.bot.commondb.TradeLock(ctx.bot, ctx.author, member):
            await coro(self, ctx, member, *args, **kwargs)

    if not is_command:
        return wrapped
    wrapped.__module__ = coro_or_command.callback.__module__
    coro_or_command.callback = wrapped
    return coro_or_command
