import discord
from discord.ext import commands
from utils.misc import MenuView


class Tutorial(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        texts = [
            [
                "DittoBOT tutorial.",
                """
                **This tutorial aims to explain the basics of DittoBOT.**
                As a new user, you might be confused by the multitude of commands in DittoBOT. This guide serves to explain the most fundamental features of DittoBOT.
                **Table of Contents:**
                    - Page 1 - **Catching Pokemon**
                    - Page 2 - **Managing your Pokemon**
                    - Page 3 - **Dueling with your Pokemon**
                    - Page 4 - **Trading your Pokemon**
                    - Page 5 - **Breeding your Pokemon**
                    - Page 6 - **Selling your Pokemon**
                    - Page 7 - **Filtering your Pokemon**
                    - Page 8 - **Nicknames and Tags**
                    - Page 9 - **Manage your inventory**
                    - Page 10 - **Credits and Redeems**
                    - Page 11 - **Other miscellaneous activities**
                    - Page 12 - **Setting up DittoBOT in your server**
                Those are the basics of DittoBOT!
                """,
            ],
            [
                "Catching pokemon",
                """
                In DittoBOT, to catch a Pokemon, you just have to say it's name after it spawns!
                **You do not need to use any command or apostrophe (`'`)!**
                
                Pokemon spawn as you chat, so keep talking to attract more spawns!
                Server owners can disable spawns in specific channels with `/spawns disable`, or make all spawns go to specific channels with `/redirect add`.

                You can also get Pokemon by __redeeming__.
                Redeems are a special currency that allow you get any Pokemon at all, from Ultra Beasts to Dittoes!
                See page 9, or `/redeem` for more.
                """,
            ],
            [
                "Managing your Pokemon",
                """
                `/p` - List the Pokemon you own.
                `/select <Pokemon #>` - Selects the specified Pokemon .
                - This number can be found using `/p`
                `/i [Pokemon #]` - View detailed information about a pokemon. If a pokemon number is not provided, defaults to your selected pokemon.
                -  Shows your Pokemon's Gender, Name, Level, Ability, Experience, Nature, Type, Egg Group, IVs, EVs, Happiness, Moves, Item, Original Trainer, Number, and Global ID
                `/release <Pokemon #>` - Release a pokemon. Released pokemon cannot be reacquired.
                - You can release multiple Pokemon at once, ex. `/release 1 12 24 48`
                `/fav add <Pokemon #>` - Mark a pokemon as a favorite to prevent it from being traded or released.
                `/fav remove <Pokemon #>` - Unmark a pokemon as a favorite.
                `/buy candy <#>` - Purchase rare candies. Each rare candy increases your Pokemon's level by 1.
                `/change nature <nature>` - Use a nature capsule to change your Pokemon's nature.
                `/add evs <amount> <stat>` - Add EVs to your selected pokemon.
                """,
            ],
            [
                "Dueling with your Pokemon",
                """
                You can challenge your friends to a Pokemon battle using the pokemon you have collected on DittoBOT!

                **Prepare for a duel**
                `/moveset` - Shows a list of moves your selected Pokemon can learn.
                `/learn <slot> <move>` - Teaches a move to your selected Pokemon in the slot selected.
                - Pokemon have 4 move slots.
                `/moves` - Shows your selected Pokemon's configured moves.
                `/party` - View your Pokemon party. Parties are used for 6v6 duels.
                `/party add <slot> <Pokemon #>` - Add the specified Pokemon to the slot selected.
                `/party remove <slot>` - Removes the Pokemon in the party slot selected.
                `/party register <party name>` - Saves your current party to be loaded again later.
                `/party list` - Shows all of your saved parties and their names.
                `/party load <party name>` Load a registered party, overriding your current party.

                **Take part in a duel**
                `/duel single <@user>` - 1v1 duel another user. This will use your selected pokemon.
                `/duel party <@user>` - 6v6 duel another user. This will use your party.
                `/duel npc` - 1v1 duel an NPC with your selected Pokemon. If you defeat them, you will gain some credits as a reward.
                """,
            ],
            [
                "Trading your Pokemon",
                """
                `/gift credits <@user> <# credits>` - Gives the mentioned user the specified amount of credits.
                `/gift pokemon <@user> <Pokemon #>` - Gives the mentioned user the specified Pokemon.
                If you want to give items to a player, you can give them a Pokemon holding that item.
                `/trade <@user>` - Sends a trade request to the mentioned user.
                - The other user player must `;accept` to begin the trade, or `;reject` to deny to trade.
                - In a trade, the following can be used to modify the trade:
                `;add c <# credits>` - Adds the specified amount of credits to the trade.
                `;remove c <# credits>` - Removes the specified amount of credits from the trade.
                `;add p <Pokemon #>` - Adds the specified Pokemon to the trade.
                `;remove p <Pokemon #>` - Removes the specified Pokemon from the trade.
                - You are able add or remove multiple Pokemon in one message, ex. `;add p 1 22 3 44 5`.
                `;confirm` - Completes the trade when both users confirm.

                __Redeems can only be traded in the DittoBOT Official Server.__
                __Make sure to check the Pokemon and their # to make sure they are trading the right thing!__
                """,
            ],
            [
                "Breeding your Pokemon",
                """
                **Requirements For Breeding**
                **1.** Pokemon must share an egg group.
                - Use `/i <Pokemon name>` to see what egg group the Pokemon is in.
                - You can search for your Pokemon based on their egg group and what Pokemon can breed with them
                `/f p egg-group <egg group>` - Find Pokemon in a specified egg group.
                `/breedswith <Pokemon #> [filter args]` - Find Pokemon that can breed with the specified Pokemon.
                - Supports adding additional filter arguments. See page 7 for more information.
                **2.** Pokemon must be deformed before being able to breed
                - Use `/deform` with a Pokemon selected to deform it.
                **3.** You need to have an available Daycare Space.
                - Use `/bal` to see how many Daycare Spaces you have. 
                - Use `/buy daycare <#>` to buy additional spaces.

                **How to Breed**
                `/breed <male Pokemon #> <female Pokemon #>` - Breed two Pokemon. Pokemon must be in the same egg group to breed.
                - ex. `/breed 12 43`
                - Ditto can breed with any gender of Pokemon that is not in the undiscovered egg group (legendary, mythical, baby Pokemon, and another Ditto). 
                - Manaphy is an exception which will produce Phione.

                `/f p cooldown` - View the breeding cooldown on your female Pokemon.
                `/f p name egg` - View your unhatched eggs.
                `/sell egg <Pokemon #>` - Sell an unhatched egg.
                """,
            ],
            [
                "Selling your Pokemon",
                """
                `/m add <Pokemon #> <# credits>` - Lists your Pokemon on the market for the amount specified.
                - New market listings require a 15% deposit.
                - Deposit is refunded upon a successful sale. If you cancel your listing, you will lose your deposit.
                `/buy item market space` - Purchases an additional market space.
                `/m remove <Market ID>` - Removes your Pokemon from the market.
                - You will lose your deposit if you remove your pokemon from the market.
                `/m i <Market ID>` - View the specified marketed Pokemon's stats and price.
                `/m buy <Market ID>` - Purchase the specified Pokemon from the market.
                `/f m <filter args>`  - Searches the market for Pokemon.
                - Supports adding additional filter arguments. See page 7 for more information.
                `/f m owned` - Views the Pokemon you have listed in the market with the market IDs.
                """,
            ],
            [
                "Filtering your Pokemon",
                """
                `/f p <filter args>` - Filter your owned Pokemon.
                `/f m <filter args>` - Filter the market listings.

                **Basic Filter Arguments:**
                `name <names...>`, `evo <names...> `, `nickname <nick>`,
                `type <types...>`, `egg-group <egg groups...>`, `item <items...>`,
                `nature <natures...>`, `tags <tags...>`, `hidden-power <type>`, 
                `skins [skins...]`, `ot [user_id]`,
                `male`, `female`, `genderless`, `starter`, `legend`, `ultra`, `pseudo`,
                `alola`, `galar`, `shiny`, `radiant`, `regular`, `fav`, `cooldown`

                **Advanced Filter Arguments:**
                `level <level>`, `atkiv <iv>`, `defiv <iv>`, `spatkiv <iv>`, `spdefiv <iv>`, `speediv <iv>`, `hpiv <iv>`
                These arguments support `level 50` to specify an exact value or `level > 50` to specify a relative value.

                **Sorting Arguments:**
                `iv [direction]`, `ev [direction]`, `name [direction]`, `level [direction]`
                These arguments can be passed with an optional direction of either `ascending` or `decending` to specify the direction to sort.

                **Market Arguments:**
                `owned`, `id [direction]`, `price [direction or value]`
                The `price` argument can be used either to filter or to sort, depending on how it is used: 
                `price ascending`
                - Listings, from low price to high price.
                `price < 10000`
                - Listings that cost less than 10,000 credits.

                **Arguments can be combined using `&`, `|`, and `!`:**
                `/f p name pikachu | male`
                - Filters for any pokemon that are either pikachus or are male.
                `/f p type fire & type ghost`
                - Filters for any pokemon that are duel type fire ghost.
                `/f p !type fire`
                - Filters for any pokemon that are not a fire type.
                `/f p male & iv`
                - Filters for male pokemon, sorted by iv.
                `/f p egg amorphous & (male | (!evo mimikyu & female))`
                - Filters for all pokemon in the amorphous egg group, with female pokemon in the mimikyu evolution line excluded.
                """,
            ],
            [
                "Nicknames and Tags",
                """
                You can add a nickname or tag to your Pokemon to help highlight your favorite Pokemon, or add another level of organization to your collection.

                The Pokemon you want to nickname needs to be selected by using `/select <Pokemon #>`
                Then you can use `/nick <nickname>` to apply a nickname.
                You can search for your Pokemon by using `/f p nick <nickname>`

                `/tags add <tag> <Pokemon #s>` - Add a tag to one or more Pokemon.
                - Tags cannot have a space.
                - You can add multiple Pokemon at once, ex. `/tags add Kermit 1 22 3 44 5`.
                `/tags remove <tag> <Pokemon #s>` - Removes a tag from one or more Pokemon.
                `/tags list <Pokemon #>` - Show what tags a Pokemon has been assigned.
                `/f p tag <tag>` - Filter pokemon that have been given a certain tag.
                """,
            ],
            [
                "Manage your inventory",
                """
                The shop is an area where you can spend your credits on various items for your Pokemon.
                `/bag` - Opens up your inventory to show what items you have.
                `/shop` - Shows what stores are available.
                `/shop <shop name>` - Opens the specified store to view items it sells.
                `/buy item <item name>` - Purchases the specified item for your selected Pokemon.
                `/sell item <item name>` - Sell an item from your bag for 65% of its shop value.
                `/equip <item name>` - Gives the specified item to your selected Pokemon. 
                `/unequip` - Removes your Pokemon's held item and returns it to your bag.
                `/drop` - COMPLETELY DELETES the item held by your selected Pokemon.
                """,
            ],
            [
                "Credits and Redeems",
                """
                In DittoBOT, you have two major currencies, Credits and Redeems.
                `/bal` - Shows your Credits, Redeems, EV points, Upvote Points and your Fishing Rod.
               
                **Credits**
                Credits are the main currency of DittoBOT that you can use to buy most things.
                You can obtain credits by:
                **1.** Upvoting the bot and claiming rewards
                - Use `/vote` for links to upvote DittoBOT.
                - Voting gives you upvote points.
                - Use `/claim` when you have 5 upvote points to get some credits.
                **2.** Trading and selling Pokemon
                - See pages 4 and 6 for more information.
                **3.** Dueling NPC trainers
                - See page 11 for more information.
                **4.** Completing missions
                - See page 11 for more information.
                **5.** Opening chests
                - Chests are found randomly from catching Pokemon or fishing. They can also be bought for credits or redeems.
                **6.** Donating to the bot
                - Use `/donate` to obtain a link. You can donate via Patreon or Paypal.
                - Donations through paypal give **3 redeems** and **2000 credits** per $1 USD donated.
                - Patreon rewards can be claimed monthly using `/predeem`.

                **Redeems**
                Redeems are a special currency that can be used to purchase items that credits can't.
                You can obtain redeems by:
                **1.** Upvoting the bot and claiming rewards
                - Use `/vote` for links to upvote DittoBOT.
                - Voting gives you upvote points.
                - Use `/claim` when you have 5 upvote points to get some credits.
                **2.** Purchasing redeems with credits using `/buy redeems`
                - You can buy 15 redeems per week this way, at 60,000 credits per redeem.
                **3.** Opening chests
                - Chests are found randomly from catching Pokemon or fishing. They can also be bought for credits or redeems.
                **4.** Donating to the bot
                - Use `/donate` to obtain a link. You can donate via Patreon or Paypal.
                - Donations through paypal give **3 redeems** and **2000 credits** per $1 USD donated.
                - Patreon rewards can be claimed monthly using `/predeem`.
                """,
            ],
            [
                "**Other miscellaneous activities**",
                """
                `/duel npc` - 1v1 duel an NPC with your selected Pokemon. If you defeat them, you will gain some credits as a reward.
                `/fish` - Guess the water Pokemon's name to catch it.
                - You will need a fishing rod by purchasing one from the shop using `/shop rods`.
                """,
            ],
            [
                "Setting up DittoBOT in your server",
                """
                **Note**: Only the owner of the server and users with the `manage_messages` permission can configure DittoBOT in a server.
                `[channel]` Defaults to the channel it is executed in.

                
                **Managing Spawns**
                `/spawns disable [channel]` - Prevents messages in the provided channel from triggering spawns.
                `/spawns enable [channel]` - Allows messages in the provided channel to trigger spawns.
                
                `/redirect add [channel]` - Adds the provided channel to the redirect list.
                `/redirect remove [channel]` - Removes the provided channel from the redirect list.
                `/redirect clear` - Clear all channels from the redirect list.
                If any channels exist on the redirect list, all spawns will be redirected to a random redirect channel instead of being sent in the channel they were triggered from.
                
                `/spawns check` - Lists the channels in your server, and shows which ones are set up to allow spawns.

                
                **Managing Commands**
                `/commands disable [channel]` - Prevents commands from being used in the provided channel.
                `/commands enable [channel]` - Allows commands to be used in the provided channel.
                
                **Note**: Discord provides a permissions system that allows server owners to modify command permissions per role, channel, and member. See [the blog post](https://discord.com/blog/slash-commands-permissions-discord-apps-bots) for more information.

                
                **Other Commands**
                `/spawns small` - Toggle the size of the pokemon image in a spawn message between a large and small version.
                `/auto delete` - Toggle spawn messages getting deleted when the pokemon despawns.
                `/auto pin` - Toggle automatically pinning rare spawns when they are caught.
                `/silence server` - Silence level up messages across the entire server.
                """,
            ],
        ]
        self.pages = []
        for help_texts in texts:
            embed = discord.Embed(color=bot.get_random_color())
            embed.title = help_texts[0]
            embed.description = help_texts[1]
            self.pages.append(embed)

    @commands.hybrid_command()
    async def tutorial(self, ctx):
        """Opens a brief tutorial providing basic information."""
        await MenuView(ctx, self.pages).start()

    @commands.hybrid_command()
    async def help(self, ctx):
        """Opens a brief tutorial providing basic information."""
        await MenuView(ctx, self.pages).start()


async def setup(bot):
    await bot.add_cog(Tutorial(bot))
