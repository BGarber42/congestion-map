from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional, Union, overload

from pydantic_extra_types.coordinate import Latitude, Longitude

from app.models import PingPayload, PingRecord

# PingPayload Utility Functions


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
) -> Union[PingPayload, Dict[str, Any]]:
    """Helper to get a sample PingPayload (optionally as a dict)"""
    ping_data: Dict[str, Any] = {
        "device_id": "abc123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lat": 40.743,
        "lon": -73.989,
    }

    if overrides:
        ping_data.update(overrides)

    if return_instance:
        return PingPayload(**ping_data)
    else:
        return ping_data


def make_ping_record(overrides: Optional[Dict[str, Any]] = None) -> PingRecord:
    """Helper function to create a PingRecord instance for tests.
    
    Use for testing the data model. Use `get_mock_ping_request` for testing the API.
    """
    now = datetime.now(timezone.utc)
    record_data: Dict[str, Any] = {
        "h3_hex": "8a0106375dfffff",
        "device_id": "device_default",
        "ts": now,
        "lat": Latitude(0),
        "lon": Longitude(0),
        "accepted_at": now,
        "processed_at": now,
    }
    if overrides:
        record_data.update(overrides)
    return PingRecord(**record_data)
