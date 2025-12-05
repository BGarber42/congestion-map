from typing import Any, Dict, Literal, Optional, Union, overload
from datetime import datetime, timezone

from h3 import latlng_to_cell  # type: ignore

from app.settings import settings
from app.models import PingPayload

# H3 Utility Functions


def coords_to_hex(
    lat: float, lon: float, resolution: int = settings.default_h3_resolution
) -> Any:
    return latlng_to_cell(lat, lon, resolution)


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
