import discord
import os
from dotenv import load_dotenv

load_dotenv()
bot = discord.Bot()

#TBD

bot.run(os.getenv('TOKEN'))