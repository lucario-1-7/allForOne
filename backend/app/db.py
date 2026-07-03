from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    interests: Mapped[list["Interest"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    follows: Mapped[list["Follow"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Interest(Base):
    """One row per domain the user enabled; config holds the per-domain refinement.

    domain: tech | sports | games | screen
    config examples:
      sports: {"leagues": ["PL", "PD"]}
      games:  {"esports": "valorant"}
      tech:   {"subtopics": ["ai", "hardware"]}
      screen: {}
    """

    __tablename__ = "interests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    domain: Mapped[str] = mapped_column(String(32))
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="interests")


class Follow(Base):
    """A followed item: kind is 'tv' (TVmaze id) or 'anime' (AniList id)."""

    __tablename__ = "follows"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    external_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="follows")


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
