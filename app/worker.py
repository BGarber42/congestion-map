from datetime import datetime, timezone, timedelta
import logging
import json

from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient
from typing import List

from app.models import PingPayload, PingRecord
from app.settings import settings
from app.utils import coords_to_hex
from app.dynamodb import store_ping_in_dynamodb
from app.sqs import get_pings_from_queue

logger = logging.getLogger(__name__)


def is_valid_timestamp(timestamp: datetime) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    max_age = timedelta(seconds=settings.max_ping_age_seconds)
    clock_skew = timedelta(seconds=settings.max_clock_skew_seconds)

    if timestamp > now + clock_skew:
        reason = (
            f"Timestamp is too far in the future by "
            f"{(timestamp - now).total_seconds():.0f} seconds."
        )
        return False, reason

    age = now - timestamp
    if age > max_age:
        reason = (
            f"Timestamp is too old by "
            f"{(age - max_age).total_seconds():.0f} seconds."
        )
        return False, reason

    return True, "Timestamp is valid."


def check_ping_dwell(accepted_at: datetime | None) -> None:
    if accepted_at is None:
        return

    now = datetime.now(timezone.utc)
    dwell = now - accepted_at
    if dwell > timedelta(seconds=settings.queue_warnings_seconds):
        logger.warning(
            f"Ping has been queued for {dwell.total_seconds():.0f} seconds"
            f"(Ingest: {accepted_at.isoformat()}) - possible queue backlog"
        )


def enrich_ping_record(ping: PingPayload) -> PingRecord:
    if ping.accepted_at is None:
        raise ValueError("Accepted at is required")

    h3_hex = coords_to_hex(ping.lat, ping.lon)

    return PingRecord(
        h3_hex=h3_hex,
        device_id=ping.device_id,
        ts=ping.timestamp,
        lat=ping.lat,
        lon=ping.lon,
        accepted_at=ping.accepted_at,
        processed_at=datetime.now(timezone.utc),
    )


async def process_ping_from_queue(
    sqs_client: SQSClient,
    sqs_queue_url: str,
    dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> List[PingRecord]:
    response = await sqs_client.receive_message(
        QueueUrl=sqs_queue_url,
        MaxNumberOfMessages=settings.max_pings,
        WaitTimeSeconds=settings.wait_time_seconds,
    )

    messages = response.get("Messages", [])
    pings = []

    for message in messages:
        receipt_handle = message["ReceiptHandle"]
        message_id = message["MessageId"]

        try:
            message_body = message["Body"]
            ping_data = json.loads(message_body)
            ping = PingPayload(**ping_data)
        except Exception as e:
            logger.error(f"Error parsing ping: {e}")
            await sqs_client.delete_message(
                QueueUrl=sqs_queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
            continue

        # Check queue health
        check_ping_dwell(ping.accepted_at)

        # Check timestamp validity
        is_valid, reason = is_valid_timestamp(ping.timestamp)
        if not is_valid:
            logger.warning(
                f"Invalid timestamp '{ping.timestamp.isoformat()}' found for device '{ping.device_id}'. "
                f"Reason: {reason}. Discarding message."
            )
            await sqs_client.delete_message(
                QueueUrl=sqs_queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
            continue

        try:
            happy_ping = enrich_ping_record(ping)
            await store_ping_in_dynamodb(
                dynamodb_client, dynamodb_table_name, happy_ping
            )

            await sqs_client.delete_message(
                QueueUrl=sqs_queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )

            pings.append(happy_ping)

        except Exception as e:
            logger.error(f"Error processing ping: {e}")
            await sqs_client.delete_message(
                QueueUrl=sqs_queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
            continue

    return pings
