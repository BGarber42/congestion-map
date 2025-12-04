from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport

from app.api import app

@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client