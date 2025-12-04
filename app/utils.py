from typing import Any, Dict, Optional

from app.models import PingPayload


def get_mock_ping_request(
    overrides: Optional[Dict[str, Any]] = None, return_instance: bool = True
) -> PingPayload:
    ping_data = {
        "device_id": "abc123",
        "timestamp": "2025-01-01T12:34:56Z",
        "lat": 40.743,
        "lon": -73.989,
    }

    if overrides:
        ping_data.update(overrides)

    if return_instance:
        return PingPayload(**ping_data)
    else:
        return ping_data
