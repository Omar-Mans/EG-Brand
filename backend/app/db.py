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
    "posts": {"design": "JSON", "bg_url": "VARCHAR(1000)", "video_url": "VARCHAR(1000)", "metrics": "JSON", "metrics_at": "TIMESTAMP WITH TIME ZONE"},
    "brands": {"discovery": "JSON", "strategy": "JSON"},
}


def ensure_columns(conn=None) -> None:
    if conn is None:
        with engine.begin() as c:
            return ensure_columns(c)
    insp = inspect(conn)
    pg = conn.dialect.name == "postgresql"
    for table, cols in ADDED_COLUMNS.items():
        if not insp.has_table(table):
            continue
        have = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in cols.items():
            if name in have:
                continue
            if pg:  # IF NOT EXISTS: safe even if another process added it a moment ago
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl.replace('TIMESTAMP WITH TIME ZONE', 'DATETIME')}"))


SCHEMA_LOCK = 774201  # any constant: Postgres advisory lock id for schema setup


def init_db() -> None:
    """The API and the worker start together; on Postgres they take turns so they never race on CREATE/ALTER."""
    from . import models  # noqa: F401  (register tables)

    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": SCHEMA_LOCK})
        Base.metadata.create_all(conn)
        ensure_columns(conn)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"
