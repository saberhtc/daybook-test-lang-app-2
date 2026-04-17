import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def set_test_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_file
    os.environ.setdefault("JWT_SECRET", "test-secret")
    yield
    os.environ.pop("DB_PATH", None)


@pytest_asyncio.fixture
async def client(set_test_db):
    from app import app
    from db import init_db

    init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
