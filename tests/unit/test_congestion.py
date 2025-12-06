from datetime import datetime, timezone

import h3  # type: ignore

from app.congestion import calculate_device_congestion, calculate_group_congestion
from tests.helpers import make_ping_record


def test_calculate_congestion() -> None:
    """Should calculate the congestion for a given h3_hex."""

    pings = [
        # Two devices, one hex, first device has two pings.
        make_ping_record({"h3_hex": "8a0106375dfffff", "device_id": "device_1"}),
        make_ping_record({"h3_hex": "8a0106375dfffff", "device_id": "device_1"}),
        make_ping_record({"h3_hex": "8a0106375dfffff", "device_id": "device_2"}),
        # One device second hex, one ping.
        make_ping_record({"h3_hex": "8a01063759fffff", "device_id": "device_3"}),
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
        make_ping_record({"device_id": "device1", "h3_hex": first_child}),
        make_ping_record({"device_id": "device2", "h3_hex": first_child}),
        make_ping_record({"device_id": "device2", "h3_hex": last_child}),
        make_ping_record({"device_id": "device3", "h3_hex": last_child}),
    ]

    group_congestion = calculate_group_congestion(pings, resolution=11)

    assert len(group_congestion) == 1
    assert top_hex in group_congestion

    result = group_congestion[top_hex]

    assert result["device_count"] == 3
    assert result["active_hex_count"] == 2
    assert result["total_hex_count"] == 7
