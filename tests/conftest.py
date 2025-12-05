from typing import AsyncGenerator, cast

import pytest
from httpx import AsyncClient, ASGITransport
import aioboto3
from botocore.config import Config
from types_aiobotocore_sqs.client import SQSClient
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.settings import settings
from app.api import app, get_sqs_client, get_sqs_queue_url


@pytest.fixture
def sqs_endpoint_url() -> str:
    if settings.sqs_endpoint_url is None:
        raise ValueError("SQS endpoint URL is not set")
    return settings.sqs_endpoint_url


@pytest.fixture
async def sqs_client(sqs_endpoint_url: str) -> AsyncGenerator[SQSClient, None]:
    session = aioboto3.Session()
    async with session.client(  # type: ignore[call-overload]
        "sqs",
        endpoint_url=sqs_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or "x",
        aws_secret_access_key=settings.aws_secret_access_key or "x",
        config=Config(retries={"max_attempts": 0}),
    ) as client:
        yield cast(SQSClient, client)


@pytest.fixture
async def sqs_queue_url(
    sqs_client: SQSClient, sqs_endpoint_url: str
) -> AsyncGenerator[str, None]:
    queue_name = f"{settings.sqs_queue_name}-test"
    response = await sqs_client.create_queue(QueueName=queue_name)
    queue_url = response["QueueUrl"]

    yield queue_url

    await sqs_client.delete_queue(QueueUrl=queue_url)


@pytest.fixture
async def dynamodb_endpoint_url() -> str:
    if settings.dynamodb_endpoint_url is None:
        raise ValueError("DynamoDB endpoint URL is not set")
    return settings.dynamodb_endpoint_url


@pytest.fixture
async def dynamodb_client(
    dynamodb_endpoint_url: str,
) -> AsyncGenerator[DynamoDBClient, None]:
    session = aioboto3.Session()
    async with session.client(  # type: ignore[call-overload]
        "dynamodb",
        endpoint_url=dynamodb_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or "x",
        aws_secret_access_key=settings.aws_secret_access_key or "x",
        config=Config(retries={"max_attempts": 0}),
    ) as client:
        yield cast(DynamoDBClient, client)


@pytest.fixture
async def dynamodb_table_name(
    dynamodb_client: DynamoDBClient, dynamodb_endpoint_url: str
) -> AsyncGenerator[str, None]:
    table_name = f"{settings.dynamodb_table_name}-test"
    await dynamodb_client.create_table(
        TableName=table_name,
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
    await dynamodb_client.get_waiter("table_exists").wait(TableName=table_name)

    yield table_name

    await dynamodb_client.delete_table(TableName=table_name)


# Doc Ref: https://fastapi.tiangolo.com/advanced/testing-dependencies/
@pytest.fixture
async def async_client(
    sqs_client: SQSClient, sqs_queue_url: str
) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_sqs_client] = lambda: sqs_client
    app.dependency_overrides[get_sqs_queue_url] = lambda: sqs_queue_url

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
