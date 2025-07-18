import discord
import logging
import os
import asyncio
import re
from database_util.db_util import add_or_update_mapping

EMOJI_REGEX = re.compile(
    r'(<a?:\w+:\d+>)|([\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF])'
)

class AddSoundFlow:
    def __init__(self, bot: discord.Bot, ctx: discord.ApplicationContext):
        self.bot = bot
        self.ctx = ctx
        self.guild_id = ctx.guild.id
        self.user_id = ctx.author.id

    async def start(self):
        await self.ctx.respond(
            "📥 Please send a message with the emoji you want to bind and attach *one* sound file to that message.",
            ephemeral=True
        )

        def check(message: discord.Message):
            if message.author.id != self.user_id:
                return False
            if message.channel.id != self.ctx.channel.id:
                return False
            if len(message.attachments) != 1:
                return False
            if not self.extract_emoji(message.content):
                return False
            return True

        try:
            message = await self.bot.wait_for("message", check=check, timeout=300)  # 5 minutes timeout

            emoji = self.extract_emoji(message.content)
            if not emoji:
                await message.reply("❌ Could not find a valid emoji in your message.", mention_author=False)
                return

            attachment = message.attachments[0]

            guild_dir = os.path.join("sound_files", str(self.guild_id))
            os.makedirs(guild_dir, exist_ok=True)
            save_path = os.path.join(guild_dir, attachment.filename)

            await attachment.save(save_path)
            logging.info(f"Saved uploaded file to {save_path}")

            await add_or_update_mapping(
                guild_id=self.guild_id,
                emoji=emoji,
                filename=attachment.filename,
                uploader_id=self.user_id
            )

            await message.reply(
                f"✅ Successfully bound {emoji} to `{attachment.filename}`!",
                mention_author=False
            )

        except asyncio.TimeoutError:
            await self.ctx.followup.send(
                "⌛ Timeout! You took too long to upload the sound file. Please try the command again.",
                ephemeral=True
            )
        except Exception as e:
            logging.exception("Error during addsound file upload")
            await self.ctx.followup.send(
                "❌ There was an error processing your upload. Please try again.",
                ephemeral=True
            )

    def extract_emoji(self, text: str) -> str | None:
        match = EMOJI_REGEX.search(text)
        if not match:
            return None
        custom_emoji = match.group(1)
        unicode_emoji = match.group(2)
        return custom_emoji if custom_emoji else unicode_emoji
