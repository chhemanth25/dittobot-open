"""
Unless otherwise mentioned, source code in this repository is owned by the Dittobot Developers mentioned in README.md in the root of this repository.
This source code is un-licensed.  As such, standard copyright laws apply.
Any unauthorized access, distribution, or use is strictly prohibited.

This code is structured off the IdleRPG Discord bot's launcher, which you can find here:
https://github.com/Gelbpunkt/IdleRPG/blob/current/launcher.py
"""


from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import signal
import sys
from socket import socket
from time import time
from traceback import print_exc
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from uuid import uuid4

import aiohttp
import aioredis
import orjson
import psutil
from dotenv import load_dotenv

abspath = os.path.abspath(__file__)
directory = os.path.dirname(abspath)
os.chdir(directory)

load_dotenv("./env/bot.env")
load_dotenv("./env/mongo.env")
load_dotenv("./env/postgres.env")
load_dotenv("./env/voting.env")

logger = logging.getLogger("dittobot")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "[MAIN] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

shards_per_cluster = 10

payload = {
    "Authorization": f"Bot {os.environ['MTOKEN']}",
    "User-Agent": "Dittobot launcher 0.0.1a",
    "Content-Type": "application/json",
}

cluster_names = {
    1: "Pika",
    2: "Eevee",
    3: "Bulbasaur",
    4: "Grovyle",
    5: "Charmander",
    6: "Squirtle",
    7: "Torchic",
    8: "Piplup",
    9: "Snorlax",
    10: "Luvdisc",
    11: "Lucario",
    12: "Lapras",
    13: "Magikarp",
    14: "Psyduck",
    15: "Meowth",
    16: "Lugia",
    17: "Magnezone",
    18: "Electivire",
    19: "Chikorita",
    20: "Pelipper",
}


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        logger.critical("Invalid clusters flag.  Usage: --clusters 1 2 3 4 ...")
        sys.exit(1)


async def get_shard_count():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://discordapp.com/api/v8/gateway/bot", headers=payload
        ) as req:
            gateway_json = await req.json()
        try:
            shard_count = gateway_json["shards"]
        except KeyError as e:
            raise RuntimeError("Are you sure your token is correct?") from e
        return shard_count


async def get_app_info() -> Tuple[str, int]:
    async with aiohttp.ClientSession() as session, session.get(
        "https://discord.com/api/oauth2/applications/@me", headers=payload
    ) as req:
        response = await req.json()
    return response["name"], response["id"]


def get_cluster_list(shards: int):
    return [
        list(range(shards)[i : i + shards_per_cluster])
        for i in range(0, shards, shards_per_cluster)
    ]


