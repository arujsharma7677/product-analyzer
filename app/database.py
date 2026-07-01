"""
SQLAlchemy 2.0 async engine + session factory.

Use `async with SessionLocal() as session:` to get a session. All DB access
goes through the ORM models in app.models.db.

Connection notes (Supabase pooler):
  - DATABASE_URL must point at the TRANSACTION-mode pooler (port 6543), not
    session mode (5432). On a redeploy the old instance still holds its
    connections during the swap, and session mode caps clients hard.
  - statement_cache_size=0 is REQUIRED: pgbouncer transaction mode can't
    reuse asyncpg prepared statements.
  - The pool is kept small and bounded so one instance never hogs clients.
"""
import ssl as ssl_lib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _build_url_and_connect_args() -> tuple[str, dict]:
    """Normalise DATABASE_URL for the SQLAlchemy asyncpg driver.

    Forces the postgresql+asyncpg driver, strips libpq-only query params
    (sslmode / pgbouncer) that asyncpg doesn't understand, and rebuilds the
    equivalent SSL behaviour via connect_args.
    """
    raw = settings.database_url
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    query.pop("pgbouncer", None)  # not understood by asyncpg/SQLAlchemy

    url = urlunsplit(
        ("postgresql+asyncpg", parts.netloc, parts.path, urlencode(query), parts.fragment)
    )

    # Required for pgbouncer transaction mode.
    connect_args: dict = {"statement_cache_size": 0}

    # Supabase requires SSL. Replicate sslmode=require semantics (encrypt,
    # don't verify the cert) unless explicitly disabled.
    if sslmode != "disable":
        ctx = ssl_lib.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl_lib.CERT_NONE
        connect_args["ssl"] = ctx

    return url, connect_args


_url, _connect_args = _build_url_and_connect_args()

engine = create_async_engine(
    _url,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def connect() -> None:
    """Fail fast at startup if the DB is unreachable."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def disconnect() -> None:
    await engine.dispose()
