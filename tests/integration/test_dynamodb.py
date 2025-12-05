from datetime import datetime, timezone

import pytest
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.dynamodb import (
    store_ping_in_dynamodb,
    get_ping_from_dynamodb,
    query_pings_by_hex,
)
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
            accepted_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )

        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, record)

        retrieved_record = await get_ping_from_dynamodb(
            dynamodb_client, dynamodb_table_name, record.h3_hex, record.timestamp
        )

        assert retrieved_record is not None
        assert retrieved_record.h3_hex == record.h3_hex
        assert retrieved_record.device_id == ping.device_id
        assert retrieved_record.timestamp == ping.timestamp
        assert retrieved_record.lat == ping.lat
        assert retrieved_record.lon == ping.lon
        assert retrieved_record.processed_at is not None
        assert retrieved_record.processed_at == record.processed_at

    @pytest.mark.asyncio
    async def test_query_pings_by_h3_hex(
        self, dynamodb_client: DynamoDBClient, dynamodb_table_name: str
    ) -> None:
        """Should query all pings for a given h3_hex."""
        ping = get_mock_ping_request()
        h3_hex = coords_to_hex(ping.lat, ping.lon)

        record = PingRecord(
            h3_hex=h3_hex,
            device_id=ping.device_id,
            timestamp=ping.timestamp,
            lat=ping.lat,
            lon=ping.lon,
            accepted_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )

        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, record)

        records = await query_pings_by_hex(dynamodb_client, dynamodb_table_name, h3_hex)

        assert len(records) == 1
        assert records[0].h3_hex == h3_hex
