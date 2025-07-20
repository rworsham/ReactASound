import logging
import discord
from database_util.db_util import get_all_emojis_for_guild, get_pinned_message_id, upsert_pinned_message_id


class ReactionBoard:
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    async def get_or_create_pinned_message(self, guild: discord.Guild) -> discord.Message:
        channel = discord.utils.get(guild.text_channels, name="reactasound")
        if not channel:
            raise ValueError(f"reactasound channel not found in guild: {guild.name}")

        pinned_msg_id = await get_pinned_message_id(guild.id)
        if pinned_msg_id:
            try:
                msg = await channel.fetch_message(pinned_msg_id)
                return msg
            except discord.NotFound:
                logging.warning(f"Pinned message ID {pinned_msg_id} from DB not found in channel. Will recreate.")

        pins = await channel.pins()
        for pin in pins:
            if pin.author == self.bot.user:
                await upsert_pinned_message_id(guild.id, pin.id)
                return pin

        message = await channel.send("🎵 React with an emoji below to play your sound!")
        await message.pin()
        await upsert_pinned_message_id(guild.id, message.id)
        logging.info(f"Created and pinned new soundboard message in {guild.name}")
        return message

    async def update_reactions(self, guild: discord.Guild):
        message = await self.get_or_create_pinned_message(guild)
        existing_reactions = [str(reaction.emoji) for reaction in message.reactions]

        emoji_list = await get_all_emojis_for_guild(guild.id)

        for emoji in emoji_list:
            if emoji not in existing_reactions:
                try:
                    await message.add_reaction(emoji)
                except discord.HTTPException:
                    logging.warning(f"Failed to add reaction: {emoji} (possibly invalid?)")
