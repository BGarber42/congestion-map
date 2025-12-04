from typing import Any, Dict

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root() -> Dict[str, Any]:
    return {"status": "ok"}
