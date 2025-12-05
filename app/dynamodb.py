from datetime import datetime
from typing import List

from pydantic_extra_types.coordinate import Latitude, Longitude
from types_aiobotocore_dynamodb.client import DynamoDBClient
from app.models import PingRecord


async def store_ping_in_dynamodb(
    dynamodb_client: DynamoDBClient, dynamodb_table_name: str, ping_record: PingRecord
) -> None:
    # Convert to DDB item
    item = {
        "h3_hex": {"S": ping_record.h3_hex},
        "device_id": {"S": ping_record.device_id},
        "timestamp": {"S": ping_record.timestamp.isoformat()},
        "lat": {"N": str(ping_record.lat)},
        "lon": {"N": str(ping_record.lon)},
        "accepted_at": {"S": ping_record.accepted_at.isoformat()},
        "processed_at": {"S": ping_record.processed_at.isoformat()},
    }
    await dynamodb_client.put_item(
        TableName=dynamodb_table_name,
        Item=item,
    )


async def get_ping_from_dynamodb(
    dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    h3_hex: str,
    timestamp: datetime,
) -> PingRecord | None:
    response = await dynamodb_client.get_item(
        TableName=dynamodb_table_name,
        Key={"h3_hex": {"S": h3_hex}, "timestamp": {"S": timestamp.isoformat()}},
    )
    item = response.get("Item")
    if not item:
        return None

    return PingRecord(
        h3_hex=item["h3_hex"]["S"],
        device_id=item["device_id"]["S"],
        timestamp=datetime.fromisoformat(item["timestamp"]["S"]),
        lat=Latitude(item["lat"]["N"]),
        lon=Longitude(item["lon"]["N"]),
        accepted_at=datetime.fromisoformat(item["accepted_at"]["S"]),
        processed_at=datetime.fromisoformat(item["processed_at"]["S"]),
    )


async def query_pings_by_hex(
    dynamodb_client: DynamoDBClient, dynamodb_table_name: str, h3_hex: str
) -> List[PingRecord]:
    response = await dynamodb_client.query(
        TableName=dynamodb_table_name,
        KeyConditionExpression="h3_hex = :h3_hex",
        ExpressionAttributeValues={":h3_hex": {"S": h3_hex}},
    )
    items = response.get("Items", [])

    records = []
    for item in items:
        records.append(
            PingRecord(
                h3_hex=item["h3_hex"]["S"],
                device_id=item["device_id"]["S"],
                timestamp=datetime.fromisoformat(item["timestamp"]["S"]),
                lat=Latitude(item["lat"]["N"]),
                lon=Longitude(item["lon"]["N"]),
                accepted_at=datetime.fromisoformat(item["accepted_at"]["S"]),
                processed_at=datetime.fromisoformat(item["processed_at"]["S"]),
            )
        )
    return records


async def query_recent_pings(
    dynamodb_client: DynamoDBClient, dynamodb_table_name: str, cutoff: datetime
) -> List[PingRecord]:
    response = await dynamodb_client.query(
        TableName=dynamodb_table_name,
        KeyConditionExpression="timestamp >= :cutoff",
        ExpressionAttributeValues={":cutoff": {"S": cutoff.isoformat()}},
    )

    items = response.get("Items", [])
    pings: List[PingRecord] = []

    for item in items:
        pings.append(
            PingRecord(
                h3_hex=item["h3_hex"]["S"],
                device_id=item["device_id"]["S"],
                timestamp=datetime.fromisoformat(item["timestamp"]["S"]),
                lat=Latitude(item["lat"]["N"]),
                lon=Longitude(item["lon"]["N"]),
                accepted_at=datetime.fromisoformat(item["accepted_at"]["S"]),
                processed_at=datetime.fromisoformat(item["processed_at"]["S"]),
            )
        )
    return pings
