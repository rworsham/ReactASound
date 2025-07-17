import discord
import logging
from database_util.db import Session
from database_util.models import EmojiSoundMap

class AddSoundModal(discord.ui.Modal):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(title="Add Sound Binding")
        self.guild_id = guild_id
        self.user_id = user_id

        self.add_item(discord.ui.InputText(label="Emoji (e.g. 🔊)", placeholder="🔊"))
        self.add_item(discord.ui.InputText(label="Sound filename (e.g. sound.mp3)", placeholder="sound.mp3"))

    async def callback(self, interaction: discord.Interaction):
        emoji = self.children[0].value.strip()
        sound_filename = self.children[1].value.strip()

        logging.info(f"User {self.user_id} is adding binding '{emoji}' -> '{sound_filename}' in guild {self.guild_id}")

        try:
            async with Session() as session:
                new_map = EmojiSoundMap(
                    guild_id=self.guild_id,
                    emoji=emoji,
                    sound_filename=sound_filename,
                    uploader_id=self.user_id
                )
                session.add(new_map)
                await session.commit()

            await interaction.response.send_message(f"✅ Bound {emoji} to {sound_filename}", ephemeral=True)
            logging.info(f"Successfully added binding for {emoji} in guild {self.guild_id}")

        except Exception as e:
            logging.error(f"Error adding sound binding for guild {self.guild_id}: {e}")
            await interaction.response.send_message("❌ Failed to add sound binding.", ephemeral=True)
