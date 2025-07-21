import os
import logging
import discord
from discord import RawReactionActionEvent

from database_util.db_util import get_sound_filename
from interactions.reaction_board import ReactionBoard

async def handle_reaction(bot: discord.Bot, payload: RawReactionActionEvent):
    if payload.guild_id is None:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    reaction_board = ReactionBoard(bot)
    try:
        pinned_message = await reaction_board.get_or_create_pinned_message(guild)
    except Exception as e:
        logging.warning(f"Could not get pinned message in {guild.name}: {e}")
        return

    if payload.message_id != pinned_message.id:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "reactasound":
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    emoji = str(payload.emoji)
    guild_id = payload.guild_id

    sound_filename = await get_sound_filename(guild_id, emoji)
    if not sound_filename:
        logging.info(f"No sound mapped for emoji {emoji} in guild {guild.name}")
        return

    voice_state = member.voice
    if not voice_state or not voice_state.channel:
        await channel.send(f"{member.mention} you're not in a voice channel!")
        return

    voice_channel = voice_state.channel

    try:
        vc_client = await voice_channel.connect()
        filepath = f"sound_files/{guild_id}/{sound_filename}"
        if not os.path.isfile(filepath):
            await channel.send(f"⚠️ Sound file not found: `{sound_filename}`")
            await vc_client.disconnect()
            return

        vc_client.play(discord.FFmpegPCMAudio(source=filepath))
        while vc_client.is_playing():
            await discord.utils.sleep_until(
                discord.utils.utcnow() + discord.utils.timedelta(seconds=0.5)
            )
        await vc_client.disconnect()

        message = await channel.fetch_message(payload.message_id)
        await message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))

    except discord.ClientException:
        await channel.send("⚠️ I'm already connected to a voice channel.")
    except Exception as e:
        logging.exception("Failed to play sound:")
        await channel.send("❌ An error occurred trying to play the sound.")
