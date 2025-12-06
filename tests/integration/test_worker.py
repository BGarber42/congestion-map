from datetime import datetime, timedelta, timezone

from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.sqs import send_ping_to_queue
from app.worker import process_ping_from_queue
from tests.helpers import get_mock_ping_request


class TestWorker:
    async def test_end_to_end_workflow(
        self,
        sqs_client: SQSClient,
        sqs_queue_url: str,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        """Test the complete workflow"""
        # Create a ping
        ping = get_mock_ping_request()
        ping.accepted_at = datetime.now(timezone.utc)

        # Send it to the queue
        await send_ping_to_queue(sqs_client, sqs_queue_url, ping)

        # Process the ping (It handles validation, conversion, and storage)
        processed = await process_ping_from_queue(
            sqs_client, sqs_queue_url, dynamodb_client, dynamodb_table_name
        )

        # We should have one ping back
        assert len(processed) == 1
        assert processed[0].device_id == ping.device_id
        assert processed[0].ts == ping.timestamp
        assert processed[0].lat == ping.lat
        assert processed[0].lon == ping.lon

    async def test_worker_rejects_bad_ping(
        self,
        sqs_client: SQSClient,
        sqs_queue_url: str,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_name: str,
    ) -> None:
        """Test the worker rejects a bad ping"""
        # Create a ping with a timestamp in the past
        ping = get_mock_ping_request(
            {"timestamp": datetime.now(timezone.utc) - timedelta(days=1)}
        )
        ping.accepted_at = datetime.now(timezone.utc)

        # Send it to the queue
        await send_ping_to_queue(sqs_client, sqs_queue_url, ping)

        # Process the ping (it should reject it and not return anything)
        processed = await process_ping_from_queue(
            sqs_client, sqs_queue_url, dynamodb_client, dynamodb_table_name
        )

        assert len(processed) == 0
