import discord
import os
import logging
from dotenv import load_dotenv

from interactions.add_sound import AddSoundFlow
from interactions.remove_sound import RemoveSoundModal
from logs.log_config import setup_logging

setup_logging()
load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    logging.info(f'Bot is ready! Logged in as {bot.user}')

@bot.event
async def on_guild_join(guild):
    existing = discord.utils.get(guild.text_channels, name="reactasound")
    if existing:
        logging.info(f"'reactasound' channel already exists in {guild.name}")
        return

    try:
        channel = await guild.create_text_channel("reactasound", reason="ReactASound bot setup")
        logging.info(f"Created 'reactasound' channel in {guild.name}")

        setup_msg = (
            "👋 Welcome to **ReactASound**!\n\n"
            "🔧 Use `/addsound` to create your mappings.\n"
            "🔧 Use `/removesound` to create your mappings.\n"
            "📜 Use `/list` to see all bindings.\n"
            "▶️ Use a reaction on any message in this channel to play the corresponding sound."
        )
        await channel.send(setup_msg)

    except discord.Forbidden:
        logging.error(f"Missing permissions to create channel or send message in {guild.name}")
    except Exception as e:
        logging.error(f"Error creating channel or sending setup prompt in {guild.name}: {e}")

@bot.slash_command(description="Bind an emoji to a sound file by uploading a file in a message")
async def addsound(ctx: discord.ApplicationContext):
    handler = AddSoundFlow(bot, ctx)
    await handler.start()

@bot.slash_command(description="Remove an emoji-to-sound binding via modal")
async def removesound(ctx: discord.ApplicationContext):
    modal = RemoveSoundModal(guild_id=ctx.guild.id, user_id=ctx.author.id)
    await ctx.send_modal(modal)

@bot.event
async def on_error(event, *args, **kwargs):
    logging.exception(f"Unhandled error in event: {event}")


if __name__ == "__main__":
    try:
        bot.run(os.getenv("TOKEN"))
    except Exception as e:
        logging.exception("Bot crashed with exception:")