import discord
from discord.ext import commands

from dittocogs.pokemon_list import _


class HelpCog(commands.Cog):
    # @commands.group(name="help", case_insensitive=True)
    async def help(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="DittoBot commands",
                description="For more detailed help and information, Visit the official DittoBot wiki page [here](https://DittoBot.wiki)",
                color=3553600,
            )
            embed.add_field(
                name="DittoBot Tutorial :flashlight:", value=f"`{ctx.prefix}tutorial`"
            )
            embed.add_field(
                name="Pokemon commands", value=f"`{ctx.prefix}help pokemon`"
            )
            embed.add_field(
                name="Breeding commands", value=f"`{ctx.prefix}help breeding`"
            )
            embed.add_field(
                name="Activities", value=f"`{ctx.prefix}help activities`", inline=True
            )
            embed.add_field(
                name="Missions", value=f"`{ctx.prefix}help missions`", inline=True
            )
            embed.add_field(
                name="Forms commands", value=f"`{ctx.prefix}help forms`", inline=True
            )
            embed.add_field(
                name="Party commands", value=f"`{ctx.prefix}help party`", inline=True
            )
            embed.add_field(
                name="Admin commands", value=f"`{ctx.prefix}help admin`", inline=True
            )
            embed.add_field(
                name="Trading commands",
                value=f"`{ctx.prefix}help trading`",
                inline=True,
            )
            embed.add_field(
                name="Extra commands", value=f"`{ctx.prefix}help extras`", inline=True
            )
            embed.add_field(
                name="More Information About DittoBot",
                value="Visit the official DittoBot wiki page [here](https://DittoBot.wiki)",
            )

            embed.set_thumbnail(
                url="http://pm1.narvii.com/5848/b18cd35647528a7bdffc8e4b8e4d6a1465fc5253_00.jpg"
            )
            await ctx.send(embed=embed)

    # @help.command()
    async def general(self, ctx):
        embed = discord.Embed(title="General Commands", color=3553600)
        embed.add_field(
            name="Getting Started",
            value=f"To start, use the start command and then state the Pokemon's name.\nExample:\n`{ctx.prefix}start`\n`{ctx.prefix}start Bulbasaur`",
        )
        embed.add_field(
            name="Selecting a Pokemon",
            value=f"To select, use the command and add the Pokemon's number after.\nExample: `{ctx.prefix} 1`",
        )
        embed.add_field(
            name="Displaying your Pokemon",
            value=f"Displays your pokemon by their caught number.\n`{ctx.prefix}pokemon`",
        )
        embed.add_field(
            name="Searching caught Pokemon",
            value=f"This is done with the filter command. More details can be found using `{ctx.prefix}help filter`.",
        )
        embed.add_field(
            name="Infoing Pokemon",
            value=f"`{ctx.prefix}info (pokemon's name)` - Shows base stats of a Pokemon\n`{ctx.prefix} (pokemon's number)` will display the entered number stats.",
        )
        embed.add_field(
            name="Trainer Cards",
            value=f"`{ctx.prefix}trainer` - Shows your trainer card\n`{ctx.prefix}visible (enable/disable)` - Hides or Unhides your trainer card",
        )
        embed.add_field(
            name="Spawning Pokemon",
            value="Spawns are generated from messages sent that don't belong in a bot's prefix. They are active for 40 minutes, include the hint, and are caught by saying the Pokemon's name. No catch command needed",
        )
        await ctx.send(embed=embed)

    # @help.command(aliases=["favs"])
    async def fav(self, ctx):
        e = discord.Embed(title="Fav commands", color=3553600)
        e.description = (
            f"`{ctx.prefix}favs`- Shows Favourite Pokemon\n"
            f"`{ctx.prefix}fav add <pokemon_number>` - Adds Pokemon to Favourites\n"
            f"`{ctx.prefix}fav remove <pokemon_number>` - Removes Pokemon to Favourites"
        )
        await ctx.send(embed=e)

    # @help.command()
    async def activities(self, ctx):
        e = discord.Embed(title="Activities currently in DittoBot", color=3553600)
        e.add_field(name="Fishing Activity", value=f"`{ctx.prefix}help fishing`")
        e.add_field(name="Game corner", value=f"`{ctx.prefix}help game corner`")
        e.add_field(name="NPC interaction", value=f"`{ctx.prefix}duel npc`")
        await ctx.send(embed=e)

    # @help.command()
    async def missions(self, ctx):
        e = discord.Embed(title="Daily missions/rewards", color=3553600)
        e.add_field(name="Daily missions", value=f"`{ctx.prefix}missions`")
        e.add_field(
            name="Claim rewards",
            value=f"`{ctx.prefix}missions claim | Claim 10,000 credits from Missions completed`",
        )
        e.set_footer(text="Missions reset daily, complete them while you can!")
        await ctx.send(embed=e)

    # @help.group()
    async def game(self, ctx):
        ...

    # @game.command()
    async def corner(self, ctx):
        e = discord.Embed(title="Game corner tutorial", color=3553600)
        e.add_field(
            name="Slots",
            value=f"Get a Coin Case and Play the slot machines with `{ctx.prefix}slots`! Payouts are a Random % between 90 and 100, hitting the jackpot doubles the payout.",
        )
        e.add_field(
            name="Coins",
            value=f"You can Buy Coins into your Coin Case!, 1 Coin costs half a Credit, so 1 Credit = 2 Coins! Buy coins with `{ctx.prefix}buy coins <coin_amount>`",
        )
        e.add_field(
            name="Luck",
            value="Higher Luck increases your chances of hitting the Jackpot or 2 Rows, how to get more luck? just keep playing the Slot machines, you get double the luck on hitting the jackpot too!",
        )
        e.add_field(
            name="Energy",
            value="Just like other activities, The Slot machines deplete your Energy!\nYou will get an Energy Bar after every 20 Minutes!",
        )
        e.add_field(
            name="Cashing Out",
            value=f"You can convert all your earned Coins to Credits with `{ctx.prefix}cash out <coin_amount>`",
        )
        e.set_footer(text="Also totally worth the grind!")
        await ctx.send(embed=e)

    # @help.command()
    async def fishing(self, ctx):
        e = discord.Embed(title="Fishing tutorial", color=3553600)
        e.add_field(
            name="Fishing",
            value=f"`{ctx.prefix}fish`.Obtain items and Pokemon from Fishing!\nThe better your Rod, the better your fishing experience.",
        )
        e.add_field(
            name="Rare Pokemon",
            value="The Rarest Pokemon that can be gotten from Fishing are - Dratini, Dragonair, Dragonite, Gyarados, Lapras and Greninja -",
        )
        e.add_field(
            name="Fishing Levels",
            value="Higher Fishing Levels also mean Higher Chance for more expensive items and rarer Pokemon, your fishing level can be increased through fishing!",
        )
        e.add_field(
            name="Energy",
            value="You'll lose 1 energy starting your fishing and then another energy if you miss the Pokemon's name!",
        )
        e.set_footer(text="It's totally worth the grind!")
        await ctx.send(embed=e)

    # @help.command(aliases=["ev", "evs"])
    async def evpoints(self, ctx):
        e = discord.Embed(title="EV points Tutorial", color=3553600)
        e.add_field(
            name="Using them",
            value=(
                f"Correct usage of this command is: `{ctx.prefix}add evs <amount> <stat_name>`\n\n"
                f"Example: `{ctx.prefix}add evs 252 speed` to add to your __selected__ Pokemon`",
            ),
        )
        await ctx.send(embed=e)

    # @help.command(aliases=["trade", "trades"])
    async def trading(self, ctx):
        e = discord.Embed(title="Trading tutorial", color=3553600)
        e.add_field(
            name="Begin Trade",
            value=f"`{ctx.prefix}trade @User | All Trading Commands will be viewed when the trade starts`",
        )
        e.add_field(
            name="Credits",
            value=f"`{ctx.prefix}gift @User <credit_amount> | Give a user credits`",
        )
        e.add_field(
            name="Pokemon",
            value=f"`{ctx.prefix}give @User <pokemon_number> | Give a user a Pokemon`",
        )
        """e.add_field(
            name="Redeems",
            value="`{ctx.prefix}giveredeem @User <redeems_amount> | Give a user redeems`",
        )"""
        await ctx.send(embed=e)

    # @help.command(aliases=["form", "mega"])
    async def forms(self, ctx):
        e = discord.Embed(title="Form tutorial", color=3553600)
        e.add_field(
            name=f"`{ctx.prefix}form <form_name>`",
            value="Transform Your Selected Pokemon to it's form!",
        )
        e.add_field(
            name=f"`{ctx.prefix}solarize <solgaleo_number`",
            value="Solarize your Necrozma to Necrozma-dusk form",
        )
        e.add_field(
            name=f"`{ctx.prefix}lunarize <lunala_number>`",
            value="Lunarize your Necrozma to Necrozma-dawn form",
        )
        e.add_field(
            name=f"`{ctx.prefix}fuse black <zekrom_number>`",
            value="Fuse your Zekrom with Kyurem to Get Kyurem-black!",
        )
        e.add_field(
            name=f"`{ctx.prefix}fuse white <reshiram_number>`",
            value="Fuse your Reshiram with Kyurem to Get Kyurem-white!",
        )
        e.add_field(
            name=f"`{ctx.prefix}mega evolve`", value="Mega You Selected Pokemon"
        )
        e.add_field(
            name=f"`{ctx.prefix}mega evolve (x/y)`",
            value="Mega evolve selected Pokemon to X or Y form",
        )
        e.add_field(
            name=f"`{ctx.prefix}deform`",
            value="To make any Pokemon go back to it's default form",
        )
        await ctx.send(embed=e)

    # @help.command()
    async def trainer(self, ctx):
        e = discord.Embed(title="Trainer card help", color=3553600)
        e.add_field(
            name=f"`{ctx.prefix}nick <nickname>`",
            value="To change your Trainer Nickname",
        )
        await ctx.send(embed=e)

    # @help.command(aliases=["move"])
    async def moves(self, ctx):
        embed = discord.Embed(title="Pokemon commands", color=3553600)
        embed.add_field(name="Moves", value="See your current moves")
        embed.add_field(
            name="Learn A Move", value=f"`{ctx.prefix}learn <slot_number> <move_name>`"
        )
        embed.add_field(
            name="Moveset",
            value=f"Get the entire moveset of your pokemon `{ctx.prefix}moveset`",
        )
        await ctx.send(embed=embed)

    # @help.command()
    async def shop(self, ctx):
        e = discord.Embed(
            title="Items you can buy in the Shop!",
            description=f"`{ctx.prefix}shop <shop_name>`",
            color=3553600,
        )
        e.add_field(
            name="Forms",
            value=f"`{ctx.prefix}shop forms` to see available Items you can buy for forms!",
        )
        e.add_field(
            name="Mega",
            value=f"`{ctx.prefix}shop mega` Buy The Mega Stone to Mega your Pokemon and say `{ctx.prefix}mega evolve`!",
        )
        e.add_field(
            name="Items",
            value=f"`{ctx.prefix}shop items` to buy Rare candies, Items to Boost Pokemon Abilities such as Zinc e.t.c",
        )
        e.add_field(
            name="Held items",
            value=f"`{ctx.prefix}shop held items` To see Held Items you can buy for your Pokemon!",
        )
        e.add_field(
            name="Battle Items",
            value=f"`{ctx.prefix}shop battle items` will show you all items usable for battles.",
        )
        e.add_field(
            name="Key items",
            value=f"`{ctx.prefix}shop key items` Currently only Shiny Charm",
        )
        e.add_field(
            name="Stones", value=f"Say `{ctx.prefix}shop stones` for evolution stones"
        )
        e.add_field(
            name="Vitamins",
            value=f"Say `{ctx.prefix}shop vitamins` for vitamins to boost stats!",
        )
        e.add_field(name="Buy", value=f"`{ctx.prefix}buy <item_name>` to buy an item")
        e.set_footer(text="Buy items!")
        await ctx.send(embed=e)

    # @help.command()
    async def pokemon(self, ctx):
        embed = discord.Embed(title="Pokemon commands", color=3553600)
        embed.add_field(
            name="Display Trainer Card",
            value=f"`{ctx.prefix}trainer [bal | gold | credits]`",
            inline=False,
        )
        embed.add_field(
            name="View all Pokemon",
            value=f"`{ctx.prefix}pokemon [p | pokes]`",
            inline=False,
        )
        embed.add_field(
            name="Select Pokemon",
            value=f"`{ctx.prefix}select <pokemon_number>`",
            inline=False,
        )
        embed.add_field(
            name="Select Newest Pokemon",
            value=f"`{ctx.prefix}select [newest | latest | new]`",
            inline=False,
        )
        embed.add_field(
            name="Show Pokemon Information",
            value=f"`{ctx.prefix}info <pokemon_number>`",
            inline=False,
        )
        embed.add_field(
            name="Show Newest Pokemon Information",
            value=f"`{ctx.prefix}info [newest | latest | new]`",
            inline=False,
        )
        embed.add_field(
            name="Show Pokemon Information [Quick]",
            value=f"`{ctx.prefix}qinfo <pokemon_number>`",
            inline=False,
        )
        embed.add_field(
            name="Show Newest Pokemon Information [Quick]",
            value=f"`{ctx.prefix}qinfo [newest | latest | new]`",
            inline=False,
        )
        embed.add_field(
            name="Change Pokemon Nickname",
            value=f"`{ctx.prefix}nickname <nickname>`",
            inline=False,
        )
        embed.add_field(
            name="Filter | Sort Pokemon Commands",
            value=f"`{ctx.prefix}help filter`",
            inline=False,
        )
        embed.add_field(
            name="Favourite Pokemon Commands",
            value=f"`{ctx.prefix}help fav`",
            inline=False,
        )
        embed.add_field(
            name="Bag Commands", value=f"`{ctx.prefix}help bag`", inline=False
        )
        await ctx.send(embed=embed)

    # @help.command()
    async def bag(self, ctx):
        e = discord.Embed(title="Bag commands", color=3553600)
        e.add_field(name="View Bag", value=f"`{ctx.prefix}bag`")
        e.add_field(name="Equip to a Pokemon", value=f"`{ctx.prefix}equip <item_name>`")
        e.add_field(name="Unequip items from a Pokemon", value=f"`{ctx.prefix}unequip`")
        await ctx.send(embed=await _(e))

    # @help.command(aliases=["item"])
    async def items(self, ctx):
        embed = discord.Embed(title="Item tutorial", color=3553600)
        prefix = ctx.prefix
        embed.add_field(
            name="Items", value=f"See all your acquired items with `{ctx.prefix}items`!"
        )
        embed.add_field(
            name="Equip",
            value=f"Equip Items on a Pokemon with this command `{ctx.prefix}equip <pokemon_number>`",
        )
        embed.add_field(
            name="Change Nature",
            value=f"Change the Nature of your Selected Pokemon with `{prefix}change nature <nature_name>`. You must have a Nature Capsule to change natures!",
        )
        embed.add_field(
            name="Inventory", value=f"See your inventory with `{prefix}inventory`!"
        )
        embed.add_field(
            name="Transfer Items!",
            value=f"Use `{ctx.prefix}transfer item <pokemon_number>` to transfer items from your Selected Pokemon to another Pokemon!",
        )
        await ctx.send(embed=embed)

    # @help.command()
    async def order(self, ctx):
        doc = (
            "You can Order by `ivs, evs, name, or level` or by default.\n"
            "[Example]\n"
            f"`{ctx.prefix}order by ivs`"
        )
        e = discord.Embed(title="Default Order Help!", color=3553600)
        e.add_field(name="Default Orders", value=doc)
        await ctx.send(embed=e)

    # @help.command()
    async def filter(self, ctx):
        e = discord.Embed(title="Filtering help!", color=3553600)
        e.add_field(
            name="Pokemon",
            value=f"`{ctx.prefix}[filter | f] [pokemon | p] <options>` filter or sort your Pokemon using available options",
        )
        e.add_field(
            name="Market",
            value=f"`{ctx.prefix}[filter | f] [market | m] <options>` filter or sort market Pokemon using available options",
        )
        e.add_field(
            name="Options",
            value=(
                f"Available Options are - `.name, .nickname, .nature, .type, .types, .level, .shiny, .iv, .ev, .page, .owned, .legendary, .pseudo, .ultra beast, .price, .item, .egg-group`\n\n"
            ),
        )
        e.add_field(
            name="Examples",
            value=(
                "```css\n"
                "[Search for my Shiny Gyarados-mega and order by the IVs]\n"
                f"{ctx.prefix}filter pokemon .name gyarados-mega .iv descending .shiny\n\n"
                "[Search for all Pokemon Above level 50 and order by EVs]\n"
                f"{ctx.prefix}filter pokemon .level > 50 .ev d\n\n"
                "[Search for my Market listings]\n"
                f"{ctx.prefix}filter market .owned\n\n"
                "[Search for all my shiny legendaries]\n"
                f"{ctx.prefix}f p .legendary .shiny"
                "```"
            ),
        )

        await ctx.send(embed=e)

    # @help.command()
    async def party(self, ctx):
        embed = discord.Embed(title="Party commands", color=3553600)
        embed.add_field(
            name="Party", value=f"Displays your current party.\n`{ctx.prefix}party`"
        )
        embed.add_field(
            name="Add to Party",
            value=f"Adds a pokemon to your party\n`{ctx.prefix}party add [slot_number] [pokemon_number]`",
        )
        embed.add_field(
            name="Remove from Party",
            value=f"Removes a pokemon from your party\n`{ctx.prefix}party remove [slot_number]`",
        )
        embed.add_field(
            name="Register/Update a new Party",
            value=f"If the entered name already exist, it'll update that party. If not, it'll make a new party.\n`{ctx.prefix}party register [name]`",
        )
        embed.add_field(
            name="List of Parties",
            value=f"This command displays saved parties.\n`{ctx.prefix}party list`",
        )
        embed.add_field(
            name="Load a Party",
            value=f"Replace current party with previously saved party.\n`{ctx.prefix}party load [name]`",
        )
        await ctx.send(embed=embed)

    # @help.command(aliases=["voting", "upvotes", "daily", "claim"])
    async def upvote(self, ctx):
        embed = discord.Embed(color=3553600)
        embed.add_field(name="Claim upvote points", value=f"`{ctx.prefix}claim`")
        await ctx.send(embed=embed)

    # @help.command(aliases=["settings"])
    async def admin(self, ctx):
        embed = discord.Embed(title="Admin commands", color=3553600)
        # `{ctx.prefix}settings language <language>` - Change server language
        embed.set_thumbnail(
            url="https://images.discordapp.net/avatars/519850436899897346/038a1e4fcce1f27161040a5f9013338c.png?size=512"
        )
        embed.add_field(
            name="Change Prefix", value=f"`{ctx.prefix}prefix <prefix>`", inline=True
        )
        embed.add_field(
            name="Toggle Bot Commands",
            value=f"`{ctx.prefix}channel disable/enable <channel>`",
            inline=True,
        )
        embed.add_field(
            name="Toggle Spawns",
            value=f"`{ctx.prefix}spawns disable/enable`",
            inline=True,
        )
        embed.add_field(
            name="Spawn Redirection",
            value=f"`{ctx.prefix}redirect spawns #channel`",
            inline=True,
        )
        embed.add_field(
            name="Disable Redirection",
            value=f"`{ctx.prefix}redirect disable`",
            inline=True,
        )
        embed.add_field(
            name="Auto Pin Rare Spawns",
            value=f"`{ctx.prefix}auto pin spawns #channel`",
            inline=True,
        )
        embed.add_field(
            name="Auto Delete Spawns on Catch",
            value=f"`{ctx.prefix}auto delete spawns #channel`",
            inline=True,
        )
        await ctx.send(embed=embed)

    # @help.command(aliases=["extra"])
    async def extras(self, ctx):
        embed = discord.Embed(title="Extra commands", color=3553600)
        embed.add_field(name="Updates", value=f"`{ctx.prefix}updates`")
        embed.add_field(
            name="Level up Messages",
            value=f"`{ctx.prefix}silence` or `{ctx.prefix}stfu`, re-enable with `{ctx.prefix}level up`!",
        )
        embed.add_field(
            name="Trainer Card Visibility",
            value=f"Make your Trainer Card invisible with `{ctx.prefix}visible disable` and Make it Visible again with `{ctx.prefix}visible enable`!",
        )
        embed.add_field(
            name="Status",
            value="User count, server count, CPU and Memory Status and More!",
        )
        embed.add_field(name="Leaderboard", value="See the Top Players of DittoBot!")

        embed.set_footer(
            text="© 2020 Pokémon. © 1995–2020 Nintendo/Creatures Inc./GAME FREAK inc. Pokémon, Pokémon character names, Nintendo Switch, Nintendo 3DS, Nintendo DS, Wii, Wii U, and WiiWare are trademarks of Nintendo. The YouTube logo is a trademark of Google Inc. Other trademarks are the property of their respective owners."
        )
        await ctx.send(embed=embed)

    # @help.command()
    async def market(self, ctx):
        embed = discord.Embed(
            title="Market commands",
            description="Basic market commands within DittoBot",
            color=3553600,
        )
        embed.add_field(
            name="Add Pokemon to market",
            value=f"`{ctx.prefix}market add <pokemon_number> <price>`",
        )
        embed.add_field(
            name="Searching market",
            value=f"Use`{ctx.prefix}help filter` for more details on how to search market!",
        )
        embed.add_field(
            name="Remove Pokemon from market",
            value=f"`{ctx.prefix}market remove <pokemon_id>`",
        )
        embed.add_field(
            name="Buy Pokemon From the market",
            value=f"`{ctx.prefix}market buy <pokemon_id>`",
        )
        await ctx.send(embed=embed)

    # @help.command(aliases=["duel"])
    async def duels(self, ctx):
        embed = discord.Embed(title="How to Battle Your Friends!", color=3553600)
        embed.add_field(
            name="How it works",
            value="DittoBot has both Single Pokemon Duels and Party Battle!",
        )
        embed.add_field(
            name="Battle Command",
            value=f"`{ctx.prefix}battle @user` to Challenge them to 6v6 Battle! You must have a Complete Party for this!. Say `{ctx.prefix}help part`for more on that",
        )
        embed.add_field(
            name="Duel Command",
            value=f"`{ctx.prefix}duel @user` To Challenge them to a Duel with their Currently selected Pokemon!. A Complete Party is not required for this.",
        )
        embed.set_footer(
            text="While duels are proposed to be debugged, Battles are extensively Buggy. Please Join the official server to report bugs, if you find any."
        )
        await ctx.send(embed=embed)

    # @help.command()
    async def vitamin(self, ctx):
        e = discord.Embed(
            title="Buy vitamins!!",
            description="All Vitamins Cost 1,000 Credits!",
            color=3553600,
        )
        e.add_field(
            name="hp-up",
            value=f"`{ctx.prefix}buy vitamin hp-up` to boost your HP EVs by 10!",
        )
        e.add_field(
            name="Protein",
            value=f"`{ctx.prefix}buy vitamin protein` to boost your Attack EVs by 10!",
        )
        e.add_field(
            name="Iron",
            value=f"`{ctx.prefix}buy vitamin iron` to boost your Defense EVs by 10!",
        )
        e.add_field(
            name="Calcium",
            value=f"`{ctx.prefix}buy vitamin calcium` to boost your Special Attack EVs by 10!",
        )
        e.add_field(
            name="Zinc",
            value=f"`{ctx.prefix}buy vitamin zinc` to boost your Special Defense EVs by 10!",
        )
        e.add_field(
            name="Carbos",
            value=f"`{ctx.prefix}buy vitamin carbos` to boost your Speed EVs by 10!",
        )
        await ctx.send(embed=e)

    # @help.command()
    async def breeding(self, ctx):
        e = discord.Embed(
            title="How to breed Pokemon",
            description="Breeding Pokemon is simple!, all you need are two Pokemon of opposite Genders in the same Egg groups!",
        )
        e.add_field(name="How to Breed", value=f"`{ctx.prefix}breed <male> <female>`")
        e.add_field(
            name="Breeding Limits",
            value=f"You can only breed according to your Daycare Limit, You can increase this by Buying packs (`{ctx.prefix}packs`) or Buying a Daycare Space",
        )
        e.add_field(
            name="Breeding Success Rate",
            value="Successful breeding is calculated by the catch rate, or rarity divided by IV total of both parents. So in other words, the Higher IVs of Parents and the rarer they are the harder it is.",
        )
        e.add_field(
            name="Breeding tips",
            value="With an Everstone, You can Pass down the nature of a Parent to the Egg\nAlso, with Destiny Knot and Ultra Destiny Knot, you can pass down 2-3 or 2-5 random exact Stats respectively of a Parent to the Offspring!",
        )
        e.add_field(name="Breeding Forms", value="Note: You can not breed forms!")
        e.add_field(
            name="Obtaining Phione",
            value="You can obtain Phione by breeding a Manaphy with Ditto or another Phione with Ditto!",
        )
        await ctx.send(embed=e)

    # @help.command()
    async def sky(self, ctx):
        embed = discord.Embed(
            title="Staff Commands by Role",
            description="To find ID's you must enable developer mode in your settings. After enabling this, you can obtain an id by right clicking or taping and holding on any discord object (chan, user, etc). \n**[For help turning on dev mode click here](https://discordia.me/developer-mode)**",
            color=3553600,
        )
        embed.set_author(name="ditto.cogs.sky", icon_url="http://skys.fun/stuff/mew.png")
        embed.set_footer(
            text="Abuse of these commands is prohibited ",
            icon_url="http://skys.fun/stuff/mew.png",
        )
        embed.add_field(
            name="__Moderator Commands__",
            value=(
                "**Addpoke:** `addpoke [userID] [pokeID]`\n"
                "```diff\n"
                "+Add specified pokemon to a users array.\n"
                "(yeet, grant, bestow)\n"
                "```\n"
                "**Removepoke:** `removepoke [userID] [pokeID]`\n"
                "```diff\n"
                "-Remove specified pokemon from a users array\n"
                "(yoink, steal, rob)\n"
                "```\n"
                "**Mock:** `mock [userID] [command]`\n"
                "```md\n"
                "Mock another user invoking a command.\n"
                "---\n"
                "> The prefix must not be entered.\n"
                "```\n"
                "**Reload ditto Cog:** `reload trade`, `reload sky`\n"
                "```diff\n"
                "+ Reload a cog by name"
                "```\n"
                "**Whoowns:** `whoowns [pokeID]`\n"
                "```md\n"
                "# Fetch the userID of the user who owns the pokeID specified. \n"
                "You can find any pokemons pokeID in the footer of its info embed.\n"
                "---------------------------```"
            ),
            inline=True,
        )
        embed.add_field(
            name="__Admin Commands__",
            value=(
                "**Botban:**\n"
                "`bb [userID]`\n"
                "```diff\n"
                "-Botban the specified user by their [userID]"
                "```\n"
                "**Un-botban:** `ubb [userID]`\n"
                "```md\n"
                "Un-botban the specified user by their [userID]\n"
                "**Server Ban** `serverban [serverID]`\n"
                "----------------------------```"
            ),
            inline=True,
        )
        await ctx.send(embed=embed)

    # @help.command()
    async def newticket(self, ctx):
        embed = discord.Embed(
            title="New Ticket Creation",
            colour=discord.Colour(0x65BAF),
            description=(
                "**Command:** `;newticket`\n**Usage:** `;newticket <description of issue>`\n**Purpose:** Provide an orderly way for Support Team members to report issues that people post within #questions or any of the bug report channels.\n**__Example__:** *if issue is in regards to one person, please provide ID or username somewhere in the description of issue.*\n```md\n;newticket There is an issue causing everyone to lose all of their pokemon, omg were losing everything, aaaaaaaahhhhh\n--```"
            ),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog())
