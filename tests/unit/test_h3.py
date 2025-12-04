from h3 import latlng_to_cell


class TestH3:
    def test_coords_to_hex(self) -> None:
        lat = 40.743
        lon = -73.989
        expected_hex = latlng_to_cell(lat, lon, 12)

        assert isinstance(expected_hex, str)
        assert len(expected_hex) >= 1
        assert expected_hex.startswith("8")
        assert expected_hex == "8c2a100d2189bff"

    def test_not_same(self) -> None:
        lat1, lon1 = 40.743, -73.989  # New York
        lat2, lon2 = 37.7749, -122.4194  # San Francisco

        hex1 = latlng_to_cell(lat1, lon1, 12)
        hex2 = latlng_to_cell(lat2, lon2, 12)

        assert hex1 != hex2
