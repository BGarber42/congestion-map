from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Latitude, Longitude


class PingPayload(BaseModel):
    device_id: Annotated[str, Field(min_length=1)]
    timestamp: datetime
    lat: Latitude
    lon: Longitude

    ...
