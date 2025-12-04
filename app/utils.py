from typing import Any, Dict, Literal, Optional, overload

from app.models import PingPayload


# Type Hinting
# Doc Ref: https://docs.python.org/3/library/typing.html#typing.overload
# Doc Ref: https://mypy.readthedocs.io/en/stable/more_types.html
@overload
def get_mock_ping_request(
    overrides: Optional[Dict[str, Any]] = None, return_instance: Literal[True] = True
) -> PingPayload: ...


@overload
def get_mock_ping_request(
    overrides: Optional[Dict[str, Any]] = None, return_instance: Literal[False] = ...
) -> Dict[str, Any]: ...


def get_mock_ping_request(
    overrides: Optional[Dict[str, Any]] = None, return_instance: bool = True
) -> PingPayload:
    ping_data: Dict[str, Any] = {
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
