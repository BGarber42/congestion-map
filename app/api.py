from typing import Any, Dict

from fastapi import FastAPI, status

app = FastAPI()


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/ping", status_code=status.HTTP_202_ACCEPTED)
async def ping(ping_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "accepted"}
