from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Set

import h3  # type: ignore

from app.models import PingRecord


def calculate_device_congestion(pings: List[PingRecord]) -> Dict[str, int]:
    """Get device counts from pings in a given h3_hex"""
    # Make the dict a set for device uniqueness
    hex_to_device_count: DefaultDict[str, Set[str]] = defaultdict(set)

    # Add the device id to the set for each ping.
    for ping in pings:
        hex_to_device_count[ping.h3_hex].add(ping.device_id)

    # Return the number of devices for each hex.
    device_counts = {
        h3_hex: len(devices) for h3_hex, devices in hex_to_device_count.items()
    }

    return device_counts


def calculate_group_congestion(
    pings: List[PingRecord], resolution: int
) -> Dict[str, Dict[str, Any]]:
    """Aggregate congestion data for a given resolution"""

    # Make our dict two sets of devices and child hexes for deuplication
    parent_data: DefaultDict[str, Dict[str, Any]] = defaultdict(
        lambda: {"devices": set(), "child_hexes": set()}
    )

    if not pings:
        return {}

    # Get the resolution of the first ping, all should be the same.
    source_resolution = h3.get_resolution(pings[0].h3_hex)

    # Iterate over the pings and add it to the dict of the parent hex.
    for ping in pings:
        parent_hex = h3.cell_to_parent(ping.h3_hex, resolution)
        parent_data[parent_hex]["devices"].add(ping.device_id)
        parent_data[parent_hex]["child_hexes"].add(ping.h3_hex)

    results = {}

    # Loop over the parents
    for parent_hex, parent_info in parent_data.items():
        total_hex_count = h3.cell_to_children_size(parent_hex, source_resolution)

        # Add the parent hex to the results.
        results[parent_hex] = {
            "device_count": len(parent_info["devices"]),
            "active_hex_count": len(parent_info["child_hexes"]),
            "total_hex_count": total_hex_count,
        }

    return results
