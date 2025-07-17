import discord
import logging
from database_util.models import EmojiSoundMap
from database_util.db import Session

class RemoveSoundModal(discord.ui.Modal):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(title="Remove Sound Binding")
        self.guild_id = guild_id
        self.user_id = user_id

        self.add_item(discord.ui.InputText(label="Emoji to unbind (e.g. 🔊)", placeholder="🔊"))

    async def callback(self, interaction: discord.Interaction):
        emoji = self.children[0].value.strip()
        logging.info(f"User {self.user_id} requested to remove binding for '{emoji}' in guild {self.guild_id}")

        try:
            async with Session() as session:
                await session.execute(
                    EmojiSoundMap.__table__.delete().where(
                        (EmojiSoundMap.guild_id == self.guild_id) &
                        (EmojiSoundMap.emoji == emoji)
                    )
                )
                await session.commit()

            logging.info(f"Successfully removed binding for '{emoji}' in guild {self.guild_id}")
            await interaction.response.send_message(f"🗑️ Removed binding for {emoji}", ephemeral=True)

        except Exception as e:
            logging.error(f"Failed to remove binding for '{emoji}' in guild {self.guild_id}: {e}")
            await interaction.response.send_message("❌ Failed to remove binding.", ephemeral=True)
