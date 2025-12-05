from typing import Callable
from fastapi import status
from httpx import AsyncClient
import pytest
from unittest.mock import ANY
from datetime import datetime, timezone
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.utils import get_mock_ping_request, coords_to_hex
from app.models import PingRecord
from app.dynamodb import store_ping_in_dynamodb


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
