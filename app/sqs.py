async def send_ping_to_queue(
    sqs_client: SQSClient, sqs_queue_url: str, ping: PingPayload
) -> None:
    pass


async def get_ping_from_queue(
    sqs_client: SQSClient, sqs_queue_url: str
) -> List[PingPayload]:
    pass
