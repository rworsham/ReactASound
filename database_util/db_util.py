from database_util.db import Session
from database_util.models import EmojiSoundMap
from sqlalchemy import select

async def add_or_update_mapping(guild_id, emoji, filename, uploader_id):
    async with Session() as session:
        existing = await session.scalar(
            select(EmojiSoundMap).where(EmojiSoundMap.guild_id == guild_id, EmojiSoundMap.emoji == emoji)
        )

        if existing:
            existing.sound_filename = filename
        else:
            session.add(EmojiSoundMap(
                guild_id=guild_id,
                emoji=emoji,
                sound_filename=filename,
                uploader_id=uploader_id
            ))

        await session.commit()

async def get_sound_filename(guild_id, emoji):
    async with Session() as session:
        row = await session.scalar(
            select(EmojiSoundMap.sound_filename).where(
                EmojiSoundMap.guild_id == guild_id,
                EmojiSoundMap.emoji == emoji
            )
        )
        return row