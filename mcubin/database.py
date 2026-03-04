from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_DIR = Path.home() / ".mcubin"
DB_PATH = DB_DIR / "inventory.db"


class Base(DeclarativeBase):
    pass


def get_engine():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )


engine = get_engine()
Session = sessionmaker(bind=engine)
