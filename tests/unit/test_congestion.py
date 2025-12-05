from datetime import datetime, timezone

import h3  # type: ignore
from pydantic_extra_types.coordinate import Latitude, Longitude

from app.congestion import calculate_device_congestion, calculate_group_congestion
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


def test_calculate_parent_grid_congestion() -> None:
    top_hex = "8b2a1072d0d5fff"

    children = h3.cell_to_children(top_hex, 12)
    first_child = children[0]
    last_child = children[-1]

    now = datetime.now(timezone.utc)
    pings = [
        PingRecord(
            device_id="device1",
            h3_hex=first_child,
            ts=now,
            accepted_at=now,
            processed_at=now,
            lat=Latitude(0),
            lon=Longitude(0),
        ),
        PingRecord(
            device_id="device2",
            h3_hex=first_child,
            ts=now,
            accepted_at=now,
            processed_at=now,
            lat=Latitude(0),
            lon=Longitude(0),
        ),
        PingRecord(
            device_id="device2",
            h3_hex=last_child,
            ts=now,
            accepted_at=now,
            processed_at=now,
            lat=Latitude(0),
            lon=Longitude(0),
        ),
        PingRecord(
            device_id="device3",
            h3_hex=last_child,
            ts=now,
            accepted_at=now,
            processed_at=now,
            lat=Latitude(0),
            lon=Longitude(0),
        ),
    ]

    group_congestion = calculate_group_congestion(pings, resolution=11)

    assert len(group_congestion) == 1
    assert top_hex in group_congestion

    result = group_congestion[top_hex]

    assert result["device_count"] == 3
    assert result["active_hex_count"] == 2
    assert result["total_hex_count"] == 7
