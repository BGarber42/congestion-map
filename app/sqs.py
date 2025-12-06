import json
import logging
from typing import List

from botocore.exceptions import ClientError
from types_aiobotocore_sqs.client import SQSClient

from app.models import PingPayload
from app.settings import settings

logger = logging.getLogger(__name__)


# Helper that takes in a ping and sends it to the queue
async def send_ping_to_queue(
    sqs_client: SQSClient, sqs_queue_url: str, ping: PingPayload
) -> str:
    try:
        # Convert the ping to a JSON string, it's already been validated by Pydantic.
        message_body = ping.model_dump_json()

        # Send the message to the queue
        response = await sqs_client.send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=message_body,
        )

        # Get the message id from the response
        message_id = response["MessageId"]
        # Log the success
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
