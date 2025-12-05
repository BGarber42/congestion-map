from collections import defaultdict
from typing import Dict, List

from app.models import PingRecord


def calculate_device_congestion(pings: List[PingRecord]) -> Dict[str, int]:
    """Get device counts by h3 hex."""
    hex_to_device_count = defaultdict(set)

    for ping in pings:
        hex_to_device_count[ping.h3_hex].add(ping.device_id)

    device_counts = {
        h3_hex: len(devices) for h3_hex, devices in hex_to_device_count.items()
    }

    return device_counts
