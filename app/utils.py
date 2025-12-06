from typing import Any, Dict, Optional
from datetime import datetime, timezone

from h3 import latlng_to_cell  # type: ignore

from app.settings import settings


# H3 Utility Functions


def coords_to_hex(
    lat: float, lon: float, resolution: int = settings.default_h3_resolution
) -> Any:
    return latlng_to_cell(lat, lon, resolution)
