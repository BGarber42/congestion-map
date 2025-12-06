from datetime import datetime, timedelta, timezone

from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.dynamodb import (
    get_ping_from_dynamodb,
    query_pings_by_hex,
    query_recent_pings,
    store_ping_in_dynamodb,
)
from app.models import PingRecord
from app.settings import settings
from app.utils import coords_to_hex
from tests.helpers import get_mock_ping_request


class TestDynamoDB:
    async def test_save_ping_to_table(
        self, dynamodb_client: DynamoDBClient, dynamodb_table_name: str
    ) -> None:
        """Should save a ping to the table"""
        ping = get_mock_ping_request()
        # Convert the coordinates to the h3 hex id
        h3_hex = coords_to_hex(ping.lat, ping.lon)
        # Convert the ping to a PingRecord
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

        retrieved_record = await get_ping_from_dynamodb(
            dynamodb_client, dynamodb_table_name, record.h3_hex, record.ts
        )

        assert retrieved_record is not None
        assert retrieved_record.h3_hex == record.h3_hex
        assert retrieved_record.device_id == ping.device_id
        assert retrieved_record.ts == ping.timestamp
        assert retrieved_record.lat == ping.lat
        assert retrieved_record.lon == ping.lon
        assert retrieved_record.processed_at is not None
        assert retrieved_record.processed_at == record.processed_at

    async def test_query_pings_by_h3_hex(
        self, dynamodb_client: DynamoDBClient, dynamodb_table_name: str
    ) -> None:
        """Should query all pings for a given h3_hex."""
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

        records = await query_pings_by_hex(dynamodb_client, dynamodb_table_name, h3_hex)

        assert len(records) == 1
        assert records[0].h3_hex == h3_hex

    async def test_get_recent_pings(
        self, dynamodb_client: DynamoDBClient, dynamodb_table_name: str
    ) -> None:
        """Test fetching all recent pings"""
        # Set some recent and old ping times
        now = datetime.now(timezone.utc)
        recent_ping_time = now - timedelta(minutes=5)
        old_ping_time = now - timedelta(minutes=40)

        # Create a 5 minute old ping
        new_ping = get_mock_ping_request({"timestamp": recent_ping_time})
        new_record = PingRecord(
            h3_hex=coords_to_hex(new_ping.lat, new_ping.lon),
            device_id="new_device",
            ts=new_ping.timestamp,
            lat=new_ping.lat,
            lon=new_ping.lon,
            accepted_at=now,
            processed_at=now,
        )

        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, new_record)

        # Create a 40 minute old ping
        old_ping = get_mock_ping_request({"timestamp": old_ping_time})
        old_record = PingRecord(
            h3_hex=coords_to_hex(old_ping.lat, old_ping.lon),
            device_id="old_device",
            ts=old_ping.timestamp,
            lat=old_ping.lat,
            lon=old_ping.lon,
            accepted_at=now,
            processed_at=now,
        )

        await store_ping_in_dynamodb(dynamodb_client, dynamodb_table_name, old_record)

        # Set the cutoff time for recent pings
        cutoff = now - timedelta(minutes=settings.default_congestion_window)

        # We should only get the new ping back
        pings = await query_recent_pings(dynamodb_client, dynamodb_table_name, cutoff)

        assert len(pings) == 1
        assert pings[0].h3_hex == new_record.h3_hex
        assert pings[0].device_id == new_record.device_id
        assert pings[0].ts == new_record.ts
        assert pings[0].lat == new_record.lat
        assert pings[0].lon == new_record.lon
        assert pings[0].processed_at == new_record.processed_at
