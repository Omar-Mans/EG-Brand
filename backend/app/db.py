from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configure(url: str) -> None:
    """Point the app at another database (used by tests)."""
    global engine
    engine = _make_engine(url)
    SessionLocal.configure(bind=engine)


# Columns added after the first release. create_all() does not alter existing tables, so add them here
# until the project moves to Alembic.
ADDED_COLUMNS = {
    "posts": {"design": "JSON", "bg_url": "VARCHAR(1000)", "metrics": "JSON", "metrics_at": "TIMESTAMP WITH TIME ZONE"},
}


def ensure_columns() -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in ADDED_COLUMNS.items():
            if not insp.has_table(table):
                continue
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name in have:
                    continue
                if engine.dialect.name != "postgresql":
                    ddl = ddl.replace("TIMESTAMP WITH TIME ZONE", "DATETIME")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    ensure_columns()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"
