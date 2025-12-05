from typing import Any, Dict, AsyncGenerator, Annotated
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from fastapi import FastAPI, status, Depends, HTTPException
from types_aiobotocore_sqs.client import SQSClient
import aioboto3
from botocore.config import Config

from app.models import PingPayload
from app.sqs import send_ping_to_queue
from app.settings import settings

## Housekeeping dependencies
sqs_client: SQSClient | None = None
sqs_queue_url: str | None = None

logger = logging.getLogger(__name__)


async def get_sqs_client() -> SQSClient:
    if sqs_client is None:
        raise RuntimeError("SQS client not initialized")
    return sqs_client


async def get_sqs_queue_url() -> str:
    if sqs_queue_url is None:
        raise RuntimeError("SQS queue URL not initialized")
    return sqs_queue_url


# Doc Ref: https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global sqs_client, sqs_queue_url

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

        yield

    sqs_client = None
    sqs_queue_url = None


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
