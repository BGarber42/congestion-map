from datetime import datetime, timezone

from pydantic_extra_types.coordinate import Latitude, Longitude

from app.congestion import calculate_device_congestion
from app.models import PingRecord


def test_calculate_congestion() -> None:
    """Should calculate the congestion for a given h3_hex."""
    now = datetime.now(timezone.utc)

    # Two devices, one hex, first device has two pings.
    # One device second hex, one ping.
    pings = [
        PingRecord(
            h3_hex="8a0106375dfffff",
            device_id="device_1",
            ts=now,
            lat=Latitude(0),
            lon=Longitude(0),
            accepted_at=now,
            processed_at=now,
        ),
        PingRecord(
            h3_hex="8a0106375dfffff",
            device_id="device_1",
            ts=now,
            lat=Latitude(0),
            lon=Longitude(0),
            accepted_at=now,
            processed_at=now,
        ),
        PingRecord(
            h3_hex="8a0106375dfffff",
            device_id="device_2",
            ts=now,
            lat=Latitude(0),
            lon=Longitude(0),
            accepted_at=now,
            processed_at=now,
        ),
        PingRecord(
            h3_hex="8a01063759fffff",
            device_id="device_3",
            ts=now,
            lat=Latitude(0),
            lon=Longitude(0),
            accepted_at=now,
            processed_at=now,
        ),
    ]

    congestion = calculate_device_congestion(pings)

    expected_congestion = {
        "8a0106375dfffff": 2,
        "8a01063759fffff": 1,
    }

    assert congestion == expected_congestion
