from datetime import datetime, timezone

import pytest
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.dynamodb import store_ping_in_dynamodb, get_ping_from_dynamodb
from app.utils import get_mock_ping_request
from app.models import PingRecord
from app.utils import coords_to_hex


class TestDynamoDB:
    @pytest.mark.asyncio
    async def test_save_ping_to_table(
        self, dynamodb_client: DynamoDBClient, dynamodb_table_name: str
    ) -> None:
        ping = get_mock_ping_request()
        h3_hex = coords_to_hex(ping.lat, ping.lon)
        record = PingRecord(
            h3_hex=h3_hex,
            device_id=ping.device_id,
            timestamp=ping.timestamp,
            lat=ping.lat,
            lon=ping.lon,
            processed_at=datetime.now(timezone.utc),
        )

        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, record)

        retrieved_ping = await get_ping_from_dynamodb(
            dynamodb_client, dynamodb_table_name, record.h3_hex
        )

        assert retrieved_ping is not None
        assert retrieved_ping.h3_hex == record.h3_hex
        assert retrieved_ping.timestamp == ping.timestamp
        assert retrieved_ping.lat == ping.lat
        assert retrieved_ping.lon == ping.lon
