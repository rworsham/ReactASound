from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, Integer


class Base(AsyncAttrs, DeclarativeBase):
    pass


class EmojiSoundMap(Base):
    __tablename__ = "emoji_sound_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    emoji: Mapped[str] = mapped_column(Text)
    sound_filename: Mapped[str] = mapped_column(Text)
    uploader_id: Mapped[int] = mapped_column(BigInteger)