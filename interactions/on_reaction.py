import os
import logging
import asyncio
import discord
from discord import RawReactionActionEvent, ConnectionClosed

from database_util.db_util import get_sound_filename
from interactions.reaction_board import ReactionBoard

guild_locks = {}

async def _wait_until_done(vc: discord.VoiceClient):
    while vc.is_playing():
        await asyncio.sleep(0.5)

async def connect_with_retries(voice_channel, text_channel, guild, max_retries=5, delay=10):
    for attempt in range(1, max_retries + 1):
        logging.info(f"[Connect] Attempt {attempt} to connect to {voice_channel.name}")

        vc = guild.voice_client
        if vc:
            if vc.is_connected():
                if vc.channel.id != voice_channel.id:
                    logging.info(f"[Connect] Disconnecting from wrong channel {vc.channel.name}")
                    try:
                        await vc.disconnect(force=True)
                        guild.voice_client = None
                        await asyncio.sleep(3)
                    except Exception as e:
                        logging.error(f"[Connect] Error disconnecting stale client: {e}")
                else:
                    logging.info("[Connect] Already connected to correct channel")
                    return vc
            else:
                logging.info("[Connect] Disconnecting stale voice client")
                try:
                    await vc.disconnect(force=True)
                    guild.voice_client = None
                    await asyncio.sleep(3)
                except Exception as e:
                    logging.error(f"[Connect] Error disconnecting stale client: {e}")

        try:
            logging.info("Connecting to voice...")
            vc = await voice_channel.connect(reconnect=True)
            logging.info("[Connect] Voice handshake complete.")
            return vc

        except ConnectionClosed as cc:
            logging.error(f"[Connect] Voice websocket closed (code {cc.code})")
            if cc.code == 4006:
                logging.warning("[Connect] Session invalidated. Forcing fresh reconnect.")
                if vc:
                    try:
                        await vc.disconnect(force=True)
                        guild.voice_client = None  # reset voice client state
                        await asyncio.sleep(5)
                    except Exception as e:
                        logging.error(f"[Connect] Error during forced disconnect: {e}")
                await asyncio.sleep(10)  # longer delay on 4006
            else:
                await asyncio.sleep(delay)
        except Exception as e:
            logging.error(f"[Connect] Exception connecting to voice: {e}")
            await asyncio.sleep(delay)

    logging.error("[Connect] Failed to connect after retries")
    return None

async def handle_reaction(bot: discord.Bot, payload: RawReactionActionEvent):
    if payload.guild_id is None:
        return
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    reaction_board = ReactionBoard(bot)
    try:
        pinned = await reaction_board.get_or_create_pinned_message(guild)
    except Exception as e:
        logging.warning(f"[Init] {e}")
        return
    if payload.message_id != pinned.id:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or channel.name != "reactasound":
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    emoji = str(payload.emoji)
    logging.info(f"[Reaction] '{emoji}' from {member.display_name} in {guild.name}")

    soundfile = await get_sound_filename(guild.id, emoji)
    if not soundfile:
        logging.info("[Reaction] No sound mapped.")
        return

    if not member.voice or not member.voice.channel:
        await channel.send(f"{member.mention} you’re not in voice!")
        return
    voice_channel = member.voice.channel

    filepath = f"sound_files/{guild.id}/{soundfile}"
    if not os.path.isfile(filepath):
        await channel.send(f"⚠️ Missing file: {soundfile}")
        return

    lock = guild_locks.setdefault(guild.id, asyncio.Lock())

    async with lock:
        vc = guild.voice_client
        connected_here = False

        if vc:
            if not vc.is_connected():
                logging.info("[Cleanup] Disconnect stale client")
                try:
                    await vc.disconnect(force=True)
                    await asyncio.sleep(2)
                except Exception as e:
                    logging.error(f"[Cleanup] Error disconnecting stale client: {e}")
                vc = None
            elif vc.channel.id != voice_channel.id:
                logging.info("[Cleanup] Disconnect wrong-channel client")
                try:
                    await vc.disconnect(force=True)
                    await asyncio.sleep(2)
                except Exception as e:
                    logging.error(f"[Cleanup] Error disconnecting wrong-channel client: {e}")
                vc = None

        if not vc:
            vc = await connect_with_retries(voice_channel, channel, guild)
            if not vc or not vc.is_connected():
                await channel.send("❌ Could not connect to voice.")
                return
            connected_here = True

        await asyncio.sleep(1)

        # Play audio
        logging.info(f"[Play] {filepath}")
        try:
            if vc.is_playing():
                vc.stop()
                await asyncio.sleep(0.2)
            audio = discord.FFmpegPCMAudio(source=filepath, options="-vn")
            vc.play(audio)
        except Exception as e:
            logging.error(f"[Play] Error: {e}")
            await channel.send("❌ Playback failed.")
            if connected_here:
                try:
                    await vc.disconnect(force=True)
                    await asyncio.sleep(1)
                except Exception:
                    pass
            return

        try:
            await asyncio.wait_for(_wait_until_done(vc), timeout=30)
        except asyncio.TimeoutError:
            logging.warning("[Play] Timeout, stopping")
            vc.stop()

        await asyncio.sleep(1)

        try:
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, member)
        except Exception as e:
            logging.warning(f"[React] Remove failed: {e}")

        if connected_here and vc.is_connected():
            try:
                logging.info(f"[Disconnect] {voice_channel.name}")
                await vc.disconnect(force=True)
                await asyncio.sleep(1)
                if vc.is_connected():
                    logging.warning("[Disconnect] Still connected!")
            except Exception as e:
                logging.warning(f"[Disconnect] Error: {e}")
