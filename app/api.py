from typing import Any, Dict

from fastapi import FastAPI, status

from app.models import PingPayload

app = FastAPI()


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/ping", status_code=status.HTTP_202_ACCEPTED)
async def ping(ping_payload: PingPayload) -> Dict[str, Any]:
    return {"status": "accepted"}
