import asyncio
import logging
from typing import cast

from botocore.exceptions import ClientError
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.aws_clients import AWSClientManager
from app.dynamodb import create_table_if_not_exists
from app.settings import settings
from app.worker import process_ping_from_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting worker")

    async with AWSClientManager(service_names=["sqs", "dynamodb"]) as aws_clients:
        sqs_client = cast(SQSClient, aws_clients.clients["sqs"])
        dynamodb_client = cast(DynamoDBClient, aws_clients.clients["dynamodb"])

        try:
            response = await sqs_client.get_queue_url(QueueName=settings.sqs_queue_name)
            sqs_queue_url = response["QueueUrl"]
            logger.info(f"Queue {settings.sqs_queue_name} found.")
        except ClientError as e:
            if e.response["Error"]["Code"] == "QueueDoesNotExist":
                logger.info(
                    f"Queue {settings.sqs_queue_name} does not exist, creating it"
                )
                response = await sqs_client.create_queue(
                    QueueName=settings.sqs_queue_name
                )
                sqs_queue_url = response["QueueUrl"]
            else:
                raise

        await create_table_if_not_exists(dynamodb_client, settings.dynamodb_table_name)

        logger.info("Worker ready to process pings")
        while True:
            try:
                pings = await process_ping_from_queue(
                    sqs_client,
                    sqs_queue_url,
                    dynamodb_client,
                    settings.dynamodb_table_name,
                )
                if pings:
                    logger.info(f"Processed {len(pings)} pings")
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error during ping processing: {e}", exc_info=True)
                await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception in worker: {e}", exc_info=True)
        raise
