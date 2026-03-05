import os
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

_pool = ConnectionPool(conninfo=os.getenv("DATABASE_URL"), max_size=10, kwargs={"autocommit": True, "prepare_threshold": None}, open=False)

# Better — create once at startup, reuse everywhere
_checkpointer = None

def get_checkpointer():
    global _checkpointer
    if _checkpointer is None:
        _pool.open(wait=True)
        _checkpointer = PostgresSaver(_pool)
        _checkpointer.setup()
    return _checkpointer