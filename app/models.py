from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_serializer
from pydantic_extra_types.coordinate import Latitude, Longitude

# Doc Ref: https://docs.pydantic.dev/latest/concepts/types/
# Doc Ref: https://docs.pydantic.dev/latest/concepts/serialization/


class PingPayload(BaseModel):
    device_id: Annotated[str, Field(min_length=1)]
    timestamp: datetime
    lat: Latitude
    lon: Longitude

    # Workaround for datetime not always being automatically serialized
    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.isoformat()

    ...
