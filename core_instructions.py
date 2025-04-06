from typing import Final
import os
from dotenv import load_dotenv
from discord import Intents, Interaction
from discord.ext import commands
from responses import retrieve_weather
from discord import app_commands
from discord.ui import View, Button
import random
import discord

#### Wallet Management for Blackjack/Future Games"
import json
WALLET = "wallets.json"

def load_wallets():
    if not os.path.exists(WALLET):
        return {}
    with open(WALLET, "r") as f:
        return json.load(f)
    
def save_wallets(wallets):
    with open(WALLET, "w") as f:
        json.dump(wallets, f, indent=4)

def get_balance(user_id):
    wallets = load_wallets()
    return wallets.get(str(user_id), 2000) 

def update_balance(user_id, amount):
    wallets = load_wallets()
    uid = str(user_id)
    wallets[uid] = wallets.get(uid, 2000) + amount
    save_wallets(wallets)
####################################################

#STEP 0: LOAD OUR TOKEN FROM SOMEWHERE SAFE

# Load environment variables from a .env file int o the program's environment
load_dotenv()

# Get the value of the "DISCORD_TOKEN" env. variable
# and assign it to the TOKEN variable. The Final[str] type hint indicates that
# TOKEN should not be reassigned and is expected to be of type str
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
# print(TOKEN)   (remove for debugging purposes, not necessary though)
# Get the value of the "WEATHER_API_KEY" env. variable
WEATHER_API_KEY: Final[str] = os.getenv('WEATHER_API_KEY')

# Step 1: BOT SETUP

intents: Intents = Intents.default()
intents.message_content = True #NOQA
# Maintain the prefix "." for old command without slash
bot = commands.Bot(command_prefix=".", intents=intents)

# ==========================================================================================================
# (WEATHER SECTION)
# the inclusion of defining a slash command for weather
@bot.tree.command(name="weather", description="Get Current Weather Information for a City")
async def weather(interaction: Interaction, city: str):
  #  """Handling the /weather slash command process here."""
    try:
        response = retrieve_weather(city, WEATHER_API_KEY)
        await interaction.response.send_message(response)
    except Exception as e:
        print(f'Error Retrieving Weather: {e}')
        await interaction.response.send_message("Sorry, I could not get the weather. Please try again.")

# ==========================================================================================================
# ==========================================================================================================
# Blackjack Section
# Basic game and commands for SINGLE player only

# Cards with basic values (A=11, kings, queens, joker = 10, and normal #s)
def draw_card():
    cards = {
        'A': 11, '2': 2, '3': 3, '4': 4, '5': 5,
        '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
        'J': 10, 'Q': 10, 'K': 10
    }
    card = random.choice(list(cards.keys()))
    return card, cards[card]

# sum basic function used to find the total value of hand
# check to make sure values don't exceed 21
def hand_value(hand):
    value = sum(card[1] for card in hand)
    aces = sum(1 for card in hand if card[0] == 'A')
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

# convert the hand list into a string that is easily readable
def format_hand(hand):
    return " ".join(card[0] for card in hand)

# Class to manage 
class BlackjackView(View):
    def __init__(self, player_hand, dealer_hand, interaction, bet):
        super().__init__()
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.interaction = interaction
        self.bet = bet
        self.user_id = interaction.user.id
    # when turn ends, prevent user from using this
    async def disable_all(self):
        for child in self.children:
            child.disabled = True
        await self.interaction.edit_original_response(view=self)

    # button for Hit
    @discord.ui.button(label = "Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: Interaction, button: Button):

        # prevent other users from pressing the button LOL
        if interaction.user.id != self.user_id:
            return
        
        card = draw_card()
        self.player_hand.append(card)

        value = hand_value(self.player_hand)
        hand_text = format_hand(self.player_hand)

        # needed to insert this after users were having issues with games
        # going over...
        if value > 21:
            await self.disable_all()
            await interaction.response.edit_message(content=f"💥 You busted with {hand_text} (**{value}**)! You lost ${self.bet}.")
        else:
            await interaction.response.edit_message(content=f"🃏 Your hand: {hand_text} (**{value}**)", view=self)

    @discord.ui.button(label = "Stand", style = discord.ButtonStyle.secondary)
    async def stand(self, interaction: Interaction, button: Button):

        if interaction.user.id != self.user_id:
            return

        await self.disable_all()

        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_card())

        player_total = hand_value(self.player_hand)
        dealer_total = hand_value(self.dealer_hand)

        dealer_text = format_hand(self.dealer_hand)
        player_text = format_hand(self.player_hand)

        # conditionals in place for determining winner of both sides
        # Update user's balances after each game
        if dealer_total > 21 or player_total > dealer_total:
            # update user balance
            update_balance(self.user_id, self.bet * 2)
            result = f"✅ You win ${self.bet * 2}!"
        elif dealer_total == player_total:
            update_balance(self.user_id, self.bet)
            result = f"🤝 It's a tie. You got your ${self.bet} back."
        else:
            result = f"❌ Dealer wins. You lost ${self.bet}."

        await interaction.response.edit_message(
            content=(
                f"🃏 Your hand: {player_text} (**{player_total}**)\n"
                f"🧑‍💼 Dealer hand: {dealer_text} (**{dealer_total}**)\n\n"
                f"{result}"
            ),
            view=self
        )

