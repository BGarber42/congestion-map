from fastapi import status
from httpx import AsyncClient
import pytest

from app.utils import get_mock_ping_request


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPingEndpoint:
    @pytest.mark.asyncio
    async def test_valid_ping(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request().model_dump()

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted"}

    async def test_invalid_latitude(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request({"lat": 91}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_invalid_longitude(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request({"lon": 181}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_missing_device_id(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request({"device_id": ""}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_missing_timestamp(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request({"timestamp": None}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_not_a_timestamp(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request(
            {"timestamp": "not a timestamp"}, return_instance=False
        )

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_not_real_coordinates(self, async_client: AsyncClient) -> None:
        ping_payload = get_mock_ping_request(
            {"lat": "somestring", "lon": ["not a number"]}, return_instance=False
        )

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestCongestionEndpoint:
    @pytest.mark.asyncio
    async def test_get_congestion(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/congestion")

        # TODO: Implement proper tests
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}
