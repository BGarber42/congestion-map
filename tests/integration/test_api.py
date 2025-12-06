from datetime import datetime, timezone
import random
from typing import Callable, List
from unittest.mock import ANY

from fastapi import status
import h3  # type: ignore
from httpx import AsyncClient
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.dynamodb import store_ping_in_dynamodb
from app.models import PingRecord
from app.utils import coords_to_hex
from tests.helpers import get_mock_ping_request


class TestRootEndpoint:

    async def test_root(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPingEndpoint:

    async def test_valid_ping(self, async_client: AsyncClient) -> None:
        """Test a valid ping request"""
        ping_payload = get_mock_ping_request(return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted", "message_id": ANY}

    async def test_invalid_latitude(self, async_client: AsyncClient) -> None:
        """Test an invalid latitude"""
        ping_payload = get_mock_ping_request({"lat": 91}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_invalid_longitude(self, async_client: AsyncClient) -> None:
        """Test an invalid longitude"""
        ping_payload = get_mock_ping_request({"lon": 181}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_missing_device_id(self, async_client: AsyncClient) -> None:
        """Test a missing device id"""
        ping_payload = get_mock_ping_request({"device_id": ""}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_missing_timestamp(self, async_client: AsyncClient) -> None:
        """Test a missing timestamp"""
        ping_payload = get_mock_ping_request({"timestamp": None}, return_instance=False)

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_not_a_timestamp(self, async_client: AsyncClient) -> None:
        """Test a non-timestamp timestamp"""
        ping_payload = get_mock_ping_request(
            {"timestamp": "not a timestamp"}, return_instance=False
        )

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_not_real_coordinates(self, async_client: AsyncClient) -> None:
        """Test non-real coordinates"""
        ping_payload = get_mock_ping_request(
            {"lat": "somestring", "lon": ["not a number"]}, return_instance=False
        )

        response = await async_client.post("/ping", json=ping_payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestCongestionEndpoint:

    async def test_no_congestion(self, async_client: AsyncClient) -> None:
        """Test app with no pings"""
        response = await async_client.get("/congestion")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"congestion": []}

    async def test_recent_congestion(
        self,
        async_client: AsyncClient,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        """Test app with a couple of pings"""
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
        # Store the ping in DynamoDB
        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, record)

        # Immediately check the congestion
        response = await async_client.get("/congestion")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "congestion" in data
        assert len(data["congestion"]) == 1
        assert data["congestion"][0]["h3_hex"] == h3_hex
        assert data["congestion"][0]["device_count"] == 1

    async def test_congestion_with_hex(
        self,
        async_client: AsyncClient,
        ping_record_factory: Callable[[], PingRecord],
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        """Test app with a couple of pings and fetch via hex"""
        # Generate some pings
        pings = [ping_record_factory() for _ in range(5)]

        # Store the pings in DynamoDB
        for ping in pings:
            await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, ping)

        # Fetch the congestion via hex
        response = await async_client.get(f"/congestion?h3_hex={pings[0].h3_hex}")

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert "congestion" in response_data
        congestion_data = response_data["congestion"]

        assert len(congestion_data) == 1

        hex_data = congestion_data[0]
        assert hex_data["h3_hex"] == pings[0].h3_hex

    async def test_congestion_with_coordinates(
        self,
        async_client: AsyncClient,
        ping_record_factory: Callable[[], PingRecord],
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        """Test app with a couple of pings and fetch via coordinates"""
        # Generate some pings
        pings = [ping_record_factory() for _ in range(5)]

        # Store the pings in DynamoDB
        for ping in pings:
            await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, ping)

        # Fetch via coordinates
        response = await async_client.get(
            f"/congestion?lat={pings[0].lat}&lon={pings[0].lon}"
        )

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()

        assert "congestion" in response_data
        congestion_data = response_data["congestion"]

        assert len(congestion_data) == 1

    async def test_congestion_with_resolution(
        self,
        async_client: AsyncClient,
        ping_record_factory: Callable[..., PingRecord],
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        """Test app with a couple of pings and fetch w/ custom resolution"""
        # Define the parent hex and resolution
        parent_hex = "8b2a1072d0d5fff"
        parent_resolution = h3.get_resolution(parent_hex)

        # Generate data one level down
        child_resolution = parent_resolution + 1

        # Get the children of the parent hex
        children = h3.cell_to_children(parent_hex, child_resolution)

        # Generate random pings in children
        pings: List[PingRecord] = [
            ping_record_factory(h3_hex=child, device_id=f"device_{child}_{i}")
            for child in children
            for i in range(random.randint(1, 5))
        ]

        # Store the pings in DynamoDB
        # TODO: Figure out how to bulk insert these (coroutine?)
        for ping in pings:
            await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, ping)

        # Fetch the congestion w/ resolution
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