# slash command to begin the blackjack game
# User must bet >$1 and greater than their 
@bot.tree.command(name = "blackjack", description = "Play Blackjack with a bet")
@app_commands.describe(bet = "Amount to bet (from your wallet)")
async def blackjack(interaction: Interaction, bet: int):
    user_id = interaction.user.id
    balance = get_balance(user_id)

    if bet < 1:
        await interaction.response.send_message("Your bet must be at least $1.", ephemeral=True)
        return
    if bet > balance:
        await interaction.response.send_message(f"Not enough funds. You have ${balance}.", ephemeral=True)
        return

    # update wallet balance 
    update_balance(user_id, -bet)

    player_hand = [draw_card(), draw_card()]
    dealer_hand = [draw_card()]

    value = hand_value(player_hand)
    hand_text = format_hand(player_hand)

    # return the game state to the player
    view = BlackjackView(player_hand, dealer_hand, interaction, bet)
    await interaction.response.send_message(
        f"💰 Bet: ${bet}\n🃏 Your hand: {hand_text} (**{value}**)", view=view
    )

# (ADMIN SECTION)

#                                           =Shutdown Command=
@bot.tree.command(name="shutdown", description="Shutdown the bot. (Admin Use only) CAUTION: Will shut down other instances.")
async def shutdown(interaction: Interaction):
    """
    Shuts down the bot if the user has Administrator or Manage Channels permissions.
    """
    # DEBUG: Log user permissions
    print(f'User {interaction.user} Permissions: {interaction.user.guild_permissions}')

    # Acknowledge the interaction immediately
    # Discord  requires a response to slash commands within 3 secs
    # Allows Discord bot to avoid "application not responding" error
    await interaction.response.defer()

    # Check if the user has the required permissions
    if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels:
        await interaction.followup.send("Shutting down.")
        await bot.close()  # Shutdown the bot
    else:
        # DEBUG: Which permission failed
        print(f'User {interaction.user} lacks required permissions: Administrator or Manage Channels')

        # Find roles with either Administrator or Manage Channels permission to alert admin team
        # Check all server roles for roles with these permitted permissions
        eligible_roles = [
            role for role in interaction.guild.roles
            if role.permissions.administrator or role.permissions.manage_channels
        ]

        if eligible_roles:
            # Mention all roles with the permissions
            # Provided a message for the roles and mention the eligbile_roles (with permissions)
            role_mentions = ", ".join([role.mention for role in eligible_roles])
            alert_message = (
                f"🚨 **Unauthorized Shutdown Attempt** 🚨\n"
                f" "
                f"User {interaction.user.mention} tried to shut down the bot.\n"
                f" "
                f" "
                f"Alerting: {role_mentions}"
            )

            # Send alert to the channel
            # Notify the user and alert the eligible roles in channel where shutdown started
            await interaction.followup.send(
                f"You don't have permission to shut me down! Alerting: {role_mentions}"
            )
            await interaction.channel.send(alert_message)
        else:
            # If no roles were found with the required permissions
            # Inform user
            # ALso if no roles were found
            await interaction.followup.send(
                "You don't have permission to shut me down. No roles to alert were found."
            )
# ==========================================================================================================


# ==========================================================================================================
# (STARTUP SECTION)
@bot.event
async def on_ready():
    try:
        await bot.tree.sync() # sync all the slash commands
        print(f'Bot is ready and logged in as {bot.user}')
    except Exception as e:
        print(f'Error syncing commands: {e}')
# ==========================================================================================================

# ==========================================================================================================
# (MAIN ENTRY POINT)
def main():
    bot.run(TOKEN)

if __name__ == '__main__':
    main()
# ==========================================================================================================
