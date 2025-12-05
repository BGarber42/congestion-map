from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Any, AsyncGenerator, Dict

import aioboto3
from botocore.config import Config
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic_extra_types.coordinate import Latitude, Longitude
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.congestion import calculate_device_congestion, calculate_group_congestion
from app.dynamodb import create_table_if_not_exists, query_recent_pings
from app.models import PingPayload
from app.settings import settings
from app.sqs import send_ping_to_queue
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


import asyncio
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
)


# Doc Ref: https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global sqs_client, sqs_queue_url, dynamodb_client

    connected = False
    while not connected:
        try:
            logger.info("API attempting to connect to AWS services...")
            session = aioboto3.Session()
            async with session.client(  # type: ignore[call-overload]
                "sqs",
                endpoint_url=settings.sqs_endpoint_url,
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id or "x",
                aws_secret_access_key=settings.aws_secret_access_key or "x",
                config=Config(
                    connect_timeout=2, read_timeout=25, retries={"max_attempts": 0}
                ),
            ) as client:
                sqs_client = client

                # The worker is responsible for creating resources.
                # The API will just wait until they are available.
                response = await client.get_queue_url(QueueName=settings.sqs_queue_name)
                sqs_queue_url = response["QueueUrl"]
                logger.info("API SQS queue found.")

                async with session.client(  # type: ignore[call-overload]
                    "dynamodb",
                    endpoint_url=settings.dynamodb_endpoint_url,
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id or "x",
                    aws_secret_access_key=settings.aws_secret_access_key or "x",
                    config=Config(
                        connect_timeout=2, read_timeout=25, retries={"max_attempts": 0}
                    ),
                ) as ddb_client:
                    dynamodb_client = ddb_client
                    # Check if the table exists by trying to describe it.
                    await ddb_client.describe_table(
                        TableName=settings.dynamodb_table_name
                    )
                    logger.info("API DynamoDB table found.")

                    logger.info("API connection to AWS services successful.")
                    connected = True
                    yield
        except (
            ClientError,
            ConnectTimeoutError,
            ReadTimeoutError,
            ConnectionClosedError,
            EndpointConnectionError,
            asyncio.TimeoutError,
        ) as e:
            logger.warning(
                f"API could not connect to AWS services: {type(e).__name__}. Retrying in 3 seconds..."
            )
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"API unexpected error during startup: {e}", exc_info=True)
            raise

    # Cleanup
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
    lat: Annotated[Latitude | None, Query()] = None,
    lon: Annotated[Longitude | None, Query()] = None,
    resolution: Annotated[int | None, Query(ge=0, le=15)] = None,
) -> Dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.default_congestion_window
    )

    filter_hex = h3_hex
    if lat and lon:
        if h3_hex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot specify both h3_hex and lat/lon",
            )
        else:
            end_resolution = (
                resolution if resolution is not None else settings.default_h3_resolution
            )
            filter_hex = coords_to_hex(lat, lon, end_resolution)
    elif lat is not None or lon is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify both lat and lon",
        )

    recent_pings = await query_recent_pings(
        dynamodb_client, dynamodb_table_name, cutoff=cutoff, h3_hex=filter_hex
    )

    if resolution is not None:
        congestion_counts = calculate_group_congestion(recent_pings, resolution)
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
        device_counts = calculate_device_congestion(recent_pings)

        congestion_data = [
            {"h3_hex": h3_hex, "device_count": device_count}
            for h3_hex, device_count in device_counts.items()
        ]

    return {"congestion": congestion_data}
