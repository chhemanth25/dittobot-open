import contextlib
import random
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks


# Lord only knows why this is here or what it does...
class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Mother(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.cluster["id"] == 1:
            self.mother.start()
            self.energy.start()

    @tasks.loop(minutes=24)
    async def energy(self):
        async with self.bot.db[0].acquire() as pconn:
            await pconn.execute(
                "UPDATE users SET energy = energy + 1 WHERE energy < 10"
            )

    @tasks.loop(seconds=60 * 10)
    async def mother(self):
        primary_key = random.choice(list(self.bot.primaries.keys()))
        primary_value = self.bot.primaries[primary_key][1]
        secondary_key = random.choice(list(self.bot.secondaries.keys()))
        secondary_value = self.bot.secondaries[secondary_key][1]
        existing = await self.bot.db[1].missions.find_one()
        if not existing:
            insert = {
                "createdAt": datetime.now(),
                "missions": [
                    [primary_key, random.randint(1, primary_value)],
                    [secondary_key, random.randint(1, secondary_value)],
                ],
            }
            # Add the new mission reqs
            await self.bot.db[1].missions.insert_one(insert)
            # Reset the missions progress for all users
            await self.bot.db[1].users.delete_many({})

        async with self.bot.db[0].acquire() as pconn:
            honeys = await pconn.fetch(
                "SELECT * FROM honey WHERE expires < $1", int(time.time())
            )
            channels = [t["channel"] for t in honeys]
            ids = [t["id"] for t in honeys]
            owners = [t["owner"] for t in honeys]
            types = [t["type"] for t in honeys]
            for idx, id in enumerate(ids):
                await pconn.execute("DELETE FROM honey WHERE id = $1", id)
                with contextlib.suppress(discord.HTTPException):
                    owner = await self.bot.fetch_user(owners[idx])
                    await owner.send(
                        embed=discord.Embed(
                            title=f"Your {types[idx]} spread has expired!",
                            description=f"Your {types[idx]} Spread in <#{channels[idx]}> has expired!\nSpread some more with `/spread`.",
                            color=0xFFB6C1,
                        )
                    )

    def cog_unload(self):
        self.energy.cancel()
        self.mother.cancel()


async def setup(bot):
    await bot.add_cog(Mother(bot))
