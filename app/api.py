from typing import Any, Dict, AsyncGenerator, Annotated
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging

from fastapi import FastAPI, Query, status, Depends, HTTPException
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient
import aioboto3
from botocore.config import Config

from app.congestion import calculate_device_congestion
from app.dynamodb import query_recent_pings
from app.models import PingPayload
from app.sqs import send_ping_to_queue
from app.settings import settings
from app.utils import coords_to_hex

## Housekeeping dependencies
sqs_client: SQSClient | None = None
sqs_queue_url: str | None = None
dynamodb_client: DynamoDBClient | None = None

logger = logging.getLogger(__name__)


async def get_sqs_client() -> SQSClient:
    if sqs_client is None:
        raise RuntimeError("SQS client not initialized")
    return sqs_client


async def get_sqs_queue_url() -> str:
    if sqs_queue_url is None:
        raise RuntimeError("SQS queue URL not initialized")
    return sqs_queue_url


async def get_dynamodb_client() -> DynamoDBClient:
    if dynamodb_client is None:
        raise RuntimeError("DynamoDB client not initialized")
    return dynamodb_client


async def get_dynamodb_table_name() -> str:
    return settings.dynamodb_table_name


# Doc Ref: https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global sqs_client, sqs_queue_url, dynamodb_client

    session = aioboto3.Session()
    async with session.client(  # type: ignore[call-overload]
        "sqs",
        endpoint_url=settings.sqs_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or "x",
        aws_secret_access_key=settings.aws_secret_access_key or "x",
        config=Config(retries={"max_attempts": 0}),
    ) as client:
        sqs_client = client

        response = await client.get_queue_url(QueueName=settings.sqs_queue_name)
        sqs_queue_url = response["QueueUrl"]

        async with session.client(  # type: ignore[call-overload]
            "dynamodb",
            endpoint_url=settings.dynamodb_endpoint_url,
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or "x",
            aws_secret_access_key=settings.aws_secret_access_key or "x",
            config=Config(retries={"max_attempts": 0}),
        ) as ddb_client:
            dynamodb_client = ddb_client

            yield

    sqs_client = None
    sqs_queue_url = None
    dynamodb_client = None


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/ping", status_code=status.HTTP_202_ACCEPTED)
async def ping(
    ping_payload: PingPayload,
    sqs_client: Annotated[SQSClient, Depends(get_sqs_client)],
    sqs_queue_url: Annotated[str, Depends(get_sqs_queue_url)],
) -> Dict[str, Any]:
    ping_payload.accepted_at = datetime.now(timezone.utc)

    try:
        message_id = await send_ping_to_queue(sqs_client, sqs_queue_url, ping_payload)
        return {"status": "accepted", "message_id": message_id}
    except Exception as e:
        logger.error(f"Failed to send ping to queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )


@app.get("/congestion", status_code=status.HTTP_200_OK)
async def congestion(
    dynamodb_client: Annotated[DynamoDBClient, Depends(get_dynamodb_client)],
    dynamodb_table_name: Annotated[str, Depends(get_dynamodb_table_name)],
    h3_hex: Annotated[str | None, Query()] = None,
) -> Dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.default_congestion_window
    )

    recent_pings = await query_recent_pings(
        dynamodb_client, dynamodb_table_name, cutoff=cutoff, h3_hex=h3_hex
    )

    device_counts = calculate_device_congestion(recent_pings)

    congestion_data = [
        {"h3_hex": h3_hex, "device_count": device_count}
        for h3_hex, device_count in device_counts.items()
    ]

    return {"congestion": congestion_data}
