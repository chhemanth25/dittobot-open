import random
import traceback

import discord


class DittoMisc:
    def __init__(self, bot):
        self.bot = bot

    def get_type_emote(self, t):
        t = t.lower()
        types = {
            "normal": "<:normal1:1013132036380315690><:normal2:1013138069525889167>",
            "fighting": "<:fighting1:1013132042894061628><:fighting2:1013138084449226925>",
            "flying": "<:flying1:1013132040666882171><:flying2:1013138088261849089>",
            "poison": "<:poison1:1013132031925952563><:poison2:1013138071337848904>",
            "ground": "<:ground1:1013132033452675092><:ground2:1013138066749263994>",
            "rock": "<:rock1:1013132024426528778><:rock2:1013138074928164925>",
            "bug": "<:bug1:1013132030252437574><:bug2:1013138077998395492>",
            "ghost": "<:ghost1:1013132034882945096><:ghost2:1013138090249961542>",
            "steel": "<:steel1:1013132019397578894><:steel2:1013138604790386821>",
            "fire": "<:fire1:1013132012577636412><:fire2:1013138087058084091>",
            "water": "<:water1:1013132027958141030><:water2:1013138076656209930>",
            "grass": "<:grass1:1013789298073538634><:grass2:1013138065490976938>",
            "electric": "<:electric1:1013132013546524736><:electric2:1013138081806811237>",
            "psychic": "<:psychic1:1013132017380110389><:psychic2:1013138073422417991>",
            "ice": "<:ice1:1013132015631081552><:ice2:1013138068099825828>",
            "dragon": "<:dragon1:1013132026402054235><:dragon2:1013138080439484528>",
            "dark": "<:dark1:1013132037466632224><:dark2:1013138079218942114>",
            "fairy": "<:fairy1:1013132039333101668><:fairy2:1013138082989625424>",
        }
        return None if t not in types else types[t]

    def get_egg_emote(self, egg_group):
        egg_group = egg_group.lower()
        egg_groups = {
            "monster": "`monster`",
            "bug": "`bug`",
            "flying": "`flying`",
            "field": "`field`",
            "fairy": "`fairy`",
            "grass": "`grass`",
            "humanlike": "`humanlike`",
            "mineral": "`mineral`",
            "amorphous": "`amorphous`",
            "water1": "`water1`",
            "water2": "`water2`",
            "water3": "`water3`",
            "dragon": "`dragon`",
            "ditto": "`ditto`",
            "undiscovered": "`undiscovered`",
        }
        return None if egg_group not in egg_groups else egg_groups[egg_group]

    def get_random_egg_emote(self):
        return random.choice(
            [
                "<:monsteregg:764298668161105961>",
                "<:bugegg:764297919728713729>",
                "<:flyingegg:764297946396098560>",
                "<:fieldegg:764298329675923456>",
                "<:fairyegg:764298417215635477>",
                "<:grassegg:764297886644699197>",
                "<:humanlikeegg:764300101497389066>",
                "<:mineralegg:764298485494710272>",
                "<:amorphousegg:764603483667562587>",
                "<:water1egg:764298234381860904>",
                "<:water2egg:764297822144430100>",
                "<:water3egg:764297852650258452>",
                "<:dragonegg:764298849900298252>",
            ]
        )

    def get_gender_emote(self, gender):
        return (
            "<:male:1011932024438800464>"
            if gender == "-m"
            else ("<:female:1011935234067021834>" if gender == "-f" else "<:genderless:923737986447847435>")
        )

    async def log_error(self, ctx, error):
        await ctx.send("`The command encountered an error. Try again in a moment.`")
        ctx.bot.logger.exception(
            f"Error in command | {ctx.command.qualified_name} - Command = {ctx.command}"
        )
        # "404 unknown interaction" from the interaction timing out and becoming invalid before responded to.
        # I don't know how to possibly fix this other than to get a better host, stop spamming logs.
        if isinstance(error, discord.NotFound) and error.code == 10062:
            return

        def paginate(text: str):
            """Paginates arbitrary length text."""
            last = 0
            pages = []
            for curr in range(0, len(text), 1800):
                pages.append(text[last:curr])
                last = curr
            pages.append(text[last:])
            pages = list(filter(lambda a: a != "", pages))
            return pages

        stack = "".join(traceback.TracebackException.from_exception(error).format())
        pages = paginate(stack)
        for idx, page in enumerate(pages):
            if idx == 0:
                page = (
                    f"Guild ID   {ctx.guild.id}\n"
                    f"Channel ID {ctx.channel.id}\n"
                    f"User ID    {ctx.author.id}\n"
                    f"Path       {ctx.command.qualified_name}\n"
                    f"Args       {ctx.args}\n\n"
                ) + page
            await ctx.bot.get_partial_messageable(1004572745415266395).send(
                f"```py\n{page}\n```"
            )
