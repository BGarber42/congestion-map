import pytest
from types_aiobotocore_sqs.client import SQSClient

from app.utils import get_mock_ping_request
from app.sqs import send_ping_to_queue, get_pings_from_queue


class TestSQS:
    @pytest.mark.asyncio
    async def test_send_message(
        self, sqs_client: SQSClient, sqs_queue_url: str
    ) -> None:
        ping = get_mock_ping_request()

        message_id = await send_ping_to_queue(sqs_client, sqs_queue_url, ping)

        assert message_id is not None

        received_pings = await get_pings_from_queue(sqs_client, sqs_queue_url)

        assert len(received_pings) > 0
        received_ping = received_pings[0]

        assert received_ping is not None
        assert received_ping.device_id == ping.device_id
        assert received_ping.timestamp== ping.timestamp
        assert received_ping.lat == ping.lat
        assert received_ping.lon == ping.lon
