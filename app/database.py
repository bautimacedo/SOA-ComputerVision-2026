from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import app.config

engine = create_engine(app.config.settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
