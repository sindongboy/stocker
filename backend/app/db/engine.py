from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Repo root is 3 levels up from backend/app/db/engine.py
_REPO_ROOT = Path(__file__).parents[3]
_DB_FILE = _REPO_ROOT / "data" / "trading.db"
_DB_FILE.parent.mkdir(parents=True, exist_ok=True)

_DB_URL = f"sqlite:///{_DB_FILE}"
_engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def get_session() -> Session:
    return Session(_engine)
