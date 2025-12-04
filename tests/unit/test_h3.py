import pytest

from app.utils import coords_to_hex


class TestH3:
    def test_coords_to_hex(self) -> None:
        expected_hex = coords_to_hex(lat=40.743, lon=-73.989)

        assert isinstance(expected_hex, str)
        assert len(expected_hex) >= 1
        assert expected_hex.startswith("8")
        assert expected_hex == "8c2a100d2189bff"

    def test_not_same(self) -> None:
        lat1, lon1 = 40.743, -73.989  # New York
        lat2, lon2 = 37.7749, -122.4194  # San Francisco

        hex1 = coords_to_hex(lat=lat1, lon=lon1)
        hex2 = coords_to_hex(lat=lat2, lon=lon2)

        assert hex1 != hex2

    def test_same_coordinate_wrap(self) -> None:
        # TIL: H3 wraps coordinates around the world
        hex1 = coords_to_hex(lat=10, lon=10)
        hex2 = coords_to_hex(lat=370, lon=10)

        assert hex1 == hex2
