import pytest
from whiteboard_mcp.db import connect, ensure_schema


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "coach.db"
    conn = connect(db_path)
    ensure_schema(conn)
    yield conn
    conn.close()
