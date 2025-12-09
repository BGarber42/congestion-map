from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

from pydantic_extra_types.coordinate import Latitude, Longitude
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.models import PingRecord

logger = logging.getLogger(__name__)


# Helper to check table exists
async def create_table_if_not_exists(
    dynamodb_client: DynamoDBClient, dynamodb_table_name: str
) -> None:
    try:
        # If describe fails, it doesn't exist (or we don't have permission)
        await dynamodb_client.describe_table(TableName=dynamodb_table_name)
        logger.info(f"Table {dynamodb_table_name} already exists")
    except dynamodb_client.exceptions.ResourceNotFoundException:
        logger.info(f"Table {dynamodb_table_name} does not exist, creating it")
        await dynamodb_client.create_table(
            TableName=dynamodb_table_name,
            KeySchema=[
                {"AttributeName": "h3_hex", "KeyType": "HASH"},
                {"AttributeName": "ts", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "h3_hex", "AttributeType": "S"},
                {"AttributeName": "ts", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        await dynamodb_client.get_waiter("table_exists").wait(
            TableName=dynamodb_table_name
        )
        logger.info(f"Table {dynamodb_table_name} created")


# Helper to store an enhanced ping in the table
async def store_ping_in_dynamodb(
    dynamodb_client: DynamoDBClient, dynamodb_table_name: str, ping_record: PingRecord
) -> None:
    # Convert to DDB item
    item = {
        "h3_hex": {"S": ping_record.h3_hex},
        "device_id": {"S": ping_record.device_id},
        "ts": {"S": ping_record.ts.astimezone(timezone.utc).replace(microsecond=0).isoformat()},
        "lat": {"N": str(ping_record.lat)},
        "lon": {"N": str(ping_record.lon)},
        "accepted_at": {"S": ping_record.accepted_at.isoformat()},
        "processed_at": {"S": ping_record.processed_at.isoformat()},
    }
    await dynamodb_client.put_item(
        TableName=dynamodb_table_name,
        Item=item,
    )


# Helper to get a single ping from the table
async def get_ping_from_dynamodb(
    dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    h3_hex: str,
    timestamp: datetime,
) -> PingRecord | None:
    response = await dynamodb_client.get_item(
        TableName=dynamodb_table_name,
        Key={"h3_hex": {"S": h3_hex}, "ts": {"S": timestamp.isoformat()}},
    )
    item = response.get("Item")
    if not item:
        return None

    return PingRecord(
        h3_hex=item["h3_hex"]["S"],
        device_id=item["device_id"]["S"],
        ts=datetime.fromisoformat(item["ts"]["S"]),
        lat=Latitude(item["lat"]["N"]),
        lon=Longitude(item["lon"]["N"]),
        accepted_at=datetime.fromisoformat(item["accepted_at"]["S"]),
        processed_at=datetime.fromisoformat(item["processed_at"]["S"]),
    )


# Helper to get all pings for a given hex
async def query_pings_by_hex(
    dynamodb_client: DynamoDBClient, dynamodb_table_name: str, h3_hex: str
) -> List[PingRecord]:
    response = await dynamodb_client.query(
        TableName=dynamodb_table_name,
        KeyConditionExpression="h3_hex = :h3_hex",
        ExpressionAttributeValues={":h3_hex": {"S": h3_hex}},
    )
    items = response.get("Items", [])

    pings: List[PingRecord] = [_ddb_item_to_ping_record(item) for item in items]

    return pings


# Helper to get all recent pings from the table
async def query_recent_pings(
    dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    cutoff: datetime,
    h3_hex: str | None = None,
) -> List[PingRecord]:
    if h3_hex:
        response = await dynamodb_client.query(
            TableName=dynamodb_table_name,
            KeyConditionExpression="h3_hex = :h3_hex AND ts >= :cutoff",
            ExpressionAttributeValues={
                ":h3_hex": {"S": h3_hex},
                ":cutoff": {"S": cutoff.isoformat()},
            },
        )
    else:
        response = await dynamodb_client.scan(
            TableName=dynamodb_table_name,
            FilterExpression="ts >= :cutoff",
            ExpressionAttributeValues={":cutoff": {"S": cutoff.isoformat()}},
        )

    items = response.get("Items", [])

    pings: List[PingRecord] = [_ddb_item_to_ping_record(item) for item in items]

    return pings


# Reduce code duplication for this conversion
def _ddb_item_to_ping_record(item: Dict[str, Any]) -> PingRecord:
    return PingRecord(
        h3_hex=item["h3_hex"]["S"],
        device_id=item["device_id"]["S"],
        ts=datetime.fromisoformat(item["ts"]["S"]),
        lat=Latitude(item["lat"]["N"]),
        lon=Longitude(item["lon"]["N"]),
        accepted_at=datetime.fromisoformat(item["accepted_at"]["S"]),
        processed_at=datetime.fromisoformat(item["processed_at"]["S"]),
    )
