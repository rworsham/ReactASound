import discord
import os
import logging
from dotenv import load_dotenv

from interactions.add_sound import AddSoundFlow
from interactions.remove_sound import DeleteSound
from interactions.on_reaction import handle_reaction
from interactions.reaction_board import ReactionBoard
from database_util.db_util import get_pinned_message_id
from logs.log_config import setup_logging

setup_logging()
load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

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
            "▶️ Use a reaction on the pinned message in this channel to play the corresponding sound.\n\n"
            "📢 Please use the **#botcommands** thread attached to this message for bot commands and help.\n"
        )
        message = await channel.send(setup_msg)

        thread = await message.create_thread(name="botcommands", auto_archive_duration=60)
        logging.info(f"Created thread 'botcommands' in {guild.name}")

        commands_guide = (
            "**Bot Commands Guide:**\n\n"
            "🔧 `/addsound` — Bind an emoji to a sound file by uploading it.\n"
            "🗑️ `/removesound` — Remove an emoji-to-sound binding.\n"
            "❓ Ask any questions here!\n\n"
            "Enjoy! 🎶"
        )
        await thread.send(commands_guide)

        reaction_board = ReactionBoard(bot)
        await reaction_board.update_reactions(guild)

    except discord.Forbidden:
        logging.error(f"Missing permissions to create channel, send message, or create thread in {guild.name}")
    except Exception as e:
        logging.error(f"Error during guild join setup in {guild.name}: {e}")

@bot.slash_command(description="Bind an emoji to a sound file by uploading a file in a message")
async def addsound(ctx: discord.ApplicationContext):
    handler = AddSoundFlow(bot, ctx)
    await handler.start()

@bot.slash_command(description="Remove an emoji-to-sound binding by choosing from a list")
async def removesound(ctx: discord.ApplicationContext):
    handler = DeleteSound(bot, ctx)
    await handler.start()

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await handle_reaction(bot, payload)

async def recreate_pinned_message_and_thread(guild: discord.Guild, bot: discord.Bot):
    reaction_board = ReactionBoard(bot)
    try:
        message = await reaction_board.get_or_create_pinned_message(guild)
        channel = message.channel

        all_threads = [t for t in guild.threads if t.parent_id == channel.id]

        thread = next((t for t in all_threads if t.name == "botcommands"), None)

        if not thread:
            thread = await message.create_thread(name="botcommands", auto_archive_duration=60)
            commands_guide = (
                "**Bot Commands Guide:**\n\n"
                "🔧 `/addsound` — Bind an emoji to a sound file by uploading it.\n"
                "🗑️ `/removesound` — Remove an emoji-to-sound binding.\n"
                "❓ Ask any questions here!\n\n"
                "Enjoy! 🎶"
            )
            await thread.send(commands_guide)
            logging.info(f"Created missing 'botcommands' thread in {guild.name}")

        await reaction_board.update_reactions(guild)
        logging.info(f"Recreated pinned message and ensured thread in {guild.name}")

    except Exception as e:
        logging.error(f"Failed to recreate pinned message or thread in {guild.name}: {e}")

@bot.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "reactasound":
        return

    pinned_msg_id = await get_pinned_message_id(guild.id)
    if pinned_msg_id == payload.message_id:
        logging.info(f"Pinned message deleted in {guild.name}, recreating...")
        await recreate_pinned_message_and_thread(guild, bot)

@bot.event
async def on_thread_delete(thread: discord.Thread):
    if thread.name == "botcommands" and thread.parent and thread.parent.name == "reactasound":
        guild = thread.guild
        if guild:
            logging.info(f"'botcommands' thread deleted in {guild.name}, recreating...")
            await recreate_pinned_message_and_thread(guild, bot)

@bot.event
async def on_error(event, *args, **kwargs):
    logging.exception(f"Unhandled error in event: {event}")

if __name__ == "__main__":
    try:
        bot.run(os.getenv("TOKEN"))
    except Exception as e:
        logging.exception("Bot crashed with exception:")