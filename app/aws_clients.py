import asyncio
from contextlib import AsyncExitStack
import logging
from types import TracebackType
from typing import Optional, Self, Type

import aioboto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    ReadTimeoutError,
)
from types_aiobotocore_dynamodb.client import DynamoDBClient
from types_aiobotocore_sqs.client import SQSClient

from app.settings import settings

logger = logging.getLogger(__name__)

# Doc Ref: https://aioboto3.readthedocs.io/en/latest/usage.html#clients
# Doc Ref: https://docs.python.org/3/library/contextlib.html#async-context-managers-and-asyncexitstack


class AWSClientManager:
    """
    Manages AWS clients for the application.
    """

    def __init__(self, service_names: list[str]):
        self._service_names = service_names
        self.clients: dict[str, SQSClient | DynamoDBClient] = {}
        self._exit_stack = AsyncExitStack()
        self._session = aioboto3.Session()

    # __aenter__ is called when we `with` the context manager.
    async def __aenter__(self) -> Self:
        logger.info("Creating AWS clients...")

        for service_name in self._service_names:
            # Create a client for the service and add it to the exit stack.
            client = await self._exit_stack.enter_async_context(
                self._session.client(  # type: ignore[call-overload]
                    service_name,
                    endpoint_url=getattr(settings, f"{service_name}_endpoint_url"),
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    config=Config(
                        connect_timeout=2,
                        read_timeout=25,
                        retries={"max_attempts": 0},
                    ),
                )
            )
            # Add the client to the clients dictionary.
            self.clients[service_name] = client
        # Log that we connected to the services.
        logger.info("AWS Clients created successfully.")
        return self

    # __aexit__ is called when we exit the context manager.
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.shutdown()

    async def shutdown(self) -> None:
        """Clean up all managed clients."""
        self.clients.clear()
        await self._exit_stack.aclose()
