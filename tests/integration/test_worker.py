from datetime import datetime, timezone, timedelta

import pytest
from types_aiobotocore_sqs.client import SQSClient
from types_aiobotocore_dynamodb.client import DynamoDBClient

from app.utils import get_mock_ping_request
from app.sqs import send_ping_to_queue
from app.worker import process_ping_from_queue


class TestWorker:
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(
        self,
        sqs_client: SQSClient,
        sqs_queue_url: str,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        ping = get_mock_ping_request()
        ping.accepted_at = datetime.now(timezone.utc)

        await send_ping_to_queue(sqs_client, sqs_queue_url, ping)

        processed = await process_ping_from_queue(
            sqs_client, sqs_queue_url, dynamodb_client, dynamodb_table_name
        )

        assert len(processed) == 1
        assert processed[0].device_id == ping.device_id
        assert processed[0].timestamp == ping.timestamp
        assert processed[0].lat == ping.lat
        assert processed[0].lon == ping.lon

    @pytest.mark.asyncio
    async def test_worker_rejects_bad_ping(
        self,
        sqs_client: SQSClient,
        sqs_queue_url: str,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        ping = get_mock_ping_request(
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=1)}
        )
        ping.accepted_at = datetime.now(timezone.utc)

        await send_ping_to_queue(sqs_client, sqs_queue_url, ping)

        processed = await process_ping_from_queue(
            sqs_client, sqs_queue_url, dynamodb_client, dynamodb_table_name
        )

        assert len(processed) == 0
