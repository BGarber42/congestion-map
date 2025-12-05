from datetime import datetime, timezone
import random
from typing import Callable, List
from unittest.mock import ANY

from fastapi import status
import h3  # type: ignore
from httpx import AsyncClient
import pytest
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.dynamodb import store_ping_in_dynamodb
from app.models import PingRecord
from app.utils import coords_to_hex, get_mock_ping_request


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
        assert response.json() == {"status": "accepted", "message_id": ANY}

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
    async def test_no_congestion(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/congestion")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"congestion": []}

    @pytest.mark.asyncio
    async def test_recent_congestion(
        self,
        async_client: AsyncClient,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        ping = get_mock_ping_request()
        h3_hex = coords_to_hex(ping.lat, ping.lon)
        record = PingRecord(
            h3_hex=h3_hex,
            device_id=ping.device_id,
            ts=ping.timestamp,
            lat=ping.lat,
            lon=ping.lon,
            accepted_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, record)

        response = await async_client.get("/congestion")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "congestion" in data
        assert len(data["congestion"]) == 1
        assert data["congestion"][0]["h3_hex"] == h3_hex
        assert data["congestion"][0]["device_count"] == 1

    @pytest.mark.asyncio
    async def test_congestion_with_hex(
        self,
        async_client: AsyncClient,
        make_ping_record: Callable[[], PingRecord],
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        pings = [make_ping_record() for _ in range(5)]

        for ping in pings:
            await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, ping)

        response = await async_client.get(f"/congestion?h3_hex={pings[0].h3_hex}")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert "congestion" in response_data
        congestion_data = response_data["congestion"]

        assert len(congestion_data) == 1

        hex_data = congestion_data[0]
        assert hex_data["h3_hex"] == pings[0].h3_hex

    @pytest.mark.asyncio
    async def test_congestion_with_coordinates(
        self,
        async_client: AsyncClient,
        make_ping_record: Callable[[], PingRecord],
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        pings = [make_ping_record() for _ in range(5)]

        for ping in pings:
            await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, ping)

        response = await async_client.get(
            f"/congestion?lat={pings[0].lat}&lon={pings[0].lon}"
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert "congestion" in response_data
        congestion_data = response_data["congestion"]

        assert len(congestion_data) == 1

    @pytest.mark.asyncio
    async def test_congestion_with_resolution(
        self,
        async_client: AsyncClient,
        make_ping_record: Callable[..., PingRecord],
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:

        parent_hex = "8b2a1072d0d5fff"
        parent_resolution = h3.get_resolution(parent_hex)

        child_resolution = parent_resolution + 1

        children = h3.cell_to_children(parent_hex, child_resolution)

        # Generate random pings in children
        pings: List[PingRecord] = [
            make_ping_record(h3_hex=child, device_id=f"device_{child}_{i}")
            for child in children
            for i in range(random.randint(1, 5))
        ]

        for ping in pings:
            await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, ping)

        response = await async_client.get(f"/congestion?resolution={parent_resolution}")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert "congestion" in response_data
        congestion_data = response_data["congestion"]

        assert len(congestion_data) == 1

        result = congestion_data[0]
        assert result["h3_hex"] == parent_hex
        assert result["device_count"] == len(pings)
        assert result["active_hex_count"] == len(children)
        assert result["total_hex_count"] == len(children)
