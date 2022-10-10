import discord
from discord.ext import commands
from utils.misc import MenuView, pagify

from dittocogs.json_files import *
from dittocogs.pokemon_list import *


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def shop(self, ctx, val=None):
        if val is None:
            e = discord.Embed(
                title="Items you can buy in the Shop!",
                description="`/shop <shop_name>`",
                color=3553600,
            )

            e.add_field(name="Forms", value="`/shop forms`", inline=False)
            e.add_field(name="Mega Pokemon", value="`/shop mega`", inline=False)
            e.add_field(name="Items", value="`/shop items`", inline=False)
            e.add_field(name="Trade items", value="`/shop trade items`", inline=False)
            e.add_field(name="Battle Items", value="`/shop battle items`", inline=False)
            e.add_field(
                name="Stones", value="`/shop stones` Evolution stones", inline=False
            )

            e.add_field(name="Vitamins", value="`/shop vitamins`", inline=False)
            e.add_field(name="Rods", value="`/shop rods`", inline=False)
            e.set_footer(
                text="Items can also be gotten through Item Drops from spawned Pokemon!"
            )

            await ctx.send(embed=e)
            return
        elif val.lower() in ("rod", "rods", "fish", "fishing"):
            rods = [t["item"] for t in SHOP if "-rod" in t["item"]]
            prices = [t["price"] for t in SHOP if t["item"] in rods]
            e = discord.Embed(
                title="Fishing Rods!",
                description="Say `/buy item <rod_name>` to buy a Rod",
                color=3553600,
            )

            for idx, rod in enumerate(rods):
                e.add_field(
                    name=rod.capitalize().replace("-", " "),
                    value=f"Costs {prices[idx]} Credits",
                )

            e.set_footer(
                text="Items can also be gotten through Item Drops from spawned Pokemon!"
            )

            await ctx.send(embed=e)
        elif val.lower() in ("item", "items"):
            e = discord.Embed(
                title="Items to Evolve or Boost stats, e.t.c", color=3553600
            )
            e.add_field(
                name="Rare Candies",
                value="Buy rare candies with `/buy candy <amount>`. Costs 100c Each!",
            )

            e.add_field(
                name="Everstone",
                value="Buy the Everstone to Automatically stop evolution! Costs 3,000 Credits",
            )

            e.add_field(
                name="XP-Block",
                value="Stop any Pokemon from gaining Experience with the XP-Block. Costs 3,000 Credits",
            )

            e.add_field(
                name="Lucky Egg",
                value="Boost EXP Gain of your selected Pokemon by 150% Costs 5,000 Credits",
            )

            e.add_field(
                name="Soothe bell",
                value="Boost Friendship Gain of your Selected Pokemon by 50% Costs 5,000 Credits",
            )

            e.add_field(
                name="Ability Capsule",
                value="Change your Pokemons ability by buying the Ability Capsule! Costs 10,000 Credits",
            )

            e.add_field(
                name="Daycare Space",
                value="Buy an Extra Space in the Daycare to breed more Pokemon! Costs 10,000 Credits",
            )

            e.add_field(
                name="Market Space",
                value="Buy an extra space in the market to sell more pokemon! Costs 30,000 Credits",
            )

            e.add_field(
                name="Destiny Knot",
                value="Pass down 2-3 Random Stats to an Offspring during Breeding! Costs 15,000 Credits",
            )

            e.add_field(
                name="Ultra Destiny Knot",
                value="Pass down 2-5 Random Stats to an Offspring during Breeding! Costs 30,000 Credits",
            )

            e.add_field(
                name="EV Reset",
                value="Reset EVs of your selected Pokemon with the EV reset! Costs 10,000 Credits",
            )

            e.add_field(
                name="Coin Case",
                value="Get a Coin Case and Enjoy DittoBOT's game corner! Costs 1000 Credits",
            )

            await ctx.send(embed=e)
        elif val.lower() == "stones":
            e = discord.Embed(title="Evolution Stones", color=3553600)
            e.description = "All Stones Cost 1,000 Credits!" + "\nSun stone"
            e.description += "\nDusk stone"
            e.description += "\nThunder stone"
            e.description += "\nFire stone"
            e.description += "\nIce stone"
            e.description += "\nWater stone"
            e.description += "\nDawn stone"
            e.description += "\nLeaf stone"
            e.description += "\nMoon stone"
            e.description += "\nShiny stone"
            await ctx.send(embed=e)
        elif val.lower() == "forms":
            e = discord.Embed(
                title="Buy Items to change your pokemon Forms!!", color=3553600
            )

            e.add_field(
                name="Blue orb",
                value="Buy the Blue Orb to make your Kyogre Primal! | 10,000ℳ",
            )

            e.add_field(
                name="Red orb",
                value="Buy the Red Orb to make your Groudon Primal! | 10,000ℳ",
            )

            e.add_field(
                name="Meteorite",
                value="Have your Deoxys Interact with it to Get the Forms! | 10,500ℳ",
            )

            e.add_field(
                name="N-Solarizer",
                value="Buy the N-Solarizer to Fuse your Necrozma and a Solgaleo to Get Necrozma Dusk Forme! | 9,500ℳ",
            )

            e.add_field(
                name="N-Lunarizer",
                value="Buy the N-Lunarizer to Fuse your Necrozma and a Lunala to get Necrozma Dawn Forme! | 9,500ℳ",
            )

            e.add_field(
                name="Arceus Plates",
                value="Need Arceus Plates to Transform it?, just say `/shop plates`",
            )

            e.add_field(
                name="Light Stone",
                value="Buy this to Fuse your Kyurem with Reshiram for Kyurem-white! | 9,500ℳ",
            )

            e.add_field(
                name="Dark Stone",
                value="Buy this to Fuse your Kyurem with Zekrom for Kyurem-black | 9,500ℳ",
            )

            e.add_field(
                name="Reveal Glass",
                value="Buy this to Change the forms of the forces of nature! | 10,500ℳ",
            )

            e.add_field(
                name="Zygarde cell",
                value="Get Zygarde-complete by Buying the Zygarde Cell! | 15,000 ℳ",
            )

            e.add_field(
                name="Gracidea flower",
                value="Buy the Gracidea flower to Evolve your Shaymin to Shaymin-sky! | 7,500ℳ",
            )

            e.add_field(
                name="Griseous Orb",
                value="Buy the Griseous orb to evolve Giratina to it's Origin Forme! | 10,000ℳ",
            )

            e.add_field(
                name="Prison Bottle",
                value="Buy the Prison Bottle to evolve Hoopa into Unbound Forme! | 9,500ℳ",
            )

            await ctx.send(embed=e)
        elif val.lower() == "plates":
            plates = {
                "Draco": "dragon",
                "Earth": "ground",
                "Dread": "dark",
                "Fist": "fighting",
                "Flame": "fire",
                "Icicle": "ice",
                "Insect": "bug",
                "Iron": "steel",
                "Meadow": "grass",
                "Mind": "psychic",
                "Pixie": "fairy",
                "Sky": "flying",
                "Splash": "water",
                "Spooky": "ghost",
                "Stone": "rock",
                "Toxic": "poison",
                "Zap": "electric",
            }

            e = discord.Embed(
                title="Arceus Plates!",
                description="All Plates Cost 10,000",
                color=3553600,
            )

            for plate in plates:
                type_ = plates.get(plate)
                e.add_field(
                    name=f"{plate} Plate",
                    value=f"Change Arceus and Judgement to {type_} type",
                )

            e.set_footer(
                text="Buy plates to evolve your Arceus!\nItems can also be gotten through Item Drops from spawned Pokemon!"
            )

            await ctx.send(embed=e)
        elif val.lower() == "mega":
            e = discord.Embed(
                title="Mega Stones!",
                description="Say `/buy <mega_stone>` to buy it",
                color=3553600,
            )

            e.add_field(
                name="Buy Mega Stones", value="To evolve your Pokemon to It's Mega Form"
            )

            e.add_field(
                name="Choose Between\nMega Stone - 2000 Credits \nMega stone X - 3500 Credits\nMega stone Y - 3500 Credits",
                value="To Mega your selected Pokemon",
            )

            await ctx.send(embed=e)
        elif "trade" in val.lower():
            e = discord.Embed(title="Trade Item Shop!", color=3553600)
            e.description = "All Trade Items Cost 3,000 Credits" + "\nDeep Sea Scale"
            e.description += "\n Sea Tooth"
            e.description += "\nDragon Scale"
            e.description += "\nElectirizer"
            e.description += "\nMagmarizer"
            e.description += "\nUp-grade"
            e.description += "\nKings Rock"
            e.description += "\nMetal Coat"
            e.description += "\nProtector"
            e.description += "\nPrism Scale"
            e.description += "\nRazor Fang"
            e.description += "\nRazor Claw"
            e.description += "\nOval Stone"
            e.description += "\nSachet"
            e.description += "\nWhipped Dream"
            e.description += "\nReaper cloth"
            e.description += "\nDubious disc"
            await ctx.send(embed=e)
        elif val.lower() in ("vitamins", "vitamin"):
            e = discord.Embed(
                title="Buy Vitamins!!",
                description="All Vitamins Cost 100 Credits!",
                color=3553600,
            )

            e.add_field(name="hp-up", value="`/buy vitamin hp-up` to boost your HP EV!")
            e.add_field(
                name="Protein", value="`/buy vitamin protein` to boost your Attack EV!"
            )

            e.add_field(
                name="Iron", value="`/buy vitamin iron` to boost your Defense EV!"
            )
            e.add_field(
                name="Calcium",
                value="`/buy vitamin calcium` to boost your Special Attack EV!",
            )
            e.add_field(
                name="Zinc",
                value="`/buy vitamin zinc` to boost your Special Defense EV!",
            )
            e.add_field(
                name="Carbos", value="`/buy vitamin carbos` to boost your Speed EV!"
            )
            await ctx.send(embed=e)
        elif val.lower() in ("battle items", "duel items", "battle item", "duel items"):
            items = [t["item"] for t in BATTLE_ITEMS]
            prices = [t["price"] for t in BATTLE_ITEMS]
            desc = ""
            for idx, item in enumerate(items):
                price = prices[idx]
                desc += f"**{item.capitalize().replace('-', ' ')}** - {price:,.0f}\n"
            embed = discord.Embed(
                title="Items for Battles! Buy with /buy <item>", color=3553600
            )

            pages = pagify(desc, base_embed=embed)
            await MenuView(ctx, pages).start()
        else:
            await ctx.send(
                "That is not a valid shop! To view the available shops, run `/shop`."
            )


async def setup(bot):
    await bot.add_cog(Shop(bot))
