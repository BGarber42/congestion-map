import asyncio
import logging
from typing import cast

from botocore.exceptions import ClientError
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.aws_clients import AWSClientManager, retry_aws
from app.dynamodb import create_table_if_not_exists
from app.settings import settings
from app.sqs import get_or_create_queue
from app.worker import process_ping_from_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting worker")

    async with AWSClientManager(service_names=["sqs", "dynamodb"]) as aws_clients:
        sqs_client = cast(SQSClient, aws_clients.clients["sqs"])
        dynamodb_client = cast(DynamoDBClient, aws_clients.clients["dynamodb"])

        async def get_queue() -> str:
            return await get_or_create_queue(sqs_client, settings.sqs_queue_name)

        sqs_queue_url = await retry_aws(get_queue)

        async def create_table() -> None:
            return await create_table_if_not_exists(
                dynamodb_client, settings.dynamodb_table_name
            )

        await retry_aws(create_table)

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
