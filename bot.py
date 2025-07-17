import discord
import os
import logging
from dotenv import load_dotenv

from forms.add_sound_form import AddSoundModal
from forms.remove_sound_form import RemoveSoundModal
from logs.log_config import setup_logging

setup_logging()
load_dotenv()

bot = discord.Bot()

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
            "🔧 Use `/addsound to create your mappings.\n"
            "🔧 Use `/removesound to create your mappings.\n"
            "📜 Use `/list` to see all bindings.\n"
            "▶️ Use a reaction on any message in this channel to play the corresponding sound."
        )
        await channel.send(setup_msg)

    except discord.Forbidden:
        logging.error(f"Missing permissions to create channel or send message in {guild.name}")
    except Exception as e:
        logging.error(f"Error creating channel or sending setup prompt in {guild.name}: {e}")

@bot.slash_command(description="Bind an emoji to a sound file via modal")
async def addsound(ctx: discord.ApplicationContext):
    modal = AddSoundModal(guild_id=ctx.guild.id, user_id=ctx.author.id)
    await ctx.send_modal(modal)

@bot.slash_command(description="Remove an emoji-to-sound binding via modal")
async def removesound(ctx: discord.ApplicationContext):
    modal = RemoveSoundModal(guild_id=ctx.guild.id, user_id=ctx.author.id)
    await ctx.send_modal(modal)

bot.run(os.getenv('TOKEN'))