import contextlib
import time

from discord.ext import commands

wait_cache = {}
immune_ids = (
    455277032625012737,  # dylee
    728736503366156361,  # bust
    221109271998234635,  # DJspree
    302178158260781056,  # Draxx
    403696018828296192,  # indo
    334782659031203841,  # Silver5mith
    631840748924436490,
    473974336219381770,
    101118549958877184,  # Motzumoto
    409149408681263104,
    383105414171983875,
    335363151187017728,
    332557977292636170,
    568060157175529495,
    332557977292636170,
    568060157175529495,
    728736503366156361,
    280835732728184843,  # YUNO
    473541068378341376,
    334155028170407949,
)


class Cooldown(commands.Cog):
    def get_command_cooldown(self, command):
        return 3
        # commands_cooldown = {
        #     "duel": 15,
        #     "breed": 35,
        # }
        # return commands_cooldown.get(command, 3)

    async def bot_check(self, ctx):
        if ctx.author.id in immune_ids:
            return True

        if ctx.guild:
            if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
                return False
            if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
                await ctx.send(
                    "I require `embed_links` permission in order to function properly. Please give me that permission and try again."
                )
                return False
        if ctx.author.id in wait_cache and not ctx.command.parent:
            wait = wait_cache.get(ctx.author.id)
            if wait > time.time():
                secs = wait - time.time()
                cooldown = f"<t:{int(round(secs))}:R>"
                with contextlib.suppress(Exception):
                    await ctx.channel.send(f"Command on cooldown for {cooldown} ")
                return
            else:
                wait_cache[ctx.author.id] = time.time() + 3
                return True
        else:
            wait_cache[ctx.author.id] = time.time() + 3
            return True


async def setup(bot):
    await bot.add_cog(Cooldown())
