from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Any, AsyncGenerator, Dict, cast

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic_extra_types.coordinate import Latitude, Longitude
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.aws_clients import AWSClientManager, retry_aws
from app.congestion import calculate_device_congestion, calculate_group_congestion
from app.dynamodb import query_recent_pings
from app.models import PingPayload
from app.settings import settings
from app.sqs import send_ping_to_queue
from app.utils import coords_to_hex

logger = logging.getLogger(__name__)

## Housekeeping dependencies
sqs_client: SQSClient | None = None
sqs_queue_url: str | None = None
dynamodb_client: DynamoDBClient | None = None


# Dependency Injection Helpers
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
    """
    Lifespan for the FastAPI application.
    """
    global sqs_client, sqs_queue_url, dynamodb_client

    async with AWSClientManager(
        service_names=["sqs", "dynamodb"]
    ) as aws_client_manager:
        # Cast the clients to the correct types to make type checking happy.
        # We gotta make locals here due to the inline functions below to make mypy happy
        local_sqs_client = cast(SQSClient, aws_client_manager.clients["sqs"])
        local_dynamodb_client = cast(
            DynamoDBClient, aws_client_manager.clients["dynamodb"]
        )

        # Assign to globals, since it's all the same.
        sqs_client = local_sqs_client
        dynamodb_client = local_dynamodb_client

        async def wait_for_queue() -> str:
            # Wait for Queue
            response = await local_sqs_client.get_queue_url(
                QueueName=settings.sqs_queue_name
            )
            return response["QueueUrl"]

        sqs_queue_url = await retry_aws(wait_for_queue)

        logger.info("SQS queue found.")

        async def wait_for_table() -> None:
            # Wait for Table
            await local_dynamodb_client.describe_table(
                TableName=settings.dynamodb_table_name
            )

        await retry_aws(wait_for_table)

        logger.info("DynamoDB table found.")

        yield

    # Cleanup
    sqs_client = None
    sqs_queue_url = None
    dynamodb_client = None


app = FastAPI(lifespan=lifespan)


# Root Endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    return {"status": "ok"}


# Ping Endpoint
@app.post("/ping", status_code=status.HTTP_202_ACCEPTED)
async def ping(
    ping_payload: PingPayload,
    sqs_client: Annotated[SQSClient, Depends(get_sqs_client)],
    sqs_queue_url: Annotated[str, Depends(get_sqs_queue_url)],
) -> Dict[str, Any]:
    # Set when we accepted the ping.
    ping_payload.accepted_at = datetime.now(timezone.utc)

    try:
        # Send the ping to the queue and immediately return.
        message_id = await send_ping_to_queue(sqs_client, sqs_queue_url, ping_payload)
        return {"status": "accepted", "message_id": message_id}
    except Exception as e:
        logger.error(f"Failed to send ping to queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )


# Congestion Endpoint
@app.get("/congestion", status_code=status.HTTP_200_OK)
async def congestion(
    dynamodb_client: Annotated[DynamoDBClient, Depends(get_dynamodb_client)],
    dynamodb_table_name: Annotated[str, Depends(get_dynamodb_table_name)],
    h3_hex: Annotated[str | None, Query()] = None,
    lat: Annotated[Latitude | None, Query()] = None,
    lon: Annotated[Longitude | None, Query()] = None,
    resolution: Annotated[int | None, Query(ge=0, le=15)] = None,
) -> Dict[str, Any]:
    # Set our cutoff time now
    cutoff = (datetime.now(timezone.utc) - timedelta(
        minutes=settings.default_congestion_window
    )).replace(microsecond=0)

    # Set our filter hex
    filter_hex = h3_hex

    # If we have lat and lon, we need to convert them to a hex.
    if lat and lon:
        if h3_hex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot specify both h3_hex and lat/lon",
            )
        else:
            # Set our end resolution to the resolution we were given or the default.
            end_resolution = (
                resolution if resolution is not None else settings.default_h3_resolution
            )
            filter_hex = coords_to_hex(lat, lon, end_resolution)
    # If we only have one of lat or lon, we need to raise an error.
    elif lat is not None or lon is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify both lat and lon",
        )

    # Query the recent pings.
    recent_pings = await query_recent_pings(
        dynamodb_client, dynamodb_table_name, cutoff=cutoff, h3_hex=filter_hex
    )

    # If we have a resolution, we need to calculate the congestion for the group.
    if resolution is not None:
        # Calculate the congestion for the group.
        congestion_counts = calculate_group_congestion(recent_pings, resolution)
        # Format the data for the response.
        congestion_data = [
            {
                "h3_hex": h,
                "device_count": data["device_count"],
                "active_hex_count": data["active_hex_count"],
                "total_hex_count": data["total_hex_count"],
            }
            for h, data in congestion_counts.items()
        ]

    else:
        # Calculate the congestion for the device.
        device_counts = calculate_device_congestion(recent_pings)
        # Format the data for the response.
        congestion_data = [
            {"h3_hex": h3_hex, "device_count": device_count}
            for h3_hex, device_count in device_counts.items()
        ]

    return {"congestion": congestion_data}
