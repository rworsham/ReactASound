import discord
import logging
import os
import asyncio
from discord import RawReactionActionEvent, ConnectionClosed
from database_util.db_util import get_sound_filename
from interactions.reaction_board import ReactionBoard

guild_locks = {}

async def _wait_until_done(vc: discord.VoiceClient):
    logging.info("[Wait] Waiting for audio to finish playing...")
    while vc.is_playing():
        await asyncio.sleep(0.5)
    logging.info("[Wait] Audio finished.")

async def connect_with_retries(voice_channel: discord.VoiceChannel, max_retries=5, delay=10):
    for attempt in range(1, max_retries + 1):
        logging.info(f"[Connect] Attempt {attempt} to connect to {voice_channel.name} ({voice_channel.guild.id})")
        try:
            vc = await voice_channel.connect()
            logging.info("[Connect] Voice handshake complete.")
            return vc
        except ConnectionClosed as cc:
            logging.error(f"[Connect] Voice websocket closed (code {cc.code})")
            if cc.code == 4006:
                logging.warning("[Connect] Session invalidated. Forcing fresh reconnect.")
                try:
                    if voice_channel.guild.voice_client:
                        await voice_channel.guild.voice_client.disconnect()
                        await asyncio.sleep(5)
                except Exception as e:
                    logging.error(f"[Connect] Error during forced disconnect: {e}")
                await asyncio.sleep(10)
            else:
                await asyncio.sleep(delay)
        except Exception as e:
            logging.error(f"[Connect] Exception connecting to voice: {e}")
            await asyncio.sleep(delay)
    logging.error("[Connect] Failed to connect after retries")
    return None

async def handle_reaction(bot: discord.Bot, payload: RawReactionActionEvent):
    logging.info(f"[Reaction] Handling reaction from user {payload.user_id} in guild {payload.guild_id}")

    if payload.guild_id is None:
        logging.warning("[Reaction] Missing guild_id.")
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        logging.warning(f"[Reaction] Guild with ID {payload.guild_id} not found.")
        return

    reaction_board = ReactionBoard(bot)
    try:
        pinned = await reaction_board.get_or_create_pinned_message(guild)
        logging.info(f"[Reaction] Found or created pinned message: {pinned.id}")
    except Exception as e:
        logging.warning(f"[Init] Error initializing pinned message: {e}")
        return

    if payload.message_id != pinned.id:
        logging.info(f"[Reaction] Ignoring reaction, message ID doesn't match pinned.")
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "reactasound":
        logging.info(f"[Reaction] Ignoring reaction, incorrect channel: {channel.name if channel else 'Unknown'}")
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        logging.info(f"[Reaction] Ignoring reaction from bot or missing member.")
        return

    emoji = str(payload.emoji)
    logging.info(f"[Reaction] Received '{emoji}' from {member.display_name} in {guild.name}")

    soundfile = await get_sound_filename(guild.id, emoji)
    if not soundfile:
        logging.info("[Reaction] No sound mapped for emoji.")
        return

    if not member.voice or not member.voice.channel:
        await channel.send(f"{member.mention} you’re not in voice!")
        logging.info(f"[Reaction] {member.display_name} is not in a voice channel.")
        return
    voice_channel = member.voice.channel

    filepath = f"sound_files/{guild.id}/{soundfile}"
    if not os.path.isfile(filepath):
        await channel.send(f"⚠️ Missing file: {soundfile}")
        logging.warning(f"[Reaction] Missing file: {soundfile}")
        return

    lock = guild_locks.setdefault(guild.id, asyncio.Lock())

    async with lock:
        vc = guild.voice_client
        connected_here = False

        if vc:
            if not vc.is_connected():
                logging.info("[Cleanup] Disconnecting stale client")
                try:
                    await vc.disconnect()
                    await asyncio.sleep(2)
                except Exception as e:
                    logging.error(f"[Cleanup] Error disconnecting stale client: {e}")
                vc = None
            elif vc.channel.id != voice_channel.id:
                logging.info("[Cleanup] Disconnecting client from wrong channel")
                try:
                    await vc.disconnect()
                    await asyncio.sleep(2)
                except Exception as e:
                    logging.error(f"[Cleanup] Error disconnecting wrong-channel client: {e}")
                vc = None

        if not vc:
            logging.info(f"[Connect] Connecting to voice channel {voice_channel.name}")
            vc = await connect_with_retries(voice_channel)
            if not vc or not vc.is_connected():
                await channel.send("❌ Could not connect to voice.")
                logging.error("[Connect] Could not connect to voice.")
                return
            connected_here = True

        await asyncio.sleep(1)

        logging.info(f"[Play] Attempting to play audio from {filepath}")
        try:
            if vc.is_playing():
                logging.info("[Play] Stopping currently playing audio.")
                vc.stop()
                await asyncio.sleep(0.2)
            audio = discord.FFmpegOpusAudio(source=filepath, options="-vn")
            vc.play(audio)
            logging.info("[Play] Playing audio.")
        except Exception as e:
            logging.error(f"[Play] Error: {e}")
            await channel.send("❌ Playback failed.")
            if connected_here:
                try:
                    await vc.disconnect()
                    await asyncio.sleep(1)
                except Exception:
                    pass
            return

        try:
            await asyncio.wait_for(_wait_until_done(vc), timeout=30)
        except asyncio.TimeoutError:
            logging.warning("[Play] Timeout, stopping audio.")
            vc.stop()

        await asyncio.sleep(1)

        try:
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, member)
            logging.info("[React] Removed user reaction.")
        except Exception as e:
            logging.warning(f"[React] Failed to remove reaction: {e}")

        if connected_here and vc.is_connected() and not vc.is_playing():
            try:
                logging.info(f"[Disconnect] Disconnecting from {voice_channel.name}")
                await vc.disconnect()
                await asyncio.sleep(1)
            except Exception as e:
                logging.warning(f"[Disconnect] Error during disconnect: {e}")
