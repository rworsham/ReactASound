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
                logging.warning(f"Pinned message ID {pinned_msg_id} from DB not found. Recreating.")

        pins = await channel.pins()
        for pin in pins:
            if pin.author == self.bot.user:
                await upsert_pinned_message_id(guild.id, pin.id)
                return pin

        file = discord.File("assets/reaction_board.jpg", filename="reaction_board.jpg")

        embed = discord.Embed(
            title="🎵 ReactASound Soundboard",
            description="React with one of the emojis you have setup below to play a sound!\n\n"
                        "Use `/addsound` or `/removesound` in a botcommands thread to manage bindings.",
            color=discord.Color.blurple()
        )
        embed.set_image(url="attachment://reaction_board.jpg")
        embed.set_footer(text="Only works if you're in a voice channel!")

        message = await channel.send(embed=embed, file=file)
        await message.pin()
        await upsert_pinned_message_id(guild.id, message.id)
        logging.info(f"Created and pinned new soundboard message in {guild.name}")
        return message

    async def update_reactions(self, guild: discord.Guild):
        message = await self.get_or_create_pinned_message(guild)

        try:
            await message.clear_reactions()
        except discord.Forbidden:
            logging.warning(f"Missing permissions to clear reactions in guild {guild.name}")
        except Exception as e:
            logging.warning(f"Could not clear reactions in {guild.name}: {e}")

        emoji_list = await get_all_emojis_for_guild(guild.id)
        if not emoji_list:
            logging.info(f"No emoji mappings found for guild {guild.name}")
            return

        for emoji in emoji_list:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException as e:
                logging.warning(f"Failed to add reaction: {emoji} in {guild.name} — {e}")
