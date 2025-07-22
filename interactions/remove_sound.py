import discord
import logging
import asyncio
import os

from database_util.db_util import get_all_emojis_for_guild
from database_util.models import EmojiSoundMap
from sqlalchemy import select, delete
from database_util.db import Session
from interactions.reaction_board import ReactionBoard


class DeleteSound:
    def __init__(self, bot: discord.Bot, ctx: discord.ApplicationContext):
        self.bot = bot
        self.ctx = ctx
        self.guild = ctx.guild
        self.guild_id = ctx.guild.id
        self.user_id = ctx.author.id

    async def start(self):
        member: discord.Member = self.ctx.author
        if not member.guild_permissions.administrator:
            await self.ctx.respond("🚫 Only server administrators can delete sound mappings.", ephemeral=True)
            return

        emojis = await get_all_emojis_for_guild(self.guild_id)
        if not emojis:
            await self.ctx.respond("⚠️ No sound mappings found in this server.", ephemeral=True)
            return

        emoji_list = "\n".join(f"{idx + 1}. {emoji}" for idx, emoji in enumerate(emojis))
        await self.ctx.respond(
            f"🗑️ **Current emoji-sound mappings:**\n\n{emoji_list}\n\n"
            "Please reply with the number of the emoji you'd like to delete.",
            ephemeral=True
        )

        def check(message: discord.Message):
            return (
                message.author.id == self.user_id and
                message.channel.id == self.ctx.channel.id and
                message.content.isdigit() and
                1 <= int(message.content) <= len(emojis)
            )

        try:
            message = await self.bot.wait_for("message", check=check, timeout=60)
            selected_idx = int(message.content) - 1
            emoji_to_delete = emojis[selected_idx]

            async with Session() as session:
                result = await session.scalar(
                    select(EmojiSoundMap.sound_filename).where(
                        EmojiSoundMap.guild_id == self.guild_id,
                        EmojiSoundMap.emoji == emoji_to_delete
                    )
                )

                if result:
                    filename = result
                    await session.execute(
                        delete(EmojiSoundMap).where(
                            EmojiSoundMap.guild_id == self.guild_id,
                            EmojiSoundMap.emoji == emoji_to_delete
                        )
                    )
                    await session.commit()

                    file_path = os.path.join("sound_files", str(self.guild_id), filename)
                    try:
                        os.remove(file_path)
                        logging.info(f"Deleted sound file: {file_path}")
                    except FileNotFoundError:
                        logging.warning(f"File not found when trying to delete: {file_path}")
                    except Exception as e:
                        logging.error(f"Failed to delete file: {file_path} — {e}")
                else:
                    await message.reply("❌ Could not find a sound mapping to delete.", mention_author=False)
                    return

            await message.reply(f"✅ Deleted mapping and removed `{filename}` for {emoji_to_delete}.", mention_author=False)

            reaction_board = ReactionBoard(self.bot)
            await reaction_board.update_reactions(self.guild)

        except asyncio.TimeoutError:
            await self.ctx.followup.send("⌛ Timeout! No input received. Please try again.", ephemeral=True)
        except Exception as e:
            logging.exception("Error during deletion of sound mapping")
            await self.ctx.followup.send("❌ There was an error processing your deletion. Please try again.", ephemeral=True)