class Instance:
    def __init__(
        self,
        instance_id: int,
        shard_list: List[int],
        shard_count: int,
        name: str,
        loop: asyncio.AbstractEventLoop,
        logging_code: int,
        main: Optional["Main"] = None,
    ):
        self.main = main
        self.loop = loop
        self.shard_count = shard_count  # overall shard count
        self.shard_list = shard_list
        self.started_at = 0.0
        self.id = instance_id
        self.pid = 0
        self.name = name
        self.logging_code = logging_code
        self.command = (
            f"/usr/bin/python3.9 -m cProfile -o /home/ubuntu/cprofiles/cluster-{self.name}"
            f' {os.getcwd()}/ditto/__main__.py "{shard_list}" {shard_count}'
            f' {self.id} {self.name} {self.logging_code} "{os.getcwd()}"'
            if self.main.cprofile
            else f'/usr/bin/python3.9 {os.getcwd()}/ditto "{shard_list}" {shard_count}'
            f' {self.id} {self.name} {self.logging_code} "{os.getcwd()}"'
        )

        self._process: Optional[asyncio.subprocess.Process] = None
        self.status = "initialized"
        self.loop.create_task(self.start())

    @property
    def is_active(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def start(self) -> None:
        if self.is_active:
            logger.info(f"Cluster #{self.id} ({self.name}) The cluster is already up")
            return
        if self.main is None:
            raise RuntimeError("This cannot be possible.")
        self.started_at = time()
        self._process = await asyncio.create_subprocess_shell(self.command)
        task = self.loop.create_task(self._run())
        logger.info(
            f"Cluster #{self.id} ({cluster_names[self.id]}) Started successfully"
        )
        self.status = "running"
        task.add_done_callback(
            self.main.dead_process_handler
        )  # TODO: simply use it inline

    async def stop(self, prevent_logs=False) -> None:
        self.status = "stopped"

        if not self.is_active:
            logger.error(f"Cluster #{self.id} ({self.name}) is already stopped")
            return
        if self._process is None:
            raise RuntimeError(
                "Function cannot be called before initializing the Process."
            )

        payload = {
            "scope": "bot",
            "action": "shutdown",
            "command_id": str(uuid4()),
            "args": {
                "cluster_id": self.id,
                "restart": False,
                "yesiknowwhatimdoingpleasedontspammessages": prevent_logs,
            },
        }

        await self.main.redis.execute(
            "PUBLISH", "dittobot_clusters", orjson.dumps(payload)
        )

        with contextlib.suppress(ProcessLookupError):
            self._process.terminate()

        await asyncio.sleep(10)
        if self.is_active:
            with contextlib.suppress(ProcessLookupError):
                self._process.kill()
            logger.error(f"Cluster #{self.id} ({self.name})'s shell got force killed")
        elif psutil.pid_exists(self._process.pid):
            os.kill(self.pid, 1)
            logger.error(f"Cluster #{self.id} ({self.name}) was force killed")
        else:
            logger.debug(f"Cluster #{self.id} ({self.name}) Killed gracefully")

    async def restart(self, prevent_logs=False) -> None:
        if self.is_active:
            await self.stop(prevent_logs)
        await self.start()

    async def _run(self) -> Tuple["Instance", bytes, bytes]:
        if self._process is None:
            raise RuntimeError(
                "Function cannot be called before initializing the Process."
            )
        stdout, stderr = await self._process.communicate()

        return self, stdout, stderr

    def __repr__(self) -> str:
        return (
            f"<Cluster ID={self.id} name={self.name}, active={self.is_active},"
            f" shards={self.shard_list}, started={self.started_at}>"
        )


class Main:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop or asyncio.get_event_loop()
        self.redis_task = None

        self.to_launch = None
        self.shard_count = None
        self.waiting_for_msg = False
        self.launching = 0
        self.restarting = False

        self.logging_code = 0
        self.cprofile = False

        self.instances: List[Instance] = []
        self.redis: Optional[aioredis.Redis] = None

    def dead_process_handler(
        self, result: asyncio.Future[Tuple[Instance, bytes, bytes]]
    ) -> None:
        instance, _, stderr = result.result()
        if instance._process is None:
            raise RuntimeError(
                "This callback cannot run without a process that exited."
            )
        logger.info(
            f"Cluster #{instance.id} ({instance.name}) Exited with code"
            f" {instance._process.returncode}"
        )
        """
        if instance._process.returncode == 0:
            logger.info(f"Cluster #{instance.id} ({instance.name}) Stopped gracefully")
        elif instance.status == "stopped":
            logger.info(
                f"Cluster #{instance.id} ({instance.name}) Stopped by command, not restarting"
            )
        else:
            logger.info(f"Cluster #{instance.id} ({instance.name}) Restarting...")
            instance.loop.create_task(instance.start())
        """

    def get_instance(self, iterable: Iterable[Instance], id: int) -> Instance:
        for elem in iterable:
            if getattr(elem, "id") == id:
                return elem
        raise ValueError("Unknown instance")

    async def acknowledge(self, payload):
        await self.redis.execute(
            "PUBLISH",
            "dittobot_clusters",
            orjson.dumps(
                {
                    "command_id": payload["command_id"],
                    "output": "ok",
                    "scope": "bot",
                }
            ),
        )

    async def event_handler(self) -> None:
        try:
            self.redis = await aioredis.create_pool(
                "redis://178.28.0.13", minsize=1, maxsize=2
            )
        except aioredis.RedisError:
            print_exc()
            exit("[ERROR] Redis must be installed properly")

        await self.redis.execute_pubsub("SUBSCRIBE", "dittobot_clusters")
        channel = self.redis.pubsub_channels[bytes("dittobot_clusters", "utf-8")]
        while await channel.wait_message():
            try:
                payload = await channel.get_json(encoding="utf-8")
            except orjson.JSONDecodeError:
                continue  # not a valid JSON message
            if payload.get("scope") != "launcher" or not payload.get("action"):
                continue  # not the launcher's task

            try:
                # parse the JSON args
                args = payload.get("args", {})
                id_ = args.get("id")
                id_exists = id_ is not None

                if id_exists:
                    try:
                        instance = self.get_instance(self.instances, id_)
                    except ValueError:
                        # unknown instance
                        continue

                if payload["action"] == "restart" and id_exists:
                    logger.info(f"Restart requested for cluster #{id_}")
                    self.loop.create_task(instance.restart(True))
                    await self.acknowledge(payload)
                elif payload["action"] == "stop" and id_exists:
                    logger.info(f"Stop requested for cluster #{id_}")
                    self.loop.create_task(instance.stop(True))
                    await self.acknowledge(payload)
                elif payload["action"] == "start" and id_exists:
                    logger.info(f"Start requested for cluster #{id_}")
                    self.loop.create_task(instance.start())
                    await self.acknowledge(payload)
                elif payload["action"] == "statuses" and payload.get("command_id"):
                    statuses = {}
                    for instance in self.instances:
                        statuses[str(instance.id)] = {
                            "active": instance.is_active,
                            "status": instance.status,
                            "name": instance.name,
                            "started_at": instance.started_at,
                            "shard_list": instance.shard_list,
                        }
                    await self.redis.execute(
                        "PUBLISH",
                        "dittobot_clusters",
                        orjson.dumps(
                            {
                                "command_id": payload["command_id"],
                                "output": statuses,
                                "scope": "bot",
                            }
                        ),
                    )
                elif payload["action"] == "launch_next" and self.launching == id_:
                    self.waiting_for_msg = False
                    instance.pid = args["pid"]
                elif payload["action"] == "num_processes":
                    payload = {
                        "command_id": payload["command_id"],
                        "scope": "bot",
                        "output": {
                            "clusters": len(self.instances),
                            "shards": self.shard_count,
                        },
                    }
                    await self.redis.execute(
                        "PUBLISH", "dittobot_clusters", orjson.dumps(payload)
                    )
                elif payload["action"] == "restartclusters":
                    await self.acknowledge(payload)
                    logger.info("Received request to restart all clusters")

                    await self.shutdown(False)
                    logger.info("------------------------------------------------")
                    self.loop.create_task(self.launch())
                elif payload["action"] == "restartprocess":
                    await self.acknowledge(payload)
                    logger.info(
                        "Received request to restart process; Systemctl will restart"
                    )
                    self.restarting = True
                    signal.raise_signal(signal.SIGINT)
                elif payload["action"] == "stopprocess":
                    await self.acknowledge(payload)
                    logger.critical("Received request to stop process")
                    self.restarting = False
                    signal.raise_signal(signal.SIGINT)
                elif payload["action"] == "rollingrestart":
                    await self.acknowledge(payload)
                    logger.info("Received request to perform rolling restart")
                    self.loop.create_task(self.rolling_restart())
            except Exception as e:
                logger.error("Exception in Launcher Redis handler", exc_info=True)

    async def launch(self) -> None:
        if not self.redis_task:
            self.redis_task = loop.create_task(self.event_handler())
        self.shard_count = await get_shard_count()
        clusters = get_cluster_list(self.shard_count)
        name, id = await get_app_info()
        if self.to_launch:
            logger.info(f"Starting {name} ({id}) - {len(self.to_launch)} clusters")
        else:
            logger.info(
                f"Starting {name} ({id}) - {self.shard_count} shards, {len(clusters)} clusters"
            )

        logger.info(f"Running from directory: {os.getcwd()}")

        if self.cprofile:
            logger.info(
                "Started with cProfile flag.  Clusters will generate cprofiles in /home/dylee/cprofiles"
            )

        for i, shard_list in enumerate(clusters, 1):
            if not shard_list:
                continue
            if self.to_launch and i not in self.to_launch:
                continue
            self.launching = i
            name = cluster_names[i]
            self.instances.append(
                Instance(
                    i,
                    shard_list,
                    self.shard_count,
                    name,
                    self.loop,
                    self.logging_code,
                    main=self,
                )
            )
            self.waiting_for_msg = True
            while self.waiting_for_msg:
                await asyncio.sleep(1)
            logger.debug(
                "Received request to launch next cluster.  Waiting for concurrency timeout period..."
            )
            await asyncio.sleep(5)
        payload = {
            "command_id": str(uuid4()),
            "scope": "bot",
            "action": "all_clusters_launched",
        }
        await self.redis.execute("PUBLISH", "dittobot_clusters", orjson.dumps(payload))
        logger.info("All clusters successfully launched")

    async def shutdown(self, shutdown_task=True) -> None:
        await asyncio.gather(*[instance.stop(True) for instance in self.instances])
        self.instances = []
        if shutdown_task:
            self.redis_task.cancel()

    async def rolling_restart(self) -> None:
        for instance in self.instances:
            self.launching = instance.id
            self.waiting_for_msg = True
            await instance.restart(True)
            while self.waiting_for_msg:
                await asyncio.sleep(1)
            logger.debug(
                "Received request to launch next cluster.  Waiting for concurrency timeout period..."
            )
        logger.info("Rolling restart complete")

    def parse_argparse_flags(self):
        parser = NoExitParser(description="dittobot Cluster Launcher")

        parser.add_argument(
            "--clusters", dest="clusters", type=int, nargs="+", default=[]
        )

        parser.add_argument("--debug", dest="dittodebug", action="store_true")
        parser.add_argument("--dpy-debug", dest="dpydebug", action="store_true")
        parser.add_argument("--cprofile", dest="cprofile", action="store_true")

        try:
            args = vars(parser.parse_args())
        except Exception:
            logger.critical("Invalid parser flags.")

        self.to_launch = args["clusters"]
        self.cprofile = args["cprofile"]

        # 0 => ditto INFO, Dpy WARNING (Standard)
        # 1 => ditto DEBUG, dpy WARNING
        # 2 => ditto INFO, dpy DEBUG
        # 3 => Both DEBUG

        if args["dittodebug"] and args["dpydebug"]:
            logger.setLevel(logging.DEBUG)
            self.logging_code = 3
        elif args["dpydebug"]:
            self.logging_code = 2
        elif args["dittodebug"]:
            logger.setLevel(logging.DEBUG)
            self.logging_code = 1
        else:
            self.logging_code = 0


if __name__ == "__main__":
    main = Main()
    main.parse_argparse_flags()

    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
    loop.create_task(main.launch())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(main.shutdown())
        logger.info("All clusters shut down.  Cleaning up...")

        def shutdown_handler(
            _loop: asyncio.AbstractEventLoop,
            context: Dict[
                str,
                Union[
                    str,
                    Exception,
                    asyncio.Future[Any],
                    asyncio.Handle,
                    asyncio.Protocol,
                    asyncio.Transport,
                    socket,
                ],
            ],
        ) -> None:
            # all the types are from https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_exception_handler
            if "exception" not in context or not isinstance(
                context["exception"], asyncio.CancelledError
            ):
                _loop.default_exception_handler(context)  # TODO: fix context

        loop.set_exception_handler(shutdown_handler)
        tasks = asyncio.gather(
            *asyncio.all_tasks(loop=loop), loop=loop, return_exceptions=True
        )
        tasks.add_done_callback(lambda t: loop.stop())
        tasks.cancel()

        while not tasks.done() and not loop.is_closed():
            loop.run_forever()
    finally:
        if hasattr(loop, "shutdown_asyncgens"):
            loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        if main.restarting:
            sys.exit(1)
        else:
            sys.exit(0)
