import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")
if not DATABASE_URL:
    raise RuntimeError("DB_URL is missing from backend/.env")

_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=int(os.getenv("DB_POOL_MAX_SIZE", "5")),
    open=False,
)


def get_pool() -> ConnectionPool:
    if _pool.closed:
        _pool.open(wait=True)
    return _pool


@contextmanager
def get_connection():
    with get_pool().connection() as connection:
        yield connection


def close_pool() -> None:
    if not _pool.closed:
        _pool.close()