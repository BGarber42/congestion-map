from fastapi import status
from httpx import AsyncClient
import pytest


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

class TestPingEndpoint:
    @pytest.mark.asyncio
    async def test_valid_ping(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "device_id": "abc123",
            "timestamp": "2025-01-01T12:34:56Z",
            "lat": 40.743,
            "lon": -73.989
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted"}

    async def test_invalid_latitude(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "device_id": "abc123",
            "timestamp": "2025-01-01T12:34:56Z",
            "lat": 91,
            "lon": -73.989
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    async def test_invalid_longitude(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "device_id": "abc123",
            "timestamp": "2025-01-01T12:34:56Z",
            "lat": 40.743,
            "lon": 181
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    async def test_missing_device_id(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "timestamp": "2025-01-01T12:34:56Z",
            "lat": 40.743,
            "lon": -73.989
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    async def test_missing_timestamp(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "device_id": "abc123",
            "lat": 40.743,
            "lon": -73.989
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    
    async def test_not_a_timestamp(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "device_id": "abc123",
            "timestamp": "not a timestamp",
            "lat": 40.743,
            "lon": -73.989
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_not_real_coordinates(self, async_client: AsyncClient) -> None:
        ping_payload = {
            "device_id": "abc123",
            "timestamp": "2025-01-01T12:34:56Z",
            "lat": "somestring",
            "lon": ["not a number"]
        }

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT