from app.configs.app_configs import getAppConfig
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

config = getAppConfig()
class Base(DeclarativeBase):
    pass


engine = create_engine(config.database_url)

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