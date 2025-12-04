from httpx import AsyncClient
import pytest

class TestRoot:
    @pytest.mark.asyncio
    async def test_root(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}