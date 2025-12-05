import asyncio
import logging

import aioboto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    ReadTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
)

from app.worker import process_ping_from_queue
from app.settings import settings
from app.dynamodb import create_table_if_not_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting worker")

    connected = False
    while not connected:
        try:
            logger.info("Worker attempting to connect to AWS services...")
            session = aioboto3.Session()
            async with session.client(
                "sqs",
                endpoint_url=settings.sqs_endpoint_url,
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id or "x",
                aws_secret_access_key=settings.aws_secret_access_key or "x",
                config=Config(
                    connect_timeout=2, read_timeout=25, retries={"max_attempts": 0}
                ),
            ) as sqs_client:
                try:
                    response = await sqs_client.get_queue_url(
                        QueueName=settings.sqs_queue_name
                    )
                    sqs_queue_url = response["QueueUrl"]
                    logger.info(f"Queue {settings.sqs_queue_name} found.")
                except sqs_client.exceptions.QueueDoesNotExist:
                    logger.info(
                        f"Queue {settings.sqs_queue_name} does not exist, creating it"
                    )
                    response = await sqs_client.create_queue(
                        QueueName=settings.sqs_queue_name
                    )
                    sqs_queue_url = response["QueueUrl"]

                async with session.client(
                    "dynamodb",
                    endpoint_url=settings.dynamodb_endpoint_url,
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id or "x",
                    aws_secret_access_key=settings.aws_secret_access_key or "x",
                    config=Config(
                        connect_timeout=2, read_timeout=25, retries={"max_attempts": 0}
                    ),
                ) as dynamodb_client:
                    await create_table_if_not_exists(
                        dynamodb_client, settings.dynamodb_table_name
                    )
                    logger.info("Worker connection to AWS services successful.")
                    connected = True

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
                                # Short sleep to prevent busy-waiting when queue is empty
                                await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(
                                f"Error during ping processing: {e}", exc_info=True
                            )
                            await asyncio.sleep(1)
        except (
            ClientError,
            ConnectTimeoutError,
            ReadTimeoutError,
            ConnectionClosedError,
            EndpointConnectionError,
            asyncio.TimeoutError,
        ) as e:
            logger.warning(
                f"Worker could not connect to AWS services: {type(e).__name__}. Retrying in 3 seconds..."
            )
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Worker unexpected error during startup: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception in worker: {e}", exc_info=True)
        raise
