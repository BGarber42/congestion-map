from datetime import datetime

import pytest
from pydantic import ValidationError

from app.utils import get_mock_ping_request


class TestPingPayload:
    def test_valid_payload(self) -> None:
        ping = get_mock_ping_request()
        assert ping.device_id == "abc123"
        assert isinstance(ping.timestamp, datetime)
        assert ping.lat == 40.743
        assert ping.lon == -73.989

    def test_invalid_coordinates(self) -> None:
        with pytest.raises(ValidationError):
            get_mock_ping_request({"lat": 91, "lon": -73.989})

        with pytest.raises(ValidationError):
            get_mock_ping_request({"lat": 40.743, "lon": 181})

    def test_missing_device_id(self) -> None:
        with pytest.raises(ValidationError):
            get_mock_ping_request({"device_id": ""})

    def test_missing_timestamp(self) -> None:
        with pytest.raises(ValidationError):
            get_mock_ping_request({"timestamp": None})

    def test_not_a_timestamp(self) -> None:
        with pytest.raises(ValidationError):
            get_mock_ping_request({"timestamp": "not a timestamp"})
