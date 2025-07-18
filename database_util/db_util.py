from database_util.db import Session
from database_util.models import EmojiSoundMap
from database_util.models import GuildPinnedMessage
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

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

async def get_all_emojis_for_guild(guild_id: int) -> list[str]:
    async with Session() as session:
        result = await session.scalars(
            select(EmojiSoundMap.emoji).where(EmojiSoundMap.guild_id == guild_id)
        )
        return result.all()

async def get_pinned_message_id(guild_id: int) -> int | None:
    async with Session() as session:
        row = await session.scalar(
            select(GuildPinnedMessage.pinned_message_id).where(GuildPinnedMessage.guild_id == guild_id)
        )
        return row

async def upsert_pinned_message_id(guild_id: int, pinned_message_id: int):
    async with Session() as session:
        stmt = pg_insert(GuildPinnedMessage).values(
            guild_id=guild_id,
            pinned_message_id=pinned_message_id
        ).on_conflict_do_update(
            index_elements=[GuildPinnedMessage.guild_id],
            set_={"pinned_message_id": pinned_message_id}
        )
        await session.execute(stmt)
        await session.commit()