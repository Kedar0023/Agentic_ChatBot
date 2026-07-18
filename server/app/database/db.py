from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.app_configs import getAppConfig

config = getAppConfig()


class Base(DeclarativeBase):
    pass


engine = create_engine(config.database_url.get_secret_value())

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

ASYNC_DATABASE_URL = config.database_url.get_secret_value().replace(
    "postgresql://",
    "postgresql+asyncpg://",
    1,
)

# same physical DB, async driver (e.g. postgresql+asyncpg://... instead of postgresql://...)
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

def get_async_db_session() -> async_sessionmaker[AsyncSession]:
    return AsyncSessionLocal

