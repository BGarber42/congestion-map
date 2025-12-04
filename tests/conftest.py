from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport
import aioboto3  # type: ignore
from botocore.config import Config
from mypy_boto3_sqs.client import SQSClient

from app.settings import settings
from app.api import app


@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client


@pytest.fixture(scope="session")
def sqs_endpoint_url() -> str:
    if settings.sqs_endpoint_url is None:
        raise ValueError("SQS endpoint URL is not set")
    return settings.sqs_endpoint_url


@pytest.fixture(scope="session")
async def sqs_client(sqs_endpoint_url: str) -> AsyncGenerator[SQSClient, None]:
    session = aioboto3.Session()
    async with session.client(
        "sqs",
        endpoint_url=sqs_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(retries={"max_attempts": 0}),
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def sqs_queue_url(
    sqs_client: SQSClient, sqs_endpoint_url: str
) -> AsyncGenerator[str, None]:
    queue_name = f"{settings.sqs_queue_name}-test"
    response = await sqs_client.create_queue(QueueName=queue_name)
    queue_url = response["QueueUrl"]

    yield queue_url

    await sqs_client.delete_queue(QueueUrl=queue_url)
