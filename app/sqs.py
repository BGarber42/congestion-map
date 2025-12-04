from typing import List, Union
import json

from types_aiobotocore_sqs.client import SQSClient

from app.models import PingPayload
from app.settings import settings


async def send_ping_to_queue(
    sqs_client: SQSClient, sqs_queue_url: str, ping: PingPayload
) -> None:
    message_body = ping.model_dump_json()

    response = await sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=message_body,
    )

    return response["MessageId"]


async def get_pings_from_queue(
    sqs_client: SQSClient, sqs_queue_url: str
) -> Union[List[PingPayload], None]:
    response = await sqs_client.receive_message(
        QueueUrl=sqs_queue_url,
        MaxNumberOfMessages=settings.max_pings,
        WaitTimeSeconds=settings.wait_time_seconds,
    )

    messages = response.get("Messages", [])
    pings = []
    for message in messages:
        message_body = message["Body"]
        ping_data = json.loads(message_body)
        ping = PingPayload(**ping_data)

        await sqs_client.delete_message(
            QueueUrl=sqs_queue_url,
            ReceiptHandle=message["ReceiptHandle"],
        )

        pings.append(ping)

    return pings
