from typing import List, Union
import json
import logging

from types_aiobotocore_sqs.client import SQSClient
from botocore.exceptions import ClientError

from app.models import PingPayload
from app.settings import settings
from app.utils import coords_to_hex

logger = logging.getLogger(__name__)


async def send_ping_to_queue(
    sqs_client: SQSClient, sqs_queue_url: str, ping: PingPayload
) -> str:
    try:
        message_body = ping.model_dump_json()

        response = await sqs_client.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=message_body,
        )

        message_id = response["MessageId"]
        logger.debug(f"Successfully sent ping to queue: {message_id}")
        return message_id
    except ClientError as e:
        # Doc Ref https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
        # Doc Ref https://docs.python.org/3/library/exceptions.html
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(f"Error Sending Message: {error_code} - {error_message}")
        raise RuntimeError(
            f"Error Sending Message: {error_code} - {error_message}"
        ) from e
    except Exception as e:
        logger.error(f"Unknown error: {e}")
        raise RuntimeError(f"Unknown error: {e}") from e


async def get_pings_from_queue(
    sqs_client: SQSClient, sqs_queue_url: str
) -> List[PingPayload]:
    try:
        response = await sqs_client.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=settings.max_pings,
            WaitTimeSeconds=settings.wait_time_seconds,
        )

        messages = response.get("Messages", [])
        pings = []
        for message in messages:
            try:
                message_body = message["Body"]
                ping_data = json.loads(message_body)
                ping = PingPayload(**ping_data)

                await sqs_client.delete_message(
                    QueueUrl=sqs_queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )

                pings.append(ping)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding message: {e}")
                continue
            except Exception as e:
                logger.error(f"Unknown error: {e}")
                continue
    except ClientError as e:
        # Doc Ref https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
        # Doc Ref https://docs.python.org/3/library/exceptions.html
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(f"Error Receiving Messages: {error_code} - {error_message}")
        raise RuntimeError(
            f"Error Receiving Messages: {error_code} - {error_message}"
        ) from e
    except Exception as e:
        logger.error(f"Unknown error: {e}")
        raise RuntimeError(f"Unknown error: {e}") from e

    return pings
