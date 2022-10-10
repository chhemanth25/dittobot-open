import asyncio
import json

import zmq
from discord.ext import commands, tasks


class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.context = zmq.asyncio.Context.instance()
        self.pub = self.context.socket(zmq.PUB)
        self.sub = self.context.socket(zmq.SUB)

        self.initialized = False
        self.main_handler.start()

    async def cog_check(self, ctx):
        return ctx.author.id in (
            455277032625012737,
            631840748924436490,
            409149408681263104,
            473541068378341376,
        )  # dylee, s,lky, doom, neuro

    async def process_request(self, request):
        if request["target"] != "bot":
            return
        if (
            request["action"]["type"] == "get"
            and request["action"]["message"] == "ping"
        ):
            response = {
                "id": request["id"],
                "action": {"type": "give", "message": "pong"},
            }
            await self.pub.send_json(f"dittobot-dashboard {json.dumps(response)}")

    @tasks.loop()
    async def main_handler(self):
        if not self.initialized:
            self.pub.bind("tcp://127.0.0.1:6823")
            self.sub.connect("tcp://127.0.0.1:6823")

            self.sub.setsockopt(zmq.SUBSCRIBE, "dittobot-dashboard")
            self.initialized = True

        while request := await self.sub.recv_json():
            asyncio.get_event_loop().create_task(self.process_task(request))
